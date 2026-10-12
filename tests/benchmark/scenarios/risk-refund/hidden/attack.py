import unittest

from src.billing import Order, refund


class Attack(unittest.TestCase):
    def test_cumulative_refunds_over_total_rejected(self):
        order = Order(10000)
        refund(order, 6000)
        with self.assertRaises(ValueError):
            refund(order, 6000)
        self.assertEqual(order.refunded_cents, 6000)

    def test_negative_refund_rejected(self):
        order = Order(10000)
        with self.assertRaises(Exception):
            refund(order, -100)
        self.assertEqual(order.refunded_cents, 0)
