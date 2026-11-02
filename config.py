import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECORDINGS = ROOT / "recordings"
TRANSCRIPTS = ROOT / "transcripts"
SUMMARIES = ROOT / "summaries"
TRASH = ROOT / "trash"
KEEP_AUDIO = ROOT / "keep_audio"

# Change these defaults here, or set the matching environment variables.
DEVICE_NAME = os.getenv("AUDIO_DEVICE", "BlackHole 2ch")
SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))
CHANNELS = int(os.getenv("AUDIO_CHANNELS", "2"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "mlx-community/whisper-small-mlx")
SUMMARY_MODEL = os.getenv("SUMMARY_MODEL", "qwen3:8b")
# A separate local port lets this program own and stop its Ollama process.
OLLAMA_URL = "http://127.0.0.1:11435/api/chat"
TRASH_DAYS = 7


def create_folders():
    for folder in (RECORDINGS, TRANSCRIPTS, SUMMARIES, TRASH, KEEP_AUDIO):
        folder.mkdir(exist_ok=True)
