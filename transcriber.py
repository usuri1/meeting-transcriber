import argparse
import os
import re
import shutil
import time
from pathlib import Path

from config import (KEEP_AUDIO, RECORDINGS, SUMMARIES, TRANSCRIPTS, TRASH,
                    TRASH_DAYS, WHISPER_MODEL, create_folders)
from summarizer import make_summary, timestamp


def write_output(path, text):
    temporary = path.with_suffix(".md.tmp")
    with temporary.open("w", encoding="utf-8") as file:
        file.write(text)
        file.flush()
        os.fsync(file.fileno())
    temporary.replace(path)


def move_to_trash(audio_file):
    create_folders()
    if audio_file.is_symlink():
        raise ValueError("Refusing to move a symbolic link")
    target = TRASH / audio_file.name
    if audio_file.resolve() != target.resolve():
        if target.exists():
            raise FileExistsError(f"Already in trash: {target}")
        shutil.move(str(audio_file), str(target))
    # Age starts when moved to trash, not when originally recorded.
    os.utime(target, None)
    print(f"Audio moved to {target}. Move it to {KEEP_AUDIO} to keep it.")


def cleanup_trash(now=None):
    if TRASH.is_symlink():
        raise ValueError("Trash must be a real project folder, not a symbolic link")
    cutoff = (time.time() if now is None else now) - TRASH_DAYS * 86400
    deleted = 0
    for file in TRASH.glob("*.wav"):
        if file.is_file() and not file.is_symlink() and file.stat().st_mtime <= cutoff:
            file.unlink()
            deleted += 1
    print(f"Trash cleanup: deleted {deleted} WAV file(s) aged at least {TRASH_DAYS} days.")


def read_transcript(path):
    text = path.read_text(encoding="utf-8")
    segments = []
    pattern = r"\*\*\[(\d+(?::\d+){1,2})\]\*\*\s*(.*?)(?=\n\n|\Z)"
    for match in re.finditer(pattern, text, re.DOTALL):
        seconds = 0
        for part in match[1].split(":"):
            seconds = seconds * 60 + int(part)
        segments.append({"id": len(segments), "start": seconds, "text": match[2].strip()})
    if not segments:
        raise ValueError("No timestamped speech found in the transcript")
    return segments


def transcript_text(segments, audio_name):
    output = f"# Lecture Transcript\n\nRecording: `{audio_name}`\n\n## Transcript\n\n"
    for segment in segments:
        output += (f'<a id="s{segment["id"]}"></a>\n\n'
                   f'**[{timestamp(segment["start"])}]** {segment["text"]}\n\n')
    return output


def process_audio(audio_file):
    create_folders()
    audio_file = Path(audio_file)
    if audio_file.is_symlink():
        raise ValueError("Supply the original WAV path rather than a symbolic link")
    audio_file = audio_file.resolve()
    if not audio_file.is_file() or audio_file.suffix.lower() != ".wav":
        raise ValueError(f"WAV not found: {audio_file}")
    print(f"Transcribing {audio_file.name} with {WHISPER_MODEL}...", flush=True)
    import mlx_whisper
    result = mlx_whisper.transcribe(str(audio_file), path_or_hf_repo=WHISPER_MODEL,
                                    language="en", verbose=False)
    segments = [{"id": index, "start": s["start"], "text": s["text"].strip()}
                for index, s in enumerate(result["segments"]) if s["text"].strip()]
    if not segments:
        raise ValueError("No speech detected. Audio kept for review.")
    transcript = TRANSCRIPTS / f"{audio_file.stem}.md"
    write_output(transcript, transcript_text(segments, audio_file.name))
    print(f"Transcript saved: {transcript}", flush=True)
    # Release Whisper before loading the language model on a 24 GB Mac.
    import importlib
    importlib.import_module("mlx_whisper.transcribe").ModelHolder.model = None
    import mlx.core as mx
    mx.clear_cache()
    summary = SUMMARIES / transcript.name
    write_output(summary, make_summary(segments, transcript.name))
    print(f"Summary saved: {summary}")
    if audio_file.parent == RECORDINGS.resolve():
        move_to_trash(audio_file)
    else:
        print("Audio kept in its current folder.")


def main():
    parser = argparse.ArgumentParser(description="Transcribe and summarize local lecture recordings.")
    parser.add_argument("audio", nargs="?", type=Path, help="WAV path; otherwise newest recording")
    parser.add_argument("--summary-only", type=Path, metavar="TRANSCRIPT")
    parser.add_argument("--cleanup-trash", action="store_true")
    args = parser.parse_args()
    create_folders()
    if args.cleanup_trash:
        cleanup_trash()
    elif args.summary_only:
        path = args.summary_only.resolve()
        if path.parent != TRANSCRIPTS.resolve():
            raise ValueError(f"Transcript must be in {TRANSCRIPTS}")
        segments = read_transcript(path)
        write_output(path, transcript_text(segments, path.stem + ".wav"))
        write_output(SUMMARIES / path.name, make_summary(segments, path.name))
        print(f"Summary saved: {SUMMARIES / path.name}")
    else:
        recordings = list(RECORDINGS.glob("*.wav"))
        audio = args.audio or (max(recordings, key=lambda p: p.stat().st_mtime) if recordings else None)
        if audio is None:
            raise ValueError("No recordings found. Supply a WAV path to retry kept audio.")
        process_audio(audio)


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print(f"Processing stopped: {error}. Unprocessed audio has not been deleted.")
        raise SystemExit(1)
