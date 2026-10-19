"""Build realistic "slop" evaluation fixtures in three conditions.

Usage: python3 -I evaluations/harness/slop/build_fixtures.py <eval_root> [replicates]

Conditions:
  control  - the codebase only; no agent instructions.
  context  - adds PROJECT_CONTEXT.md and a CLAUDE.md pointer to it.
  full     - adds AGENTS.md, standards/, templates/, PROJECT_CONTEXT.md, and the
             README's recommended CLAUDE.md pointer.
Prompts are plain user requests, identical across conditions. Runs are named
r<replicate>-<task>-<condition> so sorted order interleaves conditions.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

FULL_POINTER = """Follow AGENTS.md and the applicable standards under standards/.
Read PROJECT_CONTEXT.md before making changes.
Use its component-specific conventions, reference files, and verification commands.
Apply standards/CLI_OPERATIONS.md when using infrastructure or repository CLIs.
Preserve existing contracts and report the checks actually performed and their results.
"""
CONTEXT_POINTER = """Read PROJECT_CONTEXT.md before making changes.
Use its conventions, reference files, and verification commands.
"""

TASKS = {}

# --------------------------------------------------------------------------- T1
TASKS["T1"] = {
    "prompt": "Add an adjust_quantity handler to the inventory service. It takes a payload "
              "with a sku and a delta (a positive or negative whole number) and updates the "
              "item's stock. Stock can never go below zero.",
    "context": """| Area | Project facts |
| --- | --- |
| Purpose | In-memory inventory service used by internal tools. |
| Language | Python 3 standard library; tests use unittest. |
| Reference implementations | `inventory/handlers.py` (`create_item`, `get_item`). |
| Conventions | Handlers take a payload dict and an optional `store`, validate with `inventory/validation.py`, are wrapped in `@handle`, return `ok(...)`, and record changes with `audit(...)`. |
| Error handling | Raise `ServiceError` subclasses from `inventory/errors.py`; `@handle` converts them to error responses. |
| Testing | `python3 -m unittest discover -s tests` |
""",
    "files": {
        "README.md": "# Inventory service\n\nRun tests: `python3 -m unittest discover -s tests`\n",
        "inventory/__init__.py": "",
        "inventory/errors.py": '''class ServiceError(Exception):
    """Base error with a stable code returned to callers."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


class ValidationError(ServiceError):
    def __init__(self, field, message):
        super().__init__("invalid_input", f"{field}: {message}")
        self.field = field


class NotFoundError(ServiceError):
    def __init__(self, resource, key):
        super().__init__("not_found", f"{resource} {key} not found")


class ConflictError(ServiceError):
    def __init__(self, message):
        super().__init__("conflict", message)
''',
        "inventory/validation.py": '''"""Payload validation helpers shared by all handlers."""
from inventory.errors import ValidationError


def require_str(payload, field, *, max_length=200):
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(field, "must be a non-empty string")
    if len(value) > max_length:
        raise ValidationError(field, f"must be at most {max_length} characters")
    return value.strip()


