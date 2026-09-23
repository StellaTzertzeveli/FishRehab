"""
Wraps MediaPipe Hands and turns raw landmarks into the three gesture
signals the game needs:

  - pinch point + is_pinching   (debris grab)
  - palm center + palm speed    (predator push-away)
  - per-finger tip position + "tap" edge detection (feeding)

All coordinates returned are in pixel space of the given frame size.
"""

from collections import deque
import mediapipe as mp
import numpy as np
import config

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

# Landmark indices (MediaPipe Hands topology)
WRIST = 0
THUMB_TIP = 4
INDEX_MCP, INDEX_PIP, INDEX_TIP = 5, 6, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_TIP = 9, 10, 12
RING_MCP, RING_PIP, RING_TIP = 13, 14, 16
PINKY_MCP, PINKY_PIP, PINKY_TIP = 17, 18, 20

FINGER_TIPS = {
    "index": INDEX_TIP,
    "middle": MIDDLE_TIP,
    "ring": RING_TIP,
    "pinky": PINKY_TIP,
}
FINGER_PIPS = {
    "index": INDEX_PIP,
    "middle": MIDDLE_PIP,
    "ring": RING_PIP,
    "pinky": PINKY_PIP,
}
PALM_LANDMARKS = [WRIST, INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]


class HandState:
    """Derived per-frame signals for a single tracked hand."""

    def __init__(self):
        self.present = False
        self.pinch_point = None      # (x, y) midpoint of thumb+index tips
        self.is_pinching = False
        self.palm_center = None      # (x, y)
        self.palm_speed = 0.0        # px/frame, smoothed
        self.is_palm_open = False
        self.finger_tips = {}        # name -> (x, y)

    def push_velocity(self, x: float) -> None:
        pass


class HandTracker:
    def __init__(self, frame_w: int, frame_h: int, max_hands: int = 1):
        self.frame_w = frame_w
        self.frame_h = frame_h
        self._hands = mp_hands.Hands(
            model_complexity=0,
            max_num_hands=max_hands,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )
        self._prev_palm_center = None
        self._palm_speed_hist = deque(maxlen=3)

    def close(self):
        self._hands.close()

    def _px(self, landmark):
        return landmark.x * self.frame_w, landmark.y * self.frame_h

    def process(self, frame_rgb: np.ndarray) -> HandState:
        """Run MediaPipe on an RGB frame and return derived gesture state."""
        state = HandState()
        results = self._hands.process(frame_rgb)
        if not results.multi_hand_landmarks:
            self._prev_palm_center = None
            return state

        landmarks = results.multi_hand_landmarks[0].landmark
        state.present = True

        # --- pinch (thumb tip <-> index tip) ---
        tx, ty = self._px(landmarks[THUMB_TIP])
        ix, iy = self._px(landmarks[INDEX_TIP])
        dist = ((tx - ix) ** 2 + (ty - iy) ** 2) ** 0.5
        state.pinch_point = ((tx + ix) / 2.0, (ty + iy) / 2.0)
        state.is_pinching = dist < config.PINCH_DISTANCE_PX

        # --- palm center + speed ---
        pts = [self._px(landmarks[i]) for i in PALM_LANDMARKS]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        state.palm_center = (cx, cy)
        if self._prev_palm_center is not None:
            dx = cx - self._prev_palm_center[0]
            dy = cy - self._prev_palm_center[1]
            speed = (dx * dx + dy * dy) ** 0.5
            self._palm_speed_hist.append(speed)
            state.palm_speed = sum(self._palm_speed_hist) / len(self._palm_speed_hist)
        self._prev_palm_center = (cx, cy)

        # --- palm open: fingers extended (tip further from wrist than pip) ---
        wx, wy = self._px(landmarks[WRIST])
        extended = 0
        for finger in FINGER_TIPS:
            tip_x, tip_y = self._px(landmarks[FINGER_TIPS[finger]])
            pip_x, pip_y = self._px(landmarks[FINGER_PIPS[finger]])
            d_tip = ((tip_x - wx) ** 2 + (tip_y - wy) ** 2) ** 0.5
            d_pip = ((pip_x - wx) ** 2 + (pip_y - wy) ** 2) ** 0.5
            if d_tip > d_pip:
                extended += 1
        state.is_palm_open = extended >= 3

        # --- individual fingertip positions (feeding phase) ---
        for finger, idx in FINGER_TIPS.items():
            state.finger_tips[finger] = self._px(landmarks[idx])

        return state
