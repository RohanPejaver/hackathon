"""Ticket lifecycle transition table (17 §Ticket lifecycle).

::

    RECEIVED --normalize--+- RESOLVED --> (bindable: still RECEIVED)
                          +- AMBIGUOUS/UNRESOLVABLE --> BLOCKED --resolve--> RECEIVED
    (bindable) --tap--> BOUND --> IN_PREP --> COMPLETE --+--> RELEASED
                                                         +--> HELD --human--> RELEASED | VOIDED
    any non-terminal --> VOIDED (timeout t_abandon, or explicit)
    VOIDED/RELEASED --rework--> a NEW ticket (never a transition of this one)

Invariants (tested in ``tests/unit/orders/test_lifecycle.py``):

1. ``BLOCKED -> BOUND`` is unreachable: there is no path from BLOCKED to BOUND that does not
   pass through RECEIVED (i.e. through a resolution).
2. ``HELD -> RELEASED`` exists in the table, but the *event* that performs it
   (TICKET_RELEASED) is operator-only by the envelope validator in ``src.events.catalog``;
   there is no timer and no system path.
3. RELEASED and VOIDED are terminal; a rework opens a new ticket with ``rework_of`` set.

A ticket staying where it is (e.g. RECEIVED after TICKET_RESTRICTION_RESOLVED) is not a
transition, so ``can_transition(s, s)`` is False for every state.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from src.domain import TicketLifecycle as L

TERMINAL_STATES: Final[frozenset[L]] = frozenset({L.RELEASED, L.VOIDED})

TRANSITIONS: Final[Mapping[L, frozenset[L]]] = MappingProxyType(
    {
        L.RECEIVED: frozenset({L.BOUND, L.BLOCKED, L.VOIDED}),
        L.BLOCKED: frozenset({L.RECEIVED, L.VOIDED}),
        L.BOUND: frozenset({L.IN_PREP, L.VOIDED}),
        L.IN_PREP: frozenset({L.COMPLETE, L.VOIDED}),
        L.COMPLETE: frozenset({L.RELEASED, L.HELD, L.VOIDED}),
        L.HELD: frozenset({L.RELEASED, L.VOIDED}),
        L.RELEASED: frozenset(),
        L.VOIDED: frozenset(),
    }
)


def can_transition(frm: L, to: L) -> bool:
    """True iff ``frm -> to`` is a row of the 17 lifecycle table."""
    return to in TRANSITIONS[frm]


def reachable_from(frm: L, *, excluding: frozenset[L] = frozenset()) -> frozenset[L]:
    """States reachable from ``frm`` by allowed transitions that never enter ``excluding``.

    ``reachable_from(BLOCKED, excluding={RECEIVED})`` is how invariant 1 is proven.
    """
    seen: set[L] = set()
    frontier = [frm]
    while frontier:
        state = frontier.pop()
        for nxt in TRANSITIONS[state]:
            if nxt in excluding or nxt in seen:
                continue
            seen.add(nxt)
            frontier.append(nxt)
    return frozenset(seen)
