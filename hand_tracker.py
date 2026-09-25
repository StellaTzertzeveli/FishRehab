from collections import deque

import mediapipe as mp
import numpy as np

import config


mp_hands = mp.solutions.hands

WRIST = 0

THUMB_TIP = 4

INDEX_MCP = 5
INDEX_PIP = 6
INDEX_TIP = 8

MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_TIP = 12

RING_MCP = 13
RING_PIP = 14
RING_TIP = 16

PINKY_MCP = 17
PINKY_PIP = 18
PINKY_TIP = 20


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


PALM_LANDMARKS = [
    WRIST,
    INDEX_MCP,
    MIDDLE_MCP,
    RING_MCP,
    PINKY_MCP,
]

class SingleHandState:

    def __init__(self):

        self.present = True

        # Pinch
        self.pinch_point = None
        self.is_pinching = False

        # Palm
        self.palm_center = None
        self.palm_speed = 0.0
        self.is_palm_open = False

        # Fingers
        self.finger_tips = {}


class HandState:

    def __init__(self):

        # THIS IS THE IMPORTANT PART
        # It contains every detected hand.
        self.hands = []

        # Compatibility with old game code
        self.present = False
        self.pinch_point = None
        self.is_pinching = False
        self.palm_center = None
        self.palm_speed = 0.0
        self.is_palm_open = False
        self.finger_tips = {}


# ============================================================
# HAND TRACKER
# ============================================================

class HandTracker:

    def __init__(
        self,
        frame_w: int,
        frame_h: int,
        max_hands: int = 2,
    ):

        self.frame_w = frame_w
        self.frame_h = frame_h

        # --------------------------------
        # MediaPipe
        # --------------------------------

        self._hands = mp_hands.Hands(

            model_complexity=0,

            # IMPORTANT:
            max_num_hands=2,

            min_detection_confidence=0.5,

            min_tracking_confidence=0.5,
        )

        # --------------------------------
        # Movement history
        # --------------------------------

        self._previous_palm_centers = [
            None,
            None,
        ]

        self._speed_history = [
            deque(maxlen=3),
            deque(maxlen=3),
        ]

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self):

        self._hands.close()

    # ========================================================
    # CONVERT TO PIXELS
    # ========================================================

    def _px(self, landmark):

        return (
            landmark.x * self.frame_w,
            landmark.y * self.frame_h,
        )

    def _process_hand(
        self,
        landmarks,
        hand_index,
    ):

        state = SingleHandState()
        tx, ty = self._px(
            landmarks[THUMB_TIP]
        )

        ix, iy = self._px(
            landmarks[INDEX_TIP]
        )

        distance = (
            (tx - ix) ** 2
            +
            (ty - iy) ** 2
        ) ** 0.5

        state.pinch_point = (
            (tx + ix) / 2,
            (ty + iy) / 2,
        )

        state.is_pinching = (
            distance < config.PINCH_DISTANCE_PX
        )

        # --------------------------------
        # PALM CENTER
        # --------------------------------

        palm_points = []

        for index in PALM_LANDMARKS:

            palm_points.append(
                self._px(
                    landmarks[index]
                )
            )

        cx = sum(
            point[0]
            for point in palm_points
        ) / len(palm_points)

        cy = sum(
            point[1]
            for point in palm_points
        ) / len(palm_points)

        state.palm_center = (
            cx,
            cy,
        )

        previous = (
            self._previous_palm_centers[
                hand_index
            ]
        )

        if previous is not None:
            dx = cx - previous[0]
            dy = cy - previous[1]
            speed = (dx ** 2 + dy ** 2) ** 0.5
            self._speed_history[hand_index].append(speed)

            state.palm_speed = (
                sum(self._speed_history[hand_index])/len(
                    self._speed_history[hand_index]))

        self._previous_palm_centers[hand_index] = (cx,cy,)
        wx, wy = self._px(landmarks[WRIST])
        extended_fingers = 0
        for finger in FINGER_TIPS:

            tip_x, tip_y = self._px(
                landmarks[
                    FINGER_TIPS[finger]
                ]
            )

            pip_x, pip_y = self._px(
                landmarks[
                    FINGER_PIPS[finger]
                ]
            )

            tip_distance = (
                (tip_x - wx) ** 2
                +
                (tip_y - wy) ** 2
            ) ** 0.5

            pip_distance = (
                (pip_x - wx) ** 2
                +
                (pip_y - wy) ** 2
            ) ** 0.5

            if tip_distance > pip_distance:

                extended_fingers += 1

        state.is_palm_open = (
            extended_fingers >= 3
        )

        # --------------------------------
        # FINGERTIPS
        # --------------------------------

        for finger, index in FINGER_TIPS.items():

            state.finger_tips[finger] = (
                self._px(
                    landmarks[index]
                )
            )

        return state

    # ========================================================
    # PROCESS FRAME
    # ========================================================

    def process(
        self,
        frame_rgb: np.ndarray,
    ):

        state = HandState()

        results = self._hands.process(
            frame_rgb
        )

        # --------------------------------
        # NO HANDS
        # --------------------------------

        if not results.multi_hand_landmarks:

            self._previous_palm_centers = [
                None,
                None,
            ]

            return state

        # --------------------------------
        # PROCESS EVERY HAND
        # --------------------------------

        for hand_index, hand_landmarks in enumerate(
            results.multi_hand_landmarks
        ):

            # We only want two hands.
            if hand_index >= 2:
                break

            landmarks = (
                hand_landmarks.landmark
            )

            hand = self._process_hand(
                landmarks,
                hand_index,
            )

            # THIS IS THE IMPORTANT LINE
            state.hands.append(hand)

        # --------------------------------
        # Compatibility with old code
        # --------------------------------

        if state.hands:

            first_hand = state.hands[0]

            state.present = True

            state.pinch_point = (
                first_hand.pinch_point
            )

            state.is_pinching = (
                first_hand.is_pinching
            )

            state.palm_center = (
                first_hand.palm_center
            )

            state.palm_speed = (
                first_hand.palm_speed
            )

            state.is_palm_open = (
                first_hand.is_palm_open
            )

            state.finger_tips = (
                first_hand.finger_tips
            )

        return state

