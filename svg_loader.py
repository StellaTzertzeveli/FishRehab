"""
Loads .png assets as BGR/BGRA numpy arrays (OpenCV's native layout)
so they can be composited onto camera frames.
"""

import os
import cv2
import numpy as np
import config

_cache = {}


def load_background(width_px: int, height_px: int) -> np.ndarray:
    """Load and resize the underwater PNG background."""
    key = ("underwater_background", (width_px, height_px))

    if key in _cache:
        return _cache[key]

    filename = config.ASSET_FILES["underwater_background"]
    png_path = os.path.join(config.ASSET_DIR, filename)

    if not os.path.isfile(png_path):
        raise FileNotFoundError(f"Missing background asset: {png_path}")

    # Load PNG using OpenCV.
    img = cv2.imread(png_path, cv2.IMREAD_UNCHANGED)

    if img is None:
        raise ValueError(f"Could not load background asset: {png_path}")

    # Backgrounds are expected to be opaque.
    # If the PNG happens to contain an alpha channel, discard it.
    if img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    # Resize to requested dimensions.
    img = cv2.resize(
        img,
        (width_px, height_px),
        interpolation=cv2.INTER_LINEAR,
    )

    _cache[key] = img
    return img


def load_sprite(filename: str) -> np.ndarray:
    """
    Load a PNG sprite as BGRA.

    PNGs with no alpha channel are converted to BGRA with
    a fully opaque alpha channel.
    """
    key = ("sprite", filename)

    if key in _cache:
        return _cache[key]

    png_path = os.path.join(config.ASSET_DIR, filename)

    if not os.path.isfile(png_path):
        raise FileNotFoundError(f"Missing sprite asset: {png_path}")

    sprite = cv2.imread(png_path, cv2.IMREAD_UNCHANGED)

    if sprite is None:
        raise ValueError(f"Could not load sprite asset: {png_path}")

    if sprite.ndim == 2:
        # Grayscale -> BGRA
        sprite = cv2.cvtColor(sprite, cv2.COLOR_GRAY2BGRA)

    elif sprite.shape[2] == 3:
        # BGR -> BGRA with fully opaque alpha
        sprite = cv2.cvtColor(sprite, cv2.COLOR_BGR2BGRA)

    elif sprite.shape[2] != 4:
        raise ValueError(
            f"Unexpected PNG channel count ({sprite.shape[2]}): {png_path}"
        )

    _cache[key] = sprite
    return sprite


def overlay_bgra(
    frame_bgr: np.ndarray,
    sprite_bgra: np.ndarray,
    cx: int,
    cy: int,
) -> None:
    """
    Alpha-composite `sprite_bgra` onto `frame_bgr` centered at (cx, cy).

    Modifies frame_bgr in place and silently clips the sprite at
    the frame edges.
    """
    h, w = sprite_bgra.shape[:2]

    # Sprite position in the destination frame.
    x0 = cx - w // 2
    y0 = cy - h // 2
    x1 = x0 + w
    y1 = y0 + h

    # Frame dimensions.
    fh, fw = frame_bgr.shape[:2]

    # Source crop coordinates.
    sx0 = max(0, -x0)
    sy0 = max(0, -y0)
    sx1 = w - max(0, x1 - fw)
    sy1 = h - max(0, y1 - fh)

    # Destination coordinates.
    dx0 = max(0, x0)
    dy0 = max(0, y0)
    dx1 = min(fw, x1)
    dy1 = min(fh, y1)

    # Completely off-screen.
    if sx1 <= sx0 or sy1 <= sy0 or dx1 <= dx0 or dy1 <= dy0:
        return

    sprite_crop = sprite_bgra[sy0:sy1, sx0:sx1]
    background_crop = frame_bgr[dy0:dy1, dx0:dx1]

    # Alpha channel: 0 = transparent, 255 = opaque.
    alpha = sprite_crop[:, :, 3:4].astype(np.float32) / 255.0

    foreground = sprite_crop[:, :, :3].astype(np.float32)
    background = background_crop.astype(np.float32)

    # Alpha compositing.
    blended = (
        foreground * alpha
        + background * (1.0 - alpha)
    )

    frame_bgr[dy0:dy1, dx0:dx1] = blended.astype(np.uint8)