import ast
import os
import unittest
from contextlib import ExitStack
from unittest import mock
import src.money

from src.invoice import invoice_line
from src.money import format_money
from src.receipt import receipt_total
from src.report import report_row


class Accept(unittest.TestCase):
    def test_reference(self):
        self.assertEqual(format_money(1234.5, "USD"), "$1,234.50")
        self.assertEqual(format_money(0.456, "EUR"), "€0.46")
        self.assertEqual(format_money(1500.4, "JPY"), "¥1,500")

    def test_modules_use_it(self):
        self.assertEqual(invoice_line("pen", 1234.5, "USD"), "pen: $1,234.50")
        self.assertEqual(receipt_total([1000, 234.5], "USD"), "TOTAL $1,234.50")
        self.assertEqual(receipt_total([100], "JPY"), "TOTAL ¥100")
        self.assertEqual(report_row("a", 1234.5, "EUR"), "a         €1,234.50")
        # Patch the shared function and any directly imported aliases.
        for func, args in ((invoice_line, ("pen", 3, "USD")),
                           (receipt_total, ([1, 2], "USD")),
                           (report_row, ("a", 3, "USD"))):
            with ExitStack() as stack:
                spy = mock.Mock(wraps=src.money.format_money)
                aliases = {k: spy for k, v in func.__globals__.items() if v is src.money.format_money}
                stack.enter_context(mock.patch.dict(func.__globals__, aliases))
                stack.enter_context(mock.patch.object(src.money, "format_money", spy))
                func(*args)
                spy.assert_called_with(3, "USD")

    def test_no_duplicate_formatters(self):
        # Only src/money.py may contain currency symbol tables.
        for name in ("invoice.py", "receipt.py", "report.py"):
            src = open(os.path.join("src", name), encoding="utf-8").read()
            self.assertNotIn("€", src, name)
            self.assertNotIn("%.2f", src, name)
