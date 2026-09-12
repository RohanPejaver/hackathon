"""Config loader, hierarchy and validation (31). Device B owns loading and I/O; the shape
of the *values* is `config/defaults.yaml` (published first).

Hierarchy: defaults.yaml <- profiles/<profile>.yaml <- station/<id>.yaml <- env overrides
(dev/eval only; `demo` and `prod` reject them). Validation before FULL: schema of every
layer, referential integrity (zone contents resolve in the knowledge bundle; menu
required_zones exist in the station map), range checks on every window, checksums of the
station + knowledge bundles. Any failure raises `ConfigError` with a specific message —
safety-critical config never loads partially (23 P12).
"""

from __future__ import annotations

import hashlib
import os
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ENV_PREFIX = "ASL_"  # ASL_temporal__t_dwell_ms=300 overrides temporal.t_dwell_ms
Profile = Literal["dev", "demo", "eval", "prod"]
CarrierKind = Literal["GLOVES", "TOOL", "SURFACE", "CONTAINER", "FOOD"]
ZoneKind = Literal[
    "INGREDIENT", "TOOL_RACK", "CLEAN_STOCK", "WORK", "LANDING", "GLOVE_DISPENSER", "WASH"
]
ResetKind = Literal["GLOVE_CHANGE", "TOOL_SWAP", "SURFACE_SWAP", "WASH_CYCLE", "OPERATOR_ASSERTION"]


class ConfigError(Exception):
    """Specific, human-readable. The controller shows `str(err)` in CALIBRATION."""


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# ---- values (defaults <- profile <- station.thresholds <- env) -------------------------------
class Temporal(Strict):
    t_dwell_ms: int = Field(gt=0, le=10_000)
    t_hysteresis_ms: int = Field(gt=0, le=10_000)
    t_reorder_ms: int = Field(gt=0, le=10_000)
    t_stale_s: dict[Literal["GLOVES", "TOOL", "SURFACE", "CONTAINER"], int]
    t_occlusion_max_s: int = Field(gt=0, le=600)
    t_escalate_s: int = Field(gt=0, le=3600)
    t_cooldown_s: int = Field(gt=0, le=86_400)
    t_abandon_s: int = Field(gt=0, le=86_400)
    t_manager_s: int = Field(gt=0, le=86_400)
    t_recover_s: int = Field(gt=0, le=3600)

    @model_validator(mode="after")
    def _stale_complete_and_positive(self) -> Temporal:
        missing = {"GLOVES", "TOOL", "SURFACE", "CONTAINER"} - set(self.t_stale_s)
        if missing:
            raise ValueError(f"temporal.t_stale_s missing kinds {sorted(missing)}")
        for k, v in self.t_stale_s.items():
            if not 0 < v <= 86_400:
                raise ValueError(f"temporal.t_stale_s.{k}={v} out of range (0, 86400]")
        return self


class Contamination(Strict):
    max_hops: int = Field(ge=1, le=10)
    strength_decay_per_hop: list[Literal["PRESENT", "POSSIBLE"]] = Field(min_length=1)
    station_recent_window_s: int = Field(gt=0, le=86_400)


class Threshold(Strict):
    observed: float = Field(ge=0.0, le=1.01)
    inferred: float = Field(ge=0.0, le=1.01)

    @model_validator(mode="after")
    def _ordered(self) -> Threshold:
        if self.inferred > self.observed:
            raise ValueError("inferred threshold must not exceed observed threshold")
        return self


class Camera(Strict):
    source: int | str


class Markers(Strict):
    dictionary: str
    corner_ids: list[int] = Field(min_length=4, max_length=4)
    corner_size_mm: int = Field(gt=0)
    tool_size_mm: int = Field(gt=0)


class Gloves(Strict):
    hsv_lower: tuple[int, int, int]
    hsv_upper: tuple[int, int, int]
    min_area_px: int = Field(gt=0)


class PerceptionHealth(Strict):
    frame_timeout_s: float = Field(gt=0)
    static_frames: int = Field(gt=0)


