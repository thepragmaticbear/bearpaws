import unittest

from src.cart import Cart


class CartTest(unittest.TestCase):
    def test_total(self):
        cart = Cart()
        cart.add_item("apple", 1.5, 2)
        cart.add_item("pear", 2.0)
        self.assertEqual(cart.total(), 5.0)

    def test_rejects_negative_price(self):
        with self.assertRaises(ValueError):
            Cart().add_item("x", -1)


if __name__ == "__main__":
    unittest.main()