def require_int(payload, field, *, minimum=None, maximum=None):
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(field, "must be an integer")
    if minimum is not None and value < minimum:
        raise ValidationError(field, f"must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ValidationError(field, f"must be at most {maximum}")
    return value
''',
        "inventory/responses.py": '''"""Response envelope used by every handler."""
import functools

from inventory.errors import ServiceError


def ok(data):
    return {"ok": True, "data": data}


def fail(error):
    return {"ok": False, "error": {"code": error.code, "message": error.message}}


def handle(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ServiceError as error:
            return fail(error)
    return wrapper
''',
        "inventory/audit.py": '''"""Append-only audit trail of inventory changes."""
AUDIT_LOG = []


def audit(event, **fields):
    AUDIT_LOG.append({"event": event, **fields})
''',
        "inventory/models.py": '''from dataclasses import dataclass


@dataclass
class Item:
    sku: str
    name: str
    quantity: int
''',
        "inventory/store.py": '''from inventory.models import Item


class InMemoryStore:
    def __init__(self):
        self._items = {}

    def get(self, sku):
        return self._items.get(sku)

    def put(self, item: Item):
        self._items[item.sku] = item
''',
        "inventory/handlers.py": '''from dataclasses import asdict

from inventory.audit import audit
from inventory.errors import ConflictError, NotFoundError
from inventory.models import Item
from inventory.responses import handle, ok
from inventory.store import InMemoryStore
from inventory.validation import require_int, require_str

STORE = InMemoryStore()


@handle
def create_item(payload, store=STORE):
    sku = require_str(payload, "sku", max_length=32)
    name = require_str(payload, "name")
    quantity = require_int(payload, "quantity", minimum=0)
    if store.get(sku) is not None:
        raise ConflictError(f"item {sku} already exists")
    item = Item(sku=sku, name=name, quantity=quantity)
    store.put(item)
    audit("item_created", sku=sku, quantity=quantity)
    return ok(asdict(item))


@handle
def get_item(payload, store=STORE):
    sku = require_str(payload, "sku", max_length=32)
    item = store.get(sku)
    if item is None:
        raise NotFoundError("item", sku)
    return ok(asdict(item))
''',
        "tests/__init__.py": "",
        "tests/test_handlers.py": '''import unittest

from inventory.handlers import create_item, get_item
from inventory.store import InMemoryStore


class HandlerTest(unittest.TestCase):
    def setUp(self):
        self.store = InMemoryStore()

    def test_create_then_get(self):
        create_item({"sku": "A1", "name": "Bolt", "quantity": 5}, store=self.store)
        result = get_item({"sku": "A1"}, store=self.store)
        self.assertEqual(result["data"]["quantity"], 5)

    def test_create_rejects_negative_quantity(self):
        result = create_item({"sku": "A1", "name": "Bolt", "quantity": -1}, store=self.store)
        self.assertEqual(result["error"]["code"], "invalid_input")

    def test_get_missing(self):
        self.assertEqual(get_item({"sku": "NOPE"}, store=self.store)["error"]["code"], "not_found")


if __name__ == "__main__":
    unittest.main()
''',
    },
}

# --------------------------------------------------------------------------- T2
TASKS["T2"] = {
    "prompt": "Add SMS support to notifications. If a user's preferred_channel is \"sms\" and "
              "they have a phone number, send the message by SMS instead of email; otherwise "
              "keep sending email. The transport already accepts SMS messages shaped like "
              "{\"channel\": \"sms\", \"to\": phone, \"body\": text}.",
    "context": """| Area | Project facts |
| --- | --- |
| Purpose | Sends user notifications through an injected transport. |
| Language | Python 3 standard library; tests use unittest. |
| Reference implementations | `notify/email.py` (one function per channel), `notify/service.py`. |
| Architecture | Plain functions; no plugin or provider abstraction is needed for the current channels. |
| Error handling | Raise `NotificationError` when a user cannot be notified. |
| Testing | `python3 -m unittest discover -s tests` |
""",
    "files": {
        "README.md": "# Notifications\n\nRun tests: `python3 -m unittest discover -s tests`\n",
        "notify/__init__.py": "",
        "notify/errors.py": '''class NotificationError(Exception):
    """Raised when a user cannot be notified."""
''',
        "notify/models.py": '''from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_channel: str = "email"
''',
        "notify/email.py": '''def send_email(transport, to, subject, body):
    transport.send({"channel": "email", "to": to, "subject": subject, "body": body})
''',
        "notify/service.py": '''from notify.email import send_email
from notify.errors import NotificationError


def notify_user(user, subject, body, transport):
    """Send a notification and return the channel used."""
    if not user.email:
        raise NotificationError(f"user {user.id} has no email address")
    send_email(transport, user.email, subject, body)
    return "email"
''',
        "tests/__init__.py": "",
        "tests/fakes.py": '''class FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)
''',
        "tests/test_service.py": '''import unittest

from notify.errors import NotificationError
from notify.models import User
from notify.service import notify_user
from tests.fakes import FakeTransport


class NotifyUserTest(unittest.TestCase):
    def test_sends_email(self):
        transport = FakeTransport()
        channel = notify_user(User(id="u1", email="a@example.com"), "Hi", "Body", transport)
        self.assertEqual(channel, "email")
        self.assertEqual(transport.sent[0]["to"], "a@example.com")

    def test_requires_email(self):
        with self.assertRaises(NotificationError):
            notify_user(User(id="u1"), "Hi", "Body", FakeTransport())


if __name__ == "__main__":
    unittest.main()
''',
    },
}

# --------------------------------------------------------------------------- T3
TASKS["T3"] = {
    "prompt": "Add a monthly_totals(orders) function to the reports package that summarizes "
              "revenue per calendar month for completed orders.",
    "context": """| Area | Project facts |
| --- | --- |
| Purpose | Revenue summaries for the finance dashboard. |
| Language | Python 3 standard library; tests use unittest. |
| Reference implementations | `reports/summaries.py` (`daily_totals`), `tests/test_summaries.py`. |
| Domain terms | Money is integer cents (`total_cents`); never floats. Only `completed` orders count as revenue. |
| Conventions | Summaries return lists of frozen dataclasses sorted by period; invalid orders raise `ReportError`. Tests build orders with `tests/helpers.make_order`. |
| Testing | `python3 -m unittest discover -s tests` |
""",
    "files": {
        "README.md": "# Reports\n\nRun tests: `python3 -m unittest discover -s tests`\n",
        "reports/__init__.py": "",
        "reports/errors.py": '''class ReportError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
''',
        "reports/models.py": '''from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Order:
    id: str
    status: str
    total_cents: int
    placed_on: date
''',
        "reports/summaries.py": '''from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from reports.errors import ReportError

COMPLETED = "completed"


@dataclass(frozen=True)
class DailyTotal:
    day: date
    total_cents: int
    order_count: int


def _check(order):
    if order.total_cents < 0:
        raise ReportError("invalid_order", f"order {order.id} has a negative total")


def daily_totals(orders):
    """Revenue per day for completed orders, oldest first."""
    totals = defaultdict(lambda: [0, 0])
    for order in orders:
        _check(order)
        if order.status != COMPLETED:
            continue
        bucket = totals[order.placed_on]
        bucket[0] += order.total_cents
        bucket[1] += 1
    return [DailyTotal(day, cents, count) for day, (cents, count) in sorted(totals.items())]


def status_counts(orders):
    """Number of orders in each status."""
    counts = defaultdict(int)
    for order in orders:
        counts[order.status] += 1
    return dict(counts)
''',
        "tests/__init__.py": "",
        "tests/helpers.py": '''from datetime import date

from reports.models import Order


def make_order(**overrides):
    values = {"id": "o1", "status": "completed", "total_cents": 1000, "placed_on": date(2026, 1, 15)}
    values.update(overrides)
    return Order(**values)
''',
        "tests/test_summaries.py": '''import unittest
from datetime import date

from reports.errors import ReportError
from reports.summaries import DailyTotal, daily_totals, status_counts
from tests.helpers import make_order


class DailyTotalsTest(unittest.TestCase):
    def test_groups_completed_orders_by_day(self):
        orders = [
            make_order(id="a", total_cents=500),
            make_order(id="b", total_cents=250),
            make_order(id="c", status="cancelled", total_cents=999),
        ]
        self.assertEqual(daily_totals(orders), [DailyTotal(date(2026, 1, 15), 750, 2)])

    def test_rejects_negative_totals(self):
        with self.assertRaises(ReportError):
            daily_totals([make_order(total_cents=-1)])


class StatusCountsTest(unittest.TestCase):
    def test_counts(self):
        orders = [make_order(), make_order(status="cancelled")]
        self.assertEqual(status_counts(orders), {"completed": 1, "cancelled": 1})


if __name__ == "__main__":
    unittest.main()
''',
    },
}

# --------------------------------------------------------------------------- T4
TASKS["T4"] = {
    "prompt": "Customers report being undercharged by a cent sometimes. For example "
              "parse_amount(\"1.15\") returns 114 instead of 115. Please fix it.",
    "context": """| Area | Project facts |
| --- | --- |
| Purpose | Billing amount parsing and formatting. |
| Language | Python 3 standard library; tests use unittest. |
| Public contracts | `parse_amount` returns integer cents, truncates digits beyond cents, and raises `AmountError` with codes `invalid_amount` or `negative_amount`. `format_amount` and `split_evenly` are used by invoicing. |
| Testing | `python3 -m unittest discover -s tests` |
""",
    "files": {
        "README.md": "# Billing amounts\n\nRun tests: `python3 -m unittest discover -s tests`\n",
        "billing/__init__.py": "",
        "billing/amounts.py": '''class AmountError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def parse_amount(text):
    """Parse a decimal string such as "12.30" into integer cents.

    Digits beyond cents are truncated. Raises AmountError for invalid or negative input.
    """
    if not isinstance(text, str) or not text.strip():
        raise AmountError("invalid_amount", "amount must be a non-empty string")
    try:
        value = float(text)
    except ValueError:
        raise AmountError("invalid_amount", "amount is not a number") from None
    if value < 0:
        raise AmountError("negative_amount", "amount cannot be negative")
    return int(value * 100)


def format_amount(cents):
    return f"{cents // 100}.{cents % 100:02d}"


def split_evenly(cents, parts):
    """Split cents into parts; earlier parts absorb the remainder."""
    base, remainder = divmod(cents, parts)
    return [base + (1 if index < remainder else 0) for index in range(parts)]
''',
        "tests/__init__.py": "",
        "tests/test_amounts.py": '''import unittest

from billing.amounts import AmountError, format_amount, parse_amount, split_evenly


class ParseAmountTest(unittest.TestCase):
    def test_whole_and_fractional(self):
        self.assertEqual(parse_amount("12"), 1200)
        self.assertEqual(parse_amount("12.50"), 1250)

    def test_truncates_extra_precision(self):
        self.assertEqual(parse_amount("1.239"), 123)

    def test_rejects_text(self):
        with self.assertRaises(AmountError) as ctx:
            parse_amount("abc")
        self.assertEqual(ctx.exception.code, "invalid_amount")

    def test_rejects_negative(self):
        with self.assertRaises(AmountError) as ctx:
            parse_amount("-1")
        self.assertEqual(ctx.exception.code, "negative_amount")


class FormatAndSplitTest(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_amount(1205), "12.05")

    def test_split(self):
        self.assertEqual(split_evenly(100, 3), [34, 33, 33])


if __name__ == "__main__":
    unittest.main()
''',
    },
}


def git(root, *args):
    env = {**os.environ, "GIT_AUTHOR_NAME": "dev", "GIT_AUTHOR_EMAIL": "dev@example.invalid",
           "GIT_COMMITTER_NAME": "dev", "GIT_COMMITTER_EMAIL": "dev@example.invalid"}
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


def build(run, task, condition):
    for name, body in task["files"].items():
        path = run / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    (run / ".gitignore").write_text("__pycache__/\n")
    context = "# Project context\n\n" + task["context"]
    if condition == "context":
        (run / "PROJECT_CONTEXT.md").write_text(context)
        (run / "CLAUDE.md").write_text(CONTEXT_POINTER)
    elif condition == "full":
        shutil.copy2(REPO / "AGENTS.md", run / "AGENTS.md")
        shutil.copytree(REPO / "standards", run / "standards")
        shutil.copytree(REPO / "templates", run / "templates")
        (run / "PROJECT_CONTEXT.md").write_text(context)
        (run / "CLAUDE.md").write_text(FULL_POINTER)
    git(run, "init", "-q")
    git(run, "add", "-A")
    git(run, "commit", "-q", "-m", "Initial commit")


def main():
    eval_root = Path(sys.argv[1]).resolve()
    replicates = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    runs = eval_root / "runs"
    if runs.exists():
        sys.exit(f"{runs} already exists; refusing to overwrite")
    if eval_root == REPO or REPO in eval_root.parents:
        sys.exit("eval_root must be outside the clean-code repository")
    names = []
    for replicate in range(1, replicates + 1):
        for task_id, task in TASKS.items():
            for condition in ("control", "context", "full"):
                name = f"r{replicate}-{task_id}-{condition}"
                run = runs / name
                run.mkdir(parents=True)
                build(run, task, condition)
                (runs / f"{name}.prompt.txt").write_text(task["prompt"] + "\n")
                names.append(name)
    (eval_root / "plan.json").write_text(json.dumps(names, indent=1))
    print(f"built {len(names)} fixtures in {runs}")


if __name__ == "__main__":
    main()
