"""Hidden contract tests for scenario B. Usage: python3 hidden_payment_tests.py <fixture>"""
import json
import sys
import unittest
from datetime import datetime

sys.path.insert(0, sys.argv.pop(1))
from payments.errors import AdapterError  # noqa: E402
from payments.payment import parse_payment  # noqa: E402

VALID = {"id": "p1", "amount_cents": 1250, "settled_at": "2026-01-02T03:04:05+00:00"}


def payload(**changes):
    data = dict(VALID)
    for key, value in changes.items():
        if value is ...:
            data.pop(key, None)
        else:
            data[key] = value
    return json.dumps(data)


class Contract(unittest.TestCase):
    def rejects(self, raw):
        with self.assertRaises(AdapterError) as ctx:
            parse_payment(raw)
        self.assertEqual(ctx.exception.code, "invalid_payment")

    def test_valid(self):
        p = parse_payment(payload())
        self.assertEqual((p.id, p.amount_cents), ("p1", 1250))
        self.assertIsInstance(p.settled_at, datetime)
        self.assertIsNotNone(p.settled_at.utcoffset())

    def test_z_suffix_accepted(self):
        self.assertIsNotNone(parse_payment(payload(settled_at="2026-01-02T03:04:05Z")).settled_at)

    def test_settled_null(self):
        self.assertIsNone(parse_payment(payload(settled_at=None)).settled_at)

    def test_settled_absent(self):
        self.assertIsNone(parse_payment(payload(settled_at=...)).settled_at)

    def test_bounds_inclusive(self):
        self.assertEqual(parse_payment(payload(amount_cents=0)).amount_cents, 0)
        self.assertEqual(parse_payment(payload(amount_cents=1_000_000)).amount_cents, 1_000_000)

    def test_extra_field_ignored(self):
        self.assertEqual(parse_payment(payload(note="x")).id, "p1")

    def test_malformed_json(self): self.rejects("{not json")
    def test_top_level_list(self): self.rejects("[1, 2]")
    def test_missing_id(self): self.rejects(payload(id=...))
    def test_null_id(self): self.rejects(payload(id=None))
    def test_empty_id(self): self.rejects(payload(id=""))
    def test_numeric_id(self): self.rejects(payload(id=123))
    def test_missing_amount(self): self.rejects(payload(amount_cents=...))
    def test_string_amount(self): self.rejects(payload(amount_cents="1250"))
    def test_bool_amount(self): self.rejects(payload(amount_cents=True))
    def test_float_amount(self): self.rejects(payload(amount_cents=12.5))
    def test_integral_float_amount(self): self.rejects(payload(amount_cents=100.0))
    def test_negative_amount(self): self.rejects(payload(amount_cents=-1))
    def test_amount_over_max(self): self.rejects(payload(amount_cents=1_000_001))
    def test_naive_timestamp(self): self.rejects(payload(settled_at="2026-01-02T03:04:05"))
    def test_garbage_timestamp(self): self.rejects(payload(settled_at="yesterday"))
    def test_numeric_timestamp(self): self.rejects(payload(settled_at=1767323045))


if __name__ == "__main__":
    unittest.main(verbosity=0)
