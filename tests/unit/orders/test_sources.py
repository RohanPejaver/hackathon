"""OrderSource implementations (17, 22): ManualEntrySource and FixtureSource."""

from __future__ import annotations

import pytest

from src.domain import RawOrder
from src.orders import FixtureSource, ManualEntrySource, OrderSource


def order(external_id: str, received_at: int = 0) -> RawOrder:
    return RawOrder(
        external_id=external_id, items=["turkey_sandwich"], notes=[], received_at=received_at
    )


def test_both_satisfy_the_protocol() -> None:
    assert isinstance(ManualEntrySource(), OrderSource)
    assert isinstance(FixtureSource([]), OrderSource)


# --- ManualEntrySource ----------------------------------------------------------------------


def test_manual_submit_poll_ack_ordering() -> None:
    src = ManualEntrySource()
    assert src.poll() == []
    src.submit("A", ["pesto_sandwich"], ["pine nut allergy"], received_at=10)
    src.submit("B", ["turkey_sandwich"], [], received_at=20)
    src.submit("C", ["plain_bread"], ["vegan"], received_at=30)
    assert [o.external_id for o in src.poll()] == ["A", "B", "C"]
    assert src.poll()[0] == RawOrder(
        external_id="A", items=["pesto_sandwich"], notes=["pine nut allergy"], received_at=10
    )
    assert [o.external_id for o in src.poll()] == ["A", "B", "C"]  # polling never consumes
    src.ack("B")
    assert [o.external_id for o in src.poll()] == ["A", "C"]
    src.ack("A")
    src.ack("C")
    assert src.poll() == []


def test_manual_ack_is_idempotent_and_tolerates_unknown_ids() -> None:
    src = ManualEntrySource()
    src.submit("A", [], [], received_at=0)
    src.ack("nope")
    assert [o.external_id for o in src.poll()] == ["A"]
    src.ack("A")
    src.ack("A")
    assert src.poll() == []


def test_manual_duplicate_pending_id_is_rejected_until_acked() -> None:
    src = ManualEntrySource()
    src.submit("A", [], [], received_at=0)
    with pytest.raises(ValueError, match="already pending"):
        src.submit("A", [], [], received_at=1)
    src.ack("A")
    src.submit("A", ["x"], [], received_at=2)  # a new order may reuse the id after ack
    assert src.poll()[0].received_at == 2


def test_manual_copies_its_inputs() -> None:
    src = ManualEntrySource()
    items, notes = ["a"], ["n"]
    src.submit("A", items, notes, received_at=0)
    items.append("b")
    notes.append("m")
    assert src.poll()[0].items == ["a"]
    assert src.poll()[0].notes == ["n"]


# --- FixtureSource --------------------------------------------------------------------------


def test_fixture_poll_returns_all_unacked_in_order() -> None:
    src = FixtureSource([order("A", 1), order("B", 2), order("C", 3)])
    assert [o.external_id for o in src.poll()] == ["A", "B", "C"]
    assert [o.external_id for o in src.poll()] == ["A", "B", "C"]  # idempotent poll
    src.ack("B")
    assert [o.external_id for o in src.poll()] == ["A", "C"]


def test_fixture_ack_is_idempotent() -> None:
    src = FixtureSource([order("A"), order("B")])
    src.ack("A")
    src.ack("A")
    src.ack("zzz")
    assert [o.external_id for o in src.poll()] == ["B"]
    src.ack("B")
    assert src.poll() == []
    assert src.poll() == []


def test_fixture_rejects_duplicate_external_ids() -> None:
    with pytest.raises(ValueError, match="duplicate external_id"):
        FixtureSource([order("A"), order("A")])


def test_fixture_does_not_alias_the_input_list() -> None:
    orders = [order("A")]
    src = FixtureSource(orders)
    orders.append(order("B"))
    assert [o.external_id for o in src.poll()] == ["A"]
