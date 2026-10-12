class Order:
    def __init__(self, total_cents):
        self.total_cents = total_cents
        self.refunded_cents = 0


def refund(order, amount_cents):
    if amount_cents <= 0 or order.refunded_cents + amount_cents > order.total_cents:
        raise ValueError("invalid refund amount")
    order.refunded_cents += amount_cents
    return order.refunded_cents
