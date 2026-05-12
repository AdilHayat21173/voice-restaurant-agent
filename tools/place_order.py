from utils.file_handler import load_orders, save_orders, load_menu
from utils.order_id import generate_order_id
from utils.validators import validate_items


def place_order(customer_name: str, phone: str, address: str, items: list):
    """Place a new order. Returns order details including the new order ID."""
    orders = load_orders()
    menu = load_menu()

    valid_items = validate_items(items)
    if not valid_items:
        return {
            "success": False,
            "message": "No valid menu items found in your order. Please check the menu."
        }

    total_price = sum(
        menu[item["name"]] * item["qty"]
        for item in valid_items
        if item["name"] in menu
    )

    order_id = generate_order_id()

    order = {
        "order_id": order_id,
        "customer_name": customer_name,
        "phone": phone,
        "address": address,
        "items": valid_items,
        "total_price": total_price,
        "status": "active"
    }

    orders.append(order)
    save_orders(orders)

    items_summary = ", ".join(
        f"{item['qty']}x {item['name']}" for item in valid_items
    )

    return {
        "success": True,
        "message": (
            f"Order placed successfully! Your order ID is {order_id}. "
            f"You ordered: {items_summary}. Total: Rs. {total_price}. "
            f"Please save your order ID {order_id} to track, modify or cancel your order."
        ),
        "order_id": order_id,
        "total_price": total_price,
        "items": valid_items
    }
