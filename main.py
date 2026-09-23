"""
Controls:
    Q or ESC  - quit
    R         - restart
"""

import cv2
import config, svg_loader
from game import Game
from hand_tracker import HandTracker


def main():
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

    if not cap.isOpened():
        raise RuntimeError(
            f"Could not open camera index {config.CAMERA_INDEX}. "
            "Check that a webcam is connected and not in use by another app."
        )

    ok, frame = cap.read()
    if not ok:
        raise RuntimeError("Camera opened but returned no frame.")
    frame_h, frame_w = frame.shape[:2]

    background = svg_loader.load_background(frame_w, frame_h)
    tracker = HandTracker(frame_w, frame_h, max_hands=1)
    game = Game(frame_w, frame_h)

    cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if config.MIRROR_CAMERA:
                frame = cv2.flip(frame, 1)

            # Blend the camera feed lightly under the pond background so the
            # scene reads as an aquarium rather than a raw webcam view.
            display = cv2.addWeighted(background, 0.85, frame, 0.15, 0)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hand_state = tracker.process(rgb)

            game.update(hand_state)
            game.draw(display)

            if hand_state.present and hand_state.pinch_point:
                color = (0, 255, 0) if hand_state.is_pinching else (0, 165, 255)
                cv2.circle(display, tuple(map(int, hand_state.pinch_point)), 10, color, 2)

            cv2.imshow(config.WINDOW_NAME, display)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # q or ESC
                break
            if key == ord("r"):
                game = Game(frame_w, frame_h)
    finally:
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
