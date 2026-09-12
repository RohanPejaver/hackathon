"""L1: the assertion evaluator on hand-built results. Every vocabulary item has a passing and
a failing case, and malformed/unknown assertions fail loudly instead of passing quietly."""

from __future__ import annotations

from typing import Any

from src.domain import (
    Alert,
    AlertCommand,
    AlertLifecycle,
    Carrier,
    CarrierKind,
    EpistemicStatus,
    EvidenceGrade,
    Mode,
    Pathway,
    Restriction,
    Station,
    TaintRecord,
    Ticket,
    TicketLifecycle,
    Tier,
    WorldState,
)
from src.replay import (
    ModeChange,
    Rejection,
    ReplayResult,
    StateSnapshot,
    TimedCommand,
    TimedPathway,
    evaluate_assertions,
)

# ---- builders -------------------------------------------------------------------------------


def taint(
    allergen: str, hops: int = 0, grade: EvidenceGrade = EvidenceGrade.OBSERVED
) -> TaintRecord:
    return TaintRecord(
        allergen_id=allergen,
        acquired_at=0,
        source_event_id="e0",
        source_carrier_id="bin:pesto",
        grade=grade,
        hops=hops,
    )


def state(
    carriers: dict[str, Carrier] | None = None,
    tickets: dict[str, Ticket] | None = None,
    conditions: list[str] | None = None,
    mode: Mode = Mode.REPLAY,
) -> WorldState:
    return WorldState(
        station=Station(
            station_id="st",
            config_version="1",
            knowledge_version="1",
            mode=mode,
            carriers=carriers or {},
            worker_slots=1,
        ),
        tickets=tickets or {},
        conditions=conditions or [],
    )


def carrier(
    cid: str, taints: dict[str, TaintRecord] | None = None, epistemic: str = "TRACKED"
) -> Carrier:
    return Carrier(
        carrier_id=cid,
        kind=CarrierKind.SURFACE,
        taints=taints or {},
        epistemic=EpistemicStatus(epistemic),
    )


def ticket(tid: str, lifecycle: TicketLifecycle) -> Ticket:
    return Ticket(
        ticket_id=tid,
        items=["turkey_sandwich"],
        restrictions=[
            Restriction(raw_text="pine nut allergy", allergen_ids=frozenset({"PINE_NUT"}))
        ],
        lifecycle=lifecycle,
    )


def alert(
    alert_id: str = "a1",
    tier: int = 0,
    ticket_id: str = "T1",
    blocking: list[str] | None = None,
    lifecycle: AlertLifecycle = AlertLifecycle.RAISED,
    headline: str = "Reset before starting",
    allergen: str = "PINE_NUT",
) -> Alert:
    return Alert(
        alert_id=alert_id,
        alert_key=f"st:{alert_id}",
        pathway_signature=alert_id,
        tier=Tier(tier),
        ticket_id=ticket_id,
        allergen_id=allergen,
        headline=headline,
        required_actions=[],
        derivation=[],
        raised_at=0,
        state=lifecycle,
        blocking_carriers=blocking or [],
        updated_at=0,
    )


def cmd(kind: str, a: Alert, t: int) -> TimedCommand:
    return TimedCommand(
        t=t,
        command=AlertCommand(kind=kind, alert=a, t_occurred=t, cause_event_id="e"),  # type: ignore[arg-type]
    )


def snapshot(t: int, s: WorldState, event_id: str = "e") -> StateSnapshot:
    return StateSnapshot(t=t, event_id=event_id, state=s)


def result(**fields: Any) -> ReplayResult:
    fields.setdefault("final_state", state())
    return ReplayResult(scenario="unit", **fields)


def check(entry: dict[str, Any], run: ReplayResult) -> tuple[bool, str]:
    out = evaluate_assertions([entry], run)[0]
    assert out.assertion == entry
    return out.passed, out.detail


# ---- alert commands ---------------------------------------------------------------------------


def test_alert_matches_tier_ticket_and_blocking_order_insensitively() -> None:
    run = result(commands=[cmd("RAISE", alert(tier=0, blocking=["gloves", "board"]), 1000)])
    assert check(
        {
            "at": 1000,
            "alert": {"tier": 0, "ticket": "T1", "blocking_carriers": ["board", "gloves"]},
        },
        run,
    )[0]
    assert check({"alert": {"at": 1000, "tier": 0, "allergen": "PINE_NUT"}}, run)[0]
    assert not check({"at": 1001, "alert": {"tier": 0}}, run)[0], "at is a lower bound"
    assert not check({"at": 0, "alert": {"tier": 1}}, run)[0]
    assert not check({"at": 0, "alert": {"tier": 0, "ticket": "T9"}}, run)[0]
    assert not check({"at": 0, "alert": {"tier": 0, "blocking_carriers": ["gloves"]}}, run)[0]
    assert not check({"at": 0, "alert": {"tier": 0, "allergen": "EGG"}}, run)[0]
    passed, detail = check({"at": 0, "alert": {"tier": 2}}, run)
    assert not passed and "tier=0" in detail, "failure detail lists what was seen"


