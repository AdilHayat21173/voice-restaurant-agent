from utils.file_handler import load_orders, save_orders


def cancel_order(order_id: str):
    """Cancel an order by order ID. Order must be active."""
    order_id = str(order_id).strip().upper()
    orders = load_orders()

    for order in orders:
        if str(order.get("order_id", "")).upper() == order_id:
            if order.get("status") == "cancelled":
                return {"success": False, "message": f"Order {order_id} is already cancelled."}

            order["status"] = "cancelled"
            save_orders(orders)
            return {"success": True, "message": f"Order {order_id} has been cancelled successfully."}

    return {"success": False, "message": f"Order {order_id} not found. Please check your order ID."}
