"""The loader's projection onto src/domain contracts: units become milliseconds, zone
contents become allergen profiles (contains -> PRESENT beats may_contain -> POSSIBLE), every
carrier starts UNKNOWN (13), and the station starts in CALIBRATION (23 P12)."""

from src.domain import CarrierKind, EpistemicStatus, Mode, Strength
from src.runtime.config import load, to_domain


def test_projection_units_profiles_and_start_state():
    cfg, station, k = to_domain(load("config", "demo", "demo", "demo", environ={}))
    assert cfg.t_dwell == 250 and cfg.t_reorder == 500 and cfg.t_escalate == 20_000
    assert cfg.t_stale[CarrierKind.GLOVES] == 20_000 and cfg.t_stale[CarrierKind.FOOD] == 300_000
    assert cfg.station_recent_window == 1_800_000 and cfg.max_hops == 3
    assert cfg.threshold_observed["GLOVE_CHANGE"] > 1.0  # EXP-004: not OBSERVED-capable yet
    assert station.mode == Mode.CALIBRATION
    assert all(c.epistemic == EpistemicStatus.UNKNOWN for c in station.carriers.values())
    assert station.zone_allergens["bin:pesto"] == {
        "PINE_NUT": Strength.PRESENT,
        "MILK": Strength.PRESENT,
        "TREE_NUT": Strength.POSSIBLE,
    }
    assert station.zone_allergens["bin:mayo"] == {"EGG": Strength.PRESENT}
    assert "work" not in station.zone_allergens
    assert station.zones["bin:pesto"].bound_carrier == "bin:pesto"
    assert k.allergens["PINE_NUT"].parents == ["TREE_NUT"]
    assert k.menu_items["turkey_sandwich"].required_zones == [
        "bin:bread",
        "bin:turkey",
        "bin:mayo",
        "work",
        "landing",
    ]
    assert k.ingredients["pesto"].contains == frozenset({"PINE_NUT", "MILK"})
