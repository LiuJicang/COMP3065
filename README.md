# Gesture Music Player

A cross-platform hand-gesture music controller for Windows and macOS.

## Features

- Uses OpenCV to read the webcam.
- Uses MediaPipe Hands to detect hand landmarks.
- Keeps the original gesture recognition rules:
  - `fist`: play / pause
  - `thumb_right`: next track
  - `thumb_left`: previous track
  - `thumb_up`: volume up
  - `thumb_down`: volume down
  - `index_right`: seek forward
  - `index_left`: seek backward
- Uses Windows Media Player on Windows.
- Uses Apple Music on macOS.

## Project Structure

```text
COMP3065Project/
├─ app.py                # Tkinter GUI, camera loop, playlist, gesture actions
├─ controller.py         # MediaPipe hand gesture recognition
├─ media_player.py       # Cross-platform playback abstraction
├─ requirements.txt      # Runtime Python dependencies
├─ test_mediapipe.py     # Quick MediaPipe environment check
└─ README.md             # Setup and usage notes
```

## Recreate the Virtual Environment

The bundled `.venv` and `myenv` folders were created on other machines and
should not be reused. Remove them, then create a fresh environment.

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
Allow Terminal or the Python app to control Music.

## Notes

- Webcam access must be allowed by the operating system.
- Windows seek uses the Media Player keyboard shortcut and works best when the
  player window has focus.
- Apple Music control uses AppleScript through `osascript`.
