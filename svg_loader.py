"""
Loads the underwater background and game assets.

The game uses:
    load_background()  - loads the underwater PNG
    load_asset()       - loads individual PNG/SVG game assets
    overlay_bgra()     - alpha-blends an asset onto the camera frame
"""

import os

import cv2
import numpy as np


# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")


# Cache loaded images so we don't reload them every frame
_cache = {}


# ------------------------------------------------------------
# Background
# ------------------------------------------------------------

def load_background(width_px: int, height_px: int) -> np.ndarray:
    """Load and resize the underwater background."""

    key = ("background", width_px, height_px)

    if key in _cache:
        return _cache[key].copy()

    png_path = os.path.join(
        ASSETS_DIR,
        "underwater_background.png"
    )

    if not os.path.exists(png_path):
        raise FileNotFoundError(
            f"Missing background asset: {png_path}"
        )

    image = cv2.imread(
        png_path,
        cv2.IMREAD_UNCHANGED
    )

    if image is None:
        raise RuntimeError(
            f"Could not load background asset: {png_path}"
        )

    image = cv2.resize(
        image,
        (width_px, height_px),
        interpolation=cv2.INTER_AREA
    )

    # Make sure the background is BGRA
    if image.ndim == 2:
        image = cv2.cvtColor(
            image,
            cv2.COLOR_GRAY2BGRA
        )

    elif image.shape[2] == 3:
        image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2BGRA
        )

    _cache[key] = image

    return image.copy()


# ------------------------------------------------------------
# Game assets
# ------------------------------------------------------------

def load_asset(name: str, size) -> np.ndarray:
    """
    Load a game asset and resize it.

    The game passes either:
        size = 80
    or:
        size = (80, 100)

    PNG is preferred. SVG is supported as a fallback.
    """

    # The existing game passes an integer size
    if isinstance(size, (int, float)):
        width = int(size)
        height = int(size)

    # Also support (width, height)
    else:
        width, height = map(int, size)

    key = ("asset", name, width, height)

    if key in _cache:
        return _cache[key].copy()

    # --------------------------------------------------------
    # Find the asset
    # --------------------------------------------------------

    png_path = os.path.join(
        ASSETS_DIR,
        f"{name}.png"
    )

    svg_path = os.path.join(
        ASSETS_DIR,
        f"{name}.svg"
    )

    image = None

    # Try PNG first
    if os.path.exists(png_path):

        image = cv2.imread(
            png_path,
            cv2.IMREAD_UNCHANGED
        )

        if image is None:
            raise RuntimeError(
                f"Could not read PNG asset: {png_path}"
            )

    # If there is no PNG, try SVG
    elif os.path.exists(svg_path):

        try:
            import cairosvg
        except ImportError:
            raise ImportError(
                "cairosvg is required for SVG assets. "
                "Install it with: pip install cairosvg"
            )

        png_bytes = cairosvg.svg2png(
            url=svg_path
        )

        image_array = np.frombuffer(
            png_bytes,
            dtype=np.uint8
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_UNCHANGED
        )

        if image is None:
            raise RuntimeError(
                f"Could not read SVG asset: {svg_path}"
            )

    # Neither exists
    else:
        raise FileNotFoundError(
            f"Could not find asset '{name}'. "
            f"Expected either:\n"
            f"  {png_path}\n"
            f"or\n"
            f"  {svg_path}"
        )

    # --------------------------------------------------------
    # Convert to BGRA
    # --------------------------------------------------------

    if image.ndim == 2:

        image = cv2.cvtColor(
            image,
            cv2.COLOR_GRAY2BGRA
        )

    elif image.shape[2] == 3:

        image = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2BGRA
        )

    # --------------------------------------------------------
    # Resize
    # --------------------------------------------------------

    image = cv2.resize(
        image,
        (width, height),
        interpolation=cv2.INTER_AREA
    )

    _cache[key] = image

    return image.copy()


# ------------------------------------------------------------
# Alpha overlay
# ------------------------------------------------------------

def overlay_bgra(
    frame: np.ndarray,
    overlay: np.ndarray,
    x: int,
    y: int
):
    """
    Draw a BGRA image onto a BGR frame.

    x and y specify the top-left corner of the asset.
    """

    if overlay is None:
        return

    h, w = overlay.shape[:2]

    frame_h, frame_w = frame.shape[:2]

    # --------------------------------------------------------
    # Work out visible area
    # --------------------------------------------------------

    x1 = max(0, x)
    y1 = max(0, y)

    x2 = min(frame_w, x + w)
    y2 = min(frame_h, y + h)

    # Asset is completely outside the frame
    if x1 >= x2 or y1 >= y2:
        return

    # --------------------------------------------------------
    # Corresponding area inside the asset
    # --------------------------------------------------------

    ox1 = x1 - x
    oy1 = y1 - y

    ox2 = ox1 + (x2 - x1)
    oy2 = oy1 + (y2 - y1)

    overlay_crop = overlay[oy1:oy2, ox1:ox2]
    frame_crop = frame[y1:y2, x1:x2]

    # --------------------------------------------------------
    # Alpha blending
    # --------------------------------------------------------

    alpha = (
        overlay_crop[:, :, 3].astype(np.float32)
        / 255.0
    )

    alpha = alpha[:, :, np.newaxis]

    foreground = overlay_crop[:, :, :3].astype(
        np.float32
    )

    background = frame_crop.astype(
        np.float32
    )

    blended = (
        foreground * alpha
        + background * (1.0 - alpha)
    )

    frame_crop[:] = blended.astype(np.uint8)