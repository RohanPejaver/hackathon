"""17 §Ticket lifecycle: the exhaustive table, and BLOCKED -> BOUND provably unreachable."""

from __future__ import annotations

from itertools import pairwise, product

import pytest

from src.domain import TicketLifecycle as L
from src.orders import TERMINAL_STATES, TRANSITIONS, can_transition, reachable_from

EXPECTED: dict[L, frozenset[L]] = {
    L.RECEIVED: frozenset({L.BOUND, L.BLOCKED, L.VOIDED}),
    L.BLOCKED: frozenset({L.RECEIVED, L.VOIDED}),
    L.BOUND: frozenset({L.IN_PREP, L.VOIDED}),
    L.IN_PREP: frozenset({L.COMPLETE, L.VOIDED}),
    L.COMPLETE: frozenset({L.RELEASED, L.HELD, L.VOIDED}),
    L.HELD: frozenset({L.RELEASED, L.VOIDED}),
    L.RELEASED: frozenset(),
    L.VOIDED: frozenset(),
}


@pytest.mark.parametrize(("frm", "to"), list(product(L, L)))
def test_exhaustive_table(frm: L, to: L) -> None:
    assert can_transition(frm, to) is (to in EXPECTED[frm])


def test_table_covers_every_state_exactly() -> None:
    assert set(TRANSITIONS) == set(L)
    assert dict(TRANSITIONS) == EXPECTED


def test_blocked_to_bound_is_false() -> None:
    assert can_transition(L.BLOCKED, L.BOUND) is False


def test_blocked_cannot_reach_bound_without_passing_through_received() -> None:
    """Graph search over allowed edges with RECEIVED removed: BOUND is unreachable."""
    assert L.BOUND not in reachable_from(L.BLOCKED, excluding=frozenset({L.RECEIVED}))
    assert reachable_from(L.BLOCKED, excluding=frozenset({L.RECEIVED})) == frozenset({L.VOIDED})
    # sanity: through a resolution (BLOCKED -> RECEIVED) binding becomes reachable again
    assert L.BOUND in reachable_from(L.BLOCKED)


def test_brute_force_paths_from_blocked_all_pass_through_received() -> None:
    """Independent of ``reachable_from``: enumerate every simple path BLOCKED -> BOUND."""
    paths: list[list[L]] = []

    def walk(state: L, path: list[L]) -> None:
        if state is L.BOUND:
            paths.append(path)
            return
        for nxt in TRANSITIONS[state]:
            if nxt not in path:
                walk(nxt, [*path, nxt])

    walk(L.BLOCKED, [L.BLOCKED])
    assert paths, "BOUND must be reachable after resolution"
    assert all(L.RECEIVED in p for p in paths)
    assert all(p[1] is L.RECEIVED for p in paths)


def test_terminal_states_have_no_exits() -> None:
    assert TERMINAL_STATES == frozenset({L.RELEASED, L.VOIDED})
    for state in TERMINAL_STATES:
        assert TRANSITIONS[state] == frozenset()
        assert not any(can_transition(state, to) for to in L)


def test_every_non_terminal_can_be_voided() -> None:
    for state in L:
        assert can_transition(state, L.VOIDED) is (state not in TERMINAL_STATES)


def test_held_exits_only_to_released_or_voided() -> None:
    assert TRANSITIONS[L.HELD] == frozenset({L.RELEASED, L.VOIDED})


def test_no_self_transitions() -> None:
    assert not any(can_transition(state, state) for state in L)


def test_happy_path_is_allowed() -> None:
    path = [L.RECEIVED, L.BOUND, L.IN_PREP, L.COMPLETE, L.RELEASED]
    assert all(can_transition(a, b) for a, b in pairwise(path))
    hold = [L.RECEIVED, L.BOUND, L.IN_PREP, L.COMPLETE, L.HELD, L.RELEASED]
    assert all(can_transition(a, b) for a, b in pairwise(hold))
    resolve = [L.RECEIVED, L.BLOCKED, L.RECEIVED, L.BOUND]
    assert all(can_transition(a, b) for a, b in pairwise(resolve))
