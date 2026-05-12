import re
from utils.file_handler import load_orders


def generate_order_id():
    """Generate next sequential order ID in format A1, A2, A3..."""
    orders = load_orders()
    max_number = 0

    for order in orders:
        order_id = str(order.get("order_id", ""))
        match = re.match(r"^A(\d+)$", order_id)
        if match:
            num = int(match.group(1))
            if num > max_number:
                max_number = num

    return f"A{max_number + 1}"
