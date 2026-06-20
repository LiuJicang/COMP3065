# Change Log

## 2026-06-20

- Replaced the hand-gesture classification rules with a joint-direction model:
  - A finger is bent when either the x-direction or y-direction reverses
    between its base-to-middle and middle-to-tip segments.
  - A fist requires all five fingers to be bent.
  - Each thumb direction requires a non-bent thumb, the other four fingers to
    be bent, and uses the slope of the line from landmark 2 to landmark 4.

## 2026-05-14

- Refactored the project into a cross-platform structure:
  - `app.py` owns the Tkinter GUI, camera loop, playlist UI, and gesture action mapping.
  - `controller.py` owns MediaPipe hand gesture recognition.
  - `media_player.py` owns Windows Media Player / Apple Music integration.
- Removed the old bundled virtual environments and macOS archive metadata from the project tree.
- Added a fresh local `.venv` for this Windows machine and kept it ignored by Git.
- Added GitHub repository setup and pushed the initial project to `origin/main`.
- Changed startup behavior so the app opens the first scanned audio track immediately.
- Synchronized the GUI volume slider with the playback target volume at startup.
  - Windows uses `pycaw` / `comtypes` to read and set system output volume.
  - macOS uses Apple Music `sound volume`.
- Removed `index_right` and `index_left` gesture actions because seeking by index-finger gestures was unreliable.
- Updated `README.md` to match the current gesture set and setup steps.