def test_alert_body_at_wins_over_sibling_at() -> None:
    run = result(commands=[cmd("RAISE", alert(), 500)])
    assert check({"at": 9000, "alert": {"at": 0, "tier": 0}}, run)[0]
    assert not check({"at": 0, "alert": {"at": 9000, "tier": 0}}, run)[0]


def test_alert_headline_and_include_are_lenient_matches() -> None:
    run = result(
        commands=[
            cmd(
                "RAISE",
                alert(
                    headline="Two active restrictions — SEQUENCE them",
                    blocking=["gloves", "board", "bin:mayo"],
                ),
                0,
            )
        ]
    )
    assert check({"alert": {"tier": 0, "headline_contains": "sequence"}}, run)[0]
    assert not check({"alert": {"tier": 0, "headline_contains": "hold"}}, run)[0]
    assert check({"alert": {"tier": 0, "blocking_carriers_include": ["board"]}}, run)[0]
    assert not check({"alert": {"tier": 0, "blocking_carriers_include": ["landing"]}}, run)[0]


def test_alert_counts_escalate_but_not_update() -> None:
    run = result(commands=[cmd("UPDATE", alert(tier=1), 0), cmd("ESCALATE", alert(tier=2), 5)])
    assert not check({"alert": {"tier": 1}}, run)[0]
    assert check({"alert": {"tier": 2}}, run)[0]


def test_alert_resolved_matches_tier_and_reason() -> None:
    resolved = alert(lifecycle=AlertLifecycle.RESOLVED_BY_RESET)
    run = result(commands=[cmd("RAISE", alert(), 0), cmd("RESOLVE", resolved, 100)])
    assert check({"at": 100, "alert_resolved": {"tier": 0, "reason": "RESOLVED_BY_RESET"}}, run)[0]
    assert not check(
        {"at": 101, "alert_resolved": {"tier": 0, "reason": "RESOLVED_BY_RESET"}}, run
    )[0]
    assert not check({"alert_resolved": {"tier": 0, "reason": "RESOLVED_BY_ASSERTION"}}, run)[0]
    assert not check({"alert_resolved": {"tier": 1, "reason": "RESOLVED_BY_RESET"}}, run)[0]


def test_no_alerts_after_allows_updates_and_resolves() -> None:
    run = result(
        commands=[cmd("RAISE", alert(), 0), cmd("UPDATE", alert(), 50), cmd("RESOLVE", alert(), 60)]
    )
    assert check({"no_alerts_after": 0}, run)[0]
    assert not check({"no_alerts_after": -1}, run)[0]
    late = result(commands=[cmd("ESCALATE", alert(tier=2), 70)])
    assert not check({"no_alerts_after": 60}, late)[0]


def test_no_alerts_of_tier_windows() -> None:
    run = result(
        commands=[cmd("RAISE", alert(tier=0), 1000), cmd("RAISE", alert("b", tier=1), 5000)]
    )
    assert check({"no_alerts_of_tier": {"tier": 2}}, run)[0]
    assert not check({"no_alerts_of_tier": {"tier": 0}}, run)[0]
    assert check({"no_alerts_of_tier": {"tier": 0, "after": 1000}}, run)[0]
    assert check({"no_alerts_of_tier": {"tier": 1, "before": 5000}}, run)[0]
    assert not check({"no_alerts_of_tier": {"tier": 1, "before": 5001}}, run)[0]
    assert check({"no_alerts_of_tier": {"tier": 0, "after": 500, "before": 1000}}, run)[0]
    assert not check({"no_alerts_of_tier": {"tier": 0, "after": 500, "before": 1500}}, run)[0]


def test_silence() -> None:
    assert check({"silence": True}, result())[0]
    assert check({"silence": True}, result(commands=[cmd("UPDATE", alert(), 0)]))[0]
    assert not check({"silence": True}, result(commands=[cmd("RAISE", alert(), 0)]))[0]
    assert not check({"silence": False}, result())[0], "only `true` is meaningful"


