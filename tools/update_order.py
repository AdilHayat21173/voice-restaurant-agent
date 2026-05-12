from utils.file_handler import load_orders, save_orders, load_menu
from utils.validators import validate_items


def update_order(order_id: str, new_items: list):
    """Replace items in an existing active order."""
    order_id = str(order_id).strip().upper()
    orders = load_orders()
    menu = load_menu()

    for order in orders:
        if str(order.get("order_id", "")).upper() == order_id:
            if order.get("status") == "cancelled":
                return {"success": False, "message": f"Order {order_id} is cancelled and cannot be modified."}

            valid_items = validate_items(new_items)
            if not valid_items:
                return {"success": False, "message": "No valid menu items found. Please check the menu."}

            total_price = sum(menu[item["name"]] * item["qty"] for item in valid_items)
            order["items"] = valid_items
            order["total_price"] = total_price
            save_orders(orders)

            items_summary = ", ".join(f"{item['qty']}x {item['name']}" for item in valid_items)
            return {
                "success": True,
                "message": f"Order {order_id} updated successfully! New items: {items_summary}. New total: Rs. {total_price}.",
                "order_id": order_id,
                "total_price": total_price,
                "items": valid_items,
            }

    return {"success": False, "message": f"Order {order_id} not found. Please check your order ID."}
