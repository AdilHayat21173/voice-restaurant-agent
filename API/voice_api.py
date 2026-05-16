import asyncio
from contextlib import suppress

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.genai import types
from websockets.exceptions import ConnectionClosed

from agents.gemini_client import client, LIVE_CONFIG
from agents.tool_handler import handle_tool_call
from config import MODEL

app = FastAPI(title="Voice Restaurant Agent WebSocket API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {"message": "Voice Agent API is running"}


async def run_one_turn(websocket: WebSocket, audio_queue: asyncio.Queue) -> bool:
    """
    Opens ONE Gemini Live session, streams audio from the queue into it,
    plays the response back to the browser, then closes the Gemini session.

    Returns True  → browser still connected, loop again for next turn.
    Returns False → browser disconnected, stop looping.
    """
    print("[TURN] Opening fresh Gemini Live session...")

    try:
        async with client.aio.live.connect(model=MODEL, config=LIVE_CONFIG) as session:
            print("[TURN] Gemini session open")

            turn_done  = asyncio.Event()
            browser_ok = True

            # ── Task 1: drain audio_queue → Gemini ──────────────────────────
            async def send_audio():
                try:
                    while not turn_done.is_set():
                        try:
                            chunk = await asyncio.wait_for(audio_queue.get(), timeout=0.1)
                        except asyncio.TimeoutError:
                            continue
                        await session.send_realtime_input(
                            audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                        )
                except Exception as e:
                    print(f"[SEND] Error: {repr(e)}")
                finally:
                    print("[SEND] Audio sender done")

            # ── Task 2: Gemini → browser ─────────────────────────────────────
            async def recv_audio():
                nonlocal browser_ok
                try:
                    async for response in session.receive():

                        # Audio chunk
                        if getattr(response, "data", None):
                            await websocket.send_bytes(response.data)

                        # Tool calls
                        tool_call = getattr(response, "tool_call", None)
                        if tool_call:
                            tool_responses = []
                            for fn_call in tool_call.function_calls:
                                result_str = handle_tool_call(
                                    tool_name=fn_call.name,
                                    args=dict(fn_call.args) if fn_call.args else {},
                                )
                                print(f"[TOOL] {fn_call.name} -> {result_str}")
                                tool_responses.append(
                                    types.FunctionResponse(
                                        id=fn_call.id,
                                        name=fn_call.name,
                                        response={"result": result_str},
                                    )
                                )
                            await session.send_tool_response(function_responses=tool_responses)

                        # Server content / turn complete
                        server_content = getattr(response, "server_content", None)
                        if server_content:
                            if getattr(server_content, "turn_complete", False):
                                print("[TURN] turn_complete received")
                                turn_done.set()
                                break   # exit loop; Gemini session closes cleanly

                            model_turn = getattr(server_content, "model_turn", None)
                            if model_turn:
                                for part in getattr(model_turn, "parts", []) or []:
                                    text    = getattr(part, "text", None)
                                    thought = getattr(part, "thought", False)
                                    if text and not thought:
                                        print(f"[Gemini] {text}")

                except WebSocketDisconnect:
                    print("[RECV] Browser disconnected during recv")
                    browser_ok = False
                    turn_done.set()

                except Exception as e:
                    print(f"[RECV] Error: {repr(e)}")
                    turn_done.set()

                finally:
                    print("[RECV] Receiver done")

            send_task = asyncio.create_task(send_audio(), name="send_audio")
            recv_task = asyncio.create_task(recv_audio(), name="recv_audio")

            await turn_done.wait()

            send_task.cancel()
            with suppress(asyncio.CancelledError):
                await send_task

            with suppress(Exception):
                await asyncio.wait_for(recv_task, timeout=2.0)

        print("[TURN] Gemini session closed cleanly")

    except Exception as e:
        print(f"[TURN] Session error: {repr(e)}")

    return browser_ok


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    print("\n" + "=" * 60)
    print("[WS] Browser connected")

    audio_queue: asyncio.Queue = asyncio.Queue()

    async def browser_reader():
        try:
            while True:
                chunk = await websocket.receive_bytes()
                await audio_queue.put(chunk)
        except WebSocketDisconnect:
            print("[BROWSER] Browser disconnected")
        except Exception as e:
            print(f"[BROWSER] Reader error: {repr(e)}")

    reader_task = asyncio.create_task(browser_reader(), name="browser_reader")

    turn_number = 0
    try:
        while True:
            turn_number += 1
            print(f"\n[WS] Starting turn {turn_number}")

            still_connected = await run_one_turn(websocket, audio_queue)

            if not still_connected:
                print("[WS] Browser gone - stopping")
                break

            try:
                await websocket.send_text("__TURN_COMPLETE__")
                print(f"[WS] Turn {turn_number} done - ready for next question")
            except Exception:
                print("[WS] Could not send __TURN_COMPLETE__ - browser disconnected")
                break

    except Exception as e:
        print(f"[WS] Outer loop error: {repr(e)}")

    finally:
        reader_task.cancel()
        with suppress(asyncio.CancelledError):
            await reader_task
        with suppress(Exception):
            await websocket.close()
        print(f"[WS] Closed after {turn_number} turns\n" + "=" * 60)


if __name__ == "__main__":
    uvicorn.run(
        "API.voice_api:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        ws_ping_interval=60,
        ws_ping_timeout=60,
    )