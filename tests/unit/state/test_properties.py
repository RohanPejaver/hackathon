"""11 §Invariants, property-tested over random perception sequences (33 §Property)."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from src.domain import GRADE_RANK, CarrierKind, Config, EvidenceGrade, WorldState
from src.events import GRADEDEVENT_ADAPTER, GradedEvent
from src.state import initial, reduce
from tests.unit.state.conftest import STATION_ID, make_config, make_station

CARRIERS = ["gloves", "spreader", "board", "landing", "bin:pesto", "bin:mayo"]
ZONES = ["bin:pesto", "bin:mayo", "work", "landing", "glove_dispenser"]
GRADES = ["OBSERVED", "INFERRED"]


def _event(kind: str, n: int, t: int, grade: str, **fields: object) -> GradedEvent:
    return GRADEDEVENT_ADAPTER.validate_python(
        {
            "type": kind,
            "event_id": f"p{n}",
            "seq": n,
            "t_occurred": t,
            "t_committed": t,
            "station_id": STATION_ID,
            "source": "PERCEPTION",
            "grade": grade,
            **fields,
        }
    )


step = st.one_of(
    st.tuples(st.just("ZONE_ENTRY"), st.sampled_from(CARRIERS), st.sampled_from(ZONES)),
    st.tuples(
        st.just("CONTACT_BEGIN"), st.sampled_from(CARRIERS), st.sampled_from(CARRIERS + ZONES)
    ),
    st.tuples(st.just("GLOVE_CHANGE"), st.sampled_from(["DON", "DOFF"]), st.just("")),
)
sequences = st.lists(st.tuples(step, st.sampled_from(GRADES), st.integers(0, 50)), max_size=40)
max_hops = st.integers(0, 4)


def _build(seq: list[tuple[tuple[str, str, str], str, int]]) -> list[GradedEvent]:
    events: list[GradedEvent] = []
    t = 0
    for n, ((kind, x, y), grade, dt) in enumerate(seq):
        t += dt
        if kind == "ZONE_ENTRY":
            events.append(_event(kind, n, t, grade, carrier=x, zone=y, depth=1.0))
        elif kind == "CONTACT_BEGIN":
            events.append(_event(kind, n, t, grade, a=x, b=y, contact_point={"x": 0, "y": 0}))
        else:
            events.append(_event(kind, n, t, grade, worker_slot=0, phase=x))
    return events


def _is_reset_of(e: GradedEvent, carrier_id: str) -> bool:
    return e.type == "GLOVE_CHANGE" and e.phase == "DON" and carrier_id == "gloves"


@settings(max_examples=150, deadline=None)
@given(sequences, max_hops)
def test_taint_invariants_hold_for_any_sequence(
    seq: list[tuple[tuple[str, str, str], str, int]], hops: int
) -> None:
    cfg: Config = make_config(max_hops=hops)
    state: WorldState = initial(cfg, make_station())
    for e in _build(seq):
        new, deltas = reduce(state, e, cfg)
        for cid, carrier in new.station.carriers.items():
            if carrier.kind == CarrierKind.FOOD:
                continue
            before = set(state.station.carriers[cid].taints)
            if _is_reset_of(e, cid):
                assert carrier.taints == {}
            else:
                assert before <= set(carrier.taints), (cid, e)  # 11 inv. 2: monotone between resets
            for r in carrier.taints.values():
                assert r.hops <= cfg.max_hops  # 11 inv. 6
                assert r.source_event_id in new.event_ids or r.source_event_id.startswith("seed:")
                assert GRADE_RANK[r.grade] <= GRADE_RANK[EvidenceGrade.OBSERVED]
        assert new.t_occurred >= state.t_occurred
        assert new.deltas == [*state.deltas, *deltas]
        state = new


@settings(max_examples=60, deadline=None)
@given(sequences)
def test_fold_is_deterministic(seq: list[tuple[tuple[str, str, str], str, int]]) -> None:
    cfg = make_config()
    events = _build(seq)

    def run() -> str:
        s = initial(cfg, make_station())
        for e in events:
            s, _ = reduce(s, e, cfg)
        return s.model_dump_json()

    assert run() == run()
