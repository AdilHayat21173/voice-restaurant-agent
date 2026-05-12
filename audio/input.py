import asyncio
import pyaudio
from config import FORMAT, CHANNELS, SEND_RATE, CHUNK_SIZE

pya = pyaudio.PyAudio()


async def send_audio(session, types):
    """
    Continuously stream microphone audio to Gemini Live.

    Important:
    Do not manually filter voice/silence here. Gemini Live already has
    automatic activity detection. If we only send chunks that cross a local
    threshold, the second/third user question can be missed because soft speech
    or the first words of the next turn may be dropped.
    """
    stream = pya.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SEND_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE,
    )
    print("🎙️  Listening... speak anytime.")

    try:
        while True:
            data = await asyncio.to_thread(
                stream.read,
                CHUNK_SIZE,
                exception_on_overflow=False,
            )

            await session.send_realtime_input(
                audio=types.Blob(
                    data=data,
                    mime_type=f"audio/pcm;rate={SEND_RATE}",
                )
            )

            # Let the receive task run smoothly while we stream audio.
            await asyncio.sleep(0)

    except asyncio.CancelledError:
        pass
    except Exception as exc:
        print(f"⚠️  Microphone error: {exc}")
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
