"""12 §Contact events / 20 §Contact predicate at the assembly layer, driven through the real
`process_frame` at ~15 fps (t = i * 66 ms): dwell, hysteresis, one episode per contact,
grading from blob confidence, glove change and tool swap."""

from __future__ import annotations

import dataclasses

from src.domain import StationConfig
from src.perception.config import PerceptionConfig
from src.perception.pipeline import PerceptionPipeline

from .conftest import FRAME_MS
from .synth import mm_to_px, render_frame

PESTO_MM = (170.0, 470.0)
NOWHERE_MM = (600.0, 30.0)  # below the work zone, in no zone
WORK_MM = (500.0, 190.0)
TOOL_MM = (500.0, 40.0)
# 100 mm from the tool: inside the contact radius (50 + ~60 mm) but not drawn over the marker
NEAR_TOOL_MM = (600.0, 40.0)
BOARD_MM = (450.0, 200.0)
DISPENSER_MM = (1130.0, 470.0)
CLEAN_STOCK_MM = (150.0, 130.0)


class Driver:
    def __init__(self, pcfg: PerceptionConfig, station: StationConfig) -> None:
        self.p = PerceptionPipeline()
        self.p.configure(pcfg, station)
        self.i = 0
        self.t = 0

    def run(self, n: int, **frame_kwargs: object) -> list[dict[str, object]]:
        out: list[dict[str, object]] = []
        for _ in range(n):
            self.t = self.i * FRAME_MS
            out += self.p.process_frame(render_frame(**frame_kwargs), self.t)  # type: ignore[arg-type]
            self.i += 1
        return out


def of_type(events: list[dict[str, object]], kind: str) -> list[dict[str, object]]:
    return [e for e in events if e["type"] == kind]