def test_raise_count_counts_raise_and_escalate_of_the_tier() -> None:
    run = result(
        commands=[
            cmd("RAISE", alert(tier=1), 0),
            cmd("UPDATE", alert(tier=1), 1),
            cmd("UPDATE", alert(tier=1), 2),
            cmd("ESCALATE", alert(tier=2), 3),
        ]
    )
    assert check({"raise_count": {"tier": 1, "equals": 1}}, run)[0]
    assert check({"raise_count": {"tier": 2, "equals": 1}}, run)[0]
    assert not check({"raise_count": {"tier": 1, "equals": 3}}, run)[0]
    assert check({"raise_count": {"tier": 0, "equals": 0}}, run)[0]


def test_alert_open_tracks_the_last_command_per_alert() -> None:
    run = result(
        commands=[
            cmd("RAISE", alert("a", tier=1), 0),
            cmd("ESCALATE", alert("a", tier=2), 10),
            cmd("RAISE", alert("b", tier=0), 20),
            cmd("RESOLVE", alert("b", tier=0, lifecycle=AlertLifecycle.RESOLVED_BY_RESET), 30),
        ]
    )
    assert check({"at": 5, "alert_open": {"tier": 1}}, run)[0]
    assert not check({"at": 10, "alert_open": {"tier": 1}}, run)[0], "escalated away"
    assert check({"at": 10, "alert_open": {"tier": 2}}, run)[0]
    assert check({"at": 25, "alert_open": {"tier": 0}}, run)[0]
    assert not check({"at": 30, "alert_open": {"tier": 0}}, run)[0], "resolved"
    assert check({"at": 999, "alert_open": {"tier": 2}}, run)[0], "Tier 2 never auto-resolves"
    assert not check({"alert_open": {"tier": 2}}, run)[0], "needs `at`"


# ---- state ---------------------------------------------------------------------------------


def _world() -> WorldState:
    return state(
        carriers={
            "board": carrier(
                "board", {"PINE_NUT": taint("PINE_NUT", hops=1), "MILK": taint("MILK", 1)}
            ),
            "gloves": carrier("gloves", epistemic="UNKNOWN"),
        },
        tickets={"T1": ticket("T1", TicketLifecycle.HELD)},
        conditions=["MULTI_RESTRICTION"],
    )


def test_final_state_partial_match() -> None:
    run = result(final_state=_world())
    assert check(
        {
            "final_state": {
                "carriers": {"board": {"taints": {"PINE_NUT": {"hops": 1, "grade": "OBSERVED"}}}}
            }
        },
        run,
    )[0]
    assert check({"final_state": {"carriers": {"board": {"taints": {"PINE_NUT": {}}}}}}, run)[0], (
        "subset of taints"
    )
    assert check(
        {"final_state": {"carriers": {"gloves": {"taints": {}, "epistemic": "UNKNOWN"}}}}, run
    )[0]
    assert not check({"final_state": {"carriers": {"board": {"taints": {}}}}}, run)[0], (
        "{} means no taint"
    )
    assert not check({"final_state": {"carriers": {"board": {"taints": {"EGG": {}}}}}}, run)[0]
    assert not check(
        {"final_state": {"carriers": {"board": {"taints": {"PINE_NUT": {"hops": 0}}}}}}, run
    )[0]
    assert not check({"final_state": {"carriers": {"gloves": {"epistemic": "TRACKED"}}}}, run)[0]
    assert not check({"final_state": {"carriers": {"spatula": {"taints": {}}}}}, run)[0], (
        "absent carrier"
    )
    assert check(
        {
            "final_state": {
                "conditions": ["MULTI_RESTRICTION"],
                "tickets": {"T1": {"lifecycle": "HELD"}},
            }
        },
        run,
    )[0]
    assert not check({"final_state": {"conditions": ["OTHER"]}}, run)[0]
    assert not check({"final_state": {"tickets": {"T1": {"lifecycle": "BOUND"}}}}, run)[0]
    assert not check({"final_state": {"tickets": {"T2": {"lifecycle": "BOUND"}}}}, run)[0]
    assert not check({"final_state": {"carrier": {}}}, run)[0], "unknown state key fails"


def test_state_at_picks_the_last_snapshot_at_or_before() -> None:
    early = state(carriers={"board": carrier("board")})
    late = state(carriers={"board": carrier("board", {"PINE_NUT": taint("PINE_NUT")})})
    run = result(
        states=[snapshot(0, early, "seed"), snapshot(2000, late, "e1"), snapshot(2000, early, "e2")]
    )
    assert check({"at": 1999, "state_at": {"carriers": {"board": {"taints": {}}}}}, run)[0]
    assert check({"at": 2000, "state_at": {"carriers": {"board": {"taints": {}}}}}, run)[0], (
        "same-t: last wins"
    )
    single = result(states=[snapshot(0, early), snapshot(2000, late)])
    assert check(
        {"at": 2000, "state_at": {"carriers": {"board": {"taints": {"PINE_NUT": {}}}}}}, single
    )[0]
    assert not check(
        {"at": 1999, "state_at": {"carriers": {"board": {"taints": {"PINE_NUT": {}}}}}}, single
    )[0]
    assert not check({"at": -1, "state_at": {"carriers": {}}}, single)[0], "nothing at or before"
    assert not check({"state_at": {"carriers": {}}}, single)[0], "needs `at`"


