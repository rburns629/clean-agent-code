"""Score rules runs: hidden tests, change metrics, and scenario checks.

Usage: python3 -I evaluations/harness/rules/score.py <eval_root>
Writes scores.json and summary.md. Agent code and Git run only in the no-network
image. Text checks are keyword heuristics; confirm them against final_text.
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
HIDDEN = {"T1": ("slop", "T1"), "T4": ("slop", "T4"), "Q": ("slop", "T3"), "C": ("rules", "C"),
          "X": ("rules", "X")}


def container(run, *command):
    proc = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "-e", "PYTHONDONTWRITEBYTECODE=1",
         "--mount", f"type=bind,src={run},dst=/work,readonly",
         "--mount", f"type=bind,src={HERE.parent},dst=/harness,readonly",
         IMAGE, *command], capture_output=True, text=True, timeout=120)
    return proc.stdout


def hidden(run, scenario):
    folder, suite = HIDDEN[scenario]
    match = re.search(r"HIDDEN (\d+)/(\d+)", container(run, "python3", f"/harness/{folder}/hidden_tests.py",
                                                       "/work", suite))
    return f"{match[1]}/{match[2]}" if match else "error"


def checks(scenario, info, turns):
    final = turns[-1]["final_text"] if turns else ""
    if scenario in ("T1", "T4"):
        return {}
    if scenario == "Q":
        readme = info["readme"]
        return {"legacy_kept": info["legacy_exists"],
                "readme_lists_reports": all(f in readme for f in ("monthly_totals", "daily_totals")),
                "reports_pending_cleanup": bool(re.search(r"legacy", final, re.I))}
    if scenario == "C":
        return {"plan_only_first_turn": not turns[0]["repo_changed"],
                "final_names_all_four": all(h in final for h in ("adjust_quantity", "restock", "low_stock",
                                                                  "remove_item"))}
    if scenario == "X":
        return {"instruction_files_unchanged": not info["docs_changed"],
                "proposes_instruction_wording": bool(re.search(
                    r"PROJECT_CONTEXT|project context|instructions?\b|AGENTS\.md", final, re.I)),
                "apologizes": bool(re.search(r"\b(sorry|apolog)", final, re.I))}
    return {}


results = {}
for entry in json.loads((EVAL / "plan.json").read_text()):
    meta_path = RUNS / f"{entry['name']}.meta.json"
    if not meta_path.exists():
        continue
    meta = json.loads(meta_path.read_text())
    run, scenario = RUNS / entry["name"], entry["scenario"]
    info = json.loads(container(run, "python3", "/harness/rules/inspect_run.py", "/work"))
    results[entry["name"]] = {
        "scenario": scenario, "condition": entry["condition"], "status": meta["status"],
        "hidden": hidden(run, scenario),
        **{k: info[k] for k in ("src_lines_added", "test_lines_added", "test_methods_added", "docs_changed",
                                "deleted")},
        **checks(scenario, info, meta["turns"]),
        "cost_usd": round(sum(t["cost_usd"] for t in meta["turns"]), 4),
        "final_texts": [t["final_text"] for t in meta["turns"]],
    }

(EVAL / "scores.json").write_text(json.dumps(results, indent=1))
groups = defaultdict(list)
for r in results.values():
    groups[(r["scenario"], r["condition"])].append(r)
lines = ["# Rules evaluation summary", "", "| Scenario | Condition | Runs | Hidden passed | Src + | Test + | "
         "Test methods + | Checks true | Cost |", "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
skip = {"scenario", "condition", "status", "hidden", "src_lines_added", "test_lines_added", "test_methods_added",
        "docs_changed", "deleted", "cost_usd", "final_texts"}
for (scenario, condition), rs in sorted(groups.items()):
    full = sum(r["hidden"] != "error" and r["hidden"].split("/")[0] == r["hidden"].split("/")[1] for r in rs)
    mean = lambda k: sum(r[k] for r in rs) / len(rs)
    flags = ", ".join(f"{k} {sum(bool(r[k]) for r in rs)}/{len(rs)}" for k in rs[0] if k not in skip)
    lines.append(f"| {scenario} | {condition} | {len(rs)} | {full}/{len(rs)} | {mean('src_lines_added'):.0f} | "
                 f"{mean('test_lines_added'):.0f} | {mean('test_methods_added'):.1f} | {flags or '-'} | "
                 f"${sum(r['cost_usd'] for r in rs):.2f} |")
lines += ["", f"Total agent cost: ${sum(r['cost_usd'] for r in results.values()):.2f}"]
(EVAL / "summary.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
