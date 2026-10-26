"""Blind rubric review of each run's diff by a separate Claude instance.

Usage: EVAL_ENV_FILE=key.env python3 -I evaluations/harness/slop/judge.py <eval_root> [budget_usd]
Packets omit the condition, redact framework file names, and are shuffled. The
judge runs in the evaluation image without tools. Writes judgments.json.
"""
import json
import os
import random
import re
import subprocess
import sys
from pathlib import Path

EVAL = Path(sys.argv[1]).resolve()
BUDGET = float(sys.argv[2]) if len(sys.argv) > 2 else 4.0
RUNS = EVAL / "runs"
IMAGE = "clean-code-eval:2.1.289"
MODEL = os.environ.get("EVAL_JUDGE_MODEL", "claude-opus-5-5")
DOCS = [":(exclude)AGENTS.md", ":(exclude)CLAUDE.md", ":(exclude)PROJECT_CONTEXT.md",
        ":(exclude)standards", ":(exclude)templates"]
REDACT = re.compile(r"AGENTS\.md|CLAUDE\.md|PROJECT_CONTEXT\.md|standards/[\w./-]+|clean-(?:agent-)?code", re.I)

RUBRIC = """You are reviewing a code change for a code-quality study. Judge only the change
shown, against the existing codebase and the user's request. Score each criterion
from 1 (poor) to 5 (excellent):

- correctness: the change does what was asked, including edge cases implied by the request
- simplicity: no unnecessary abstractions, indirection, configuration, or code
- consistency: matches the codebase's existing naming, structure, error handling, and style
- reuse: uses existing helpers and patterns instead of duplicating them
- tests: adds meaningful tests for the new behavior and preserves existing tests
- scope: changes are limited to the request, with no unrelated edits or reformatting
- overall: 5 means a strong senior engineer would merge it as-is; 1 means sloppy

Also report "implemented": true if the request was actually implemented in the code,
false if the change only proposes, documents, or partially does it.
Respond with only a JSON object:
{"correctness": n, "simplicity": n, "consistency": n, "reuse": n, "tests": n,
 "scope": n, "overall": n, "implemented": true|false, "rationale": "<one sentence>"}
"""


def git(run, *args):
    return subprocess.run(["git", "-C", str(run), *args], capture_output=True, text=True).stdout


def packet(run):
    root = git(run, "rev-list", "--max-parents=0", "HEAD").split()[0]
    original = []
    for name in git(run, "ls-tree", "-r", "--name-only", root).split():
        if name.endswith(".py"):
            original.append(f"--- {name}\n{git(run, 'show', f'{root}:{name}')}")
    diff = git(run, "diff", root, "--", ".", *DOCS)
    for name in git(run, "ls-files", "--others", "--exclude-standard").split():
        path = run / name
        if path.is_file() and "__pycache__" not in name:
            diff += f"\n--- new untracked file: {name}\n{path.read_text(errors='ignore')}"
    prompt = (RUNS / f"{run.name}.prompt.txt").read_text().strip()
    body = (f"{RUBRIC}\n## User request\n{prompt}\n\n## Existing code before the change\n"
            + "\n".join(original) + f"\n\n## The change (diff against the original)\n{diff or '(no changes)'}\n")
    return REDACT.sub("[docs]", body)


def judge(text):
    env_file = os.environ.get("EVAL_ENV_FILE")
    key_args = ["--env-file", env_file] if env_file else ["-e", "ANTHROPIC_API_KEY"]
    proc = subprocess.run(
        ["docker", "run", "--rm", "-i", *key_args, "--cap-drop", "ALL", IMAGE,
         "claude", "-p", "--model", MODEL, "--max-turns", "1", "--output-format", "json",
         "--max-budget-usd", "0.5",
         "--disallowedTools", "Bash,Read,Write,Edit,Glob,Grep,WebFetch,WebSearch,Task,NotebookEdit"],
        input=text, capture_output=True, text=True, timeout=300)
    try:
        result = json.loads(proc.stdout)
    except ValueError:
        return None, 0.0, proc.stderr[-500:]
    raw = result.get("result", "")
    match = re.search(r"\{.*\}", raw, re.S)
    try:
        return json.loads(match.group(0)) if match else None, result.get("total_cost_usd") or 0, raw[-300:]
    except ValueError:
        return None, result.get("total_cost_usd") or 0, raw[-300:]


def main():
    out = EVAL / "judgments.json"
    done = json.loads(out.read_text()) if out.exists() else {}
    runs = [p for p in sorted(RUNS.iterdir()) if p.is_dir() and (RUNS / f"{p.name}.trace.jsonl").exists()]
    random.Random(20261018).shuffle(runs)
    spent = sum(v.get("cost_usd", 0) for v in done.values())
    for index, run in enumerate(runs, 1):
        if run.name in done:
            continue
        if spent >= BUDGET:
            print(f"judge budget ${BUDGET:.2f} reached; stopping")
            break
        scores, cost, note = judge(packet(run))
        spent += cost
        done[run.name] = {"blind_id": f"S{index:02d}", "scores": scores, "cost_usd": cost,
                          "note": None if scores else note}
        out.write_text(json.dumps(done, indent=1))
        print(f"S{index:02d} judged (${cost:.3f}); judge total ${spent:.2f}")


main()
