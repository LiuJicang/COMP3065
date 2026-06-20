import time

import cv2
import mediapipe as mp


class GestureController:
    """Detect stable hand gestures from OpenCV frames.

    Finger bending is determined from the direction change between a finger's
    base-to-middle segment and middle-to-tip segment. Gesture classification
    then uses the requested thumb slope ranges.
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
        thumb_bent = self._is_finger_bent(landmarks, 1, 2, 4)
        other_fingers_bent = all(
            self._is_finger_bent(landmarks, base_id, middle_id, tip_id)
            for base_id, middle_id, tip_id in (
                (5, 6, 8),
                (9, 10, 12),
                (13, 14, 16),
                (17, 18, 20),
            )
        )

        if thumb_bent and other_fingers_bent:
            return "fist"

        if thumb_bent or not other_fingers_bent:
            return None

        thumb_slope = self._slope(landmarks[2], landmarks[4])
        if 0 < thumb_slope < 1:
            return "thumb_right"
        if -1 < thumb_slope < 0:
            return "thumb_left"
        if thumb_slope > 1:
            return "thumb_up"
        if thumb_slope < -1:
            return "thumb_down"
        return None

    @staticmethod
    def _is_finger_bent(landmarks, base_id, middle_id, tip_id):
        finger_base = landmarks[base_id]
        finger_middle = landmarks[middle_id]
        finger_tip = landmarks[tip_id]

        y_direction_changed = (
            (finger_tip.y - finger_middle.y)
            * (finger_middle.y - finger_base.y)
            < 0
        )
        x_direction_changed = (
            (finger_tip.x - finger_middle.x)
            * (finger_middle.x - finger_base.x)
            < 0
        )
        return y_direction_changed or x_direction_changed

    @staticmethod
    def _slope(start, end):
        delta_x = end.x - start.x
        delta_y = end.y - start.y
        if delta_x == 0:
            if delta_y > 0:
                return float("inf")
            if delta_y < 0:
                return float("-inf")
            return 0.0
        return delta_y / delta_x

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
