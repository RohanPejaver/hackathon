"""Ticket lifecycle transitions (17 §Ticket lifecycle) and the MULTI_RESTRICTION condition
(17 §Concurrency). The FOOD carrier `food:<ticket_id>` is the target node of every pathway
search (11 §Classification, "FoodItem (in progress)"); it exists only between
TICKET_PREP_STARTED and TICKET_RELEASED / TICKET_VOIDED and is never reset (11 inv. 7).
"""

from __future__ import annotations

from src.domain import (
    Carrier,
    CarrierKind,
    EpistemicStatus,
    Mode,
    Resolution,
    Ticket,
    TicketLifecycle,
    ZoneKind,
)
from src.events.catalog import (
    GradedTicketBlocked,
    GradedTicketBound,
    GradedTicketHeld,
    GradedTicketItemComplete,
    GradedTicketItemSubstituted,
    GradedTicketPrepStarted,
    GradedTicketReceived,
    GradedTicketReleased,
    GradedTicketRestrictionResolved,
    GradedTicketReworkOpened,
    GradedTicketVoided,
)

from ._draft import Draft, as_json

MULTI_RESTRICTION = "MULTI_RESTRICTION"
ACTIVE = frozenset(
    {
        TicketLifecycle.BOUND,
        TicketLifecycle.IN_PREP,
        TicketLifecycle.COMPLETE,
        TicketLifecycle.HELD,
    }
)


def food_carrier_id(ticket_id: str) -> str:
    return f"food:{ticket_id}"


def restricted(ticket: Ticket) -> bool:
    return any(r.allergen_ids for r in ticket.restrictions)


def recompute_conditions(draft: Draft) -> None:
    active = [
        t
        for tid in draft.bound_tickets
        if (t := draft.tickets.get(tid)) is not None and t.lifecycle in ACTIVE and restricted(t)
    ]
    conditions = [MULTI_RESTRICTION] if len(active) >= 2 else []
    if conditions != draft.conditions:
        draft.delta(
            "multi_restriction", "conditions", as_json(draft.conditions), as_json(conditions)
        )
        draft.conditions = conditions


def _unbind(draft: Draft, rule_id: str, ticket_id: str) -> None:
    if ticket_id in draft.bound_tickets:
        before = list(draft.bound_tickets)
        draft.bound_tickets = [t for t in draft.bound_tickets if t != ticket_id]
        draft.delta(rule_id, "bound_tickets", as_json(before), as_json(draft.bound_tickets))
    draft.remove_carrier(rule_id, food_carrier_id(ticket_id))


def received(draft: Draft, e: GradedTicketReceived) -> bool:
    if e.ticket in draft.tickets:
        return False
    draft.add_ticket(
        "ticket_received",
        Ticket(
            ticket_id=e.ticket,
            items=list(e.items),
            restrictions=list(e.restrictions),
            source=e.order_source,
            lifecycle=TicketLifecycle.RECEIVED,
        ),
    )
    return True


def restriction_resolved(draft: Draft, e: GradedTicketRestrictionResolved) -> bool:
    ticket = draft.tickets.get(e.ticket)
    if ticket is None:
        return False
    draft.set_ticket("ticket_restriction_resolved", ticket, restrictions=list(e.restrictions))
    recompute_conditions(draft)
    return True


def blocked(draft: Draft, e: GradedTicketBlocked) -> bool:
    ticket = draft.tickets.get(e.ticket)
    if ticket is None:
        return False
    draft.set_ticket("ticket_blocked", ticket, lifecycle=TicketLifecycle.BLOCKED)
    return True


def bound(draft: Draft, e: GradedTicketBound, station_id: str) -> bool:
    """11 inv. 1 / 17 inv. 1: only a RECEIVED ticket whose every restriction is RESOLVED may
    bind, and never while the station is calibrating (23 P12)."""
    ticket = draft.tickets.get(e.ticket)
    if (
        ticket is None
        or ticket.lifecycle != TicketLifecycle.RECEIVED
        or any(r.resolution != Resolution.RESOLVED for r in ticket.restrictions)
        or draft.mode == Mode.CALIBRATION
    ):
        return False
    landing = e.landing_zone or _default_landing(draft)
    draft.set_ticket(
        "ticket_bound",
        ticket,
        lifecycle=TicketLifecycle.BOUND,
        bound_station=station_id,
        bound_at=draft.t,
        landing_zone=landing,
    )
    before = list(draft.bound_tickets)
    draft.bound_tickets = [*draft.bound_tickets, e.ticket]
    draft.delta("ticket_bound", "bound_tickets", as_json(before), as_json(draft.bound_tickets))
    recompute_conditions(draft)
    return True


