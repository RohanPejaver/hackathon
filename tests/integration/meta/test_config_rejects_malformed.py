"""38 §P0 gate (B's clause): config validation rejects a deliberately malformed bundle with a
specific error — never a silent default, never a partial load (31 §Validation, 23 P12).
Each case plants one defect in a copy of `config/` and asserts the loader refuses it."""

import shutil
from pathlib import Path

import pytest
import yaml

from src.runtime.config import ConfigError, load

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def bundle(tmp_path: Path) -> Path:
    shutil.copytree(ROOT / "config", tmp_path / "config")
    return tmp_path / "config"


def _edit(path: Path, fn) -> None:
    d = yaml.safe_load(path.read_text())
    fn(d)
    path.write_text(yaml.safe_dump(d, sort_keys=False))


def test_the_real_bundle_loads_with_versions_and_checksums(bundle: Path):
    cfg = load(bundle, "demo", "demo", "demo", environ={})
    assert cfg.config_version == 1 and cfg.knowledge_version == 1
    assert len(cfg.config_checksum) == 64 and len(cfg.knowledge.checksum) == 64
    assert cfg.values.temporal.t_dwell_ms == 250 and cfg.values.contamination.max_hops == 3


@pytest.mark.parametrize(
    "file, mutate, expect",
    [
        (
            "defaults.yaml",
            lambda d: d["temporal"].__setitem__("t_hysteresis_ms", -5),
            "t_hysteresis_ms",
        ),
        (
            "station/demo.yaml",
            lambda d: d["thresholds"]["temporal"].__setitem__("t_dwell_ms", 0),
            "t_dwell_ms",
        ),
        ("defaults.yaml", lambda d: d["temporal"].pop("t_reorder_ms"), "t_reorder_ms"),
        ("defaults.yaml", lambda d: d["temporal"]["t_stale_s"].pop("GLOVES"), "t_stale_s"),
        ("defaults.yaml", lambda d: d["contamination"].__setitem__("max_hops", 0), "max_hops"),
        ("defaults.yaml", lambda d: d.__setitem__("unknown_section", {"x": 1}), "unknown_section"),
        (
            "station/demo.yaml",
            lambda d: d["zones"][0].__setitem__("contents", ["pestoo"]),
            "does not resolve",
        ),
        (
            "station/demo.yaml",
            lambda d: d["zones"][0].__setitem__("polygon", [[0, 0], [1, 1]]),
            "polygon",
        ),
        (
            "station/demo.yaml",
            lambda d: d["carriers"][1].__setitem__("home_zone", "nowhere"),
            "home_zone",
        ),
        (
            "station/demo.yaml",
            lambda d: d["zones"][4].__setitem__("bound_carrier", "ghost"),
            "bound_carrier",
        ),
        ("station/demo.yaml", lambda d: d.pop("config_version"), "config_version"),
        (
            "knowledge/demo/menu_items.yaml",
            lambda d: d["menu_items"][0].__setitem__("required_zones", ["bin:nope"]),
            "required_zone",
        ),
        (
            "knowledge/demo/ingredients.yaml",
            lambda d: d["ingredients"][0].__setitem__("contains", ["PLUTONIUM"]),
            "unknown allergen",
        ),
        (
            "knowledge/demo/taxonomy.yaml",
            lambda d: d["allergens"][9].__setitem__("parents", ["NUTS"]),
            "parent",
        ),
        (
            "knowledge/demo/taxonomy.yaml",
            lambda d: d.__setitem__("knowledge_version", 2),
            "knowledge_version",
        ),
    ],
)
def test_malformed_bundle_is_rejected_with_a_specific_error(bundle: Path, file, mutate, expect):
    _edit(bundle / file, mutate)
    with pytest.raises(ConfigError) as ei:
        load(bundle, "demo", "demo", "demo", environ={})
    assert expect in str(ei.value), str(ei.value)


def test_unparseable_yaml_is_rejected_not_defaulted(bundle: Path):
    (bundle / "defaults.yaml").write_text("temporal: [unclosed\n")
    with pytest.raises(ConfigError, match="YAML"):
        load(bundle, "demo", "demo", "demo", environ={})


def test_demo_and_prod_reject_env_overrides_but_dev_applies_them(bundle: Path):
    env = {"ASL_temporal__t_dwell_ms": "300"}
    for profile in ("demo", "prod"):
        with pytest.raises(ConfigError, match="rejects env overrides"):
            load(bundle, profile, "demo", "demo", environ=env)
    assert load(bundle, "dev", "demo", "demo", environ=env).values.temporal.t_dwell_ms == 300


def test_hierarchy_station_overrides_defaults(bundle: Path):
    _edit(
        bundle / "station/demo.yaml",
        lambda d: d.__setitem__("thresholds", {"temporal": {"t_dwell_ms": 400}}),
    )
    assert load(bundle, "demo", "demo", "demo", environ={}).values.temporal.t_dwell_ms == 400


def test_persist_frames_is_dev_eval_only(bundle: Path):
    _edit(
        bundle / "profiles/demo.yaml", lambda d: d.__setitem__("capture", {"persist_frames": True})
    )
    with pytest.raises(ConfigError, match="persist_frames"):
        load(bundle, "demo", "demo", "demo", environ={})
