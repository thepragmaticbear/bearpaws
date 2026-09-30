import unittest

from src.cart import Cart


def cart_of(total):
    c = Cart()
    c.add_item("thing", total)
    return c


class Accept(unittest.TestCase):
    def test_save10(self):
        c = cart_of(20.0)
        c.apply_discount("SAVE10")
        self.assertEqual(c.total(), 18.0)

    def test_flat5(self):
        c = cart_of(20.0)
        c.apply_discount("FLAT5")
        self.assertEqual(c.total(), 15.0)

    def test_flat5_floor(self):
        c = cart_of(3.0)
        c.apply_discount("FLAT5")
        self.assertEqual(c.total(), 0)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            cart_of(10.0).apply_discount("BOGUS")

    def test_replace(self):
        c = cart_of(20.0)
        c.apply_discount("FLAT5")
        c.apply_discount("SAVE10")
        self.assertEqual(c.total(), 18.0)

    def test_rounding(self):
        c = cart_of(9.99)
        c.apply_discount("SAVE10")
        self.assertEqual(c.total(), 8.99)

    def test_no_discount_unchanged(self):
        self.assertEqual(cart_of(7.25).total(), 7.25)
