from utils.file_handler import load_menu


def _normalize(text: str) -> str:
    return " ".join(str(text).lower().strip().split())


def validate_items(items):
    """Return only valid menu items and normalize spoken names to exact menu names."""
    menu = load_menu()
    menu_lookup = {_normalize(name): name for name in menu.keys()}

    valid = []
    for item in items or []:
        raw_name = item.get("name", "")
        qty = item.get("qty", 0)

        try:
            qty = int(qty)
        except (TypeError, ValueError):
            qty = 0

        exact_name = menu_lookup.get(_normalize(raw_name))
        if exact_name and qty > 0:
            valid.append({"name": exact_name, "qty": qty})

    return valid
