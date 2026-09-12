"""Evidence trace and required actions rendered from real assessments (25, 26)."""

from src.domain import EpistemicStatus, EvidenceGrade, TicketLifecycle
from src.policy import AlertState, evaluate
from src.risk import assess
from tests.unit.risk.builders import (
    carrier,
    cfg,
    demo_station,
    edge,
    food,
    knowledge,
    state,
    taint,
    ticket,
)

FOOD = "food:T48"


def _prep(contacts, lifecycle=TicketLifecycle.IN_PREP, **station):
    s = state(
        demo_station(t=10_000, extra=[food("T48")], **station),
        t=10_000,
        contacts=contacts,
        last_event_id="e-cause",
        last_event_type="CONTACT_BEGIN",
    )
    return s, assess(s, [ticket(lifecycle=lifecycle)], knowledge(), cfg())


def test_tier1_alert_derivation_and_copy_with_state() -> None:
    s, assessments = _prep(
        [edge("e1", 1000, "gloves", "bin:pesto"), edge("e2", 2000, "gloves", FOOD)]
    )
    [cmd] = evaluate(assessments, AlertState(cfg()), cfg(), state=s)
    alert = cmd.alert
    assert alert.tier == 1
    assert alert.headline == "STOP — gloves touched pesto"
    assert alert.body == "gloves last observed contacting pesto. Replacement not observed."
    assert [x.kind for x in alert.required_actions] == ["NEW_GLOVES"]
    assert alert.blocking_carriers == ["gloves"]
    steps = alert.derivation
    assert [st.rule_id for st in steps] == [
        "zone_acquire",
        "contact_transfer",
        "absence",
        "pathway_open",
        "alert",
    ]
    assert [st.narrative for st in steps[:4]] == [
        "gloves -> bin:pesto",
        "gloves <-> food:T48",
        "no GLOVE_CHANGE observed on gloves in window",
        "bin:pesto -> gloves -> food:T48 (1 hops, unbroken)",
    ]
    assert steps[4].narrative == 'tier=1 "STOP — gloves touched pesto"'
    assert [st.t_occurred for st in steps] == [1000, 2000, 10_000, 10_000, 10_000]
    assert [st.event_id for st in steps[:2]] == ["e1", "e2"]
    assert steps[2].grade == EvidenceGrade.PESSIMISTIC
    assert steps[0].state_delta.after == {"PINE_NUT": {"source": "bin:pesto"}}
    assert steps[1].state_delta.after == {"PINE_NUT": {"hop": 1}}
    assert steps[2].state_delta.field == "reset" and steps[2].state_delta.after is None


def test_tier2_body_uses_the_source_contact_offset() -> None:
    s, assessments = _prep(
        [
            edge("e1", 91_000, "gloves", "bin:pesto"),
            edge("e2", 92_000, "gloves", "spreader"),
            edge("e3", 93_000, "spreader", FOOD),
        ],
        lifecycle=TicketLifecycle.COMPLETE,
    )
    [cmd] = evaluate(assessments, AlertState(cfg()), cfg(), state=s)
    assert cmd.alert.tier == 2
    assert cmd.alert.headline == "HOLD — TICKET T48 — DO NOT SEND"
    assert cmd.alert.body == "PINE NUT. gloves contacted pesto at +1:31. Replacement not observed."
    assert cmd.alert.blocking_carriers == ["gloves", "spreader"]
    assert [x.kind for x in cmd.alert.required_actions] == ["HOLD", "REMAKE"]
    assert cmd.alert.required_actions[0].carrier_id == "gloves"
    assert [st.rule_id for st in cmd.alert.derivation] == [
        "zone_acquire",
        "contact_transfer",
        "contact_transfer",
        "absence",
        "absence",
        "pathway_open",
        "alert",
    ]


def test_tier0_derivation_from_taints_and_epistemic_with_state() -> None:
    s = state(
        demo_station(
            t=300_000,
            carriers={
                "gloves": carrier(
                    "gloves",
                    t_observed=300_000,
                    taints={"PINE_NUT": taint("PINE_NUT", 1000, "e1", "bin:pesto")},
                ),
                "spreader": carrier(
                    "spreader",
                    t_observed=300_000,
                    taints={"PINE_NUT": taint("PINE_NUT", 2000, "e2", "gloves", hops=1)},
                ),
                "bin:mayo": carrier("bin:mayo", t_observed=None, epistemic=EpistemicStatus.UNKNOWN),
                "board": carrier("board", t_observed=0),
            },
        ),
        t=400_000,
        last_event_id="e-bind",
        last_event_type="TICKET_BOUND",
    )
    assessments = assess(s, [ticket()], knowledge(), cfg())
    assert assessments[0].blocking_carriers == ["gloves", "spreader", "bin:mayo", "board"]
    [cmd] = evaluate(assessments, AlertState(cfg()), cfg(), state=s)
    alert = cmd.alert
    assert alert.headline == "PINE NUT — station not clean"
    assert [x.label for x in alert.required_actions] == [
        "New gloves",
        "Clean spreader",
        "Mayo container flagged — use sealed backup",
        "Fresh board",
    ]
    assert [x.kind for x in alert.required_actions] == [
        "NEW_GLOVES",
        "SWAP_TOOL",
        "USE_SEALED_BACKUP",
        "SWAP_SURFACE",
    ]
    assert [st.rule_id for st in alert.derivation] == [
        "zone_acquire",
        "absence",
        "contact_transfer",
        "absence",
        "unverified",
        "unverified",
        "precondition_unmet",
        "alert",
    ]
    narratives = [st.narrative for st in alert.derivation]
    assert narratives[0] == "gloves -> bin:pesto"
    assert narratives[2] == "gloves <-> spreader"
    assert narratives[4] == "bin:mayo UNKNOWN: never observed"
    assert narratives[5] == "board STALE: not observed for 400s"
    assert narratives[6] == "blocking: [gloves, spreader, bin:mayo, board]"
    assert narratives[7] == 'tier=0 "PINE NUT — station not clean"'
    assert alert.derivation[0].t_occurred == 1000 and alert.derivation[0].event_id == "e1"


def test_without_state_kinds_fall_back_to_id_heuristics() -> None:
    s = state(
        demo_station(
            t=10_000,
            carriers={
                "gloves": carrier(
                    "gloves", t_observed=10_000, taints={"PINE_NUT": taint("PINE_NUT", 1000)}
                ),
                "spreader": carrier(
                    "spreader", t_observed=10_000, taints={"PINE_NUT": taint("PINE_NUT", 1000)}
                ),
                "bin:mayo": carrier(
                    "bin:mayo", t_observed=10_000, taints={"PINE_NUT": taint("PINE_NUT", 1000)}
                ),
                "board": carrier(
                    "board", t_observed=10_000, taints={"PINE_NUT": taint("PINE_NUT", 1000)}
                ),
            },
        ),
        t=10_000,
    )
    assessments = assess(s, [ticket()], knowledge(), cfg())
    [with_state] = evaluate(assessments, AlertState(cfg()), cfg(), state=s)
    [without] = evaluate(assessments, AlertState(cfg()), cfg())
    assert with_state.alert.required_actions == without.alert.required_actions
    assert [st.rule_id for st in without.alert.derivation] == ["precondition_unmet", "alert"]
