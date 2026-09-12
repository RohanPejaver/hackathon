"""17 §Ticket lifecycle, 11 inv. 1 / 17 inv. 1-2, the FOOD carrier, MULTI_RESTRICTION."""

from __future__ import annotations

from src.domain import (
    CarrierKind,
    Config,
    EpistemicStatus,
    Mode,
    Resolution,
    TicketLifecycle,
    WorldState,
)
from src.state import MULTI_RESTRICTION, food_carrier_id, initial, reduce
from tests.unit.state.conftest import (
    contact,
    ev,
    fold,
    make_station,
    ticket_bound,
    ticket_received,
    zone_entry,
)

AMBIGUOUS = [{"raw_text": "ALLERGY", "resolution": "AMBIGUOUS"}]


def lifecycle(state: WorldState, ticket: str) -> TicketLifecycle:
    return state.tickets[ticket].lifecycle


# -- RECEIVED / RESOLVED / BLOCKED ---------------------------------------------------------


def test_ticket_received_creates_ticket(state: WorldState, cfg: Config) -> None:
    e = ticket_received(10, "T1", "PINE_NUT", order_source="manual")
    new, deltas = reduce(state, e, cfg)
    t = new.tickets["T1"]
    assert t.lifecycle == TicketLifecycle.RECEIVED
    assert t.items == ["turkey_sandwich"] and t.source == "manual"
    assert t.restrictions[0].allergen_ids == frozenset({"PINE_NUT"})
    assert t.bound_station is None and t.bound_at is None and t.landing_zone is None
    assert [d.rule_id for d in deltas] == ["ticket_received"]
    dup, deltas = reduce(new, ticket_received(11, "T1", "EGG"), cfg)
    assert dup is new and deltas == []


def test_restriction_resolved_replaces_restrictions_only(state: WorldState, cfg: Config) -> None:
    s = fold(state, [ticket_received(10, "T1", restrictions=AMBIGUOUS)], cfg)
    assert s.tickets["T1"].restrictions[0].resolution == Resolution.AMBIGUOUS
    resolved = [{"raw_text": "ALLERGY", "resolution": "RESOLVED", "allergen_ids": ["PINE_NUT"]}]
    new, deltas = reduce(
        s, ev("TICKET_RESTRICTION_RESOLVED", 12, ticket="T1", restrictions=resolved), cfg
    )
    assert new.tickets["T1"].restrictions[0].allergen_ids == frozenset({"PINE_NUT"})
    assert lifecycle(new, "T1") == TicketLifecycle.RECEIVED
    assert [d.rule_id for d in deltas] == ["ticket_restriction_resolved"]


def test_blocked_sets_lifecycle(state: WorldState, cfg: Config) -> None:
    s = fold(state, [ticket_received(10, "T1", restrictions=AMBIGUOUS)], cfg)
    new = fold(s, [ev("TICKET_BLOCKED", 11, ticket="T1", reason="ambiguous")], cfg)
    assert lifecycle(new, "T1") == TicketLifecycle.BLOCKED


def test_unknown_ticket_events_are_rejected(state: WorldState, cfg: Config) -> None:
    for e in (
        ev("TICKET_BLOCKED", 1, ticket="nope", reason="r"),
        ticket_bound(1, "nope"),
        ev("TICKET_PREP_STARTED", 1, ticket="nope"),
        ev("TICKET_ITEM_COMPLETE", 1, ticket="nope"),
        ev("TICKET_HELD", 1, ticket="nope", alert_id="a"),
        ev("TICKET_RELEASED", 1, ticket="nope", worker_slot=0),
        ev("TICKET_VOIDED", 1, ticket="nope", reason="r"),
        ev("TICKET_ITEM_SUBSTITUTED", 1, ticket="nope", items=["x"]),
        ev("TICKET_RESTRICTION_RESOLVED", 1, ticket="nope", restrictions=[]),
    ):
        new, deltas = reduce(state, e, cfg)
        assert new is state and deltas == [], e.type


# -- BOUND: the guarded transition -----------------------------------------------------------


