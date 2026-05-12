from utils.file_handler import load_orders


def get_order_status(order_id: str):
    """Return the current status of an order."""
    order_id = str(order_id).strip().upper()
    orders = load_orders()

    for order in orders:
        if str(order.get("order_id", "")).upper() == order_id:
            items_summary = ", ".join(
                f"{item['qty']}x {item['name']}" for item in order.get("items", [])
            )
            return {
                "success": True,
                "order_id": order_id,
                "status": order.get("status", "unknown"),
                "customer_name": order.get("customer_name", ""),
                "items": order.get("items", []),
                "total_price": order.get("total_price", 0),
                "message": (
                    f"Order {order_id} for {order.get('customer_name', 'customer')} "
                    f"is currently {order.get('status', 'unknown')}. "
                    f"Items: {items_summary}. Total: Rs. {order.get('total_price', 0)}."
                ),
            }

    return {"success": False, "message": f"Order {order_id} not found. Please check your order ID."}
