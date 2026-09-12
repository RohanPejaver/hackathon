"""System rows of the 13 table, non-mutating events, `initial`, determinism and delta shape."""

from __future__ import annotations

import json

from src.domain import (
    Config,
    EpistemicStatus,
    EvidenceGrade,
    Mode,
    StationConfig,
    WorldState,
)
from src.state import initial, reduce
from tests.unit.state.conftest import (
    contact,
    ev,
    fold,
    fold_deltas,
    glove_don,
    make_station,
    ticket_bound,
    ticket_received,
    zone_entry,
)

# -- initial ------------------------------------------------------------------------------


def test_initial_mirrors_station_config(cfg: Config, station: StationConfig) -> None:
    s = initial(cfg, station)
    assert s.station.station_id == station.station_id
    assert s.station.mode == Mode.FULL
    assert s.station.config_version == "cfg-1" and s.station.knowledge_version == "k-1"
    assert s.station.carriers == station.carriers
    assert all(c.epistemic == EpistemicStatus.UNKNOWN for c in s.station.carriers.values())
    assert s.station.zones == station.zones
    assert s.station.bound_tickets == [] and s.station.worker_slots == 1
    assert s.station.recent_allergen_exposure == {}
    assert s.zone_allergens == station.zone_allergens
    assert s.tickets == {} and s.contacts == [] and s.resets == [] and s.acquisitions == {}
    assert s.event_ids == [] and s.deltas == [] and s.conditions == []
    assert s.t_occurred == 0 and s.last_event_source == "SYSTEM"


# -- non-mutating events return the identical state ---------------------------------------


def test_non_mutating_events_are_identity(state: WorldState, cfg: Config) -> None:
    events = [
        ev("CONTACT_END", 50, a="gloves", b="spreader", duration_ms=10),
        ev("ZONE_EXIT", 50, carrier="gloves", zone="bin:pesto", dwell_ms=10),
        ev("SURFACE_WIPE", 50, carrier="board"),
        ev("HEALTH_DEGRADED", 50, cause="frame starvation", rejected_event_id=None),
    ]
    for kind in (
        "ALERT_RAISED",
        "ALERT_UPDATED",
        "ALERT_ACKNOWLEDGED",
        "ALERT_RESOLVED",
        "ALERT_ESCALATED",
        "ALERT_EXPIRED",
        "ALERT_SUPPRESSED",
    ):
        events.append(ev(kind, 50, alert_id="a1", pathway_signature="sig"))
    for e in events:
        assert e.mutates_state is False
        new, deltas = reduce(state, e, cfg)
        assert new is state, e.type
        assert deltas == []
    assert state.t_occurred == 0 and state.event_ids == []


# -- CARRIER_OBSERVABILITY_CHANGED --------------------------------------------------------


def test_observability_change_sets_epistemic_only(state: WorldState, cfg: Config) -> None:
    s = fold(state, [zone_entry(100, "gloves", "bin:pesto")], cfg)
    e = ev("CARRIER_OBSERVABILITY_CHANGED", 200, carrier="gloves", epistemic="STALE", cause="x")
    new, deltas = reduce(s, e, cfg)
    g = new.station.carriers["gloves"]
    assert g.epistemic == EpistemicStatus.STALE
    assert g.last_observed_at == 100
    assert "PINE_NUT" in g.taints  # not contaminated-vs-unverifiable: taint axis untouched
    assert [(d.rule_id, d.field, d.before, d.after) for d in deltas] == [
        ("observability", "epistemic", "TRACKED", "STALE")
    ]
    new = fold(
        new,
        [
            ev(
                "CARRIER_OBSERVABILITY_CHANGED",
                300,
                carrier="gloves",
                epistemic="TRACKED",
                cause="y",
            )
        ],
        cfg,
    )
    assert new.station.carriers["gloves"].last_observed_at == 300
    rejected, deltas = reduce(
        s,
        ev("CARRIER_OBSERVABILITY_CHANGED", 300, carrier="ghost", epistemic="UNKNOWN", cause="y"),
        cfg,
    )
    assert rejected is s and deltas == []


# -- TRACK_IDENTITY_SUSPECT ---------------------------------------------------------------


