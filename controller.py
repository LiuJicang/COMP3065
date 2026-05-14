import time

import cv2
import mediapipe as mp


class GestureController:
    """Detect stable hand gestures from OpenCV frames.

    The gesture rules are intentionally kept equivalent to the original
    project: fist, thumb directions, and index-finger directions all map to
    the same raw gesture names used by the app.
    """

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5,
            max_num_hands=1,
        )
        self.last_gesture_time = 0
        self.gesture_cooldown = 0.5

        self.gesture_history = []
        self.history_size = 5
        self.required_consistency = 3
        self.last_triggered_gesture = None
        self.gesture_hold_frames = 0
        self.min_frames_for_new_gesture = 8

        self.colors = {
            "text": (255, 255, 255),
            "fist": (255, 0, 0),
            "thumb_up": (0, 255, 255),
            "thumb_down": (255, 255, 0),
            "thumb_right": (0, 0, 255),
            "thumb_left": (255, 0, 255),
            "index_right": (128, 128, 0),
            "index_left": (0, 128, 128),
        }

    def detect_gesture(self, frame):
        output_frame = frame.copy()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        if not results.multi_hand_landmarks:
            self.gesture_history = []
            self.gesture_hold_frames = 0
            return None, output_frame

        hand = results.multi_hand_landmarks[0]
        landmarks = hand.landmark
        self._draw_landmarks(output_frame, hand)

        raw_gesture = self._classify_raw_gesture(landmarks)
        self._remember(raw_gesture)
        smooth_gesture = self._apply_gesture_smoothing()

        if smooth_gesture:
            self._draw_gesture_status(output_frame, smooth_gesture)
            current_time = time.time()
            can_trigger = current_time - self.last_gesture_time > self.gesture_cooldown
            is_new_gesture = smooth_gesture != self.last_triggered_gesture
            is_stable = self.gesture_hold_frames >= self.min_frames_for_new_gesture

            if can_trigger and is_new_gesture and is_stable:
                self.last_gesture_time = current_time
                self.last_triggered_gesture = smooth_gesture
                return smooth_gesture, output_frame

        return None, output_frame

    def _classify_raw_gesture(self, landmarks):
        wrist = landmarks[0]
        thumb_tip = landmarks[4]
        thumb_mid = landmarks[2]
        index_tip = landmarks[8]
        index_mcp = landmarks[5]
        pinky_mcp = landmarks[17]

        hand_width = abs(pinky_mcp.x - index_mcp.x)
        width_threshold = hand_width * 0.8

        fingers_extended = [
            self._is_finger_extended(landmarks, 5, 6, 8),
            self._is_finger_extended(landmarks, 9, 10, 12),
            self._is_finger_extended(landmarks, 13, 14, 16),
            self._is_finger_extended(landmarks, 17, 18, 20),
        ]
        extended_count = sum(fingers_extended)

        thumb_vec_x = thumb_tip.x - thumb_mid.x
        thumb_vec_y = thumb_tip.y - thumb_mid.y
        thumb_right = thumb_vec_x > 0 and abs(thumb_vec_x) > abs(thumb_vec_y) * 1.5
        thumb_left = thumb_vec_x < 0 and abs(thumb_vec_x) > abs(thumb_vec_y) * 1.5
        thumb_up = thumb_tip.y < thumb_mid.y - 0.05
        thumb_down = thumb_tip.y > thumb_mid.y + 0.05

        if extended_count == 0 and not (thumb_right or thumb_left):
            return "fist"
        if thumb_up and thumb_tip.y < wrist.y - 0.15 and extended_count <= 1:
            return "thumb_up"
        if thumb_down and extended_count <= 1:
            return "thumb_down"
        if thumb_right and thumb_tip.x > wrist.x + width_threshold and extended_count == 0:
            return "thumb_right"
        if thumb_left and thumb_tip.x < wrist.x - width_threshold and extended_count == 0:
            return "thumb_left"
        if (
            fingers_extended[0]
            and not any(fingers_extended[1:])
            and index_tip.x > wrist.x + width_threshold * 0.7
        ):
            return "index_right"
        if (
            fingers_extended[0]
            and not any(fingers_extended[1:])
            and index_tip.x < wrist.x - width_threshold * 0.7
        ):
            return "index_left"

        return None

    @staticmethod
    def _is_finger_extended(landmarks, base_id, mid_id, tip_id):
        finger_base = landmarks[base_id]
        finger_mid = landmarks[mid_id]
        finger_tip = landmarks[tip_id]

        base_to_mid_dist = (
            (finger_mid.x - finger_base.x) ** 2 + (finger_mid.y - finger_base.y) ** 2
        ) ** 0.5
        mid_to_tip_dist = (
            (finger_tip.x - finger_mid.x) ** 2 + (finger_tip.y - finger_mid.y) ** 2
        ) ** 0.5
        return mid_to_tip_dist > base_to_mid_dist * 0.7 and finger_tip.y < finger_mid.y

    def _remember(self, raw_gesture):
        self.gesture_history.append(raw_gesture)
        if len(self.gesture_history) > self.history_size:
            self.gesture_history.pop(0)

    def _apply_gesture_smoothing(self):
        if not self.gesture_history:
            return None

        gesture_counts = {}
        for gesture in self.gesture_history:
            if gesture is not None:
                gesture_counts[gesture] = gesture_counts.get(gesture, 0) + 1

        if not gesture_counts:
            self.gesture_hold_frames = 0
            return None

        most_common_gesture = max(gesture_counts, key=gesture_counts.get)
        if gesture_counts[most_common_gesture] < self.required_consistency:
            self.gesture_hold_frames = 0
            return None

        previous = self.gesture_history[-2] if len(self.gesture_history) >= 2 else None
        if most_common_gesture == self.last_triggered_gesture:
            self.gesture_hold_frames = min(
                self.gesture_hold_frames + 1, self.min_frames_for_new_gesture * 2
            )
        elif self.gesture_hold_frames == 0 or most_common_gesture != previous:
            self.gesture_hold_frames = 1
        else:
            self.gesture_hold_frames += 1

        return most_common_gesture

    def _draw_landmarks(self, image, landmarks):
        self.mp_drawing.draw_landmarks(
            image,
            landmarks,
            self.mp_hands.HAND_CONNECTIONS,
            self.mp_drawing_styles.get_default_hand_landmarks_style(),
            self.mp_drawing_styles.get_default_hand_connections_style(),
        )

    def _draw_gesture_status(self, image, gesture):
        cv2.putText(
            image,
            f"Gesture: {gesture}",
            (10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            self.colors.get(gesture, self.colors["text"]),
            2,
        )
        cv2.putText(
            image,
            f"Stability: {self.gesture_hold_frames}/{self.min_frames_for_new_gesture}",
            (10, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            self.colors["text"],
            1,
        )
