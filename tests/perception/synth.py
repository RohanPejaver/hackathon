"""Synthetic overhead frames for the perception tests (35: no camera exists yet; the
geometry is what is under test, so rendered fiducials + a coloured disc are sufficient).

Station frame: 1200 x 600 mm. The four corner markers (ids 0..3) sit at
`DEFAULT_CORNERS_PX` so that the station maps to 1080 x 520 px; image y grows downward and
id 0 (the front-left origin) is at the BOTTOM-left of the image.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from numpy.typing import NDArray

WIDTH_MM = 1200.0
HEIGHT_MM = 600.0
DEFAULT_CORNERS_PX: dict[int, tuple[int, int]] = {
    0: (100, 620),  # front-left = origin (0, 0)
    1: (1180, 620),  # front-right = (W, 0)
    2: (1180, 100),  # back-right = (W, H)
    3: (100, 100),  # back-left = (0, H)
}
CORNER_SIZE_PX = 80
_SX = (DEFAULT_CORNERS_PX[1][0] - DEFAULT_CORNERS_PX[0][0]) / WIDTH_MM  # 0.9 px/mm
_SY = (DEFAULT_CORNERS_PX[0][1] - DEFAULT_CORNERS_PX[3][1]) / HEIGHT_MM  # 0.8667 px/mm


def mm_to_px(xy_mm: tuple[float, float]) -> tuple[int, int]:
    """Station mm -> image px under the linear map the default corners define."""
    x_px = DEFAULT_CORNERS_PX[0][0] + xy_mm[0] * _SX
    y_px = DEFAULT_CORNERS_PX[0][1] - xy_mm[1] * _SY
    return int(round(x_px)), int(round(y_px))


def _paste_marker(
    img: NDArray[np.uint8], dictionary: str, marker_id: int, centre: tuple[int, int], size: int
) -> None:
    d = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary))
    tile = cv2.aruco.generateImageMarker(d, marker_id, size)
    half = size // 2
    x0, y0 = centre[0] - half, centre[1] - half
    h, w = img.shape[:2]
    if x0 < 0 or y0 < 0 or x0 + size > w or y0 + size > h:
        raise ValueError(f"marker {marker_id} at {centre} does not fit the frame")
    img[y0 : y0 + size, x0 : x0 + size] = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)


def render_frame(
    *,
    width: int = 1280,
    height: int = 720,
    corners_px: dict[int, tuple[int, int]] | None = None,
    glove_px: tuple[int, int] | None = None,
    glove_radius_px: int = 60,
    glove_color_bgr: tuple[int, int, int] = (200, 60, 20),
    markers_px: dict[int, tuple[int, int]] | None = None,
    marker_size_px: int = 48,
    dictionary: str = "DICT_4X4_50",
) -> NDArray[np.uint8]:
    img: NDArray[np.uint8] = np.full((height, width, 3), 255, dtype=np.uint8)
    corners = DEFAULT_CORNERS_PX if corners_px is None else corners_px
    for mid, centre in corners.items():
        _paste_marker(img, dictionary, mid, centre, CORNER_SIZE_PX)
    for mid, centre in (markers_px or {}).items():
        _paste_marker(img, dictionary, mid, centre, marker_size_px)
    if glove_px is not None:
        cv2.circle(img, glove_px, glove_radius_px, glove_color_bgr, thickness=-1)
    return img


def write_video(path: Path | str, frames: list[NDArray[np.uint8]], fps: int = 15) -> None:
    if not frames:
        raise ValueError("no frames")
    h, w = frames[0].shape[:2]
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"cannot open video writer for {path}")
    try:
        for f in frames:
            writer.write(f)
    finally:
        writer.release()
