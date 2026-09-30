from src.errors import AppError
from src.log import get_logger
from src.store import ORDERS

log = get_logger(__name__)


def refund_order(order_id):
    order = ORDERS.get(order_id)
    if order is None:
        raise AppError("not_found", f"order {order_id} not found")
    if order["status"] != "shipped":
        raise AppError("invalid_state", "only shipped orders can be refunded")
    order["status"] = "refunded"
    log.info("refunded %s", order_id)
    return order