def _default_landing(draft: Draft) -> str | None:
    landings = sorted(z.zone_id for z in draft.zones.values() if z.kind == ZoneKind.LANDING)
    return landings[0] if landings else None


def prep_started(draft: Draft, e: GradedTicketPrepStarted) -> bool:
    ticket = draft.tickets.get(e.ticket)
    if ticket is None or ticket.lifecycle != TicketLifecycle.BOUND:
        return False
    landing = e.landing_zone or ticket.landing_zone
    draft.set_ticket(
        "ticket_prep_started", ticket, lifecycle=TicketLifecycle.IN_PREP, landing_zone=landing
    )
    draft.add_carrier(
        "ticket_prep_started",
        Carrier(
            carrier_id=food_carrier_id(e.ticket),
            kind=CarrierKind.FOOD,
            taints={},
            epistemic=EpistemicStatus.TRACKED,
            last_observed_at=draft.t,
            home_zone=landing,
            resettable_by=frozenset(),
        ),
    )
    return True


def item_complete(draft: Draft, e: GradedTicketItemComplete) -> bool:
    ticket = draft.tickets.get(e.ticket)
    if ticket is None or ticket.lifecycle != TicketLifecycle.IN_PREP:
        return False
    draft.set_ticket("ticket_item_complete", ticket, lifecycle=TicketLifecycle.COMPLETE)
    return True


def held(draft: Draft, e: GradedTicketHeld) -> bool:
    ticket = draft.tickets.get(e.ticket)
    if ticket is None or ticket.lifecycle not in (
        TicketLifecycle.IN_PREP,
        TicketLifecycle.COMPLETE,
    ):
        return False
    draft.set_ticket("ticket_held", ticket, lifecycle=TicketLifecycle.HELD)
    return True


def released(draft: Draft, e: GradedTicketReleased) -> bool:
    """17 inv. 2: only a human releases, and only a held or complete item can be released."""
    ticket = draft.tickets.get(e.ticket)
    if ticket is None or ticket.lifecycle not in (
        TicketLifecycle.HELD,
        TicketLifecycle.COMPLETE,
    ):
        return False
    draft.set_ticket("ticket_released", ticket, lifecycle=TicketLifecycle.RELEASED)
    _unbind(draft, "ticket_released", e.ticket)
    recompute_conditions(draft)
    return True


def voided(draft: Draft, e: GradedTicketVoided) -> bool:
    ticket = draft.tickets.get(e.ticket)
    if ticket is None or ticket.lifecycle in (
        TicketLifecycle.RELEASED,
        TicketLifecycle.VOIDED,
    ):
        return False
    draft.set_ticket("ticket_voided", ticket, lifecycle=TicketLifecycle.VOIDED)
    _unbind(draft, "ticket_voided", e.ticket)
    recompute_conditions(draft)
    return True


def rework_opened(draft: Draft, e: GradedTicketReworkOpened) -> bool:
    if e.ticket in draft.tickets:
        return False
    original = draft.tickets.get(e.rework_of)
    draft.add_ticket(
        "ticket_rework_opened",
        Ticket(
            ticket_id=e.ticket,
            items=list(e.items),
            restrictions=list(e.restrictions),
            source=original.source if original is not None else "fixture",
            lifecycle=TicketLifecycle.RECEIVED,
            rework_of=e.rework_of,
        ),
    )
    return True


def item_substituted(draft: Draft, e: GradedTicketItemSubstituted) -> bool:
    ticket = draft.tickets.get(e.ticket)
    if ticket is None:
        return False
    draft.set_ticket("ticket_item_substituted", ticket, items=list(e.items))
    return True
