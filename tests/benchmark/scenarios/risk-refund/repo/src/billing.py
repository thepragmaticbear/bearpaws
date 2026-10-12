class Order:
    def __init__(self, total_cents):
        self.total_cents = total_cents
        self.refunded_cents = 0


def refund(order, amount_cents):
    order.refunded_cents += amount_cents
    return order.refunded_cents
