import asyncio
import json
import time
import traceback
from contextlib import suppress
from datetime import datetime
from typing import Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.genai import types

from agents.gemini_client import client, LIVE_CONFIG
from agents.tool_handler import handle_tool_call
from agents.prompts import system_prompt
from config import MODEL


app = FastAPI(title="Voice Restaurant Agent WebSocket API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# DEBUG / ERROR LOG HELPERS
# =========================
DEBUG = True
LOG_EVERY_AUDIO_CHUNKS = 50  # print every 50 mic/audio chunks so terminal is not too noisy


def now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def log(area: str, msg: str) -> None:
    print(f"[{now()}] [{area}] {msg}", flush=True)


def log_error(area: str, msg: str, exc: BaseException | None = None) -> None:
    print(f"\n[{now()}] [ERROR:{area}] {msg}", flush=True)
    if exc is not None:
        print(f"[{now()}] [ERROR:{area}] {repr(exc)}", flush=True)
        traceback.print_exception(type(exc), exc, exc.__traceback__)
    print("", flush=True)


def short(obj: Any, limit: int = 500) -> str:
    try:
        text = str(obj)
    except Exception:
        text = repr(obj)
    return text if len(text) <= limit else text[:limit] + "..."


@app.get("/")
def home():
    return {"message": "Voice Agent API is running"}


@app.get("/debug")
def debug_status():
    return {
        "message": "Debug logging is enabled" if DEBUG else "Debug logging is disabled",
        "model": MODEL,
        "audio_input_mime": "audio/pcm;rate=16000",
    }


def build_live_config() -> types.LiveConnectConfig:
    """
    One browser WebSocket connection = one Gemini Live session.
    Do not re-create session after every question.
    """
    injected_prompt = (
        system_prompt
        + "\n\nIMPORTANT CONVERSATION RULES:\n"
        + "- You are already connected with the customer after your first greeting.\n"
        + "- Do not introduce yourself again after every question.\n"
        + "- Keep the order state in memory during this same call.\n"
        + "- Remember items the customer added, removed, delivery/dine-in choice, name, phone, and address.\n"
        + "- If the customer says 'add', 'remove', 'change', or asks 'total now', use the existing order context.\n"
    )

    # Some SDK versions expose different fields on LIVE_CONFIG. getattr keeps this safe.
    return types.LiveConnectConfig(
        response_modalities=getattr(LIVE_CONFIG, "response_modalities", ["AUDIO"]),
        speech_config=getattr(LIVE_CONFIG, "speech_config", None),
        system_instruction=injected_prompt,
        tools=getattr(LIVE_CONFIG, "tools", None),
    )


async def safe_send_text(websocket: WebSocket, text: str) -> bool:
    try:
        await websocket.send_text(text)
        if DEBUG:
            log("WS->BROWSER", f"text sent: {text}")
        return True
    except Exception as e:
        log_error("WS->BROWSER", "send_text failed. Browser may be closed.", e)
        return False


async def safe_send_bytes(websocket: WebSocket, data: bytes, audio_out_count: int) -> bool:
    try:
        await websocket.send_bytes(data)
        if DEBUG and audio_out_count % LOG_EVERY_AUDIO_CHUNKS == 0:
            log("WS->BROWSER", f"audio chunks sent: {audio_out_count}, last_size={len(data)} bytes")
        return True
    except Exception as e:
        log_error("WS->BROWSER", "send_bytes failed. Browser may be closed.", e)
        return False


async def send_audio_to_gemini(session: Any, chunk: bytes, audio_in_count: int) -> bool:
    try:
        await session.send_realtime_input(
            audio=types.Blob(
                data=chunk,
                mime_type="audio/pcm;rate=16000",
            )
        )
        if DEBUG and audio_in_count % LOG_EVERY_AUDIO_CHUNKS == 0:
            log("BROWSER->GEMINI", f"audio chunks received/sent: {audio_in_count}, last_size={len(chunk)} bytes")
        return True
    except Exception as e:
        log_error(
            "BROWSER->GEMINI",
            "Failed to send mic audio to Gemini. Check audio format/sample-rate and Gemini session state.",
            e,
        )
        return False


@app.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()

    connection_started = time.time()
    log("WS", "=" * 60)
    log("WS", "Browser connected")
    log("WS", f"Using model: {MODEL}")
    log("WS", "Opening ONE Gemini Live session for the full browser conversation")

    config = build_live_config()

    # Debug counters
    audio_in_count = 0
    audio_out_count = 0
    gemini_response_count = 0
    turn_count = 0
    tool_count = 0
    browser_text_count = 0
    last_browser_audio_at: float | None = None
    last_gemini_audio_at: float | None = None
    conversation_events: list[str] = []

    stop_event = asyncio.Event()
    stop_reason = "unknown"

    try:
        try:
            session_cm = client.aio.live.connect(model=MODEL, config=config)
        except Exception as e:
            log_error("GEMINI", "Could not create Gemini Live connection context. Check API key/model/config.", e)
            await safe_send_text(websocket, "__ERROR__: Could not connect to Gemini Live")
            return

        async with session_cm as session:
            log("GEMINI", "Live session open successfully")

            async def browser_to_gemini():
                nonlocal audio_in_count, browser_text_count, last_browser_audio_at, stop_reason
                log("TASK", "browser_to_gemini started")
                try:
                    while not stop_event.is_set():
                        try:
                            message = await websocket.receive()
                        except WebSocketDisconnect:
                            stop_reason = "browser disconnected"
                            log("BROWSER", "WebSocketDisconnect while receiving from browser")
                            stop_event.set()
                            break
                        except Exception as e:
                            stop_reason = "browser receive error"
                            log_error("BROWSER", "Error while receiving browser message", e)
                            stop_event.set()
                            break

                        msg_type = message.get("type")

                        if msg_type == "websocket.disconnect":
                            stop_reason = "browser websocket.disconnect"
                            log("BROWSER", "Browser disconnected message received")
                            stop_event.set()
                            break

                        chunk = message.get("bytes")
                        if chunk is not None:
                            if not chunk:
                                if DEBUG:
                                    log("BROWSER", "empty bytes chunk ignored")
                                continue

                            audio_in_count += 1
                            last_browser_audio_at = time.time()

                            ok = await send_audio_to_gemini(session, chunk, audio_in_count)
                            if not ok:
                                stop_reason = "failed sending audio to Gemini"
                                await safe_send_text(websocket, "__ERROR__: Failed sending audio to Gemini")
                                stop_event.set()
                                break
                            continue

                        text = message.get("text")
                        if text is not None:
                            text = text.strip()
                            browser_text_count += 1
                            log("BROWSER TEXT", f"#{browser_text_count}: {text}")
                            conversation_events.append(f"Frontend text: {text}")

                            if text == "__STOP__":
                                stop_reason = "frontend sent __STOP__"
                                stop_event.set()
                                break

                            if text == "__PING__":
                                await safe_send_text(websocket, "__PONG__")
                                continue

                            # Optional debug: if your frontend sends typed text, this logs it.
                            # For Live audio, user text should normally not be sent here.
                            continue

                        log("BROWSER", f"Unknown websocket message keys: {list(message.keys())}")

                except asyncio.CancelledError:
                    log("TASK", "browser_to_gemini cancelled")
                except Exception as e:
                    stop_reason = "browser_to_gemini crashed"
                    log_error("TASK", "browser_to_gemini crashed", e)
                    stop_event.set()
                finally:
                    log("TASK", f"browser_to_gemini done | audio_in={audio_in_count}, text_in={browser_text_count}")

            async def gemini_to_browser():
                nonlocal audio_out_count, gemini_response_count, turn_count, tool_count, last_gemini_audio_at, stop_reason
                log("TASK", "gemini_to_browser started")
                try:
                    # IMPORTANT:
                    # Some Gemini Live SDK versions finish one session.receive() iterator after one turn.
                    # Therefore we call session.receive() repeatedly. If receive() returns immediately,
                    # we log it so you can see the exact issue in terminal.
                    receive_loop_count = 0

                    while not stop_event.is_set():
                        receive_loop_count += 1
                        log("RECV", f"Opening session.receive() loop #{receive_loop_count}. Waiting for Gemini response...")

                        got_any_response_this_loop = False
                        loop_started = time.time()

                        try:
                            async for response in session.receive():
                                got_any_response_this_loop = True
                                gemini_response_count += 1

                                if DEBUG:
                                    # Shows what kind of response arrived without dumping huge audio bytes.
                                    has_data = getattr(response, "data", None) is not None
                                    has_tool = getattr(response, "tool_call", None) is not None
                                    has_server = getattr(response, "server_content", None) is not None
                                    if gemini_response_count <= 5 or gemini_response_count % 25 == 0:
                                        log(
                                            "GEMINI RESP",
                                            f"#{gemini_response_count}: data={has_data}, tool={has_tool}, server_content={has_server}",
                                        )

                                # 1) Gemini audio bytes -> browser
                                data = getattr(response, "data", None)
                                if data:
                                    audio_out_count += 1
                                    last_gemini_audio_at = time.time()
                                    ok = await safe_send_bytes(websocket, data, audio_out_count)
                                    if not ok:
                                        stop_reason = "failed sending Gemini audio to browser"
                                        stop_event.set()
                                        break

                                # 2) Tool calls
                                tool_call = getattr(response, "tool_call", None)
                                if tool_call:
                                    tool_responses = []
                                    fn_calls = getattr(tool_call, "function_calls", []) or []
                                    log("TOOL", f"Gemini requested {len(fn_calls)} tool call(s)")

                                    for fn_call in fn_calls:
                                        tool_count += 1
                                        args = dict(fn_call.args) if getattr(fn_call, "args", None) else {}
                                        log("TOOL", f"#{tool_count} called: {fn_call.name} | args={args}")

                                        try:
                                            result_str = handle_tool_call(
                                                tool_name=fn_call.name,
                                                args=args,
                                            )
                                        except Exception as e:
                                            log_error("TOOL", f"Tool crashed: {fn_call.name}", e)
                                            result_str = json.dumps(
                                                {
                                                    "success": False,
                                                    "error": f"Tool crashed: {repr(e)}",
                                                }
                                            )

                                        log("TOOL", f"#{tool_count} result: {short(result_str, 700)}")
                                        conversation_events.append(
                                            f"Tool {fn_call.name}({json.dumps(args)}) -> {short(result_str, 500)}"
                                        )

                                        tool_responses.append(
                                            types.FunctionResponse(
                                                id=fn_call.id,
                                                name=fn_call.name,
                                                response={"result": result_str},
                                            )
                                        )

                                    try:
                                        await session.send_tool_response(function_responses=tool_responses)
                                        log("TOOL", "Tool response sent back to Gemini")
                                    except Exception as e:
                                        stop_reason = "failed sending tool response"
                                        log_error("TOOL", "Failed to send tool response back to Gemini", e)
                                        await safe_send_text(websocket, "__ERROR__: Failed sending tool response")
                                        stop_event.set()
                                        break

                                # 3) Server content / text / turn complete
                                server_content = getattr(response, "server_content", None)
                                if server_content:
                                    model_turn = getattr(server_content, "model_turn", None)
                                    if model_turn:
                                        for part in getattr(model_turn, "parts", []) or []:
                                            text = getattr(part, "text", None)
                                            thought = getattr(part, "thought", False)
                                            if text and not thought:
                                                log("GEMINI TEXT", text)
                                                conversation_events.append(f"Assistant said: {text}")

                                    if getattr(server_content, "turn_complete", False):
                                        turn_count += 1
                                        log("TURN", f"turn_complete #{turn_count} received")
                                        ok = await safe_send_text(websocket, "__TURN_COMPLETE__")
                                        if not ok:
                                            stop_reason = "failed sending turn_complete to browser"
                                            stop_event.set()
                                        break

                            if stop_event.is_set():
                                break

                            duration = time.time() - loop_started
                            if got_any_response_this_loop:
                                log("RECV", f"session.receive() loop #{receive_loop_count} ended after {duration:.2f}s. Re-opening for next user turn.")
                            else:
                                log(
                                    "RECV",
                                    f"WARNING: session.receive() loop #{receive_loop_count} ended with NO responses after {duration:.2f}s. Re-opening after small delay.",
                                )
                                await asyncio.sleep(0.2)

                        except asyncio.CancelledError:
                            log("TASK", "gemini_to_browser cancelled inside receive loop")
                            raise
                        except Exception as e:
                            stop_reason = "Gemini receive error"
                            log_error(
                                "GEMINI RECEIVE",
                                "Error while reading Gemini response. This is where second-message/no-response issues usually appear.",
                                e,
                            )
                            await safe_send_text(websocket, f"__ERROR__: Gemini receive error: {repr(e)}")
                            stop_event.set()
                            break

                except asyncio.CancelledError:
                    log("TASK", "gemini_to_browser cancelled")
                except Exception as e:
                    stop_reason = "gemini_to_browser crashed"
                    log_error("TASK", "gemini_to_browser crashed", e)
                    stop_event.set()
                finally:
                    log(
                        "TASK",
                        f"gemini_to_browser done | responses={gemini_response_count}, audio_out={audio_out_count}, turns={turn_count}, tools={tool_count}",
                    )

            async def watchdog():
                """
                Prints heartbeat logs. This helps you see if audio is reaching server
                but Gemini is not responding, or if browser stopped sending audio.
                """
                try:
                    while not stop_event.is_set():
                        await asyncio.sleep(5)
                        if stop_event.is_set():
                            break

                        now_ts = time.time()
                        in_age = "never" if last_browser_audio_at is None else f"{now_ts - last_browser_audio_at:.1f}s ago"
                        out_age = "never" if last_gemini_audio_at is None else f"{now_ts - last_gemini_audio_at:.1f}s ago"

                        log(
                            "WATCH",
                            "alive | "
                            f"audio_in={audio_in_count}, audio_out={audio_out_count}, "
                            f"turns={turn_count}, tools={tool_count}, "
                            f"last_browser_audio={in_age}, last_gemini_audio={out_age}",
                        )
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    log_error("WATCH", "watchdog crashed", e)

            send_task = asyncio.create_task(browser_to_gemini(), name="browser_to_gemini")
            recv_task = asyncio.create_task(gemini_to_browser(), name="gemini_to_browser")
            watch_task = asyncio.create_task(watchdog(), name="watchdog")

            # Wait until either stop_event is set or one task crashes unexpectedly.
            stop_task = asyncio.create_task(stop_event.wait(), name="stop_event_wait")
            done, pending = await asyncio.wait(
                {send_task, recv_task, watch_task, stop_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in done:
                if task is stop_task:
                    continue
                if task.cancelled():
                    log("TASK", f"{task.get_name()} ended as cancelled")
                    continue
                exc = task.exception()
                if exc:
                    log_error("TASK", f"{task.get_name()} ended with exception", exc)
                    stop_reason = f"{task.get_name()} exception"
                    stop_event.set()

            # Clean shutdown
            for task in [send_task, recv_task, watch_task, stop_task]:
                if not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task

    except asyncio.CancelledError:
        stop_reason = "server shutdown / cancelled"
        log("WS", "Cancelled / server shutdown")
        # Do not re-raise, otherwise uvicorn prints a scary traceback on Ctrl+C.
    except Exception as e:
        stop_reason = "outer websocket error"
        log_error("WS", "Outer Gemini/WebSocket error", e)
        with suppress(Exception):
            await safe_send_text(websocket, f"__ERROR__: Server error: {repr(e)}")
    finally:
        with suppress(Exception):
            await websocket.close()

        elapsed = time.time() - connection_started
        log("WS", f"Closed. reason={stop_reason}, elapsed={elapsed:.1f}s")
        log(
            "WS",
            f"Final counters: audio_in={audio_in_count}, audio_out={audio_out_count}, "
            f"gemini_responses={gemini_response_count}, turns={turn_count}, tools={tool_count}, "
            f"browser_text={browser_text_count}, events={len(conversation_events)}",
        )
        if conversation_events:
            log("WS", "Conversation events preview:")
            for i, event in enumerate(conversation_events[-10:], start=1):
                log("WS", f"  {i}. {short(event, 300)}")
        log("WS", "=" * 60)


if __name__ == "__main__":
    uvicorn.run(
        "API.voice_api:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        ws_ping_interval=60,
        ws_ping_timeout=60,
    )
