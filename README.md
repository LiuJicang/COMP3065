# Gesture Music Player

A cross-platform hand-gesture music controller for Windows and macOS.

## Features

- Uses OpenCV to read the webcam.
- Uses MediaPipe Hands to detect hand landmarks.
- Supports these gestures:
  - `fist`: play / pause
  - `thumb_right`: next track
  - `thumb_left`: previous track
  - `thumb_up`: volume up
  - `thumb_down`: volume down
- Opens the first scanned track automatically when the app starts.
- Synchronizes the volume slider with the playback target volume at startup.
- Uses Windows Media Player on Windows.
- Uses Apple Music on macOS.

## Project Structure

```text
COMP3065Project/
|-- app.py                # Tkinter GUI, camera loop, playlist, gesture actions
|-- controller.py         # MediaPipe hand gesture recognition
|-- media_player.py       # Cross-platform playback abstraction
|-- requirements.txt      # Runtime Python dependencies
|-- test_mediapipe.py     # Quick MediaPipe environment check
|-- CHANGELOG.md          # Modification log
`-- README.md             # Setup and usage notes
```

## Recreate the Virtual Environment

The `.venv` folder is local-only and is not committed to GitHub. Create a fresh
environment after cloning this repository on a new computer.

### Windows

```powershell
cd D:\COMP3065Project\COMP3065Project
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe test_mediapipe.py
.\.venv\Scripts\python.exe app.py
```

Set Windows Media Player as the default app for local audio files if another
player opens when a track starts.

### macOS

```bash
cd /path/to/COMP3065Project
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python test_mediapipe.py
./.venv/bin/python app.py
```

The first Apple Music control may trigger macOS automation permission prompts.
Allow Terminal, VS Code, or the Python app to control Music.

## Notes

- Webcam access must be allowed by the operating system.
- Windows volume synchronization uses `pycaw` to read and set the system output
  volume.
- Apple Music control uses AppleScript through `osascript`.
