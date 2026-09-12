"""`22` RuntimeController — the only owner of mode transitions (10 §Feedback edges).

Perception and the core *report*; the controller *decides*, and every decision is an event
(`STATION_MODE_CHANGED`) so mode is state (10). Rules, from 10 §Runtime modes, 23 P5/P11/P12,
ADR-0011:
  - config invalid  -> stay in CALIBRATION with the specific error; FULL refused
  - vision lost while FULL -> PROTOCOL_ONLY; vision healthy for t_recover -> back to FULL
    (carrier trust is *not* restored here — the reducer keeps carriers UNKNOWN until re-observed)
  - core exception -> PROTOCOL_ONLY, reasoning DOWN, incident recorded; never fail open
  - CALIBRATION: no ticket may bind
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from src.runtime.clock import Clock

Mode = Literal["FULL", "PROTOCOL_ONLY", "REPLAY", "CALIBRATION"]
Vision = Literal["OK", "DEGRADED", "UNAVAILABLE"]

# A draft event as a plain mapping; the composition root turns it into A's DraftEvent type.
Sink = Callable[[dict[str, Any]], None]


class RuntimeController:
    def __init__(
        self, sink: Sink, clock: Clock, t_recover_s: int, initial: Mode = "CALIBRATION"
    ) -> None:
        self._sink = sink
        self._clock = clock
        self._t_recover_ms = t_recover_s * 1000
        self._mode: Mode = initial
        self._config_ok = False
        self._message: str | None = "config not loaded"  # the specific reason shown in the banner
        self._vision: Vision = "UNAVAILABLE"
        self._vision_ok_since: int | None = None
        self._reasoning: Literal["OK", "DOWN"] = "OK"
        self._incident: str | None = None
        self._rejected = 0
        self._late = 0
        self._committed = 0

    # ---- 22 signatures --------------------------------------------------------------------
    def mode(self) -> Mode:
        return self._mode

    def request_mode(self, m: Mode, cause: str) -> None:
        if m == self._mode:
            return
        if m == "FULL" and not self._config_ok:
            self._message = f"FULL refused: {self._message}"
            return
        if m == "FULL" and self._vision != "OK":
            return  # FULL means vision is up; the caller reports vision first
        previous, self._mode = self._mode, m
        self._sink(
            {
                "type": "STATION_MODE_CHANGED",
                "t_occurred": self._clock.now(),
                "source": "SYSTEM",
                "grade": "OBSERVED",
                "payload": {"mode": m, "previous": previous, "cause": cause},
            }
        )

    def health(self) -> dict[str, Any]:
        return {
            "vision": self._vision,
            "reasoning": self._reasoning,
            "late_rate": (self._late / self._committed) if self._committed else 0.0,
            "rejected_events": self._rejected,
            "message": self._message,
            "last_incident_event_id": self._incident,
        }

    # ---- reports (inputs to the decision; never decisions themselves) -----------------------
    def report_config(self, ok: bool, message: str | None = None) -> None:
        self._config_ok, self._message = ok, message

    def report_vision(self, status: Vision) -> None:
        now = self._clock.now()
        self._vision = status
        if status != "OK":
            self._vision_ok_since = None
            if self._mode == "FULL":
                self.request_mode("PROTOCOL_ONLY", f"vision {status.lower()}")
            return
        if self._vision_ok_since is None:
            self._vision_ok_since = now
        recovered = now - self._vision_ok_since >= self._t_recover_ms
        if self._mode == "PROTOCOL_ONLY" and self._reasoning == "OK" and recovered:
            self.request_mode("FULL", "vision healthy for t_recover")

    def report_core_exception(self, event_id: str | None, exc: BaseException) -> None:
        self._reasoning = "DOWN"
        self._incident = event_id
        self._message = f"reasoning fault on {event_id}: {type(exc).__name__}: {exc}"
        if self._mode != "PROTOCOL_ONLY":
            self.request_mode("PROTOCOL_ONLY", f"core exception on {event_id}")

    def report_rejected(self) -> None:
        self._rejected += 1

    def report_committed(self, late: bool) -> None:
        self._committed += 1
        self._late += int(late)

    def bind_allowed(self) -> bool:
        return self._mode != "CALIBRATION"
