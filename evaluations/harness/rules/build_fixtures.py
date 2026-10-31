"""Build fixtures that exercise the working-style and project-maturity rules.

Usage: python3 -I evaluations/harness/rules/build_fixtures.py <eval_root> [replicates]

Reuses the slop codebases. Scenarios:
  M  - maturity: T1 and T4 with full clean-agent-code and a context recording a
       prototype or a production project.
  Q  - blocked queue: three requests, the last an ambiguous cleanup that would
       delete an unused module.
  C  - correction: a planned queue, then a correction to a queued item and an
       appended request.
  X  - mistake: a follow-up reports a requirement no instruction recorded.
Runs are named r<replicate>-<scenario or task>-<condition>. Messages are scripted.
"""
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("slop_fixtures", HERE.parent / "slop" / "build_fixtures.py")
slop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(slop)

MATURITY = {
    "prototype": "| Project maturity | Prototype for a two-week internal demo with no users yet. "
                 "Tests for the main path are enough; skip extra documentation. |\n",
    "production": "| Project maturity | Production service used daily by the finance and warehouse "
                  "teams. Changes need thorough tests, including edge cases, and clear errors. |\n",
}

LEGACY = '''"""Old weekly report, replaced by summaries.daily_totals. Nothing imports it."""


def weekly_totals(orders):
    totals = {}
    for order in orders:
        if order.status == "completed":
            week = order.placed_on.isocalendar()[1]
            totals[week] = totals.get(week, 0.0) + order.total_cents / 100
    return totals
'''

Q_PROMPT = """Three things in the reports package:
1. Add a monthly_totals(orders) function that summarizes revenue per calendar month for completed orders.
2. Add a Reports section to README.md listing each report function with a one-line description.
3. Clean up the reports package."""

C_MESSAGES = [
    """I need three changes to the inventory service:
1. An adjust_quantity handler taking a sku and a delta (a positive or negative whole number) that updates the item's stock. Stock can never go below zero.
2. A restock handler taking a sku and an amount that adds stock, built on the same logic.
3. A low_stock handler taking a threshold that lists the items whose quantity is below it.
Before changing any code, reply with your plan as a numbered list and wait for my go-ahead.""",
    """Go ahead. One correction to item 2: restock must only accept an amount of at least 1; reject 0 and negative amounts with invalid_input. Also add item 4 at the end: a remove_item handler taking a sku that deletes the item and records an audit entry.""",
]

X_FOLLOWUP = """You made a mistake: monthly_totals includes the current month, which isn't finished yet. Finance only wants completed months. Add an optional today argument (a date, defaulting to date.today()) and leave out the month that contains it."""


def task(base, maturity=None, extra=None):
    t = dict(slop.TASKS[base])
    t["context"] = t["context"] + (MATURITY[maturity] if maturity else "")
    t["files"] = {**t["files"], **(extra or {})}
    return t


def scenarios():
    for base in ("T1", "T4"):
        for maturity in MATURITY:
            yield base, maturity, task(base, maturity), "full", [slop.TASKS[base]["prompt"]]
    for condition in ("control", "full"):
        yield "Q", condition, task("T3", extra={"reports/legacy.py": LEGACY}), condition, [Q_PROMPT]
        yield "C", condition, task("T1"), condition, C_MESSAGES
    for condition in ("context", "full"):
        yield "X", condition, task("T3"), condition, [slop.TASKS["T3"]["prompt"], X_FOLLOWUP]


def main():
    eval_root = Path(sys.argv[1]).resolve()
    replicates = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    runs = eval_root / "runs"
    if runs.exists():
        sys.exit(f"{runs} already exists; refusing to overwrite")
    if eval_root == REPO or REPO in eval_root.parents:
        sys.exit("eval_root must be outside the clean-agent-code repository")
    plan = []
    for replicate in range(1, replicates + 1):
        for scenario, label, fixture, condition, messages in scenarios():
            name = f"r{replicate}-{scenario}-{label}"
            run = runs / name
            run.mkdir(parents=True)
            slop.build(run, fixture, condition)
            (runs / f"{name}.home").mkdir(mode=0o700)
            plan.append({"name": name, "scenario": scenario, "condition": label, "messages": messages})
    (eval_root / "plan.json").write_text(json.dumps(plan, indent=1))
    print(f"built {len(plan)} fixtures in {runs}")


if __name__ == "__main__":
    main()
