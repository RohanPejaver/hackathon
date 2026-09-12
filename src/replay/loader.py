"""Scenario loading and expansion (36 §Format).

A fixture event is `{t, type, ...fields}`; expansion fills the envelope and the payload
defaults a fixture may omit, then validates against the event catalog. Everything here is
pure: the same file yields the same events, in the same order, with the same ids.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import JsonValue

from src.domain import (
    CarrierKind,
    Config,
    EpistemicStatus,
    EvidenceGrade,
    Strength,
    TaintRecord,
    WorldState,
)
from src.events import EVENT_ADAPTER, Event

from .schema import ScenarioFile

_SOURCE_BY_TYPE: dict[str, str] = {
    "CONTACT_BEGIN": "PERCEPTION",
    "CONTACT_END": "PERCEPTION",
    "ZONE_ENTRY": "PERCEPTION",
    "ZONE_EXIT": "PERCEPTION",
    "GLOVE_CHANGE": "PERCEPTION",
    "TOOL_SWAP": "PERCEPTION",
    "SURFACE_SWAP": "PERCEPTION",
    "WASH_CYCLE": "PERCEPTION",
    "SURFACE_WIPE": "PERCEPTION",
    "CARRIER_OBSERVABILITY_CHANGED": "PERCEPTION",
    "TRACK_IDENTITY_SUSPECT": "PERCEPTION",
    "HEALTH_DEGRADED": "PERCEPTION",
    "TICKET_RECEIVED": "ORDER_SYSTEM",
    "TICKET_RESTRICTION_RESOLVED": "ORDER_SYSTEM",
    "TICKET_BLOCKED": "ORDER_SYSTEM",
    "TICKET_BOUND": "OPERATOR",
    "TICKET_PREP_STARTED": "OPERATOR",
    "TICKET_ITEM_COMPLETE": "OPERATOR",
    "TICKET_HELD": "OPERATOR",
    "TICKET_RELEASED": "OPERATOR",
    "TICKET_VOIDED": "OPERATOR",
    "TICKET_REWORK_OPENED": "OPERATOR",
    "TICKET_ITEM_SUBSTITUTED": "OPERATOR",
    "OPERATOR_ASSERTION": "OPERATOR",
    "STATION_MODE_CHANGED": "SYSTEM",
    "CONFIG_LOADED": "SYSTEM",
}

_ASSERTED_TYPES = frozenset({"WASH_CYCLE", "OPERATOR_ASSERTION"})

_PAYLOAD_DEFAULTS: dict[str, dict[str, JsonValue]] = {
    "CONTACT_BEGIN": {"contact_point": {"x": 0, "y": 0}},
    "CONTACT_END": {"duration_ms": 0},
    "ZONE_ENTRY": {"depth": 1.0},
    "ZONE_EXIT": {"dwell_ms": 0},
    "WASH_CYCLE": {"zone": "wash", "duration_ms": 0},
    "GLOVE_CHANGE": {"worker_slot": 0},
    "OPERATOR_ASSERTION": {"worker_slot": 0},
    "TICKET_RECEIVED": {"order_source": "fixture", "restrictions": []},
    "TICKET_BOUND": {"worker_slot": 0},
    "TICKET_RELEASED": {"worker_slot": 0},
}


def load_scenario(path: Path | str) -> ScenarioFile:
    data = yaml.safe_load(Path(path).read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return ScenarioFile.model_validate(data)


def sorted_events(scenario: ScenarioFile) -> list[tuple[int, dict[str, JsonValue]]]:
    """(file index, raw event) sorted by (t, file order); seq is assigned at commit time."""
    indexed = list(enumerate(scenario.events))
    return sorted(indexed, key=lambda pair: (_time_of(pair[1]), pair[0]))


def event_id_for(scenario: str, seq: int) -> str:
    return f"{scenario}:{seq:04d}"


def build_event(raw: Mapping[str, JsonValue], *, scenario: str, seq: int, station_id: str) -> Event:
    """Expand one fixture event into a committed catalog event; raises on a malformed one."""
    payload = dict(raw)
    t = payload.pop("t")
    type_name = str(payload.get("type", ""))
    data: dict[str, JsonValue] = {
        "event_id": event_id_for(scenario, seq),
        "seq": seq,
        "t_occurred": t,
        "t_committed": t,
        "station_id": station_id,
        "source": _SOURCE_BY_TYPE.get(type_name, "SYSTEM"),
        "grade": "ASSERTED" if type_name in _ASSERTED_TYPES else "OBSERVED",
    }
    data.update(_PAYLOAD_DEFAULTS.get(type_name, {}))
    data.update(payload)
    return EVENT_ADAPTER.validate_python(data)


# ---- initial_state seeding (36 §Format; Q8 ruling: synthetic seed provenance) --------------


def seed_state(state: WorldState, initial_state: Mapping[str, JsonValue]) -> WorldState:
    """Apply `initial_state.carriers` onto a freshly initialised WorldState.

    Seeded taints carry synthetic provenance (`seed:<carrier>:<allergen>`, acquired at 0) so
    every taint still names a source (11), and count as station exposure at t=0 so the
    pessimistic closure sees them. A seeded epistemic status is stamped observed-at-0 so
    `effective_epistemic` can age it exactly like a real observation.
    """
    unknown = sorted(set(initial_state) - {"carriers"})
    if unknown:
        raise ValueError(f"initial_state: unknown keys {unknown}")
    specs = _mapping(initial_state.get("carriers", {}), "initial_state.carriers")
    station = state.station
    carriers = dict(station.carriers)
    exposure = dict(station.recent_allergen_exposure)
    acquisitions = {k: list(v) for k, v in state.acquisitions.items()}
    for carrier_id in sorted(specs):
        if carrier_id not in carriers:
            raise ValueError(f"initial_state.carriers.{carrier_id}: not a station carrier")
        spec = _mapping(specs[carrier_id], f"initial_state.carriers.{carrier_id}")
        extra = sorted(set(spec) - {"taints", "epistemic"})
        if extra:
            raise ValueError(f"initial_state.carriers.{carrier_id}: unknown keys {extra}")
        carrier = carriers[carrier_id]
        taints = dict(carrier.taints)
        taint_specs = _mapping(
            spec.get("taints", {}), f"initial_state.carriers.{carrier_id}.taints"
        )
        for allergen in sorted(taint_specs):
            tspec = _mapping(taint_specs[allergen], f"...{carrier_id}.taints.{allergen}")
            record = TaintRecord(
                allergen_id=allergen,
                acquired_at=0,
                source_event_id=f"seed:{carrier_id}:{allergen}",
                source_carrier_id="seed",
                grade=EvidenceGrade(str(tspec.get("grade", "OBSERVED"))),
                hops=_int(tspec.get("hops", 0), "hops"),
                strength=Strength(str(tspec.get("strength", "PRESENT"))),
            )
            taints[allergen] = record
            acquisitions.setdefault(carrier_id, []).append(record)
            exposure[allergen] = 0
        update: dict[str, object] = {"taints": taints}
        if "epistemic" in spec:
            update["epistemic"] = EpistemicStatus(str(spec["epistemic"]))
            update["last_observed_at"] = 0
        carriers[carrier_id] = carrier.model_copy(update=update)
    return state.model_copy(
        update={
            "station": station.model_copy(
                update={"carriers": carriers, "recent_allergen_exposure": exposure}
            ),
            "acquisitions": acquisitions,
        }
    )


# ---- config overrides (36 `config.overrides`, dotted keys in the 31 layout) ----------------

_SECONDS: dict[str, str] = {
    "contamination.station_recent_window_s": "station_recent_window",
    "temporal.t_occlusion_max_s": "t_occlusion_max",
    "temporal.t_escalate_s": "t_escalate",
    "temporal.t_cooldown_s": "t_cooldown",
    "temporal.t_abandon_s": "t_abandon",
    "temporal.t_manager_s": "t_manager",
    "temporal.t_recover_s": "t_recover",
}
_MILLIS: dict[str, str] = {
    "temporal.t_dwell_ms": "t_dwell",
    "temporal.t_hysteresis_ms": "t_hysteresis",
    "temporal.t_reorder_ms": "t_reorder",
}
_STALE_PREFIX = "temporal.t_stale_s."


def apply_overrides(cfg: Config, overrides: Mapping[str, JsonValue]) -> Config:
    updates: dict[str, object] = {}
    t_stale = dict(cfg.t_stale)
    for key in sorted(overrides):
        value = overrides[key]
        if key == "contamination.max_hops":
            updates["max_hops"] = _int(value, key)
        elif key in _SECONDS:
            updates[_SECONDS[key]] = _int(value, key) * 1000
        elif key in _MILLIS:
            updates[_MILLIS[key]] = _int(value, key)
        elif key.startswith(_STALE_PREFIX):
            kind = CarrierKind(key[len(_STALE_PREFIX) :])
            t_stale[kind] = _int(value, key) * 1000
        else:
            raise ValueError(f"unknown config override {key!r}")
    updates["t_stale"] = t_stale
    return Config.model_validate({**cfg.model_dump(), **updates})


# ---- JsonValue helpers ----------------------------------------------------------------------


def _time_of(raw: Mapping[str, JsonValue]) -> int:
    return _int(raw.get("t"), "t")


def _int(value: JsonValue, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{where}: expected an integer, got {value!r}")
    return value


def _mapping(value: JsonValue, where: str) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError(f"{where}: expected a mapping, got {value!r}")
    return value
