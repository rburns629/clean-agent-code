"""Run multi-turn agent sessions with a simulated user.

Usage: EVAL_ENV_FILE=key.env EVAL_BUDGET_USD=8 python3 -I evaluations/harness/prompting/run.py <eval_root> [limit]

Each run starts a Claude Code session in the evaluation image with the run's prompt,
then alternates: a simulated user (a separate model that knows the hidden spec)
reviews the agent's reply and the current diff and answers with a labeled DONE,
ANSWER, or CORRECTION; the agent session is resumed with that message. Labels are
the ground truth for validating signal extraction. Git commands on agent-modified
repositories run inside the no-network container, never on the host.
"""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

EVAL = Path(sys.argv[1]).resolve()
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else None
RUNS = EVAL / "runs"
IMAGE = os.environ.get("EVAL_IMAGE", "clean-code-eval:2.1.289")
MODEL = os.environ.get("EVAL_MODEL", "claude-opus-5-5")
USER_MODEL = os.environ.get("EVAL_USER_MODEL", "claude-opus-5-5")
BUDGET = float(os.environ.get("EVAL_BUDGET_USD", "8"))
TURN_BUDGET = os.environ.get("EVAL_TURN_BUDGET_USD", "1.00")
MAX_FOLLOWUPS = int(os.environ.get("EVAL_MAX_FOLLOWUPS", "3"))
ENV_FILE = os.environ.get("EVAL_ENV_FILE")
KEY_ARGS = ["--env-file", ENV_FILE] if ENV_FILE else ["-e", "ANTHROPIC_API_KEY"]
LIMITS = ["--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "256",
          "--memory", "2g", "--cpus", "2"]

USER_PROMPT = """You are role-playing a software developer who asked an AI coding agent to make a change in your repository. Behave like a busy, competent developer.

What you actually want (the agent has not necessarily been told all of this):
{spec}

The conversation so far:
{conversation}

The current change in the repository, as a diff against the original:
{diff}

Decide your next message. Reply with one line that starts with exactly one label:
DONE: the change fully meets what you want; nothing else is needed.
ANSWER: the agent asked you a question; answer briefly, revealing only what is needed.
CORRECTION: the change is wrong, incomplete, or not what you meant; say briefly what to change, as you would to a colleague.
Do not write code. Do not mention role-playing or that you have a written spec."""


def spent():
    total = 0.0
    for meta in RUNS.glob("*.meta.json"):
        data = json.loads(meta.read_text())
        total += sum(t.get("cost_usd", 0) for t in data["turns"])
    return total


def agent_turn(name, message, session, first, trace):
    run, home = RUNS / name, RUNS / f"{name}.home"
    session_args = ["--session-id", session] if first else ["--resume", session]
    proc = subprocess.run(
        ["docker", "run", "--rm", *KEY_ARGS, *LIMITS,
         "--mount", f"type=bind,src={run},dst=/work",
         "--mount", f"type=bind,src={home},dst=/home/node",
         IMAGE, "claude", "-p", message, *session_args, "--model", MODEL,
         "--output-format", "stream-json", "--verbose", "--max-turns", "40",
         "--max-budget-usd", TURN_BUDGET, "--allowedTools", "Bash,Read,Write,Edit,Glob,Grep"],
        capture_output=True, text=True, timeout=1200)
    final, cost = "", 0.0
    with trace.open("a") as out:
        out.write(json.dumps({"type": "harness_user_message", "text": message}) + "\n")
        for line in proc.stdout.splitlines():
            out.write(line + "\n")
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "result":
                final, cost = event.get("result", ""), event.get("total_cost_usd") or 0
    return final, cost, proc.returncode, proc.stderr[-500:]


def current_diff(name):
    script = ("cd /work && git -c safe.directory='*' -c core.fsmonitor= --no-pager diff "
              "--no-ext-diff --no-textconv HEAD -- . ':!*__pycache__*' && "
              "git -c safe.directory='*' ls-files --others --exclude-standard | grep -v __pycache__ | "
              "while read f; do echo \"--- new file: $f\"; head -c 8000 \"$f\"; done")
    proc = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "--mount", f"type=bind,src={RUNS / name},dst=/work,readonly", IMAGE, "sh", "-c", script],
        capture_output=True, text=True, timeout=120)
    return proc.stdout[:30000] or "(no changes)"


def simulated_user(spec, conversation, diff):
    prompt = USER_PROMPT.format(spec=spec, conversation=conversation, diff=diff)
    proc = subprocess.run(
        ["docker", "run", "--rm", "-i", *KEY_ARGS, "--cap-drop", "ALL", IMAGE,
         "claude", "-p", "--model", USER_MODEL, "--max-turns", "1", "--output-format", "json",
         "--max-budget-usd", "0.50",
         "--disallowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Task,NotebookEdit"],
        input=prompt, capture_output=True, text=True, timeout=300)
    try:
        result = json.loads(proc.stdout)
    except ValueError:
        return "ERROR", proc.stderr[-300:], 0.0
    text = (result.get("result") or "").strip()
    cost = result.get("total_cost_usd") or 0
    for label in ("DONE", "ANSWER", "CORRECTION"):
        if text.upper().startswith(label):
            return label, text[len(label):].lstrip(":- ").strip(), cost
    return "UNPARSED", text[:300], cost


def run_one(name):
    meta_path = RUNS / f"{name}.meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else None
    if meta and meta["status"] != "running":
        print(f"skip {name} ({meta['status']})")
        return
    meta = {"name": name, "session": str(uuid.uuid4()), "status": "running", "turns": []}
    trace = RUNS / f"{name}.trace.jsonl"
    trace.write_text("")
    spec = (RUNS / f"{name}.spec.txt").read_text().strip()
    message = (RUNS / f"{name}.prompt.txt").read_text().strip()
    conversation = []
    for turn in range(MAX_FOLLOWUPS + 1):
        if spent() >= BUDGET:
            meta["status"] = "budget"
            break
        final, cost, code, err = agent_turn(name, message, meta["session"], turn == 0, trace)
        conversation += [f"Developer: {message}", f"Agent: {final or '(no reply)'}"]
        meta["turns"].append({"role": "agent", "cost_usd": cost, "exit": code,
                              "error": err if code else None})
        meta_path.write_text(json.dumps(meta, indent=1))
        if code != 0 or not final:
            meta["status"] = "agent_error"
            break
        label, reply, ucost = simulated_user(spec, "\n\n".join(conversation), current_diff(name))
        meta["turns"].append({"role": "user", "label": label, "text": reply, "cost_usd": ucost})
        meta_path.write_text(json.dumps(meta, indent=1))
        if label == "DONE":
            meta["status"] = "done"
            break
        if label in ("ERROR", "UNPARSED"):
            meta["status"] = "user_error"
            break
        message = reply
    else:
        meta["status"] = "followups_exhausted"
    meta_path.write_text(json.dumps(meta, indent=1))
    labels = [t["label"] for t in meta["turns"] if t["role"] == "user"]
    print(f"{name}: {meta['status']} labels={labels} total spent ${spent():.2f}")


def main():
    plan = json.loads((EVAL / "plan.json").read_text())
    started = 0
    for entry in plan:
        meta = RUNS / f"{entry['name']}.meta.json"
        if meta.exists() and json.loads(meta.read_text())["status"] != "running":
            continue
        if LIMIT is not None and started >= LIMIT:
            break
        if spent() >= BUDGET:
            print(f"budget ${BUDGET:.2f} reached; stopping")
            break
        run_one(entry["name"])
        started += 1
    print(f"total recorded cost: ${spent():.2f}")


main()
