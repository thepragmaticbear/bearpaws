import unittest

from src.billing import Order, refund


class RefundTest(unittest.TestCase):
    def test_partial_refund(self):
        order = Order(1000)
        refund(order, 500)
        self.assertEqual(order.refunded_cents, 500)


if __name__ == "__main__":
    unittest.main()
