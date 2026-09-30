import unittest

from src.invoice import invoice_line


class InvoiceTest(unittest.TestCase):
    def test_line(self):
        self.assertEqual(invoice_line("pen", 1234.5, "USD"), "pen: $1,234.50")
