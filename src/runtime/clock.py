"""`22` Clock — the only clock in the system (19 §Clocks; 30 rule 6).

Timestamps are integer milliseconds. `SystemClock` is Unix epoch ms (`WALL`); `LogClock` is
driven entirely by `t_occurred` of the log being replayed (`LOG`, ms from log start) and
never reads the OS. Injected by the composition root; nothing else may construct either.
"""

from __future__ import annotations

import time
from typing import Literal, Protocol

TimeKind = Literal["WALL", "LOG"]


class Clock(Protocol):
    kind: TimeKind

    def now(self) -> int: ...


class SystemClock:
    kind: TimeKind = "WALL"

    def now(self) -> int:
        return time.time_ns() // 1_000_000


class LogClock:
    """REPLAY. Advances only when the log reader says so; monotonic by construction."""

    kind: TimeKind = "LOG"

    def __init__(self, start: int = 0) -> None:
        self._t = start

    def now(self) -> int:
        return self._t

    def advance_to(self, t: int) -> None:
        if t > self._t:
            self._t = t
