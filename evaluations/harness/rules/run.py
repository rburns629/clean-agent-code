"""Run scripted multi-turn agent sessions for the rules evaluation.

Usage: EVAL_ENV_FILE=key.env EVAL_BUDGET_USD=8 python3 -I evaluations/harness/rules/run.py <eval_root>

Each run starts a Claude Code session with its first message and resumes it with
each scripted follow-up. After every turn, whether the repository changed is
recorded; Git runs inside the no-network container, never on the host.
"""
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

EVAL = Path(sys.argv[1]).resolve()
RUNS = EVAL / "runs"
IMAGE = os.environ.get("EVAL_IMAGE", "clean-code-eval:2.1.289")
MODEL = os.environ.get("EVAL_MODEL", "claude-opus-5-5")
BUDGET = float(os.environ.get("EVAL_BUDGET_USD", "8"))
TURN_BUDGET = os.environ.get("EVAL_TURN_BUDGET_USD", "1.00")
ENV_FILE = os.environ.get("EVAL_ENV_FILE")
KEY_ARGS = ["--env-file", ENV_FILE] if ENV_FILE else ["-e", "ANTHROPIC_API_KEY"]
LIMITS = ["--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "256",
          "--memory", "2g", "--cpus", "2"]


def spent():
    return sum(t["cost_usd"] for m in RUNS.glob("*.meta.json")
               for t in json.loads(m.read_text())["turns"])


def agent_turn(name, message, session, first, trace):
    session_args = ["--session-id", session] if first else ["--resume", session]
    proc = subprocess.run(
        ["docker", "run", "--rm", *KEY_ARGS, *LIMITS,
         "--mount", f"type=bind,src={RUNS / name},dst=/work",
         "--mount", f"type=bind,src={RUNS / f'{name}.home'},dst=/home/node",
         IMAGE, "claude", "-p", message, *session_args, "--model", MODEL,
         "--output-format", "stream-json", "--verbose", "--max-turns", "60",
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


def changed(name):
    script = "cd /work && git -c safe.directory='*' status --porcelain --untracked-files=all"
    proc = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "--mount", f"type=bind,src={RUNS / name},dst=/work,readonly", IMAGE, "sh", "-c", script],
        capture_output=True, text=True, timeout=120)
    return any("__pycache__" not in line for line in proc.stdout.splitlines())


def run_one(entry):
    name = entry["name"]
    meta = {"name": name, "session": str(uuid.uuid4()), "status": "running", "turns": []}
    meta_path, trace = RUNS / f"{name}.meta.json", RUNS / f"{name}.trace.jsonl"
    trace.write_text("")
    for turn, message in enumerate(entry["messages"]):
        if spent() >= BUDGET:
            meta["status"] = "budget"
            break
        final, cost, code, err = agent_turn(name, message, meta["session"], turn == 0, trace)
        meta["turns"].append({"cost_usd": cost, "exit": code, "error": err if code else None,
                              "final_text": final, "repo_changed": changed(name)})
        meta_path.write_text(json.dumps(meta, indent=1))
        if code != 0 or not final:
            meta["status"] = "agent_error"
            break
    else:
        meta["status"] = "done"
    meta_path.write_text(json.dumps(meta, indent=1))
    print(f"{name}: {meta['status']} total spent ${spent():.2f}")


def main():
    for entry in json.loads((EVAL / "plan.json").read_text()):
        meta = RUNS / f"{entry['name']}.meta.json"
        if meta.exists() and json.loads(meta.read_text())["status"] != "running":
            continue
        if spent() >= BUDGET:
            print(f"budget ${BUDGET:.2f} reached; stopping")
            break
        run_one(entry)
    print(f"total recorded cost: ${spent():.2f}")


main()
