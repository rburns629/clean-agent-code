"""Extract prompt-quality signals from session transcripts and validate them.

Usage: python3 -I evaluations/harness/prompting/score.py <eval_root>

Signals are extracted from transcript text and tool calls only, as a tool reading
real session logs would. The simulated user's labels and the known prompt levels
are used afterwards to check (1) extractor accuracy and (2) whether each signal
separates prompt levels and tracks hidden-test outcomes. Writes signals.json and
summary.md.
"""
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

EVAL = Path(sys.argv[1]).resolve()
RUNS = EVAL / "runs"
HIDDEN = Path(__file__).resolve().parents[1] / "slop"
IMAGE = "clean-code-eval:2.1.289"
LEVEL_INDEX = {"vague": 0, "partial": 1, "specific": 2}

# Agents often surface a decision instead of asking ("I chose X; if you'd prefer Y...").
QUESTION = re.compile(
    r"\?\s*$|\b(would you like|do you want|should i|shall i|which (one|option|approach)|"
    r"could you (clarify|confirm)|can you (clarify|confirm)|let me know|decision for you|"
    r"if you(?:'d| would)? (?:rather|prefer)|if you (?:also )?want|i (?:chose|assumed|went with))\b",
    re.I | re.M)
WRITE_COMMAND = re.compile(r">|\btee\b|sed\s+-i|\.write\(|\bmv\b|\bcp\b|\bpatch\b|git\s+apply")
SOURCE_PATH = re.compile(r"[\w./-]+\.(?:py|go|ts|js|java|rs|rb)\b")
CORRECTION = re.compile(
    r"\b(no[,.]|not quite|not what|instead|wrong|incorrect|missing|you missed|forgot|"
    r"should (be|have|not|also|use|return|raise|keep|reject)|shouldn't|must|needs? to|"
    r"please (change|fix|add|remove|rename|revert|keep|use|make)|revert|undo|"
    r"rename|doesn't|does not|isn't|is not|didn't|did not|also (add|need|handle))\b",
    re.I)


def parse_trace(path):
    """Split a trace into turns: [{"user": text, "agent": text, "edits": set, "tokens": n}]."""
    turns = []
    for line in path.read_text(errors="ignore").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "harness_user_message":
            turns.append({"user": event["text"], "agent": "", "edits": set(), "tokens": 0})
        elif kind == "assistant" and turns:
            for block in event["message"].get("content", []):
                if block.get("type") == "tool_use" and block.get("name") in ("Edit", "Write"):
                    turns[-1]["edits"].add(block["input"].get("file_path", ""))
                if block.get("type") == "tool_use" and block.get("name") == "Bash":
                    # Heuristic: source paths named in a command that writes files.
                    command = block["input"].get("command", "")
                    if WRITE_COMMAND.search(command):
                        turns[-1]["edits"].update(SOURCE_PATH.findall(command))
        elif kind == "result" and turns:
            turns[-1]["agent"] = event.get("result", "")
            usage = event.get("usage") or {}
            turns[-1]["tokens"] = sum(usage.get(k, 0) or 0 for k in (
                "input_tokens", "output_tokens", "cache_read_input_tokens",
                "cache_creation_input_tokens"))
    return turns


def classify_followup(previous_agent, user_text):
    """Return 'answer' or 'correction' for a follow-up message, without labels."""
    asked = bool(QUESTION.search(previous_agent[-600:]))
    corrects = bool(CORRECTION.search(user_text))
    if asked and not corrects:
        return "answer"
    return "correction" if corrects or not asked else "answer"


def hidden_tests(run, task):
    proc = subprocess.run(
        ["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
         "-e", "PYTHONDONTWRITEBYTECODE=1",
         "--mount", f"type=bind,src={run},dst=/work,readonly",
         "--mount", f"type=bind,src={HIDDEN},dst=/harness,readonly",
         IMAGE, "python3", "/harness/hidden_tests.py", "/work", task],
        capture_output=True, text=True, timeout=120)
    match = re.search(r"HIDDEN (\d+)/(\d+)", proc.stdout)
    return (int(match[1]) / int(match[2])) if match else 0.0


def ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            result[order[k]] = (i + j) / 2
        i = j + 1
    return result


