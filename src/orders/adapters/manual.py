"""``ManualEntrySource`` — a cashier types the order (17 §Abstract source)."""

from __future__ import annotations

from src.domain import RawOrder


class ManualEntrySource:
    """In-memory queue of typed orders. ``received_at`` is supplied by the caller: the
    orders layer has no clock (19; ``tests/property/test_architecture.py``)."""

    def __init__(self) -> None:
        self._pending: dict[str, RawOrder] = {}  # insertion order == submission order

    def submit(
        self, external_id: str, items: list[str], notes: list[str], received_at: int
    ) -> None:
        if external_id in self._pending:
            raise ValueError(f"order {external_id!r} is already pending; ack it first")
        self._pending[external_id] = RawOrder(
            external_id=external_id,
            items=list(items),
            notes=list(notes),
            received_at=received_at,
        )

    def poll(self) -> list[RawOrder]:
        return list(self._pending.values())

    def ack(self, external_id: str) -> None:
        self._pending.pop(external_id, None)