def test_bound_from_received_with_resolved_restrictions(state: WorldState, cfg: Config) -> None:
    s = fold(state, [ticket_received(10, "T1", "PINE_NUT")], cfg)
    e = ticket_bound(20, "T1")
    new, deltas = reduce(s, e, cfg)
    t = new.tickets["T1"]
    assert t.lifecycle == TicketLifecycle.BOUND
    assert t.bound_station == "demo-bagel" and t.bound_at == 20
    assert t.landing_zone == "landing"  # first LANDING zone by id
    assert new.station.bound_tickets == ["T1"]
    assert new.conditions == []
    assert {d.rule_id for d in deltas} == {"ticket_bound"}


def test_bound_honours_explicit_landing_zone(state: WorldState, cfg: Config) -> None:
    s = fold(
        state,
        [ticket_received(10, "T1", "PINE_NUT"), ticket_bound(20, "T1", landing_zone="work")],
        cfg,
    )
    assert s.tickets["T1"].landing_zone == "work"


def test_bound_without_landing_zone_in_station(cfg: Config) -> None:
    st = make_station()
    st = st.model_copy(update={"zones": {k: v for k, v in st.zones.items() if k != "landing"}})
    s = fold(initial(cfg, st), [ticket_received(10, "T1", "PINE_NUT"), ticket_bound(20, "T1")], cfg)
    assert s.tickets["T1"].lifecycle == TicketLifecycle.BOUND
    assert s.tickets["T1"].landing_zone is None


def test_blocked_to_bound_is_unreachable(state: WorldState, cfg: Config) -> None:
    s = fold(
        state,
        [ticket_received(10, "T1", "PINE_NUT"), ev("TICKET_BLOCKED", 11, ticket="T1", reason="r")],
        cfg,
    )
    new, deltas = reduce(s, ticket_bound(20, "T1"), cfg)
    assert new is s and deltas == []
    assert lifecycle(new, "T1") == TicketLifecycle.BLOCKED
    assert new.station.bound_tickets == []


def test_ambiguous_restriction_cannot_bind(state: WorldState, cfg: Config) -> None:
    s = fold(state, [ticket_received(10, "T1", restrictions=AMBIGUOUS)], cfg)
    new, deltas = reduce(s, ticket_bound(20, "T1"), cfg)
    assert new is s and deltas == []
    unresolvable = [{"raw_text": "moon dust", "resolution": "UNRESOLVABLE"}]
    s2 = fold(state, [ticket_received(10, "T2", restrictions=unresolvable)], cfg)
    new, deltas = reduce(s2, ticket_bound(20, "T2"), cfg)
    assert new is s2 and deltas == []


def test_calibration_mode_cannot_bind(cfg: Config) -> None:
    s = initial(cfg, make_station(mode=Mode.CALIBRATION))
    s = fold(s, [ticket_received(10, "T1", "PINE_NUT")], cfg)
    new, deltas = reduce(s, ticket_bound(20, "T1"), cfg)
    assert new is s and deltas == []
    ready = fold(s, [ev("STATION_MODE_CHANGED", 15, mode="FULL", cause="calibrated")], cfg)
    assert lifecycle(fold(ready, [ticket_bound(20, "T1")], cfg), "T1") == TicketLifecycle.BOUND


def test_bound_is_not_repeatable(bound_ticket: WorldState, cfg: Config) -> None:
    new, deltas = reduce(bound_ticket, ticket_bound(25, "T1"), cfg)
    assert new is bound_ticket and deltas == []


def test_unrestricted_ticket_binds(state: WorldState, cfg: Config) -> None:
    s = fold(state, [ticket_received(10, "T1"), ticket_bound(20, "T1")], cfg)
    assert lifecycle(s, "T1") == TicketLifecycle.BOUND


# -- MULTI_RESTRICTION (17 §Concurrency, scenario F) ---------------------------------------


def test_two_restricted_bound_tickets_raise_multi_restriction(
    bound_ticket: WorldState, cfg: Config
) -> None:
    s = fold(bound_ticket, [ticket_received(30, "T2", "EGG")], cfg)
    assert s.conditions == []
    new, deltas = reduce(s, ticket_bound(40, "T2"), cfg)
    assert new.conditions == [MULTI_RESTRICTION]
    assert any(d.rule_id == "multi_restriction" and d.after == [MULTI_RESTRICTION] for d in deltas)
    # an unrestricted third ticket changes nothing; releasing one clears the condition
    three = fold(new, [ticket_received(50, "T3"), ticket_bound(60, "T3")], cfg)
    assert three.conditions == [MULTI_RESTRICTION]
    cleared = fold(three, [ev("TICKET_VOIDED", 70, ticket="T2", reason="abandoned")], cfg)
    assert cleared.conditions == []
    assert cleared.station.bound_tickets == ["T1", "T3"]


