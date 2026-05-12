import json

from tools.place_order import place_order
from tools.cancel_order import cancel_order
from tools.update_order import update_order
from tools.get_menu import get_menu
from tools.order_status import get_order_status


def handle_tool_call(tool_name: str, args: dict) -> str:
    """
    Dispatch a tool call from Gemini to the correct Python function.
    Always returns a JSON string so Gemini can read it as a tool response.
    """
    print(f"🔧 Tool called: {tool_name} | Args: {args}")

    try:
        if tool_name == "get_menu":
            result = get_menu()

        elif tool_name == "place_order":
            result = place_order(
                customer_name=args.get("customer_name", ""),
                phone=args.get("phone", ""),
                address=args.get("address", "dine-in"),
                items=args.get("items", [])
            )

        elif tool_name == "cancel_order":
            result = cancel_order(order_id=args.get("order_id", ""))

        elif tool_name == "update_order":
            result = update_order(
                order_id=args.get("order_id", ""),
                new_items=args.get("items", [])
            )

        elif tool_name == "get_order_status":
            result = get_order_status(order_id=args.get("order_id", ""))

        else:
            result = {"success": False, "message": f"Unknown tool: {tool_name}"}

    except Exception as e:
        result = {"success": False, "message": f"Tool error: {str(e)}"}

    print(f"✅ Tool result: {result}")
    return json.dumps(result, ensure_ascii=False)
