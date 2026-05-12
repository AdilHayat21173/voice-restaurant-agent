from utils.file_handler import load_menu


def get_menu():
    """Return the full menu with item names and prices in PKR."""
    menu = load_menu()
    lines = [f"{name}: Rs. {price}" for name, price in menu.items()]
    menu_text = "\n".join(lines)
    return {
        "success": True,
        "message": f"Here is our current menu:\n{menu_text}",
        "menu": menu
    }
