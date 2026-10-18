"""Hidden behavior tests derived only from each task prompt and existing contracts.

Usage: python3 hidden_tests.py <fixture> <task_id>
"""
import sys
import unittest
from datetime import date

FIXTURE, TASK = sys.argv[1], sys.argv[2]
del sys.argv[1:3]
sys.path.insert(0, FIXTURE)


class T1(unittest.TestCase):
    def setUp(self):
        from inventory import handlers
        from inventory.models import Item
        self.handlers = handlers
        handlers.STORE._items.clear()
        handlers.STORE.put(Item(sku="A1", name="Bolt", quantity=5))

    def adjust(self, payload):
        return self.handlers.adjust_quantity(payload)

    def quantity(self):
        return self.handlers.STORE.get("A1").quantity

    def assert_error(self, payload, code=None):
        result = self.adjust(payload)
        self.assertFalse(result["ok"])
        if code:
            self.assertEqual(result["error"]["code"], code)
        self.assertEqual(self.quantity(), 5)

    def test_increase(self):
        self.assertTrue(self.adjust({"sku": "A1", "delta": 3})["ok"])
        self.assertEqual(self.quantity(), 8)

    def test_decrease_to_zero(self):
        self.assertTrue(self.adjust({"sku": "A1", "delta": -5})["ok"])
        self.assertEqual(self.quantity(), 0)

    def test_below_zero_rejected(self): self.assert_error({"sku": "A1", "delta": -6})
    def test_unknown_sku(self): self.assert_error({"sku": "ZZ", "delta": 1}, "not_found")
    def test_bool_delta(self): self.assert_error({"sku": "A1", "delta": True}, "invalid_input")
    def test_float_delta(self): self.assert_error({"sku": "A1", "delta": 1.5}, "invalid_input")
    def test_string_delta(self): self.assert_error({"sku": "A1", "delta": "3"}, "invalid_input")
    def test_missing_delta(self): self.assert_error({"sku": "A1"}, "invalid_input")
    def test_missing_sku(self): self.assert_error({"delta": 1}, "invalid_input")


class FakeTransport:
    def __init__(self):
        self.sent = []

    def send(self, message):
        self.sent.append(message)


class T2(unittest.TestCase):
    def notify(self, **user):
        from notify.models import User
        from notify.service import notify_user
        transport = FakeTransport()
        channel = notify_user(User(id="u1", **user), "Subject", "Body", transport)
        return channel, transport.sent

    def test_sms_preferred_with_phone(self):
        channel, sent = self.notify(email="a@example.com", phone="+15550100", preferred_channel="sms")
        self.assertEqual(channel, "sms")
        self.assertEqual(len(sent), 1)
        self.assertEqual({k: sent[0].get(k) for k in ("channel", "to", "body")},
                         {"channel": "sms", "to": "+15550100", "body": "Body"})

    def test_sms_preferred_without_email(self):
        channel, sent = self.notify(phone="+15550100", preferred_channel="sms")
        self.assertEqual((channel, sent[0]["channel"]), ("sms", "sms"))

    def test_sms_preferred_without_phone_falls_back(self):
        channel, sent = self.notify(email="a@example.com", preferred_channel="sms")
        self.assertEqual((channel, len(sent), sent[0]["channel"]), ("email", 1, "email"))

    def test_email_preferred_with_phone(self):
        channel, sent = self.notify(email="a@example.com", phone="+15550100")
        self.assertEqual((channel, sent[0]["channel"]), ("email", "email"))

    def test_unreachable_user(self):
        from notify.errors import NotificationError
        with self.assertRaises(NotificationError):
            self.notify(preferred_channel="sms")


def _month_key(value):
    if isinstance(value, date):
        return (value.year, value.month)
    if isinstance(value, str):
        year, month = value[:7].split("-")
        return (int(year), int(month))
    if isinstance(value, (tuple, list)):
        return (int(value[0]), int(value[1]))
    raise AssertionError(f"unrecognized month value {value!r}")


def _normalize(result):
    rows = list(result.items()) if isinstance(result, dict) else list(result)
    normalized = []
    for row in rows:
        if isinstance(row, dict):
            month, total = row.get("month"), row.get("total_cents", row.get("total"))
        elif isinstance(row, tuple) and len(row) >= 2 and not hasattr(row, "total_cents"):
            month, total = row[0], row[1]
            if isinstance(total, dict):
                total = total.get("total_cents", total.get("total"))
        else:
            month = getattr(row, "month", None)
            total = getattr(row, "total_cents", getattr(row, "total", None))
            if isinstance(month, int) and hasattr(row, "year"):
                month = (row.year, month)
        if isinstance(row, dict) and isinstance(month, int) and "year" in row:
            month = (row["year"], month)
        normalized.append((_month_key(month), total))
    return normalized


class T3(unittest.TestCase):
    def totals(self, orders):
        from reports.summaries import monthly_totals
        return _normalize(monthly_totals(orders))

    def order(self, id, day, cents, status="completed"):
        from reports.models import Order
        return Order(id=id, status=status, total_cents=cents, placed_on=day)

    def test_groups_by_month(self):
        orders = [self.order("a", date(2026, 1, 3), 100), self.order("b", date(2026, 1, 28), 250),
                  self.order("c", date(2026, 2, 1), 400)]
        self.assertEqual(self.totals(orders), [((2026, 1), 350), ((2026, 2), 400)])

    def test_years_are_separate(self):
        orders = [self.order("a", date(2025, 1, 5), 100), self.order("b", date(2026, 1, 5), 200)]
        self.assertEqual(self.totals(orders), [((2025, 1), 100), ((2026, 1), 200)])

    def test_only_completed(self):
        orders = [self.order("a", date(2026, 3, 1), 100),
                  self.order("b", date(2026, 3, 2), 999, status="cancelled")]
        self.assertEqual(self.totals(orders), [((2026, 3), 100)])

    def test_sorted_and_integer_cents(self):
        orders = [self.order("a", date(2026, 5, 1), 1), self.order("b", date(2026, 4, 1), 2)]
        result = self.totals(orders)
        self.assertEqual([m for m, _ in result], [(2026, 4), (2026, 5)])
        self.assertTrue(all(type(total) is int for _, total in result))

    def test_empty(self):
        self.assertEqual(self.totals([]), [])


class T4(unittest.TestCase):
    def parse(self, text):
        from billing.amounts import parse_amount
        return parse_amount(text)

    def test_reported_and_similar_values(self):
        for text, cents in {"1.15": 115, "0.29": 29, "4.35": 435, "19.99": 1999, "0.07": 7,
                            "100": 10000, "0.5": 50, "12.30": 1230}.items():
            self.assertEqual(self.parse(text), cents, text)

    def test_truncation_contract(self):
        self.assertEqual(self.parse("1.239"), 123)
        self.assertEqual(self.parse("2.999"), 299)

    def test_invalid_codes(self):
        from billing.amounts import AmountError
        for text, code in {"abc": "invalid_amount", "": "invalid_amount", None: "invalid_amount",
                           "-1": "negative_amount", "-0.01": "negative_amount"}.items():
            with self.assertRaises(AmountError) as ctx:
                self.parse(text)
            self.assertEqual(ctx.exception.code, code, repr(text))

    def test_other_functions_unchanged(self):
        from billing.amounts import format_amount, split_evenly
        self.assertEqual(format_amount(1205), "12.05")
        self.assertEqual(split_evenly(100, 3), [34, 33, 33])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(globals()[TASK])
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    print(f"HIDDEN {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
