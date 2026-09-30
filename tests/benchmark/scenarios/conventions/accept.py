import ast
import importlib
import os
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from src.errors import AppError
from src.store import ORDERS


class Accept(unittest.TestCase):
    def setUp(self):
        ORDERS.clear()
        self.mod = importlib.import_module("src.services.cancel_order")

    def test_cancel(self):
        ORDERS["1"] = {"status": "pending"}
        self.assertEqual(self.mod.cancel_order("1")["status"], "cancelled")

    def test_errors_are_app_errors(self):
        with self.assertRaises(AppError):
            self.mod.cancel_order("missing")
        ORDERS["2"] = {"status": "shipped"}
        with self.assertRaises(AppError):
            self.mod.cancel_order("2")
        self.assertEqual(ORDERS["2"]["status"], "shipped")

    def test_conventions(self):
        src = Path("src/services/cancel_order.py").read_text()
        tree = ast.parse(src)
        calls = [n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertNotIn("print", calls)
        with mock.patch("src.log.get_logger") as factory:
            importlib.reload(self.mod)
            factory.assert_called_with(self.mod.__name__)
            ORDERS["log-check"] = {"status": "pending"}
            self.mod.cancel_order("log-check")
            self.assertTrue(factory.return_value.method_calls, "service must log via get_logger")
        first = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"],
                               capture_output=True, text=True, check=True).stdout.strip()
        changes = subprocess.run(["git", "diff", first, "--", "src/legacy"],
                                 capture_output=True, text=True, check=True).stdout
        self.assertEqual(changes, "", "src/legacy is frozen")
        self.assertTrue(os.path.exists(os.path.join("tests", "services", "test_cancel_order.py")))