def test_unrestricted_pair_raises_nothing(state: WorldState, cfg: Config) -> None:
    s = fold(
        state,
        [
            ticket_received(1, "A"),
            ticket_bound(2, "A"),
            ticket_received(3, "B", "EGG"),
            ticket_bound(4, "B"),
        ],
        cfg,
    )
    assert s.conditions == []


# -- IN_PREP / COMPLETE / HELD / RELEASED / VOIDED and the FOOD carrier -----------------------


def test_prep_started_creates_food_carrier(bound_ticket: WorldState, cfg: Config) -> None:
    e = ev("TICKET_PREP_STARTED", 30, ticket="T1")
    new, deltas = reduce(bound_ticket, e, cfg)
    assert lifecycle(new, "T1") == TicketLifecycle.IN_PREP
    food = new.station.carriers[food_carrier_id("T1")]
    assert food.carrier_id == "food:T1"
    assert food.kind == CarrierKind.FOOD
    assert food.taints == {} and food.resettable_by == frozenset()
    assert food.epistemic == EpistemicStatus.TRACKED and food.last_observed_at == 30
    assert food.home_zone == "landing"
    assert {d.rule_id for d in deltas} == {"ticket_prep_started"}


def test_prep_started_landing_override(bound_ticket: WorldState, cfg: Config) -> None:
    new = fold(bound_ticket, [ev("TICKET_PREP_STARTED", 30, ticket="T1", landing_zone="work")], cfg)
    assert new.tickets["T1"].landing_zone == "work"
    assert new.station.carriers["food:T1"].home_zone == "work"


def test_prep_started_requires_bound(state: WorldState, cfg: Config) -> None:
    s = fold(state, [ticket_received(10, "T1", "PINE_NUT")], cfg)
    new, deltas = reduce(s, ev("TICKET_PREP_STARTED", 30, ticket="T1"), cfg)
    assert new is s and deltas == []
    assert "food:T1" not in new.station.carriers


def test_complete_held_released_path(bound_ticket: WorldState, cfg: Config) -> None:
    s = fold(bound_ticket, [ev("TICKET_PREP_STARTED", 30, ticket="T1")], cfg)
    premature, deltas = reduce(bound_ticket, ev("TICKET_ITEM_COMPLETE", 31, ticket="T1"), cfg)
    assert premature is bound_ticket and deltas == []
    s = fold(s, [ev("TICKET_ITEM_COMPLETE", 40, ticket="T1")], cfg)
    assert lifecycle(s, "T1") == TicketLifecycle.COMPLETE
    held = fold(s, [ev("TICKET_HELD", 50, ticket="T1", alert_id="a1")], cfg)
    assert lifecycle(held, "T1") == TicketLifecycle.HELD
    assert "food:T1" in held.station.carriers  # a held item is still the pathway target
    released, deltas = reduce(held, ev("TICKET_RELEASED", 60, ticket="T1", worker_slot=0), cfg)
    assert lifecycle(released, "T1") == TicketLifecycle.RELEASED
    assert "food:T1" not in released.station.carriers
    assert released.station.bound_tickets == []
    assert {d.rule_id for d in deltas} == {"ticket_released"}


def test_held_from_in_prep_and_release_from_complete(bound_ticket: WorldState, cfg: Config) -> None:
    s = fold(bound_ticket, [ev("TICKET_PREP_STARTED", 30, ticket="T1")], cfg)
    held = fold(s, [ev("TICKET_HELD", 50, ticket="T1", alert_id="a1")], cfg)
    assert lifecycle(held, "T1") == TicketLifecycle.HELD
    complete = fold(s, [ev("TICKET_ITEM_COMPLETE", 40, ticket="T1")], cfg)
    released = fold(complete, [ev("TICKET_RELEASED", 60, ticket="T1", worker_slot=0)], cfg)
    assert lifecycle(released, "T1") == TicketLifecycle.RELEASED


