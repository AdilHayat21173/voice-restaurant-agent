import pyaudio
from config import FORMAT, CHANNELS, RECEIVE_RATE, CHUNK_SIZE

pya = pyaudio.PyAudio()


def play_audio_chunk(stream, data: bytes):
    """Write a chunk of PCM audio to the speaker."""
    stream.write(data)


def open_speaker_stream():
    return pya.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RECEIVE_RATE,
        output=True,
        frames_per_buffer=CHUNK_SIZE,
    )
