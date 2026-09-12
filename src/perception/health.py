"""Frame-health monitoring (21 obligation 6, 23 P5): frame starvation, static frames, low
frame rate, plus externally reported conditions (uncalibrated, camera unavailable).

Never stores a frame: static detection compares a digest of a heavily downsampled copy.
"""

from __future__ import annotations

import hashlib
from collections import deque

import cv2
import numpy as np
from numpy.typing import NDArray

from src.domain import HealthStatus

from .config import PerceptionConfig

STARVATION = "frame starvation"
STATIC = "static frame"
LOW_FPS = "low frame rate"
NO_FRAMES = "no frames yet"
UNCALIBRATED = "uncalibrated"
CAMERA_UNAVAILABLE = "camera unavailable"

UNAVAILABLE_CAUSES = frozenset({STARVATION, NO_FRAMES, UNCALIBRATED, CAMERA_UNAVAILABLE})
FPS_WINDOW_MS = 2000


def _digest(frame_bgr: NDArray[np.uint8]) -> bytes:
    small = cv2.resize(frame_bgr, (32, 18), interpolation=cv2.INTER_AREA)
    return hashlib.blake2b(np.ascontiguousarray(small).tobytes(), digest_size=16).digest()


class HealthMonitor:
    def __init__(self, cfg: PerceptionConfig) -> None:
        self._cfg = cfg
        self._causes: dict[str, bool] = {NO_FRAMES: True}
        self._last_frame_ms: int | None = None
        self._first_frame_ms: int | None = None
        self._reference_ms: int | None = None  # first check() when no frame has arrived
        self._times: deque[int] = deque()
        self._last_digest: bytes | None = None
        self._identical_run = 0

    # ---- conditions ------------------------------------------------------------------------
    def _set(self, cause: str, active: bool, t_ms: int) -> list[dict[str, object]]:
        """Flip a condition; a HEALTH_DEGRADED draft on the inactive->active transition only."""
        was = self._causes.get(cause, False)
        self._causes[cause] = active
        if active and not was:
            return [self._draft(cause, t_ms)]
        return []

    def set_condition(self, cause: str, active: bool, t_ms: int) -> list[dict[str, object]]:
        """Pipeline-level conditions (`uncalibrated`, `camera unavailable`)."""
        return self._set(cause, active, t_ms)

    @staticmethod
    def _draft(cause: str, t_ms: int) -> dict[str, object]:
        return {
            "type": "HEALTH_DEGRADED",
            "t_occurred": t_ms,
            "source": "PERCEPTION",
            "confidence": 1.0,
            "evidence": {"track_ids": [], "zone_ids": []},
            "cause": cause,
        }

    # ---- inputs ----------------------------------------------------------------------------
    def on_frame(self, t_ms: int, frame_bgr: NDArray[np.uint8]) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        self._causes[NO_FRAMES] = False
        out += self._set(STARVATION, False, t_ms)
        self._last_frame_ms = t_ms
        if self._first_frame_ms is None:
            self._first_frame_ms = t_ms

        # static frames: digest of a 32x18 thumbnail; the frame itself is never retained
        d = _digest(frame_bgr)
        self._identical_run = self._identical_run + 1 if d == self._last_digest else 1
        self._last_digest = d
        out += self._set(STATIC, self._identical_run >= self._cfg.static_frames, t_ms)

        # rolling frame rate over the last FPS_WINDOW_MS, evaluated once a full window exists
        self._times.append(t_ms)
        while self._times and t_ms - self._times[0] > FPS_WINDOW_MS:
            self._times.popleft()
        if t_ms - self._first_frame_ms >= FPS_WINDOW_MS:
            fps = len(self._times) * 1000.0 / FPS_WINDOW_MS
            out += self._set(LOW_FPS, fps < self._cfg.frame_rate_floor_fps, t_ms)
        return out

    def check(self, now_ms: int) -> list[dict[str, object]]:
        """Frame starvation: no frame for `frame_timeout_ms` (once per outage)."""
        if self._last_frame_ms is None:
            if self._reference_ms is None:
                self._reference_ms = now_ms
            since = self._reference_ms
        else:
            since = self._last_frame_ms
        if now_ms - since >= self._cfg.frame_timeout_ms:
            return self._set(STARVATION, True, now_ms)
        return []

    # ---- outputs ---------------------------------------------------------------------------
    def causes(self) -> list[str]:
        return [c for c, on in self._causes.items() if on]

    def status(self) -> HealthStatus:
        causes = self.causes()
        return HealthStatus(healthy=not causes, causes=causes)

    @property
    def state(self) -> str:
        causes = self.causes()
        if any(c in UNAVAILABLE_CAUSES for c in causes):
            return "UNAVAILABLE"
        if causes:
            return "DEGRADED"
        return "OK"
