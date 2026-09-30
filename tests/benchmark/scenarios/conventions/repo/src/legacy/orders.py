from src.store import ORDERS


def ship_order(order_id):
    if order_id not in ORDERS:
        print("no such order", order_id)
        raise KeyError(order_id)
    ORDERS[order_id]["status"] = "shipped"
