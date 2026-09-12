"""The perception thread (39 §1): capture -> health -> calibration -> detect -> track ->
assemble -> grade -> `EventSink.emit`. One thread, one frame in memory at a time, nothing
persisted (24 §Data lifecycle). `process_frame` is synchronous and testable on synthetic
frames; the wall clock is read only inside the capture thread (19 §Clocks: `t_occurred` is
captured at frame acquisition).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from numpy.typing import NDArray

from src.domain import HealthStatus, StationConfig
from src.events import DRAFTEVENT_ADAPTER, EventSink

from .assembly import Assembler
from .calibration import detect_corners, homography_from_corners
from .config import PerceptionConfig
from .health import CAMERA_UNAVAILABLE, UNCALIBRATED, HealthMonitor
from .markers import detect_markers
from .segment import glove_blob
from .tracker import Tracker

RETRY_S = 2.0


@dataclass
class Handle:
    thread: threading.Thread | None
    stop_event: threading.Event


class PerceptionPipeline:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cfg: PerceptionConfig | None = None
        self._station: StationConfig | None = None
        self._sink: EventSink | None = None
        self._health: HealthMonitor | None = None
        self._tracker: Tracker | None = None
        self._assembler: Assembler | None = None
        self._H: NDArray[np.float64] | None = None
        self._counter = 0
        self._frame_no = 0

    # ---- lifecycle -------------------------------------------------------------------------
    def configure(self, cfg: PerceptionConfig, station: StationConfig) -> None:
        """Build the stages without a capture thread (tests drive `process_frame`)."""
        with self._lock:
            self._cfg = cfg
            self._station = station
            self._health = HealthMonitor(cfg)
            self._tracker = Tracker(cfg, station)
            self._assembler = Assembler(cfg, station)
            self._H = None if cfg.homography is None else np.array(cfg.homography, np.float64)
            self._counter = 0
            self._frame_no = 0

    def start(self, cfg: PerceptionConfig, station: StationConfig, sink: EventSink) -> Handle:
        self.configure(cfg, station)
        self._sink = sink
        stop = threading.Event()
        thread = threading.Thread(
            target=self._run, args=(cfg, stop), name="perception", daemon=True
        )
        thread.start()
        return Handle(thread=thread, stop_event=stop)

    def stop(self, h: Handle) -> None:
        h.stop_event.set()
        if h.thread is not None and h.thread.is_alive():
            h.thread.join(timeout=RETRY_S * 2)

    def health(self) -> HealthStatus:
        with self._lock:
            if self._health is None:
                return HealthStatus(healthy=False, causes=["not started"])
            return self._health.status()

    @property
    def vision_state(self) -> str:
        with self._lock:
            return "UNAVAILABLE" if self._health is None else self._health.state

    # ---- capture thread (the only place a clock is read) ---------------------------------------
    @staticmethod
    def _now_ms() -> int:
        return time.time_ns() // 1_000_000

    def _run(self, cfg: PerceptionConfig, stop: threading.Event) -> None:
        is_file = isinstance(cfg.camera_source, str)
        frame_index = 0
        while not stop.is_set():
            cap = cv2.VideoCapture(cfg.camera_source)
            if not cap.isOpened():
                cap.release()
                self._emit_all(self._condition(CAMERA_UNAVAILABLE, True, self._now_ms()))
                stop.wait(RETRY_S)
                continue
            self._emit_all(self._condition(CAMERA_UNAVAILABLE, False, self._now_ms()))
            while not stop.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    if is_file:
                        cap.release()
                        return  # end of a video file: the thread finishes
                    self._emit_all(self._check(self._now_ms()))
                    stop.wait(RETRY_S)
                    break  # reopen the camera
                if cfg.realtime:
                    t_ms = self._now_ms()
                else:
                    t_ms = frame_index * 1000 // max(1, cfg.fps)
                frame_index += 1
                self.process_frame(np.asarray(frame, dtype=np.uint8), t_ms)
                del frame
                if is_file and cfg.realtime:
                    stop.wait(1.0 / max(1, cfg.fps))
            cap.release()

    def _condition(self, cause: str, active: bool, t_ms: int) -> list[dict[str, Any]]:
        with self._lock:
            if self._health is None:
                return []
            return self._finalize_all(
                self._health.set_condition(cause, active, t_ms), self._frame_no
            )

    def _check(self, now_ms: int) -> list[dict[str, Any]]:
        with self._lock:
            if self._health is None:
                return []
            return self._finalize_all(self._health.check(now_ms), self._frame_no)

    def check(self, now_ms: int) -> list[dict[str, Any]]:
        """Starvation check callable by tests (the capture thread calls it itself)."""
        out = self._check(now_ms)
        self._emit_all(out)
        return out

    # ---- the synchronous, testable core ----------------------------------------------------------
    def process_frame(self, frame_bgr: NDArray[np.uint8], t_ms: int) -> list[dict[str, Any]]:
        with self._lock:
            out = self._process(frame_bgr, t_ms)
        self._emit_all(out)
        return out

    def _process(self, frame_bgr: NDArray[np.uint8], t_ms: int) -> list[dict[str, Any]]:
        cfg, health, tracker, assembler = self._cfg, self._health, self._tracker, self._assembler
        if cfg is None or health is None or tracker is None or assembler is None:
            raise RuntimeError("PerceptionPipeline.configure/start must be called first")
        self._frame_no += 1
        frame_no = self._frame_no
        raw: list[dict[str, object]] = list(health.on_frame(t_ms, frame_bgr))

        if self._H is None:
            corners = detect_corners(frame_bgr, cfg.marker_dictionary, cfg.corner_ids)
            if all(i in corners for i in cfg.corner_ids):
                self._H = homography_from_corners(
                    corners, cfg.corner_ids, cfg.width_mm, cfg.height_mm
                )
                raw += health.set_condition(UNCALIBRATED, False, t_ms)
            else:
                raw += health.set_condition(UNCALIBRATED, True, t_ms)
                return self._finalize_all(raw, frame_no)
        H = self._H

        glove = glove_blob(frame_bgr, cfg.hsv_lower, cfg.hsv_upper, cfg.min_area_px)
        markers = detect_markers(frame_bgr, cfg.marker_dictionary)
        tracks, honesty = tracker.update(t_ms, glove, markers, H)
        raw += honesty
        raw += assembler.step(t_ms, tracks)

        return self._finalize_all(raw, frame_no)

    def _finalize_all(self, drafts: list[dict[str, object]], frame_no: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for d in drafts:
            final = self._finalize(d, frame_no)
            if final is not None:
                out.append(final)
        return out

    def _finalize(self, draft: dict[str, object], frame_no: int) -> dict[str, Any] | None:
        """Grade (21 §Grade assignment) and complete the envelope. Below-threshold events are
        dropped, not downgraded. Returns None when dropped."""
        cfg = self._cfg
        assert cfg is not None
        kind = str(draft["type"])
        conf_raw = draft.get("confidence", 1.0)
        confidence = float(conf_raw) if isinstance(conf_raw, int | float) else 1.0
        observed, inferred = cfg.thresholds_for(kind)
        if confidence >= observed:
            grade = "OBSERVED"
        elif confidence >= inferred:
            grade = "INFERRED"
        else:
            return None
        self._counter += 1
        evidence_raw = draft.get("evidence")
        evidence: dict[str, Any] = dict(evidence_raw) if isinstance(evidence_raw, dict) else {}
        evidence.setdefault("track_ids", [])
        evidence.setdefault("zone_ids", [])
        evidence["frame_range"] = (frame_no, frame_no)
        payload: dict[str, Any] = {
            **{k: v for k, v in draft.items() if k != "evidence"},
            "event_id": f"pc-{self._counter:06d}",
            "station_id": cfg.station_id,
            "source": "PERCEPTION",
            "confidence": confidence,
            "grade": grade,
            "evidence": evidence,
        }
        return payload

    def _emit_all(self, payloads: list[dict[str, Any]]) -> None:
        sink = self._sink
        if sink is None:
            return
        for p in payloads:
            try:
                sink.emit(DRAFTEVENT_ADAPTER.validate_python(p))
            except Exception:
                # P10: a malformed draft may never crash perception; the sink quarantines
                # what it can, and an invalid payload is a defect caught by the tests.
                continue
