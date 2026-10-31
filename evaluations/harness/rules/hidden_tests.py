"""Hidden behavior tests for the rules scenarios that change the slop tasks.

Usage: python3 hidden_tests.py <fixture> <scenario>
Scenario M uses the slop hidden tests for its task; Q uses slop T3.
"""
import sys
import unittest
from datetime import date

FIXTURE, SCENARIO = sys.argv[1], sys.argv[2]
del sys.argv[1:3]
sys.path.insert(0, FIXTURE)


class C(unittest.TestCase):
    def setUp(self):
        from inventory import handlers
        from inventory.store import InMemoryStore
        self.handlers, self.store = handlers, InMemoryStore()
        self.call("create_item", {"sku": "A1", "name": "Bolt", "quantity": 5})
        self.call("create_item", {"sku": "B2", "name": "Nut", "quantity": 50})

    def call(self, handler, payload):
        return getattr(self.handlers, handler)(payload, store=self.store)

    def quantity(self, sku):
        return self.call("get_item", {"sku": sku})["data"]["quantity"]

    def assert_code(self, result, code):
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], code)

    def test_adjust(self):
        self.assertTrue(self.call("adjust_quantity", {"sku": "A1", "delta": -2})["ok"])
        self.assertEqual(self.quantity("A1"), 3)

    def test_adjust_never_below_zero(self):
        self.assertFalse(self.call("adjust_quantity", {"sku": "A1", "delta": -6})["ok"])
        self.assertEqual(self.quantity("A1"), 5)

    def test_restock_adds(self):
        self.assertTrue(self.call("restock", {"sku": "A1", "amount": 3})["ok"])
        self.assertEqual(self.quantity("A1"), 8)

    def test_restock_rejects_zero_and_negative(self):
        for amount in (0, -1):
            self.assert_code(self.call("restock", {"sku": "A1", "amount": amount}), "invalid_input")
        self.assertEqual(self.quantity("A1"), 5)

    def test_low_stock(self):
        result = self.call("low_stock", {"threshold": 10})
        self.assertTrue(result["ok"])
        self.assertIn("A1", str(result["data"]))
        self.assertNotIn("B2", str(result["data"]))

    def test_remove_item(self):
        from inventory.audit import AUDIT_LOG
        before = len(AUDIT_LOG)
        self.assertTrue(self.call("remove_item", {"sku": "A1"})["ok"])
        self.assert_code(self.call("get_item", {"sku": "A1"}), "not_found")
        self.assertGreater(len(AUDIT_LOG), before)


class X(unittest.TestCase):
    def orders(self, *days):
        from tests.helpers import make_order
        return [make_order(id=str(i), placed_on=day) for i, day in enumerate(days)]

    def test_leaves_out_month_containing_today(self):
        from reports.summaries import monthly_totals
        orders = self.orders(date(2024, 1, 5), date(2024, 2, 5), date(2024, 3, 5))
        self.assertEqual(len(monthly_totals(orders, today=date(2024, 3, 15))), 2)

    def test_today_defaults_to_now(self):
        from reports.summaries import monthly_totals
        self.assertEqual(len(monthly_totals(self.orders(date(2020, 1, 5), date.today()))), 1)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(globals()[SCENARIO])
    result = unittest.TextTestRunner(verbosity=0).run(suite)
    print(f"HIDDEN {result.testsRun - len(result.failures) - len(result.errors)}/{result.testsRun}")
