"""``FixtureSource`` — replay (17 §Abstract source): a fixed list of orders."""

from __future__ import annotations

from src.domain import RawOrder


class FixtureSource:
    def __init__(self, orders: list[RawOrder]) -> None:
        ids = [order.external_id for order in orders]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"fixture has duplicate external_id(s): {duplicates}")
        self._orders: tuple[RawOrder, ...] = tuple(orders)
        self._acked: set[str] = set()

    def poll(self) -> list[RawOrder]:
        return [order for order in self._orders if order.external_id not in self._acked]

    def ack(self, external_id: str) -> None:
        self._acked.add(external_id)
