"""L1: every fixture loads into `ScenarioFile`, every event expands into a valid catalog
event, every id it names resolves in the station/knowledge it declares, and every
expectation uses the assertion vocabulary. Needs only domain + events (+ runtime loader)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.events import EVENT_ADAPTER
from src.replay import VOCABULARY, ScenarioFile, build_event, sorted_events

from .conftest import CANONICAL, core_of, loaded_for, scenario_ids, scenario_paths

_CARRIER_KEYS = ("carrier", "a", "retired")


def test_all_thirteen_fixtures_and_the_demo_exist() -> None:
    stems = {p.stem for p in scenario_paths()}
    for letter in CANONICAL:
        assert any(s.startswith(f"{letter}-") for s in stems), f"missing fixture {letter}"
    assert "demo" in stems, "scenarios/demo.yaml (37) is missing"


@pytest.mark.parametrize("path", scenario_paths(), ids=scenario_ids())
def test_fixture_declares_hazard_and_schema_explicitly(path: Path) -> None:
    raw = yaml.safe_load(path.read_text())
    assert raw["schema_version"] == 1
    assert isinstance(raw.get("hazard"), bool), "34: every fixture says whether it is a hazard"
    assert raw["scenario"] == path.stem, "file name and `scenario` must agree"


def test_fixture_has_expectations(scenario: ScenarioFile) -> None:
    assert scenario.expect, "a fixture with nothing to assert proves nothing"
    assert scenario.description.strip()


def test_expectations_use_vocabulary(scenario: ScenarioFile) -> None:
    for entry in scenario.expect:
        keys = set(entry) - {"at"}
        assert len(keys) == 1, f"one assertion per entry: {entry}"
        assert keys <= VOCABULARY, f"unknown assertion {keys} in {entry}"


def test_events_read_in_time_order(scenario: ScenarioFile) -> None:
    # Fixtures are specification: they must read like the scenario they describe.
    order = [index for index, _ in sorted_events(scenario)]
    assert order == list(range(len(scenario.events)))


def test_every_event_expands_into_a_valid_catalog_event(scenario: ScenarioFile) -> None:
    _, station, _ = core_of(scenario)
    for seq, (_, raw) in enumerate(sorted_events(scenario)):
        event = build_event(raw, scenario=scenario.scenario, seq=seq, station_id=station.station_id)
        assert event.type == raw["type"]
        assert event.t_occurred == raw["t"] == event.t_committed
        assert event.seq == seq
        assert event.event_id == f"{scenario.scenario}:{seq:04d}"
        assert event.station_id == station.station_id
        assert EVENT_ADAPTER.validate_json(event.model_dump_json()) == event


def test_every_reference_resolves_in_the_declared_station_and_knowledge(
    scenario: ScenarioFile,
) -> None:
    loaded = loaded_for(scenario.config.profile, scenario.config.station, scenario.config.knowledge)
    _, station, k = core_of(scenario)
    carriers = set(station.carriers)
    stock = {c.carrier_id for c in loaded.station.clean_stock}
    zones = set(station.zones)
    items = set(k.menu_items)
    for raw in scenario.events:
        for key in _CARRIER_KEYS:
            if key in raw:
                assert raw[key] in carriers | stock, f"{raw}: {key} is not a carrier"
        if "b" in raw:
            assert raw["b"] in carriers | stock | zones, f"{raw}: b is neither carrier nor zone"
        for key in ("zone", "from_zone"):
            if key in raw:
                assert raw[key] in zones, f"{raw}: {key} is not a zone"
        if "introduced" in raw:
            assert raw["introduced"] in carriers | stock, f"{raw}: introduced is unknown"
        for item in raw.get("items", []):
            assert item in items, f"{raw}: {item} is not on the menu"
    seeded = scenario.initial_state.get("carriers", {})
    assert isinstance(seeded, dict)
    assert set(seeded) <= carriers, f"initial_state names unknown carriers {set(seeded) - carriers}"
    for entry in scenario.expect:
        for body in entry.values():
            if not isinstance(body, dict):
                continue
            for named in body.get("blocking_carriers", []) + body.get(
                "blocking_carriers_include", []
            ):
                assert named in carriers | stock, f"{entry}: {named} is not a carrier"
            for named in body.get("carriers", {}):
                assert named in carriers | stock, f"{entry}: {named} is not a carrier"