def test_mode_at_timestamp() -> None:
    run = result(
        mode_timeline=[
            ModeChange(t=0, mode=Mode.REPLAY),
            ModeChange(t=4000, mode=Mode.PROTOCOL_ONLY),
        ]
    )
    assert check({"at": 3999, "mode": {"mode": "REPLAY"}}, run)[0]
    assert check({"at": 4000, "mode": {"mode": "PROTOCOL_ONLY"}}, run)[0]
    assert not check({"at": 4000, "mode": {"mode": "REPLAY"}}, run)[0]
    assert not check({"at": 4000, "mode": {"mode": "FULL"}}, result())[0]


def test_held_at_or_after() -> None:
    bound = state(tickets={"T1": ticket("T1", TicketLifecycle.COMPLETE)})
    held = state(tickets={"T1": ticket("T1", TicketLifecycle.HELD)})
    run = result(states=[snapshot(0, bound), snapshot(9000, held)], final_state=held)
    assert check({"at": 9000, "held": {"ticket": "T1"}}, run)[0]
    assert check({"held": {"ticket": "T1", "at": 100}}, run)[0]
    assert not check({"at": 9001, "held": {"ticket": "T1"}}, run)[0]
    assert not check({"at": 0, "held": {"ticket": "T2"}}, run)[0]


# ---- pathways, rejections ----------------------------------------------------------------------


def _pathway(nodes: list[str]) -> Pathway:
    return Pathway(
        allergen_id="PINE_NUT",
        nodes=nodes,
        event_ids=[],
        grade=EvidenceGrade.OBSERVED,
        hops=len(nodes) - 1,
    )


def test_pathway_exact_includes_and_target() -> None:
    run = result(
        pathways=[
            TimedPathway(
                t=4000,
                ticket_id="T2",
                pathway=_pathway(["bin:pesto", "gloves", "board", "food:T2"]),
            )
        ]
    )
    assert check({"pathway": {"nodes": ["bin:pesto", "gloves", "board", "food:T2"]}}, run)[0]
    assert not check({"pathway": {"nodes": ["gloves", "board", "food:T2"]}}, run)[0]
    assert check(
        {"at": 4000, "pathway": {"includes": ["gloves", "board"], "target": "food:T2"}}, run
    )[0]
    assert not check({"pathway": {"includes": ["board", "gloves"]}}, run)[0], "order matters"
    assert not check({"pathway": {"target": "food:T9"}}, run)[0]
    assert not check({"at": 4001, "pathway": {"target": "food:T2"}}, run)[0]
    assert not check({"pathway": {"target": "food:T2"}}, result())[0]


def test_event_rejected_by_index_or_suffix() -> None:
    run = result(rejected=[Rejection(index=3, event_id="s:0003", reason="unknown type")])
    assert check({"event_rejected": {"index": 3}}, run)[0]
    assert check({"event_rejected": {"event_id_suffix": ":0003"}}, run)[0]
    assert not check({"event_rejected": {"index": 2}}, run)[0]
    assert not check({"event_rejected": {"index": 3, "event_id_suffix": ":0009"}}, run)[0]
    assert not check({"event_rejected": {}}, run)[0], "needs a selector"


# ---- robustness ------------------------------------------------------------------------------


def test_unknown_or_malformed_assertions_fail_instead_of_passing() -> None:
    run = result(commands=[cmd("RAISE", alert(), 0)])
    assert not check({"alerts": {"tier": 0}}, run)[0]
    assert not check({"alert": {"tier": 0}, "silence": True}, run)[0], "one assertion per entry"
    assert not check({"at": 0}, run)[0]
    passed, detail = check({"alert": {"tier": "zero"}}, run)
    assert not passed and "malformed" in detail
    assert not check({"alert": [0]}, run)[0]
    assert not check({"no_alerts_of_tier": {}}, run)[0]
    assert not check({"raise_count": {"tier": 1}}, run)[0]


def test_every_result_is_recorded_in_order() -> None:
    run = result(commands=[cmd("RAISE", alert(), 0)])
    out = evaluate_assertions([{"silence": True}, {"alert": {"tier": 0}}], run)
    assert [r.passed for r in out] == [False, True]
    assert out[0].assertion == {"silence": True}
