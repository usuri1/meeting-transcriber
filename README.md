# Meeting Transcriber

A Python command-line tool for recording meetings or lectures on an Apple Silicon Mac and turning them into timestamped transcripts and study notes. Uses MLX Whisper for transcription and Qwen through Ollama for local summaries, key points, and action items linked back to the transcript.

## Setup

Install Python 3.10+, BlackHole 2ch, Ollama, and FFmpeg. Route system audio through BlackHole (use a Multi-Output Device to hear it while recording), then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull qwen3:8b
python recorder.py
```

Press Enter to start and stop recording, then choose whether to process, trash, or keep the audio. Transcripts and summaries are saved as Markdown in `transcripts/` and `summaries/`. Models download on first use; audio processing runs locally.

To process an existing WAV file:

```bash
python transcriber.py /path/to/recording.wav
```

Settings are in `config.py`. Personal audio and generated notes are excluded from Git. Processed recordings move to the project's trash folder; `python transcriber.py --cleanup-trash` removes WAV files that have been there for at least seven days. Move audio to `keep_audio/` to preserve it.
