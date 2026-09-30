import unittest

from src.errors import AppError
from src.services.refund_order import refund_order
from src.store import ORDERS


class RefundTest(unittest.TestCase):
    def setUp(self):
        ORDERS.clear()

    def test_refund(self):
        ORDERS["1"] = {"status": "shipped"}
        self.assertEqual(refund_order("1")["status"], "refunded")

    def test_missing(self):
        with self.assertRaises(AppError):
            refund_order("x")
