import os
import plistlib
import subprocess
import sys
from pathlib import Path

from config import ROOT


def main():
    if sys.platform != "darwin":
        raise RuntimeError("Scheduled cleanup currently supports macOS only")
    label = "com.usuri.meeting-transcriber.cleanup"
    destination = Path.home() / "Library/LaunchAgents" / (label + ".plist")
    domain = f"gui/{os.getuid()}"
    job = {
        "Label": label,
        "ProgramArguments": [sys.executable, "-B", str(ROOT / "transcriber.py"), "--cleanup-trash"],
        "WorkingDirectory": str(ROOT),
        "StartCalendarInterval": {"Weekday": 1, "Hour": 9, "Minute": 0},
        "StandardOutPath": str(Path.home() / "Library/Logs/meeting-transcriber-cleanup.log"),
        "StandardErrorPath": str(Path.home() / "Library/Logs/meeting-transcriber-cleanup-error.log"),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        subprocess.run(["launchctl", "bootout", domain, str(destination)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with destination.open("wb") as file:
        plistlib.dump(job, file)
    subprocess.run(["plutil", "-lint", str(destination)], check=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(destination)], check=True)
    print(f"Installed Monday 9 a.m. cleanup: {destination}")


if __name__ == "__main__":
    main()
