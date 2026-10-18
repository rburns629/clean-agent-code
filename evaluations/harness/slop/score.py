"""Score slop runs: hidden tests, diff metrics, task-specific checks, and trace cost.

Usage: python3 -I evaluations/harness/slop/score.py <eval_root>
Writes scores.json and summary.md. Agent code runs only in the no-network image.
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

EVAL = Path(sys.argv[1]).resolve()
RUNS = EVAL / "runs"
HERE = Path(__file__).resolve().parent
IMAGE = "clean-code-eval:2.1.289"
DOCS = re.compile(r"^(AGENTS\.md|CLAUDE\.md|PROJECT_CONTEXT\.md|standards/|templates/)")


def git(run, *args):
    return subprocess.run(["git", "-C", str(run), *args], capture_output=True, text=True).stdout


def changes(run):
    """Added/removed lines per file versus the initial commit, including untracked files."""
    root = git(run, "rev-list", "--max-parents=0", "HEAD").split()[0]
    diff = git(run, "diff", "-U0", root)
    files = defaultdict(lambda: {"added": [], "removed": [], "new": False})
    current = None
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("--- ") or line.startswith("@@"):
            continue
        elif current and line.startswith("+"):
            files[current]["added"].append(line[1:])
        elif current and line.startswith("-"):
            files[current]["removed"].append(line[1:])
        elif line.startswith("new file"):
            pass
    for name in git(run, "diff", "--name-only", "--diff-filter=A", root).split():
        files[name]["new"] = True
    for name in git(run, "ls-files", "--others", "--exclude-standard").split():
        path = run / name
        if path.is_file():
            files[name] = {"added": path.read_text(errors="ignore").splitlines(), "removed": [], "new": True}
    return {n: f for n, f in files.items() if not DOCS.match(n) and "__pycache__" not in n}


def is_test(name):
    return name.startswith("tests/")


def added(files, predicate):
    return [l for n, f in files.items() if predicate(n) for l in f["added"]]


def hidden(run, task):
    proc = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "-e", "PYTHONDONTWRITEBYTECODE=1",
         "--mount", f"type=bind,src={run},dst=/work,readonly",
         "--mount", f"type=bind,src={HERE},dst=/harness,readonly",
         IMAGE, "python3", "/harness/hidden_tests.py", "/work", task],
        capture_output=True, text=True, timeout=120)
    match = re.search(r"HIDDEN (\d+)/(\d+)", proc.stdout)
    return (int(match[1]), int(match[2])) if match else (0, None)


def visible(run):
    proc = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "-e", "PYTHONDONTWRITEBYTECODE=1", "-w", "/work",
         "--mount", f"type=bind,src={run},dst=/work,readonly",
         IMAGE, "python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        capture_output=True, text=True, timeout=120)
    return proc.returncode == 0


def trace_metrics(path):
    calls, final = 0, {}
    if path.exists():
        for line in path.read_text(errors="ignore").splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "assistant":
                calls += sum(b.get("type") == "tool_use" for b in event["message"].get("content", []))
            elif event.get("type") == "result":
                final = event
    return {"completed": final.get("subtype") == "success" and not final.get("is_error"),
            "cost_usd": final.get("total_cost_usd") or 0, "tool_calls": calls,
            "duration_s": round((final.get("duration_ms") or 0) / 1000, 1),
            "final_text": final.get("result", "")}


def task_checks(task, files):
    src = added(files, lambda n: not is_test(n) and n.endswith(".py"))
    tests = added(files, lambda n: is_test(n))
    text = "\n".join(src)
    if task == "T1":
        handler = "\n".join(files.get("inventory/handlers.py", {}).get("added", []))
        return {
            "reuses_require_int": "require_int(" in handler,
            "uses_handle_decorator": "@handle" in handler,
            "uses_ok_envelope": "ok(" in handler,
            "records_audit": "audit(" in handler,
            "reinvented_validation": bool(re.search(r"isinstance\(.*(int|bool)", text)),
            "new_helper_functions": len([l for l in src if re.match(r"\s*def ", l)]) - 1,
        }
    if task == "T2":
        return {
            "classes_added": len([l for l in src if re.match(r"\s*class ", l)]),
            "abstraction_terms": sorted(set(re.findall(
                r"\b(ABC|abstractmethod|Protocol|[Rr]egistry|[Ff]actory|[Ss]trategy|Enum|Provider)\b", text))),
            "source_files_added": len([n for n, f in files.items() if f["new"] and not is_test(n)]),
        }
    if task == "T3":
        return {
            "float_or_decimal_money": bool(re.search(r"\bfloat\(|Decimal|round\(|/ *100\b", text)),
            "frozen_dataclass_result": "@dataclass(frozen=True)" in text,
            "validates_orders": "_check(" in text or "ReportError" in text,
            "tests_use_make_order": any("make_order" in l for l in tests),
        }
    if task == "T4":
        amounts = files.get("billing/amounts.py", {"added": [], "removed": []})
        touched = "\n".join(amounts["added"] + amounts["removed"])
        old_tests = files.get("tests/test_amounts.py", {"removed": []})["removed"]
        return {
            "touched_other_functions": bool(re.search(r"format_amount|split_evenly|divmod", touched)),
            "existing_test_lines_removed": len([l for l in old_tests if l.strip()]),
            "regression_test_added": any("1.15" in l or "0.29" in l for l in tests),
        }
    return {}


results = {}
for run in sorted(p for p in RUNS.iterdir() if p.is_dir()):
    trace = RUNS / f"{run.name}.trace.jsonl"
    if not trace.exists():
        continue
    _, task, condition = run.name.split("-")
    files = changes(run)
    passed, total = hidden(run, task)
    src_files = [n for n in files if not is_test(n)]
    results[run.name] = {
        "task": task, "condition": condition,
        "hidden_passed": passed, "hidden_total": total,
        "visible_suite_ok": visible(run),
        "src_lines_added": len(added(files, lambda n: not is_test(n))),
        "src_lines_removed": sum(len(files[n]["removed"]) for n in src_files),
        "test_lines_added": len(added(files, is_test)),
        "files_changed": sorted(files),
        **task_checks(task, files),
        **trace_metrics(trace),
    }

(EVAL / "scores.json").write_text(json.dumps(results, indent=1))
lines = ["# Slop evaluation summary", "",
         "| Run | Hidden | Visible OK | Src +/- | Test + | Cost | Task checks |",
         "| --- | --- | --- | --- | --- | --- | --- |"]
skip = {"task", "condition", "hidden_passed", "hidden_total", "visible_suite_ok", "src_lines_added",
        "src_lines_removed", "test_lines_added", "files_changed", "completed", "cost_usd",
        "tool_calls", "duration_s", "final_text"}
for name, r in results.items():
    checks = ", ".join(f"{k}={v}" for k, v in r.items() if k not in skip)
    lines.append(f"| {name} | {r['hidden_passed']}/{r['hidden_total']} | {r['visible_suite_ok']} | "
                 f"+{r['src_lines_added']}/-{r['src_lines_removed']} | +{r['test_lines_added']} | "
                 f"${r['cost_usd']:.2f} | {checks} |")
lines.append("")
lines.append(f"Total agent cost: ${sum(r['cost_usd'] for r in results.values()):.2f}")
(EVAL / "summary.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
