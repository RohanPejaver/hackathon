"""``OrderSource`` (17 §Abstract source; 22 §OrderSource).

No third-party platform appears in the core. Implementations live in ``orders/adapters/``
and that is the only place a third-party schema may appear. MVP ships ``ManualEntrySource``
and ``FixtureSource``; POS/delivery adapters are explicitly deferred (17).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain import RawOrder


@runtime_checkable
class OrderSource(Protocol):
    def poll(self) -> list[RawOrder]:
        """Every order not yet acknowledged, oldest first. Polling never consumes."""
        ...

    def ack(self, external_id: str) -> None:
        """Acknowledge one order so it stops appearing in ``poll``. Idempotent."""
        ...