def spearman(xs, ys):
    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = sum((a - mx) ** 2 for a in rx) ** 0.5
    sy = sum((b - my) ** 2 for b in ry) ** 0.5
    return round(cov / (sx * sy), 2) if sx and sy else None


def main():
    plan = json.loads((EVAL / "plan.json").read_text())
    rows, agreement = [], defaultdict(int)
    for entry in plan:
        name, meta_path = entry["name"], RUNS / f"{entry['name']}.meta.json"
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text())
        turns = parse_trace(RUNS / f"{name}.trace.jsonl")
        labels = [t["label"] for t in meta["turns"] if t["role"] == "user"]
        followups = turns[1:]
        detected = [classify_followup(turns[i]["agent"], turns[i + 1]["user"])
                    for i in range(len(followups))]
        for i, kind in enumerate(detected):
            truth = {"ANSWER": "answer", "CORRECTION": "correction"}.get(labels[i] if i < len(labels) else "", "?")
            agreement[(truth, kind)] += 1
        edited_by_turn = [{Path(p).name for p in t["edits"]} for t in turns]
        rework = len({f for i, a in enumerate(edited_by_turn) for b in edited_by_turn[i + 1:] for f in a & b})
        rows.append({
            "name": name, "task": entry["task"], "level": entry["level"], "status": meta["status"],
            "followups": len(followups),
            "corrections": detected.count("correction"),
            "clarifications": sum(bool(QUESTION.search(t["agent"][-600:])) for t in turns),
            "first_attempt_accepted": int(len(followups) == 0 and meta["status"] == "done"),
            "rework_files": rework,
            "tokens": sum(t["tokens"] for t in turns),
            "cost_usd": round(sum(t.get("cost_usd", 0) for t in meta["turns"]), 3),
            "hidden_pass_rate": round(hidden_tests(RUNS / name, entry["task"]), 2),
            "labels": labels,
        })
    (EVAL / "signals.json").write_text(json.dumps(rows, indent=1))

    signals = ["followups", "corrections", "clarifications", "first_attempt_accepted",
               "rework_files", "tokens", "cost_usd", "hidden_pass_rate"]
    lines = ["# Prompt-signal validation", "",
             f"Runs scored: {len(rows)}. Statuses: "
             + ", ".join(f"{s}={sum(r['status'] == s for r in rows)}" for s in sorted({r['status'] for r in rows})),
             "", "## Mean signal by prompt level", "",
             "| Level | Runs | " + " | ".join(signals) + " |",
             "| --- | --- | " + " | ".join("---" for _ in signals) + " |"]
    for level in LEVEL_INDEX:
        group = [r for r in rows if r["level"] == level]
        if group:
            lines.append(f"| {level} | {len(group)} | "
                         + " | ".join(f"{mean(r[s] for r in group):.2f}" for s in signals) + " |")
    lines += ["", "## Spearman correlation with prompt specificity (vague=0, specific=2)", "",
              "| Signal | All runs | Hidden pass rate correlation |", "| --- | --- | --- |"]
    levels = [LEVEL_INDEX[r["level"]] for r in rows]
    passes = [r["hidden_pass_rate"] for r in rows]
    for s in signals:
        values = [r[s] for r in rows]
        lines.append(f"| {s} | {spearman(levels, values)} | {spearman(passes, values) if s != 'hidden_pass_rate' else '-'} |")
    lines += ["", "## Extractor agreement with simulated-user labels", "",
              "| Label (truth) | Detected answer | Detected correction |", "| --- | --- | --- |"]
    for truth in ("answer", "correction", "?"):
        if agreement[(truth, "answer")] or agreement[(truth, "correction")]:
            lines.append(f"| {truth} | {agreement[(truth, 'answer')]} | {agreement[(truth, 'correction')]} |")
    total = sum(agreement.values())
    correct = agreement[("answer", "answer")] + agreement[("correction", "correction")]
    lines.append("")
    lines.append(f"Extractor accuracy: {correct}/{total}" if total else "No follow-ups to classify.")
    lines.append(f"\nTotal cost: ${sum(r['cost_usd'] for r in rows):.2f}")
    (EVAL / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


main()
