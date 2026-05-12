"""
Hujra Restaurant Voice Agent
─────────────────────────────
Runs a continuous Gemini Live voice session.
- Streams microphone audio to Gemini
- Plays Gemini audio responses through the speaker
- Intercepts tool_call events and dispatches them to local Python functions
- Sends tool results back so Gemini can continue speaking

Press Ctrl+C to stop.
"""

import asyncio
from contextlib import suppress

from websockets.exceptions import ConnectionClosed
from google.genai import types

from agents.gemini_client import client, LIVE_CONFIG
from agents.tool_handler import handle_tool_call
from audio.input import send_audio
from audio.output import open_speaker_stream, play_audio_chunk
from config import MODEL


async def receive_and_handle(session):
    """
    Receive all responses from Gemini in a single loop.

    Gemini Live sends a stream of response objects. Each one may contain:
      - response.data        → raw PCM audio bytes → play through speaker
      - server_content       → text / model turn content (log only)
      - tool_call            → function call request → dispatch + send result back
    """
    speaker = open_speaker_stream()
    print("🔊 Speaker ready...")

    try:
        while True:
            got_response = False
            async for response in session.receive():
                got_response = True

                # ── 1. Audio chunk: play it ────────────────────────────────────────
                if getattr(response, "data", None):
                    await asyncio.to_thread(play_audio_chunk, speaker, response.data)

                # ── 2. Tool call: dispatch and return result ───────────────────────
                tool_call = getattr(response, "tool_call", None)
                if tool_call:
                    tool_responses = []

                    for fn_call in tool_call.function_calls:
                        # fn_call.name  → tool name (string)
                        # fn_call.args  → dict of arguments
                        # fn_call.id    → unique call ID Gemini uses to match responses

                        result_str = handle_tool_call(
                            tool_name=fn_call.name,
                            args=dict(fn_call.args) if fn_call.args else {}
                        )

                        tool_responses.append(
                            types.FunctionResponse(
                                id=fn_call.id,
                                name=fn_call.name,
                                response={"result": result_str}
                            )
                        )

                    # Send all tool results back to Gemini so it can continue
                    await session.send_tool_response(
                        function_responses=tool_responses
                    )

                # ── 3. Text / thought (optional debug logging) ────────────────────
                server_content = getattr(response, "server_content", None)
                if server_content:
                    model_turn = getattr(server_content, "model_turn", None)
                    if model_turn:
                        for part in getattr(model_turn, "parts", []) or []:
                            text = getattr(part, "text", None)
                            thought = getattr(part, "thought", False)
                            if text and not thought:
                                print(f"[Gemini] {text}")

            if not got_response:
                break
    except ConnectionClosed as exc:
        if exc.code == 1000:
            print("🔌 Gemini session closed cleanly.")
        else:
            print(f"⚠️  Receive connection closed: {exc.code} {exc.reason}")
    except Exception as exc:
        print(f"⚠️  Receive error: {exc}")
    finally:
        with suppress(Exception):
            speaker.stop_stream()
        with suppress(Exception):
            speaker.close()


async def main():
    print("=" * 50)
    print("  Hujra Restaurant Voice Agent")
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    print()
    print("🔗 Connecting to Gemini Live...")

    async with client.aio.live.connect(model=MODEL, config=LIVE_CONFIG) as session:
        print("✅ Connected! You can start speaking.\n")

        # Run microphone capture and response handling concurrently.
        # Stop the session when either task finishes.
        send_task = asyncio.create_task(send_audio(session, types))
        receive_task = asyncio.create_task(receive_and_handle(session))

        done, pending = await asyncio.wait(
            {send_task, receive_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Cancel the surviving task
        for task in pending:
            task.cancel()
        for task in pending:
            with suppress(asyncio.CancelledError):
                await task

        # Re-raise any exception so the user sees it
        for task in done:
            exc = task.exception()
            if exc:
                raise exc


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Voice agent stopped. Goodbye!")