def test_release_needs_held_or_complete(bound_ticket: WorldState, cfg: Config) -> None:
    for s in (bound_ticket, fold(bound_ticket, [ev("TICKET_PREP_STARTED", 30, ticket="T1")], cfg)):
        new, deltas = reduce(s, ev("TICKET_RELEASED", 60, ticket="T1", worker_slot=0), cfg)
        assert new is s and deltas == []


def test_held_needs_in_prep_or_complete(bound_ticket: WorldState, cfg: Config) -> None:
    new, deltas = reduce(bound_ticket, ev("TICKET_HELD", 50, ticket="T1", alert_id="a1"), cfg)
    assert new is bound_ticket and deltas == []


def test_voided_from_any_open_state_destroys_food(bound_ticket: WorldState, cfg: Config) -> None:
    s = fold(
        bound_ticket,
        [
            ev("TICKET_PREP_STARTED", 30, ticket="T1"),
            zone_entry(100, "gloves", "bin:pesto"),
            contact(200, "gloves", "food:T1"),
        ],
        cfg,
    )
    new = fold(s, [ev("TICKET_VOIDED", 300, ticket="T1", reason="remake")], cfg)
    assert lifecycle(new, "T1") == TicketLifecycle.VOIDED
    assert "food:T1" not in new.station.carriers
    assert new.station.bound_tickets == []
    assert new.acquisitions["food:T1"]  # its history remains in the log projection
    for terminal in ("RELEASED", "VOIDED"):
        s2 = fold(
            bound_ticket,
            [
                ev("TICKET_PREP_STARTED", 30, ticket="T1"),
                ev("TICKET_ITEM_COMPLETE", 40, ticket="T1"),
            ],
            cfg,
        )
        s2 = fold(
            s2,
            [ev("TICKET_RELEASED", 50, ticket="T1", worker_slot=0)]
            if terminal == "RELEASED"
            else [ev("TICKET_VOIDED", 50, ticket="T1", reason="r")],
            cfg,
        )
        again, deltas = reduce(s2, ev("TICKET_VOIDED", 60, ticket="T1", reason="r"), cfg)
        assert again is s2 and deltas == []


def test_voided_received_ticket(state: WorldState, cfg: Config) -> None:
    s = fold(state, [ticket_received(10, "T1", "PINE_NUT")], cfg)
    new = fold(s, [ev("TICKET_VOIDED", 20, ticket="T1", reason="timeout")], cfg)
    assert lifecycle(new, "T1") == TicketLifecycle.VOIDED
    assert new.station.bound_tickets == []


# -- rework / substitution -------------------------------------------------------------------


def test_rework_opens_new_ticket(bound_ticket: WorldState, cfg: Config) -> None:
    s = fold(bound_ticket, [ev("TICKET_VOIDED", 30, ticket="T1", reason="remake")], cfg)
    e = ev(
        "TICKET_REWORK_OPENED",
        40,
        ticket="T1-R",
        rework_of="T1",
        items=["turkey_sandwich"],
        restrictions=[
            {"raw_text": "pine nut", "resolution": "RESOLVED", "allergen_ids": ["PINE_NUT"]}
        ],
    )
    new, deltas = reduce(s, e, cfg)
    t = new.tickets["T1-R"]
    assert t.lifecycle == TicketLifecycle.RECEIVED and t.rework_of == "T1"
    assert t.source == s.tickets["T1"].source
    assert lifecycle(new, "T1") == TicketLifecycle.VOIDED  # never mutated backwards
    assert [d.rule_id for d in deltas] == ["ticket_rework_opened"]
    dup, deltas = reduce(new, e, cfg)
    assert dup is new and deltas == []


def test_item_substituted_replaces_items(bound_ticket: WorldState, cfg: Config) -> None:
    new, deltas = reduce(
        bound_ticket, ev("TICKET_ITEM_SUBSTITUTED", 30, ticket="T1", items=["bagel"]), cfg
    )
    assert new.tickets["T1"].items == ["bagel"]
    assert lifecycle(new, "T1") == TicketLifecycle.BOUND
    assert [(d.rule_id, d.before, d.after) for d in deltas] == [
        ("ticket_item_substituted", ["turkey_sandwich"], ["bagel"])
    ]
