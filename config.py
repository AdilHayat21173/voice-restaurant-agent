import pyaudio

# Microphone input: Gemini Live expects 16 kHz PCM audio.
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_RATE = 16000

# Speaker output from Gemini native audio is 24 kHz PCM audio.
RECEIVE_RATE = 24000

# Smaller chunks reduce delay. 512 frames ~= 32 ms at 16 kHz.
CHUNK_SIZE = 512

MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"
