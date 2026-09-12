"""Domain-level tests (33): closure and resolution over the real demo bundle."""

from pathlib import Path

from src.knowledge import UNKNOWN_ALLERGEN_PROFILE, KnowledgeProvider, load_bundle, matches

DEMO = Path(__file__).resolve().parents[3] / "config" / "knowledge" / "demo"


def test_load_bundle_counts_and_version() -> None:
    k = load_bundle(DEMO)
    assert len(k.allergens) == 19
    assert len(k.ingredients) == 28
    assert len(k.menu_items) == 8
    assert k.knowledge_version == "1"
    assert KnowledgeProvider(k).version() == "1"
    assert k.ingredients["pesto"].verified_at == "2026-09-11"
    assert k.ingredients["pesto"].contains == frozenset({"PINE_NUT", "MILK"})
    assert k.ingredients["pesto"].may_contain == frozenset({"TREE_NUT"})


def test_load_bundle_accepts_str_path() -> None:
    assert load_bundle(str(DEMO)) == load_bundle(DEMO)


def test_closure_is_ancestors_and_descendants_not_siblings() -> None:
    kp = KnowledgeProvider(load_bundle(DEMO))
    pine = kp.closure("PINE_NUT")
    assert "PINE_NUT" in pine and "TREE_NUT" in pine
    assert "ALMOND" not in pine
    tree = kp.closure("TREE_NUT")
    assert {"TREE_NUT", "PINE_NUT", "ALMOND", "WALNUT", "CASHEW"} <= tree
    assert "PEANUT" not in tree
    assert kp.closure("SHRIMP") == frozenset({"SHRIMP", "SHELLFISH"})


def test_closure_unknown_id_is_itself() -> None:
    kp = KnowledgeProvider(load_bundle(DEMO))
    assert kp.closure("KRYPTONITE") == frozenset({"KRYPTONITE"})


def test_allergens_for() -> None:
    kp = KnowledgeProvider(load_bundle(DEMO))
    contains, may = kp.allergens_for("pesto")
    assert contains == frozenset({"PINE_NUT", "MILK"})
    assert may == frozenset({"TREE_NUT"})
    assert kp.allergens_for("mystery") == (frozenset({UNKNOWN_ALLERGEN_PROFILE}), frozenset())


def test_zones_for() -> None:
    kp = KnowledgeProvider(load_bundle(DEMO))
    assert kp.zones_for("turkey_sandwich") == [
        "bin:bread",
        "bin:turkey",
        "bin:mayo",
        "work",
        "landing",
    ]
    assert kp.zones_for("nope") == []


def test_resolve_alias_is_ingredient_scoped_and_case_insensitive() -> None:
    kp = KnowledgeProvider(load_bundle(DEMO))
    assert kp.resolve_alias("pignoli") is None  # allergen alias, not an ingredient
    assert kp.resolve_alias("Basil pesto") == "pesto"
    assert kp.resolve_alias("PESTO SAUCE") == "pesto"
    assert kp.resolve_alias("mayo") == "mayo"
    assert kp.resolve_alias(" Aioli ") == "mayo"
    assert kp.resolve_alias("") is None


def test_matches_helper() -> None:
    restricted = frozenset({"PINE_NUT", "TREE_NUT"})
    assert matches("TREE_NUT", restricted)
    assert matches(UNKNOWN_ALLERGEN_PROFILE, restricted)
    assert not matches("EGG", restricted)
    assert not matches(UNKNOWN_ALLERGEN_PROFILE, frozenset())