def test_identity_suspect_merges_and_marks_both_stale(state: WorldState, cfg: Config) -> None:
    s = fold(
        state,
        [
            zone_entry(100, "gloves", "bin:pesto"),
            zone_entry(150, "spreader", "bin:mayo"),
            contact(200, "gloves", "board"),  # board: PINE_NUT hop 1, MILK hop 1
            contact(250, "board", "spreader"),  # spreader: PINE_NUT hop 2; board: EGG hop 1
        ],
        cfg,
    )
    e = ev("TRACK_IDENTITY_SUSPECT", 300, a="gloves", b="spreader", cause="tracks crossed")
    new, deltas = reduce(s, e, cfg)
    g, sp = new.station.carriers["gloves"], new.station.carriers["spreader"]
    assert g.epistemic == EpistemicStatus.STALE and sp.epistemic == EpistemicStatus.STALE
    assert set(g.taints) == set(sp.taints) == {"EGG", "MILK", "PINE_NUT"}
    assert sp.taints["PINE_NUT"].hops == 0  # a's fewer-hop record won
    assert sp.taints["PINE_NUT"].source_event_id == e.event_id
    assert sp.taints["PINE_NUT"].source_carrier_id == "gloves"
    assert g.taints["EGG"].hops == 0 and g.taints["EGG"].source_carrier_id == "spreader"
    assert sp.taints["EGG"].acquired_at == 150  # its own record untouched
    assert {d.rule_id for d in deltas} == {"identity_merge"}
    assert new.acquisitions["spreader"][-1] == sp.taints["PINE_NUT"]


def test_identity_suspect_tie_keeps_both_own_records(state: WorldState, cfg: Config) -> None:
    s = fold(
        state,
        [zone_entry(100, "gloves", "bin:pesto"), zone_entry(200, "spreader", "bin:pesto")],
        cfg,
    )
    new = fold(s, [ev("TRACK_IDENTITY_SUSPECT", 300, a="gloves", b="spreader", cause="c")], cfg)
    assert new.station.carriers["gloves"].taints["PINE_NUT"].acquired_at == 100
    assert new.station.carriers["spreader"].taints["PINE_NUT"].acquired_at == 200


def test_identity_suspect_with_one_unknown_marks_known_stale(
    state: WorldState, cfg: Config
) -> None:
    new = fold(state, [ev("TRACK_IDENTITY_SUSPECT", 300, a="gloves", b="ghost", cause="c")], cfg)
    assert new.station.carriers["gloves"].epistemic == EpistemicStatus.STALE
    rejected, deltas = reduce(
        state, ev("TRACK_IDENTITY_SUSPECT", 300, a="x", b="y", cause="c"), cfg
    )
    assert rejected is state and deltas == []


# -- STATION_MODE_CHANGED (ADR-0011) ------------------------------------------------------


def test_protocol_only_sets_all_unknown_and_full_restores_nothing(
    state: WorldState, cfg: Config
) -> None:
    s = fold(
        state, [zone_entry(100, "gloves", "bin:pesto"), contact(200, "gloves", "spreader")], cfg
    )
    assert s.station.carriers["gloves"].epistemic == EpistemicStatus.TRACKED
    e = ev("STATION_MODE_CHANGED", 300, mode="PROTOCOL_ONLY", cause="camera fault")
    new, deltas = reduce(s, e, cfg)
    assert new.station.mode == Mode.PROTOCOL_ONLY
    assert all(c.epistemic == EpistemicStatus.UNKNOWN for c in new.station.carriers.values())
    assert "PINE_NUT" in new.station.carriers["gloves"].taints  # taint axis untouched
    assert {d.rule_id for d in deltas} == {"mode_change"}
    back = fold(new, [ev("STATION_MODE_CHANGED", 400, mode="FULL", cause="recovered")], cfg)
    assert back.station.mode == Mode.FULL
    assert all(c.epistemic == EpistemicStatus.UNKNOWN for c in back.station.carriers.values())
    seen = fold(back, [zone_entry(500, "gloves", "work")], cfg)  # only re-observation restores
    assert seen.station.carriers["gloves"].epistemic == EpistemicStatus.TRACKED
    assert seen.station.carriers["spreader"].epistemic == EpistemicStatus.UNKNOWN


def test_other_modes_touch_no_carrier(state: WorldState, cfg: Config) -> None:
    s = fold(state, [zone_entry(100, "gloves", "bin:pesto")], cfg)
    for mode in ("REPLAY", "CALIBRATION"):
        new = fold(s, [ev("STATION_MODE_CHANGED", 200, mode=mode, cause="c")], cfg)
        assert new.station.mode == mode
        assert new.station.carriers["gloves"].epistemic == EpistemicStatus.TRACKED


# -- CONFIG_LOADED ------------------------------------------------------------------------


