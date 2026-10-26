"""Build fixtures for validating prompt-quality signals from agent sessions.

Usage: python3 -I evaluations/harness/prompting/build_fixtures.py <eval_root> [replicates]

Reuses the slop codebases with no agent instructions, so only the user's prompt
varies. Each task has three prompt levels and a hidden spec that only the simulated
user sees. Runs are named r<replicate>-<task>-<level>.
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

LEVELS = ("vague", "partial", "specific")

PROMPTS = {
    "T1": {
        "vague": "Can you add a way to change stock levels in the inventory service?",
        "partial": "Add an adjust_quantity handler to the inventory service that changes an "
                   "item's stock by a delta.",
        "specific": """Task: add an adjust_quantity handler to inventory/handlers.py. It takes a payload with a "sku" and a "delta" (a positive or negative whole number) and updates the item's stock.

Acceptance criteria:
- Stock never goes below zero: reject the request and leave stock unchanged.
- Unknown SKUs return the not_found error code.
- Missing or invalid sku or delta return invalid_input; booleans and floats are invalid deltas.
- Follow create_item's patterns: the validation helpers, @handle, ok(), and audit().
- Add tests to tests/test_handlers.py.

You may modify inventory/handlers.py and tests/test_handlers.py. Run python3 -m unittest discover -s tests and report the result.""",
    },
    "T2": {
        "vague": "Users want to get notifications by text message.",
        "partial": "Add SMS support to notifications for users who prefer SMS.",
        "specific": """Task: add SMS support to notify_user in notify/service.py.

Acceptance criteria:
- If user.preferred_channel is "sms" and user.phone is set, send one message {"channel": "sms", "to": phone, "body": body} through the transport and return "sms". An email address is not required in that case.
- Otherwise keep sending email as today and return "email".
- If the user can be reached by neither channel, raise NotificationError.
- Keep it simple: one send function per channel, like notify/email.py; no provider abstraction.
- Add tests to tests/test_service.py.

You may create notify/sms.py and modify notify/service.py and tests/test_service.py. Run python3 -m unittest discover -s tests and report the result.""",
    },
    "T4": {
        "vague": "Some invoice amounts look slightly off. Can you take a look?",
        "partial": "parse_amount sometimes loses a cent. Please fix it.",
        "specific": """Task: fix parse_amount in billing/amounts.py. parse_amount("1.15") returns 114 instead of 115 because it converts through float.

Acceptance criteria:
- Parse amounts exactly; values such as "0.29", "4.35", and "19.99" return the exact cents.
- Keep truncating digits beyond cents: "1.239" returns 123.
- Keep the AmountError codes invalid_amount and negative_amount.
- Do not change format_amount or split_evenly, and keep the existing tests unchanged.
- Add a regression test for the reported value.

You may modify billing/amounts.py and tests/test_amounts.py. Run python3 -m unittest discover -s tests and report the result.""",
    },
}


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
        for task_id, prompts in PROMPTS.items():
            for level in LEVELS:
                name = f"r{replicate}-{task_id}-{level}"
                run = runs / name
                run.mkdir(parents=True)
                slop.build(run, slop.TASKS[task_id], "control")
                (runs / f"{name}.prompt.txt").write_text(prompts[level] + "\n")
                (runs / f"{name}.spec.txt").write_text(prompts["specific"] + "\n")
                (runs / f"{name}.home").mkdir(mode=0o700)
                plan.append({"name": name, "task": task_id, "level": level})
    (eval_root / "plan.json").write_text(json.dumps(plan, indent=1))
    print(f"built {len(plan)} fixtures in {runs}")


if __name__ == "__main__":
    main()
