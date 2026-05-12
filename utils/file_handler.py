import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ORDERS_FILE = DATA_DIR / "order.json"
MENU_FILE = DATA_DIR / "menu.json"


def load_orders():
    if not ORDERS_FILE.exists():
        return []
    try:
        with ORDERS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_orders(orders):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with ORDERS_FILE.open("w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)


def load_menu():
    with MENU_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)
