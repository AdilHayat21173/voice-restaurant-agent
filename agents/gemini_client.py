import os
from dotenv import load_dotenv
import google.genai as genai
from google.genai import types

from agents.prompts import system_prompt

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is missing. Add it in your .env file.")

client = genai.Client(api_key=api_key)

# Tool declarations sent to Gemini so it knows which local functions it can call.
TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="get_menu",
                description="Return the full restaurant menu with item names and prices in PKR.",
                parameters=types.Schema(type=types.Type.OBJECT, properties={}),
            ),
            types.FunctionDeclaration(
                name="place_order",
                description=(
                    "Place a new food order after collecting customer name, phone, "
                    "address or dine-in, and all items with quantities."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "customer_name": types.Schema(type=types.Type.STRING),
                        "phone": types.Schema(type=types.Type.STRING),
                        "address": types.Schema(type=types.Type.STRING),
                        "items": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "name": types.Schema(type=types.Type.STRING),
                                    "qty": types.Schema(type=types.Type.INTEGER),
                                },
                                required=["name", "qty"],
                            ),
                        ),
                    },
                    required=["customer_name", "phone", "address", "items"],
                ),
            ),
            types.FunctionDeclaration(
                name="cancel_order",
                description="Cancel an existing active order using its order ID.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"order_id": types.Schema(type=types.Type.STRING)},
                    required=["order_id"],
                ),
            ),
            types.FunctionDeclaration(
                name="update_order",
                description="Replace the items in an existing active order.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "order_id": types.Schema(type=types.Type.STRING),
                        "items": types.Schema(
                            type=types.Type.ARRAY,
                            items=types.Schema(
                                type=types.Type.OBJECT,
                                properties={
                                    "name": types.Schema(type=types.Type.STRING),
                                    "qty": types.Schema(type=types.Type.INTEGER),
                                },
                                required=["name", "qty"],
                            ),
                        ),
                    },
                    required=["order_id", "items"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_order_status",
                description="Check the current status of an order by its order ID.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={"order_id": types.Schema(type=types.Type.STRING)},
                    required=["order_id"],
                ),
            ),
        ]
    )
]

# Keep automatic activity detection ON. This is the main fix for:
# first question works, second question is not captured.
LIVE_CONFIG = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
        )
    ),
    system_instruction=system_prompt,
    tools=TOOLS,
)