class Perception(Strict):
    thresholds: dict[str, Threshold]
    frame_rate_floor_fps: int = Field(gt=0, le=120)
    camera: Camera
    markers: Markers
    gloves: Gloves
    glove_change_absence_s: float = Field(gt=0)
    health: PerceptionHealth


class Capture(Strict):
    resolution: tuple[int, int]
    fps: int = Field(gt=0, le=120)
    frame_buffer_seconds: int = Field(gt=0, le=60)
    persist_frames: bool


class Orders(Strict):
    normalizer_threshold: float = Field(ge=0.0, le=1.0)


class Retention(Strict):
    audit_days: int = Field(ge=0, le=365)


class Runtime(Strict):
    host: str
    port: int = Field(gt=0, lt=65_536)
    ui_push_hz: float = Field(gt=0, le=60)
    log_dir: str


class Values(Strict):
    schema_version: Literal[1]
    temporal: Temporal
    contamination: Contamination
    perception: Perception
    capture: Capture
    orders: Orders
    retention: Retention
    runtime: Runtime


class ProfileFile(Strict):
    profile: Profile
    allow_env_overrides: bool
    capture: dict[str, Any] | None = None


# ---- station -------------------------------------------------------------------------------
class Calibration(Strict):
    units: Literal["mm"]
    origin: str
    width_mm: int = Field(gt=0)
    height_mm: int = Field(gt=0)
    homography: list[list[float]] | None


class Zone(Strict):
    zone_id: str
    kind: ZoneKind
    contents: list[str]
    bound_carrier: str | None
    polygon: list[tuple[int, int]] = Field(min_length=3)


class Carrier(Strict):
    carrier_id: str
    kind: CarrierKind
    home_zone: str | None
    resettable_by: list[ResetKind]


class StockCarrier(Strict):
    carrier_id: str
    kind: CarrierKind
    resettable_by: list[ResetKind]


class StationMarkers(Strict):
    tools: dict[int, str] = {}
    surfaces: dict[int, str] = {}


class Station(Strict):
    station_id: str
    config_version: int = Field(ge=1)
    schema_version: Literal[1]
    worker_slots: int = Field(ge=1, le=8)
    calibration: Calibration
    zones: list[Zone] = Field(min_length=1)
    carriers: list[Carrier] = Field(min_length=1)
    clean_stock: list[StockCarrier] = []
    markers: StationMarkers = StationMarkers()
    thresholds: dict[str, Any] = {}

    @model_validator(mode="after")
    def _internal_integrity(self) -> Station:
        zone_ids = [z.zone_id for z in self.zones]
        carrier_ids = [c.carrier_id for c in self.carriers] + [
            c.carrier_id for c in self.clean_stock
        ]
        if len(set(zone_ids)) != len(zone_ids):
            raise ValueError("duplicate zone_id")
        if len(set(carrier_ids)) != len(carrier_ids):
            raise ValueError("duplicate carrier_id")
        for z in self.zones:
            if z.bound_carrier is not None and z.bound_carrier not in carrier_ids:
                raise ValueError(
                    f"zone {z.zone_id}: bound_carrier {z.bound_carrier!r} is not a carrier"
                )
            if z.contents and z.kind != "INGREDIENT":
                raise ValueError(f"zone {z.zone_id}: only INGREDIENT zones have contents")
        for marker_map in (self.markers.tools, self.markers.surfaces):
            for mid, cid in marker_map.items():
                if cid not in carrier_ids:
                    raise ValueError(
                        f"marker {mid}: {cid!r} is not a carrier or clean-stock carrier"
                    )
        for c in self.carriers:
            if c.home_zone is not None and c.home_zone not in zone_ids:
                raise ValueError(f"carrier {c.carrier_id}: home_zone {c.home_zone!r} is not a zone")
            if c.kind == "FOOD" and c.resettable_by:
                raise ValueError(
                    f"carrier {c.carrier_id}: FOOD carriers are never resettable (11 inv. 7)"
                )
        if not any(c.kind == "GLOVES" for c in self.carriers):
            raise ValueError("station has no GLOVES carrier")
        return self


