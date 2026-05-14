import os
import platform
import subprocess
import time
from pathlib import Path


SUPPORTED_AUDIO_EXTENSIONS = (".mp3", ".wav", ".wma", ".m4a", ".aac", ".flac")


def create_media_player():
    system = platform.system()
    if system == "Windows":
        return WindowsMediaPlayer()
    if system == "Darwin":
        return AppleMusicPlayer()
    return LocalFilePlayer()


class BaseMediaPlayer:
    def __init__(self):
        self.playlist = []
        self.current_track_index = -1
        self.current_track = None
        self.is_playing = False
        self.volume = self._get_initial_volume()
        self.position = 0.0
        self.duration = 0.0
        self.started_at = None

    def add_track(self, file_path):
        path = str(Path(file_path).expanduser().resolve())
        if path not in self.playlist:
            self.playlist.append(path)
            added = True
        else:
            added = False
        if self.current_track is None:
            self.current_track_index = 0
            self.current_track = self.playlist[0]
        return added

    def clear_playlist(self):
        self.playlist = []
        self.current_track_index = -1
        self.current_track = None
        self.position = 0.0
        self.duration = 0.0
        self.started_at = None

    def play_index(self, index):
        if not self.playlist:
            return
        self.current_track_index = index % len(self.playlist)
        self.current_track = self.playlist[self.current_track_index]
        self.position = 0.0
        self.started_at = time.time()
        self.is_playing = True
        self._open_track(self.current_track)

    def open_current_track(self):
        if self.current_track_index < 0 and self.playlist:
            self.current_track_index = 0
            self.current_track = self.playlist[0]
        if self.current_track is None:
            return
        self.position = 0.0
        self.started_at = time.time()
        self.is_playing = True
        self._open_track(self.current_track)

    def play_pause(self):
        if self.current_track is None and self.playlist:
            self.play_index(0)
            return
        self._toggle_play_pause()
        self.is_playing = not self.is_playing
        self.started_at = time.time() - self.position if self.is_playing else None

    def next_track(self):
        if self.playlist:
            self.play_index(self.current_track_index + 1)

    def prev_track(self):
        if self.playlist:
            self.play_index(self.current_track_index - 1)

    def volume_control(self, change):
        self.set_volume(self.volume + change)

    def set_volume(self, value):
        target_volume = max(0, min(100, int(value)))
        previous_volume = self.volume
        self.volume = target_volume
        self._set_volume(target_volume, previous_volume)

    def seek(self, seconds):
        self.position = max(0.0, self._current_position() + seconds)
        self.started_at = time.time() - self.position if self.is_playing else None
        self._seek(seconds)

    def get_current_track_info(self):
        if self.current_track is None:
            return None
        return {
            "title": Path(self.current_track).stem,
            "file": self.current_track,
            "position": self._current_position(),
            "duration": self.duration,
            "is_playing": self.is_playing,
            "volume": self.volume,
        }

    def close(self):
        pass

    def _current_position(self):
        if self.is_playing and self.started_at is not None:
            return max(0.0, time.time() - self.started_at)
        return self.position

    def _open_track(self, file_path):
        raise NotImplementedError

    def _get_initial_volume(self):
        return 50

    def _toggle_play_pause(self):
        raise NotImplementedError

    def _set_volume(self, volume, previous_volume):
        raise NotImplementedError

    def _seek(self, seconds):
        raise NotImplementedError


class WindowsMediaPlayer(BaseMediaPlayer):
    """Control Windows 11 Media Player through shell launch and media keys."""

    VK_MEDIA_NEXT_TRACK = 0xB0
    VK_MEDIA_PREV_TRACK = 0xB1
    VK_MEDIA_PLAY_PAUSE = 0xB3
    VK_VOLUME_MUTE = 0xAD
    VK_VOLUME_DOWN = 0xAE
    VK_VOLUME_UP = 0xAF
    KEYEVENTF_KEYUP = 0x0002

    def __init__(self):
        self._endpoint_volume = None
        self._init_endpoint_volume()
        super().__init__()

    def _open_track(self, file_path):
        os.startfile(file_path)

    def _toggle_play_pause(self):
        self._press_key(self.VK_MEDIA_PLAY_PAUSE)

    def _get_initial_volume(self):
        if self._endpoint_volume is None:
            return 50
        return round(self._endpoint_volume.GetMasterVolumeLevelScalar() * 100)

    def _set_volume(self, volume, previous_volume):
        if self._endpoint_volume is not None:
            self._endpoint_volume.SetMasterVolumeLevelScalar(volume / 100, None)
            return
        if volume == previous_volume:
            return
        direction = self.VK_VOLUME_UP if volume >= previous_volume else self.VK_VOLUME_DOWN
        steps = max(1, abs(volume - previous_volume) // 2)
        for _ in range(steps):
            self._press_key(direction)

    def _seek(self, seconds):
        # The new Windows Media Player has no simple public automation API.
        # Arrow shortcuts work when it has focus, while the app state remains
        # tracked locally for the progress bar.
        key = "{RIGHT}" if seconds > 0 else "{LEFT}"
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"$ws = New-Object -ComObject WScript.Shell; $ws.SendKeys('{key}')",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def _press_key(self, key_code):
        import ctypes

        ctypes.windll.user32.keybd_event(key_code, 0, 0, 0)
        ctypes.windll.user32.keybd_event(key_code, 0, self.KEYEVENTF_KEYUP, 0)

    def _init_endpoint_volume(self):
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            speakers = AudioUtilities.GetSpeakers()
            interface = speakers.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._endpoint_volume = interface.QueryInterface(IAudioEndpointVolume)
        except Exception:
            self._endpoint_volume = None


class AppleMusicPlayer(BaseMediaPlayer):
    """Control the built-in macOS Music app with AppleScript."""

    def _open_track(self, file_path):
        self._osascript(
            f'tell application "Music" to open POSIX file "{self._escape(file_path)}"',
            'tell application "Music" to play',
        )

    def _toggle_play_pause(self):
        self._osascript('tell application "Music" to playpause')

    def _get_initial_volume(self):
        try:
            output = self._osascript(
                'tell application "Music" to get sound volume',
                capture_output=True,
            )
            return int(output.strip())
        except Exception:
            return 50

    def _set_volume(self, volume, previous_volume):
        self._osascript(f'tell application "Music" to set sound volume to {volume}')

    def _seek(self, seconds):
        operator = "+" if seconds >= 0 else "-"
        self._osascript(
            'tell application "Music"',
            f"set player position to (player position {operator} {abs(int(seconds))})",
            "end tell",
        )

    def _current_position(self):
        try:
            output = self._osascript(
                'tell application "Music" to get player position',
                capture_output=True,
            )
            return float(output.strip())
        except Exception:
            return super()._current_position()

    @staticmethod
    def _escape(value):
        return value.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _osascript(*commands, capture_output=False):
        args = ["osascript"]
        for command in commands:
            args.extend(["-e", command])
        result = subprocess.run(
            args,
            check=False,
            text=True,
            capture_output=capture_output,
        )
        return result.stdout if capture_output else ""


class LocalFilePlayer(BaseMediaPlayer):
    """Fallback for unsupported platforms: open files with the OS default app."""

    def _open_track(self, file_path):
        if platform.system() == "Darwin":
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])

    def _toggle_play_pause(self):
        pass

    def _set_volume(self, volume, previous_volume):
        pass

    def _seek(self, seconds):
        pass
