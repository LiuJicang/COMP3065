import glob
import os
import platform
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

import cv2
from PIL import Image, ImageTk

from controller import GestureController
from media_player import SUPPORTED_AUDIO_EXTENSIONS, create_media_player


GESTURE_ACTIONS = {
    "fist": "Play / pause",
    "thumb_right": "Next track",
    "thumb_left": "Previous track",
    "thumb_up": "Volume up",
    "thumb_down": "Volume down",
}


class GestureMusicPlayerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gesture Music Player")
        self.root.geometry("1200x720")
        self.root.minsize(960, 600)

        self.player = create_media_player()
        self.controller = GestureController()

        self.camera = None
        self.is_camera_running = False
        self.camera_thread = None
        self.last_gesture_time = 0
        self.gesture_cooldown = 0.5

        self._build_ui()
        self.scan_music_files()
        self.open_initial_track()
        self.start_camera()
        self._schedule_playback_update()

    def _build_ui(self):
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=2)

        self.camera_label = ttk.Label(left_frame, anchor=tk.CENTER)
        self.camera_label.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        status_frame = ttk.LabelFrame(left_frame, text="Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)

        self.status_var = tk.StringVar(value="Starting camera...")
        ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 12)).pack(
            fill=tk.X, padx=5, pady=5
        )

        progress_frame = ttk.Frame(left_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(progress_frame, text="Progress").pack(side=tk.LEFT, padx=5)
        self.progress_var = tk.DoubleVar(value=0)
        ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            length=200,
            mode="determinate",
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)

        self.platform_var = tk.StringVar(value=self._platform_status_text())
        ttk.Label(right_frame, textvariable=self.platform_var).pack(
            fill=tk.X, padx=5, pady=(0, 8)
        )

        buttons_frame = ttk.Frame(right_frame)
        buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(buttons_frame, text="Add files", command=self.add_music_files).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(buttons_frame, text="Rescan", command=self.scan_music_files).pack(
            side=tk.LEFT, padx=5
        )

        playlist_frame = ttk.LabelFrame(right_frame, text="Playlist")
        playlist_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.playlist_listbox = tk.Listbox(playlist_frame, font=("Arial", 10))
        self.playlist_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.playlist_listbox.bind("<Double-Button-1>", self.on_playlist_double_click)

        volume_frame = ttk.Frame(right_frame)
        volume_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(volume_frame, text="Volume").pack(side=tk.LEFT, padx=5)
        self.volume_var = tk.IntVar(value=self.player.volume)
        ttk.Scale(
            volume_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=self.set_volume,
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        controls_frame = ttk.Frame(right_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(controls_frame, text="Play/Pause", command=self.player.play_pause).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(controls_frame, text="Previous", command=self.player.prev_track).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(controls_frame, text="Next", command=self.player.next_track).pack(
            side=tk.LEFT, padx=5
        )

        gesture_frame = ttk.LabelFrame(right_frame, text="Gestures")
        gesture_frame.pack(fill=tk.X, padx=5, pady=5)

        for gesture, action in GESTURE_ACTIONS.items():
            ttk.Label(gesture_frame, text=f"{gesture}: {action}", font=("Arial", 10)).pack(
                anchor=tk.W, padx=5, pady=2
            )

    def _platform_status_text(self):
        system = platform.system()
        if system == "Windows":
            return "Playback target: Windows Media Player"
        if system == "Darwin":
            return "Playback target: Apple Music"
        return f"Playback target: default app on {system or 'this platform'}"

    def add_music_files(self):
        patterns = " ".join(f"*{extension}" for extension in SUPPORTED_AUDIO_EXTENSIONS)
        files = filedialog.askopenfilenames(
            title="Choose audio files",
            filetypes=[("Audio files", patterns), ("All files", "*.*")],
        )

        for file_path in files:
            self._add_track_to_playlist(file_path)

        self._set_status(f"Loaded {self.playlist_listbox.size()} audio files")

    def scan_music_files(self):
        self.player.clear_playlist()
        self.playlist_listbox.delete(0, tk.END)

        for music_dir in self._music_directories():
            for extension in SUPPORTED_AUDIO_EXTENSIONS:
                pattern = str(music_dir / "**" / f"*{extension}")
                for file_path in glob.glob(pattern, recursive=True):
                    self._add_track_to_playlist(file_path)

        self._set_status(f"Scanned {self.playlist_listbox.size()} audio files")

    def open_initial_track(self):
        if self.player.current_track is None:
            self._set_status("No audio files found")
            return

        self.player.open_current_track()
        self.playlist_listbox.selection_clear(0, tk.END)
        self.playlist_listbox.selection_set(self.player.current_track_index)
        self.playlist_listbox.see(self.player.current_track_index)
        self._set_status(f"Opened {Path(self.player.current_track).name}")

    def _music_directories(self):
        home = Path.home()
        directories = [home / "Music"]

        if platform.system() == "Windows":
            system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
            directories.append(system_root / "Media")
        elif platform.system() == "Darwin":
            directories.extend(
                [
                    home / "Music" / "Music" / "Media.localized",
                    home / "Music" / "iTunes" / "iTunes Media",
                ]
            )

        return [path for path in directories if path.exists()]

    def _add_track_to_playlist(self, file_path):
        if self.player.add_track(file_path):
            self.playlist_listbox.insert(tk.END, Path(file_path).name)

    def on_playlist_double_click(self, event):
        selection = self.playlist_listbox.curselection()
        if selection:
            self.player.play_index(selection[0])
            self._set_status(f"Playing {Path(self.player.current_track).name}")

    def set_volume(self, value):
        self.player.set_volume(int(float(value)))

    def start_camera(self):
        if self.is_camera_running:
            return

        self.camera = cv2.VideoCapture(0)
        if not self.camera.isOpened():
            self._set_status("Unable to open camera")
            return

        self.is_camera_running = True
        self.camera_thread = threading.Thread(target=self._process_camera, daemon=True)
        self.camera_thread.start()

    def _process_camera(self):
        while self.is_camera_running:
            ret, frame = self.camera.read()
            if not ret:
                self.root.after(0, self._set_status, "Unable to read camera frame")
                break

            frame = cv2.flip(frame, 1)
            gesture, processed_frame = self.controller.detect_gesture(frame)
            if gesture:
                self._handle_gesture(gesture)

            image = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image)
            self.root.after(0, self._update_camera_image, image)

    def _handle_gesture(self, gesture):
        current_time = time.time()
        if current_time - self.last_gesture_time <= self.gesture_cooldown:
            return

        self.last_gesture_time = current_time
        action = GESTURE_ACTIONS.get(gesture, "Unknown")

        if gesture == "fist":
            self.player.play_pause()
        elif gesture == "thumb_right":
            self.player.next_track()
        elif gesture == "thumb_left":
            self.player.prev_track()
        elif gesture == "thumb_up":
            self.player.volume_control(+10)
            self.root.after(0, self.volume_var.set, self.player.volume)
        elif gesture == "thumb_down":
            self.player.volume_control(-10)
            self.root.after(0, self.volume_var.set, self.player.volume)

        self.root.after(0, self._set_status, f"Gesture: {gesture} -> {action}")

    def _update_camera_image(self, image):
        photo = ImageTk.PhotoImage(image=image)
        self.camera_label.configure(image=photo)
        self.camera_label.image = photo

    def _schedule_playback_update(self):
        track_info = self.player.get_current_track_info()
        if track_info:
            duration = track_info["duration"]
            progress = 0 if duration <= 0 else (track_info["position"] / duration) * 100
            self.progress_var.set(min(100, progress))
            if track_info["is_playing"]:
                self._set_status(f"Playing {track_info['title']}")

        self.root.after(500, self._schedule_playback_update)

    def _set_status(self, message):
        self.status_var.set(message)

    def on_closing(self):
        self.is_camera_running = False
        if self.camera is not None:
            self.camera.release()
        self.player.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = GestureMusicPlayerApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