# ---- knowledge bundle ------------------------------------------------------------------------
class AllergenNode(Strict):
    id: str
    display_name: str
    parents: list[str]
    regulatory_class: str | None = None
    aliases: list[str] = []


class Taxonomy(Strict):
    knowledge_version: int = Field(ge=1)
    schema_version: Literal[1]
    restaurant: str
    allergens: list[AllergenNode] = Field(min_length=1)


class Ingredient(Strict):
    ingredient_id: str
    display_name: str
    aliases: list[str]
    contains: list[str]
    may_contain: list[str]
    source: Literal["SUPPLIER_LABEL", "HOUSE_RECIPE", "MANUAL"]
    verified_at: date
    verified_by_role: str


class Ingredients(Strict):
    knowledge_version: int = Field(ge=1)
    schema_version: Literal[1]
    ingredients: list[Ingredient] = Field(min_length=1)


class MenuItem(Strict):
    item_id: str
    display_name: str
    station_id: str
    ingredient_ids: list[str] = Field(min_length=1)
    required_zones: list[str] = Field(min_length=1)


class MenuItems(Strict):
    knowledge_version: int = Field(ge=1)
    schema_version: Literal[1]
    menu_items: list[MenuItem] = Field(min_length=1)


class Knowledge(Strict):
    taxonomy: Taxonomy
    ingredients: Ingredients
    menu_items: MenuItems
    path: str
    checksum: str

    @property
    def version(self) -> int:
        return self.taxonomy.knowledge_version


class LoadedConfig(Strict):
    profile: Profile
    values: Values
    station: Station
    knowledge: Knowledge
    config_checksum: str
    config_version: int
    knowledge_version: int


