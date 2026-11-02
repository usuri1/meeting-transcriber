import argparse
import queue
import threading
from datetime import datetime

import sounddevice as sd
import soundfile as sf

from config import CHANNELS, DEVICE_NAME, RECORDINGS, SAMPLE_RATE, create_folders
from transcriber import move_to_trash, process_audio


def find_device(name):
    for index, device in enumerate(sd.query_devices()):
        if name.casefold() in device["name"].casefold() and device["max_input_channels"] >= CHANNELS:
            return index
    raise RuntimeError(f"Input device '{name}' not found. Use --list-devices or --device NAME.")


def record(device):
    create_folders()
    input("Press ENTER to start recording...")
    filename = RECORDINGS / f"{datetime.now():%Y-%m-%d_%H-%M-%S_%f}.wav"
    chunks = queue.Queue(maxsize=200)
    stopped = threading.Event()
    problems = set()

    def callback(indata, frames, callback_time, status):
        if status:
            problems.add(str(status))
        try:
            chunks.put_nowait(indata.copy())
        except queue.Full:
            problems.add("Disk writing could not keep up. Audio may be incomplete.")
            stopped.set()

    def wait_for_stop():
        try:
            input()
        except EOFError:
            pass
        stopped.set()

    print("Recording... Press ENTER to stop.")
    # Write continuously to disk instead of keeping an entire lecture in RAM.
    with sf.SoundFile(filename, "x", samplerate=SAMPLE_RATE, channels=CHANNELS,
                      subtype="PCM_16") as file:
        try:
            with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                device=device, callback=callback):
                threading.Thread(target=wait_for_stop, daemon=True).start()
                while not stopped.is_set():
                    try:
                        file.write(chunks.get(timeout=0.2))
                    except queue.Empty:
                        pass
            while not chunks.empty():
                file.write(chunks.get_nowait())
        except BaseException:
            print(f"Recording interrupted. Audio kept at {filename}")
            raise
    for problem in problems:
        print(f"Recording warning: {problem}")
    print(f"Recording saved: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(description="Record system audio, then process or trash it.")
    parser.add_argument("--device", default=DEVICE_NAME, help="Input device name (macOS controls speaker output)")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()
    if args.list_devices:
        print(sd.query_devices())
        return
    audio = record(find_device(args.device))
    while True:
        choice = input("[p] Process transcript + summary / [t] Trash / [k] Keep for later: ").strip().lower()
        if choice in ("p", "process"):
            process_audio(audio)
            return
        if choice in ("t", "trash"):
            move_to_trash(audio)
            return
        if choice in ("k", "keep"):
            print(f"Kept for later processing: {audio}")
            return
        print("Choose p, t, or k.")


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        print(f"Stopped: {error}. Saved audio has not been deleted.")
        raise SystemExit(1)
