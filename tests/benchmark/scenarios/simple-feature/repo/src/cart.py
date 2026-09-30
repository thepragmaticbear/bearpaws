class Cart:
    def __init__(self):
        self.items = []

    def add_item(self, name, price, qty=1):
        if price < 0 or qty < 1:
            raise ValueError("invalid item")
        self.items.append((name, price, qty))

    def total(self):
        return round(sum(price * qty for _, price, qty in self.items), 2)