# ---- loading ---------------------------------------------------------------------------------
def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ConfigError(f"missing config file: {path}")
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        raise ConfigError(f"{path}: not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return data


def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in over.items():
        out[k] = (
            _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
        )
    return out


def _coerce(raw: str) -> Any:
    return yaml.safe_load(raw)


def _env_overrides(environ: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, raw in environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        node = out
        parts = key[len(ENV_PREFIX) :].split("__")
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node[parts[-1]] = _coerce(raw)
    return out


def _validate(model: type[BaseModel], data: dict[str, Any], what: str) -> Any:
    try:
        return model.model_validate(data)
    except ValidationError as e:
        first = e.errors()[0]
        loc = ".".join(str(x) for x in first["loc"]) or "<root>"
        raise ConfigError(f"{what}: {loc}: {first['msg']}") from e


def _checksum(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    return h.hexdigest()


def load(
    root: Path | str,
    profile: Profile,
    station_id: str,
    knowledge_id: str,
    environ: dict[str, str] | None = None,
) -> LoadedConfig:
    """Load and validate the whole bundle or raise `ConfigError`. Never returns a partial config."""
    root = Path(root)
    environ = dict(os.environ if environ is None else environ)

    profile_file = _validate(
        ProfileFile, _read_yaml(root / "profiles" / f"{profile}.yaml"), f"profiles/{profile}.yaml"
    )
    if profile_file.profile != profile:
        raise ConfigError(f"profiles/{profile}.yaml declares profile {profile_file.profile!r}")

    station_path = root / "station" / f"{station_id}.yaml"
    station = _validate(Station, _read_yaml(station_path), f"station/{station_id}.yaml")

    merged = _read_yaml(root / "defaults.yaml")
    if profile_file.capture:
        merged = _deep_merge(merged, {"capture": profile_file.capture})
    merged = _deep_merge(merged, station.thresholds)
    env = _env_overrides(environ)
    if env:
        if not profile_file.allow_env_overrides:
            keys = sorted(k for k in environ if k.startswith(ENV_PREFIX))
            raise ConfigError(f"profile {profile!r} rejects env overrides; unset {keys}")
        merged = _deep_merge(merged, env)
    values = _validate(Values, merged, "defaults.yaml (merged)")
    if values.capture.persist_frames and profile in ("demo", "prod"):
        raise ConfigError("capture.persist_frames may only be set in dev/eval profiles (24)")

    kdir = root / "knowledge" / knowledge_id
    taxonomy = _validate(
        Taxonomy, _read_yaml(kdir / "taxonomy.yaml"), f"knowledge/{knowledge_id}/taxonomy.yaml"
    )
    ingredients = _validate(
        Ingredients,
        _read_yaml(kdir / "ingredients.yaml"),
        f"knowledge/{knowledge_id}/ingredients.yaml",
    )
    menu = _validate(
        MenuItems, _read_yaml(kdir / "menu_items.yaml"), f"knowledge/{knowledge_id}/menu_items.yaml"
    )
    versions = {taxonomy.knowledge_version, ingredients.knowledge_version, menu.knowledge_version}
    if len(versions) != 1:
        raise ConfigError(
            f"knowledge/{knowledge_id}: files disagree on knowledge_version {sorted(versions)}"
        )

    # referential integrity (31 §Validation)
    allergen_ids = {a.id for a in taxonomy.allergens}
    for a in taxonomy.allergens:
        for p in a.parents:
            if p not in allergen_ids:
                raise ConfigError(f"taxonomy: allergen {a.id} parent {p!r} does not exist")
    ingredient_ids = {i.ingredient_id for i in ingredients.ingredients}
    for i in ingredients.ingredients:
        for al in i.contains + i.may_contain:
            if al not in allergen_ids:
                raise ConfigError(
                    f"ingredients: {i.ingredient_id} references unknown allergen {al!r}"
                )
    zone_ids = {z.zone_id for z in station.zones}
    for z in station.zones:
        for c in z.contents:
            if c not in ingredient_ids:
                raise ConfigError(
                    f"station zone {z.zone_id}: contents ingredient {c!r} "
                    "does not resolve in knowledge bundle"
                )
    for m in menu.menu_items:
        if m.station_id != station.station_id:
            raise ConfigError(
                f"menu item {m.item_id}: station_id {m.station_id!r} != {station.station_id!r}"
            )
        for z in m.required_zones:
            if z not in zone_ids:
                raise ConfigError(
                    f"menu item {m.item_id}: required_zone {z!r} does not exist in station map"
                )
        for i in m.ingredient_ids:
            if i not in ingredient_ids:
                raise ConfigError(
                    f"menu item {m.item_id}: ingredient {i!r} does not resolve in knowledge bundle"
                )
    for t in values.perception.thresholds.values():
        _ = t  # validated by model; listed here so the loop is total

    kfiles = [kdir / n for n in ("taxonomy.yaml", "ingredients.yaml", "menu_items.yaml")]
    knowledge = Knowledge(
        taxonomy=taxonomy,
        ingredients=ingredients,
        menu_items=menu,
        path=str(kdir),
        checksum=_checksum(kfiles),
    )
    return LoadedConfig(
        profile=profile,
        values=values,
        station=station,
        knowledge=knowledge,
        config_checksum=_checksum(
            [root / "defaults.yaml", root / "profiles" / f"{profile}.yaml", station_path]
        ),
        config_version=station.config_version,
        knowledge_version=knowledge.version,
    )


# ---- projection into the semantic contracts (src/domain) -------------------------------------
def to_domain(loaded: LoadedConfig) -> tuple[Any, Any, Any]:
    """Map the nested YAML values (seconds/ms) onto the flat millisecond `domain.Config`,
    the `StationConfig` and the `Knowledge` bundle. This is the only place the two layouts
    meet; `runtime/` is the composition root and may import everything (30 rule 4)."""
    from src import domain as dom

    v = loaded.values
    t = v.temporal
    s = t.t_stale_s
    # CONTRACT-GAP: 19 lists four t_stale kinds; FOOD carriers use the SURFACE value —
    # food sits on a surface and is observed with it.
    t_stale = {
        dom.CarrierKind.GLOVES: s["GLOVES"] * 1000,
        dom.CarrierKind.TOOL: s["TOOL"] * 1000,
        dom.CarrierKind.SURFACE: s["SURFACE"] * 1000,
        dom.CarrierKind.CONTAINER: s["CONTAINER"] * 1000,
        dom.CarrierKind.FOOD: s["SURFACE"] * 1000,
    }
    cfg = dom.Config(
        config_version=str(loaded.config_version),
        knowledge_version=str(loaded.knowledge_version),
        max_hops=v.contamination.max_hops,
        t_reorder=t.t_reorder_ms,
        t_stale=t_stale,
        t_occlusion_max=t.t_occlusion_max_s * 1000,
        station_recent_window=v.contamination.station_recent_window_s * 1000,
        t_escalate=t.t_escalate_s * 1000,
        t_cooldown=t.t_cooldown_s * 1000,
        t_abandon=t.t_abandon_s * 1000,
        t_dwell=t.t_dwell_ms,
        t_hysteresis=t.t_hysteresis_ms,
        t_recover=t.t_recover_s * 1000,
        t_manager=t.t_manager_s * 1000,
        threshold_observed={k: th.observed for k, th in v.perception.thresholds.items()},
        threshold_inferred={k: th.inferred for k, th in v.perception.thresholds.items()},
        normalizer_threshold=v.orders.normalizer_threshold,
        strength_decay_per_hop=[dom.Strength(x) for x in v.contamination.strength_decay_per_hop],
    )

    ingredients = {i.ingredient_id: i for i in loaded.knowledge.ingredients.ingredients}
    zone_allergens: dict[str, dict[str, dom.Strength]] = {}
    for z in loaded.station.zones:
        profile: dict[str, dom.Strength] = {}
        for ing in z.contents:
            rec = ingredients[ing]
            for a in rec.may_contain:
                profile.setdefault(a, dom.Strength.POSSIBLE)
            for a in rec.contains:
                profile[a] = dom.Strength.PRESENT
        if profile:
            zone_allergens[z.zone_id] = profile

    station = dom.StationConfig(
        station_id=loaded.station.station_id,
        config_version=str(loaded.config_version),
        knowledge_version=str(loaded.knowledge_version),
        # 23 P12: nothing enters FULL before validation; the controller moves it.
        mode=dom.Mode.CALIBRATION,
        worker_slots=loaded.station.worker_slots,
        carriers={
            c.carrier_id: dom.Carrier(
                carrier_id=c.carrier_id,
                kind=dom.CarrierKind(c.kind),
                epistemic=dom.EpistemicStatus.UNKNOWN,  # 13: never observed at station start
                home_zone=c.home_zone,
                resettable_by=frozenset(dom.ResetKind(r) for r in c.resettable_by),
            )
            for c in loaded.station.carriers
        },
        zones={
            z.zone_id: dom.Zone(
                zone_id=z.zone_id,
                polygon=[dom.Point2D(x=x, y=y) for x, y in z.polygon],
                kind=dom.ZoneKind(z.kind),
                contents=list(z.contents),
                bound_carrier=z.bound_carrier,
            )
            for z in loaded.station.zones
        },
        zone_allergens=zone_allergens,
        calibration=loaded.station.calibration.model_dump(),
    )

    k = loaded.knowledge
    knowledge = dom.Knowledge(
        knowledge_version=str(k.version),
        allergens={
            a.id: dom.AllergenNode(
                id=a.id,
                display_name=a.display_name,
                parents=list(a.parents),
                regulatory_class=a.regulatory_class,
                aliases=list(a.aliases),
            )
            for a in k.taxonomy.allergens
        },
        ingredients={
            i.ingredient_id: dom.IngredientRecord(
                ingredient_id=i.ingredient_id,
                display_name=i.display_name,
                aliases=list(i.aliases),
                contains=frozenset(i.contains),
                may_contain=frozenset(i.may_contain),
                source=i.source,
                verified_at=str(i.verified_at),
                verified_by_role=i.verified_by_role,
            )
            for i in k.ingredients.ingredients
        },
        menu_items={
            m.item_id: dom.MenuItemRecord(
                item_id=m.item_id,
                ingredient_ids=list(m.ingredient_ids),
                required_zones=list(m.required_zones),
                station_id=m.station_id,
            )
            for m in k.menu_items.menu_items
        },
    )
    return cfg, station, knowledge
