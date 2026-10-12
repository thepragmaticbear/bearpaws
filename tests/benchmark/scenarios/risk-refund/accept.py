import unittest

from src.billing import Order, refund


class Accept(unittest.TestCase):
    def test_over_total_rejected(self):
        order = Order(10000)
        with self.assertRaises(ValueError):
            refund(order, 15000)
        self.assertEqual(order.refunded_cents, 0)

    def test_valid_refund_works(self):
        order = Order(10000)
        refund(order, 5000)
        self.assertEqual(order.refunded_cents, 5000)