def test_config_loaded_stamps_versions(state: WorldState, cfg: Config) -> None:
    e = ev("CONFIG_LOADED", 5, config_version="cfg-2", knowledge_version="k-9")
    new, deltas = reduce(state, e, cfg)
    assert new.station.config_version == "cfg-2"
    assert new.station.knowledge_version == "k-9"
    assert [(d.field, d.before, d.after) for d in deltas] == [
        ("config_version", "cfg-1", "cfg-2"),
        ("knowledge_version", "k-1", "k-9"),
    ]


# -- envelope, deltas, determinism --------------------------------------------------------


def test_t_occurred_never_moves_backwards(state: WorldState, cfg: Config) -> None:
    s = fold(
        state,
        [zone_entry(500, "gloves", "bin:pesto"), zone_entry(200, "gloves", "work", late=True)],
        cfg,
    )
    assert s.t_occurred == 500
    assert s.last_event_type == "ZONE_ENTRY"
    assert len(s.event_ids) == 2


def test_every_delta_is_json_serialisable_and_traceable(state: WorldState, cfg: Config) -> None:
    events = [
        ev("CONFIG_LOADED", 1, config_version="cfg-1", knowledge_version="k-1"),
        ticket_received(10, "T1", "PINE_NUT"),
        ticket_bound(20, "T1"),
        ev("TICKET_PREP_STARTED", 30, ticket="T1"),
        zone_entry(100, "gloves", "bin:pesto"),
        contact(200, "gloves", "spreader"),
        contact(300, "spreader", "landing"),
        ev("TRACK_IDENTITY_SUSPECT", 350, a="gloves", b="board", cause="c"),
        glove_don(400),
        ev("TOOL_SWAP", 500, retired="spreader", introduced="spreader_2", from_zone="clean_stock"),
        ev("WASH_CYCLE", 600, carrier="board", zone="wash", duration_ms=1),
        ev("OPERATOR_ASSERTION", 700, carrier="landing", claim="CLEAN", worker_slot=0),
        ev("STATION_MODE_CHANGED", 800, mode="PROTOCOL_ONLY", cause="c"),
        ev("TICKET_ITEM_COMPLETE", 900, ticket="T1"),
        ev("TICKET_RELEASED", 1000, ticket="T1", worker_slot=0),
    ]
    final, deltas = fold_deltas(state, events, cfg)
    assert deltas and final.deltas == deltas
    ids = {e.event_id for e in events}
    for d in deltas:
        json.dumps(d.model_dump(mode="json"))
        assert d.event_id in ids and d.rule_id and d.field
    assert final.event_ids == [e.event_id for e in events]
    for carrier_id, records in final.acquisitions.items():
        for r in records:
            assert r.source_event_id in final.event_ids, (carrier_id, r)


def test_reducing_the_same_sequence_twice_is_byte_identical(cfg: Config) -> None:
    def run() -> str:
        st = make_station()
        s = initial(cfg, st)
        events = [
            ticket_received(10, "T1", "PINE_NUT"),
            ticket_bound(20, "T1"),
            ev("TICKET_PREP_STARTED", 30, ticket="T1", event_id="fixed-3"),
            zone_entry(100, "gloves", "bin:pesto", event_id="fixed-4"),
            zone_entry(150, "gloves", "bin:mayo", event_id="fixed-5"),
            contact(200, "gloves", "landing", event_id="fixed-6"),
            glove_don(300, event_id="fixed-7"),
            zone_entry(400, "gloves", "bin:mayo", event_id="fixed-8"),
        ]
        events[0] = ticket_received(10, "T1", "PINE_NUT", event_id="fixed-1")
        events[1] = ticket_bound(20, "T1", event_id="fixed-2")
        return fold(s, events, cfg).model_dump_json()

    assert run() == run()


def test_reducer_never_mutates_its_input(state: WorldState, cfg: Config) -> None:
    before = state.model_dump_json()
    fold(
        state,
        [
            zone_entry(100, "gloves", "bin:pesto"),
            contact(200, "gloves", "spreader"),
            glove_don(300),
        ],
        cfg,
    )
    assert state.model_dump_json() == before


def test_grade_lattice_helpers() -> None:
    from src.state.taint import min_grade

    assert min_grade(EvidenceGrade.OBSERVED, EvidenceGrade.ASSERTED) == EvidenceGrade.ASSERTED
    assert min_grade(EvidenceGrade.PESSIMISTIC, EvidenceGrade.OBSERVED) == EvidenceGrade.PESSIMISTIC
    assert min_grade(EvidenceGrade.INFERRED, EvidenceGrade.INFERRED) == EvidenceGrade.INFERRED
