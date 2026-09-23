import os
# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR = os.path.join(BASE_DIR, "assets")

ASSET_FILES = {
    "banana_trash": "banana_trash.png",
    "soda_trash": "soda_trash.png",
    "shark_predator": "shark_predator.png",
    "blue_fish": "blue_fish.png",
    "green_fish": "green_fish.png",
    "pink_fish": "pink_fish.png",
    "yellow_fish": "yellow_fish.png",
    "underwater_background": "underwater_background.png",
    "apple_trash": "apple_trash.png",
    "bones_trash": "bones_trash.png"
}

# Camera / window
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
WINDOW_NAME = "Pond Rehab Game"
MIRROR_CAMERA = True  # flip horizontally so movement feels natural

# Scoring / phase lengths
# Each correct action is worth 1 point. Phases run one after another
# (debris -> predators -> feeding). The counts below are how many
# successful actions clear each phase; they add up to SCORE_TARGET.

DEBRIS_TARGET = 15
PREDATOR_TARGET = 15
FEEDING_TARGET = 20
SCORE_TARGET = DEBRIS_TARGET + PREDATOR_TARGET + FEEDING_TARGET  # 50

# ---------------------------------------------------------------------------
# Finger -> assets color mapping for the feeding phase
# pinky feeds red_fish, and yellow_fish swims around as a non-target decorative assets.
FINGER_FISH_MAP = {
    "index": "blue_fish",
    "middle": "pink_fish",
    "ring": "green_fish",
    "pinky": "green_fish",
}
DECORATIVE_FISH = ["yellow_fish"]

# ---------------------------------------------------------------------------
# Entity sizing (pixels, at FRAME_WIDTH/FRAME_HEIGHT)
# ---------------------------------------------------------------------------
TRASH_SIZE = 90
PREDATOR_SIZE = 220
FISH_SIZE = 110
DECOR_FISH_SIZE = 90

# ---------------------------------------------------------------------------
# Interaction thresholds
# ---------------------------------------------------------------------------
PINCH_DISTANCE_PX = 45          # thumb-tip to index-tip distance counted as a pinch
GRAB_HOLD_FRAMES = 4            # consecutive frames pinch+overlap must hold to count
PALM_PUSH_SPEED_PX = 28         # per-frame palm-center speed counted as a "push"
PALM_PUSH_COOLDOWN_FRAMES = 20  # frames before the same push can score again
TAP_COOLDOWN_FRAMES = 15        # frames before the same finger can score again

# Max simultaneous entities on screen per phase
MAX_DEBRIS_ON_SCREEN = 3
MAX_PREDATORS_ON_SCREEN = 1
MAX_FEED_FISH_ON_SCREEN = 4

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
FPS_TARGET = 30
HUD_FONT_SCALE = 1.0