def test_pass_through_under_dwell_emits_nothing(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    d = Driver(pcfg, station)
    events = d.run(3, glove_px=mm_to_px(PESTO_MM))
    assert of_type(events, "ZONE_ENTRY") == []


def test_dwell_satisfied_emits_exactly_one_entry(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    d = Driver(pcfg, station)
    events = d.run(5, glove_px=mm_to_px(PESTO_MM))
    entries = of_type(events, "ZONE_ENTRY")
    assert len(entries) == 1
    e = entries[0]
    assert (e["carrier"], e["zone"], e["depth"]) == ("gloves", "bin:pesto", 1.0)
    assert e["grade"] == "OBSERVED" and e["confidence"] == 1.0
    assert e["evidence"] == {
        "track_ids": ["gloves"],
        "zone_ids": ["bin:pesto"],
        "frame_range": (5, 5),
    }  # type: ignore[comparison-overlap]
    # staying put is the same episode: no further entries
    assert of_type(d.run(30, glove_px=mm_to_px(PESTO_MM)), "ZONE_ENTRY") == []


def test_hysteresis_absorbs_short_flicker(pcfg: PerceptionConfig, station: StationConfig) -> None:
    d = Driver(pcfg, station)
    d.run(6, glove_px=mm_to_px(PESTO_MM))
    events = d.run(4, glove_px=mm_to_px(NOWHERE_MM))  # 4 frames < 400 ms
    events += d.run(6, glove_px=mm_to_px(PESTO_MM))
    assert of_type(events, "ZONE_EXIT") == []
    assert of_type(events, "ZONE_ENTRY") == []


def test_leaving_past_hysteresis_emits_one_exit_with_dwell(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    d = Driver(pcfg, station)
    entered = of_type(d.run(20, glove_px=mm_to_px(PESTO_MM)), "ZONE_ENTRY")
    t_entry = int(entered[0]["t_occurred"])  # type: ignore[call-overload]
    t_last_inside = d.t
    events = d.run(8, glove_px=mm_to_px(NOWHERE_MM))
    exits = of_type(events, "ZONE_EXIT")
    assert len(exits) == 1
    assert (exits[0]["carrier"], exits[0]["zone"]) == ("gloves", "bin:pesto")
    elapsed = t_last_inside - t_entry
    assert abs(int(exits[0]["dwell_ms"]) - elapsed) <= 2 * FRAME_MS  # type: ignore[call-overload]
    assert of_type(d.run(10, glove_px=mm_to_px(NOWHERE_MM)), "ZONE_EXIT") == []


def test_work_zone_is_contact_not_zone_entry(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    d = Driver(pcfg, station)
    events = d.run(6, glove_px=mm_to_px(WORK_MM))
    assert of_type(events, "ZONE_ENTRY") == []
    begins = of_type(events, "CONTACT_BEGIN")
    assert len(begins) == 1
    assert (begins[0]["a"], begins[0]["b"]) == ("gloves", "work")
    cp = begins[0]["contact_point"]
    assert isinstance(cp, dict) and abs(cp["x"] - WORK_MM[0]) < 5 and abs(cp["y"] - WORK_MM[1]) < 5


def test_six_seconds_of_glove_tool_contact_is_one_episode(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    d = Driver(pcfg, station)
    tool = {10: mm_to_px(TOOL_MM)}
    glove = mm_to_px(NEAR_TOOL_MM)
    events = d.run(90, glove_px=glove, markers_px=tool)
    begins = [e for e in of_type(events, "CONTACT_BEGIN") if e["b"] == "spreader"]
    assert len(begins) == 1
    assert begins[0]["a"] == "gloves" and begins[0]["grade"] == "OBSERVED"
    assert of_type(events, "CONTACT_END") == []
    far = mm_to_px((TOOL_MM[0] + 300.0, TOOL_MM[1]))
    events = d.run(10, glove_px=far, markers_px=tool)
    ends = [e for e in of_type(events, "CONTACT_END") if e["b"] == "spreader"]
    assert len(ends) == 1 and ends[0]["a"] == "gloves"
    assert 5500 <= int(ends[0]["duration_ms"]) <= 6100  # type: ignore[call-overload]


def test_tool_on_board_contact_uses_sorted_pair(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    d = Driver(pcfg, station)
    events = d.run(
        6, markers_px={10: mm_to_px(TOOL_MM), 20: mm_to_px((TOOL_MM[0] + 60, TOOL_MM[1] + 10))}
    )
    pairs = [(e["a"], e["b"]) for e in of_type(events, "CONTACT_BEGIN")]
    assert ("board", "spreader") in pairs
    assert ("spreader", "board") not in pairs


def test_marginal_blob_is_inferred(pcfg: PerceptionConfig, station: StationConfig) -> None:
    d = Driver(pcfg, station)
    events = d.run(6, glove_px=mm_to_px(PESTO_MM), glove_radius_px=24)
    entries = of_type(events, "ZONE_ENTRY")
    assert len(entries) == 1
    assert entries[0]["grade"] == "INFERRED"
    assert 0.6 <= float(entries[0]["confidence"]) < 0.7  # type: ignore[arg-type]


def test_sub_threshold_blob_is_dropped_not_downgraded(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    strict = dataclasses.replace(
        pcfg,
        threshold_inferred={**pcfg.threshold_inferred, "ZONE_ENTRY": 0.75, "ZONE_EXIT": 0.75},
    )
    d = Driver(strict, station)
    events = d.run(6, glove_px=mm_to_px(PESTO_MM), glove_radius_px=24)
    assert [e for e in events if e["type"] in ("ZONE_ENTRY", "ZONE_EXIT", "CONTACT_BEGIN")] == []
    # the blob itself is still tracked: honesty events are never thresholded away
    assert of_type(events, "CARRIER_OBSERVABILITY_CHANGED") != []


def test_glove_change_is_inferred_don(pcfg: PerceptionConfig, station: StationConfig) -> None:
    d = Driver(pcfg, station)
    events = d.run(6, glove_px=mm_to_px(DISPENSER_MM))
    assert [(e["carrier"], e["zone"]) for e in of_type(events, "ZONE_ENTRY")] == [
        ("gloves", "glove_dispenser")
    ]
    events = d.run(38, glove_px=None)  # ~2.5 s absent
    assert of_type(events, "GLOVE_CHANGE") == []
    events = d.run(3, glove_px=mm_to_px(DISPENSER_MM))
    changes = of_type(events, "GLOVE_CHANGE")
    assert len(changes) == 1
    c = changes[0]
    assert (c["worker_slot"], c["phase"], c["grade"], c["confidence"]) == (
        0,
        "DON",
        "INFERRED",
        0.7,
    )
    assert of_type(d.run(10, glove_px=mm_to_px(DISPENSER_MM)), "GLOVE_CHANGE") == []


def test_glove_change_needs_dispenser_visit(pcfg: PerceptionConfig, station: StationConfig) -> None:
    d = Driver(pcfg, station)
    d.run(6, glove_px=mm_to_px(PESTO_MM))
    d.run(38, glove_px=None)
    events = d.run(3, glove_px=mm_to_px(PESTO_MM))
    assert of_type(events, "GLOVE_CHANGE") == []


def test_tool_swap_from_clean_stock(pcfg: PerceptionConfig, station: StationConfig) -> None:
    d = Driver(pcfg, station)
    tool = {10: mm_to_px(TOOL_MM)}
    # spreader (10) last touched the gloves
    d.run(8, glove_px=mm_to_px(NEAR_TOOL_MM), markers_px=tool)
    d.run(8, glove_px=mm_to_px(NOWHERE_MM), markers_px=tool)
    # spreader_2 (11) appears inside clean_stock ...
    events = d.run(6, markers_px={**tool, 11: mm_to_px(CLEAN_STOCK_MM)})
    assert ("spreader_2", "clean_stock") in [
        (e["carrier"], e["zone"]) for e in of_type(events, "ZONE_ENTRY")
    ]
    assert of_type(events, "TOOL_SWAP") == []
    # ... then moves to the work surface
    events = d.run(8, markers_px={**tool, 11: mm_to_px(WORK_MM)})
    swaps = of_type(events, "TOOL_SWAP")
    assert len(swaps) == 1
    s = swaps[0]
    assert (s["retired"], s["introduced"], s["from_zone"]) == (
        "spreader",
        "spreader_2",
        "clean_stock",
    )
    assert s["grade"] == "OBSERVED" and s["confidence"] == 0.95
    assert of_type(d.run(20, markers_px={**tool, 11: mm_to_px(WORK_MM)}), "TOOL_SWAP") == []


def test_tool_not_from_clean_stock_is_not_a_swap(
    pcfg: PerceptionConfig, station: StationConfig
) -> None:
    d = Driver(pcfg, station)
    events = d.run(12, markers_px={11: mm_to_px(WORK_MM)})
    assert of_type(events, "TOOL_SWAP") == []
