"""Every clause of the matching rule in ``src/orders/normalizer.py`` is a test here.

The demo taxonomy has TREE_NUT aliases ``[tree nuts, nuts, nut allergy]``, so "no nuts"
resolves; the 17 example "no nuts?" -> AMBIGUOUS refers to a taxonomy without that alias
and is tested against one below.
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from src.domain import Knowledge, Resolution, Restriction
from src.orders import DEFAULT_THRESHOLD, normalize
from src.orders.normalizer import FUZZY_SCORE, _score, preprocess, tokenize

R = Resolution


def resolved(r: Restriction) -> bool:
    return r.resolution is R.RESOLVED


# --- preprocessing --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  PINE NUT   allergy!! ", "pine nut allergy"),
        ("PINE_NUT allergy", "pine nut allergy"),
        ("no nuts?", "no nuts"),
        ("gluten-free", "gluten-free"),
        ("can’t have milk", "can't have milk"),
        ("", ""),
    ],
)
def test_preprocess(raw: str, expected: str) -> None:
    assert preprocess(raw) == expected


def test_tokenize_splits_hyphens_and_keeps_apostrophes() -> None:
    assert tokenize("gluten-free can't 'quoted'") == ("gluten", "free", "can't", "quoted")


# --- the fixture strings S3 replays ---------------------------------------------------------


@pytest.mark.parametrize(
    "raw", ["pine nut allergy", "PINE NUT ALLERGY", "PINE_NUT allergy", "pine-nut allergy"]
)
def test_pine_nut_allergy_variants_resolve(k: Knowledge, raw: str) -> None:
    r = normalize(raw, k)
    assert r == Restriction(
        kind="AVOID_ALLERGEN",
        allergen_ids=frozenset({"PINE_NUT"}),
        raw_text=raw,
        resolution=R.RESOLVED,
        severity_declared="STATED_ALLERGY",
    )


def test_no_pine_nuts_is_a_stated_preference(k: Knowledge) -> None:
    r = normalize("no pine nuts", k)
    assert resolved(r)
    assert r.allergen_ids == frozenset({"PINE_NUT"})
    assert r.severity_declared == "STATED_PREFERENCE"
    assert r.kind == "AVOID_ALLERGEN"


def test_allergy_alone_is_ambiguous_scenario_g(k: Knowledge) -> None:
    r = normalize("ALLERGY", k)
    assert r.resolution is R.AMBIGUOUS
    assert r.allergen_ids == frozenset()
    assert r.severity_declared == "STATED_ALLERGY"
    assert r.raw_text == "ALLERGY"


# --- outcomes -------------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["", "   ", "?!", "severe allergies", "no", "please be careful"])
def test_nothing_named_is_ambiguous(k: Knowledge, raw: str) -> None:
    r = normalize(raw, k)
    assert r.resolution is R.AMBIGUOUS
    assert r.allergen_ids == frozenset()


@pytest.mark.parametrize("raw", ["no durian", "durian allergy", "extra napkins", "napkins"])
def test_unknown_content_word_is_unresolvable(k: Knowledge, raw: str) -> None:
    r = normalize(raw, k)
    assert r.resolution is R.UNRESOLVABLE
    assert r.allergen_ids == frozenset()


def test_raw_text_is_preserved_verbatim(k: Knowledge) -> None:
    raw = "  PINE NUT  allergy!! "
    assert normalize(raw, k).raw_text == raw


def test_no_nuts_resolves_via_taxonomy_alias(k: Knowledge) -> None:
    assert normalize("no nuts", k).allergen_ids == frozenset({"TREE_NUT"})
    assert normalize("no nuts?", k).allergen_ids == frozenset({"TREE_NUT"})
    assert resolved(normalize("no nuts?", k))


def test_no_nuts_is_ambiguous_without_the_alias(k: Knowledge) -> None:
    """17's "no nuts?" example: with no `nuts` alias the intent is clear, the allergen not."""
    tree_nut = k.allergens["TREE_NUT"]
    stripped = tree_nut.model_copy(
        update={"aliases": [a for a in tree_nut.aliases if a not in ("nuts", "nut allergy")]}
    )
    k2 = k.model_copy(update={"allergens": {**k.allergens, "TREE_NUT": stripped}})
    r = normalize("no nuts?", k2)
    # "nuts" is one word of "tree nuts" (TREE_NUT) and of "pine nuts" (PINE_NUT): the
    # candidates disagree, so the fuzzy score is 0.0 -> AMBIGUOUS under any threshold.
    assert r.resolution is R.AMBIGUOUS
    assert r.allergen_ids == frozenset()
    assert _score("no nuts?", k2).confidence == 0.0
    assert normalize("no nuts?", k2, threshold=0.01).resolution is R.AMBIGUOUS


def test_specific_allergen_never_widens_to_parent(k: Knowledge) -> None:
    """Closure is the risk engine's job (15); PINE_NUT stays PINE_NUT here."""
    assert normalize("pine nut allergy", k).allergen_ids == frozenset({"PINE_NUT"})


# --- ingredients ---------------------------------------------------------------------------


def test_no_pesto_contributes_contains_union_may_contain(k: Knowledge) -> None:
    """Rule: an ingredient match yields contains | may_contain. Demo pesto: contains
    {PINE_NUT, MILK}, may_contain {TREE_NUT} -> all three."""
    r = normalize("no pesto", k)
    assert r == Restriction(
        kind="AVOID_INGREDIENT",
        allergen_ids=frozenset({"PINE_NUT", "MILK", "TREE_NUT"}),
        raw_text="no pesto",
        resolution=R.RESOLVED,
        severity_declared="STATED_PREFERENCE",
    )


def test_allergen_phrase_beats_ingredient_alias_for_the_same_span(k: Knowledge) -> None:
    """The word "tuna" is both the allergen TUNA and an alias of the tuna_salad
    ingredient (contains TUNA, EGG). Naming the allergen means the allergen."""
    r = normalize("no tuna", k)
    assert r.allergen_ids == frozenset({"TUNA"})
    assert r.kind == "AVOID_ALLERGEN"
    r2 = normalize("no tuna salad", k)
    assert r2.allergen_ids == frozenset({"TUNA", "EGG"})
    assert r2.kind == "AVOID_INGREDIENT"


def test_kind_is_avoid_allergen_when_any_allergen_word_matched(k: Knowledge) -> None:
    r = normalize("no pesto, milk allergy", k)
    assert r.kind == "AVOID_ALLERGEN"
    assert r.allergen_ids == frozenset({"PINE_NUT", "MILK", "TREE_NUT"})
    assert r.severity_declared == "STATED_ALLERGY"


def test_known_ingredient_without_allergens_resolves_to_empty_set(k: Knowledge) -> None:
    r = normalize("no onion", k)
    assert resolved(r)
    assert r.kind == "AVOID_INGREDIENT"
    assert r.allergen_ids == frozenset()


def test_matches_win_over_unknown_extra_words(k: Knowledge) -> None:
    """Documented choice: a recognized allergen resolves even with unrecognized words
    around it (table numbers, names). Only a note with *nothing* recognized is UNRESOLVABLE."""
    r = normalize("pine nut allergy for table 4, name Priya", k)
    assert resolved(r)
    assert r.allergen_ids == frozenset({"PINE_NUT"})


# --- dietary --------------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["gluten-free", "gluten free", "GLUTEN FREE please"])
def test_gluten_free_is_dietary_wheat(k: Knowledge, raw: str) -> None:
    r = normalize(raw, k)
    assert resolved(r)
    assert r.kind == "DIETARY"
    assert r.allergen_ids == frozenset({"WHEAT"})


def test_celiac_is_dietary_wheat_and_a_stated_allergy(k: Knowledge) -> None:
    r = normalize("celiac", k)
    assert resolved(r)
    assert r.kind == "DIETARY"
    assert r.allergen_ids == frozenset({"WHEAT"})
    assert r.severity_declared == "STATED_ALLERGY"


@pytest.mark.parametrize("raw", ["vegan", "vegetarian", "halal", "kosher"])
def test_unmapped_dietary_words_resolve_with_no_allergens(k: Knowledge, raw: str) -> None:
    r = normalize(raw, k)
    assert r == Restriction(
        kind="DIETARY",
        allergen_ids=frozenset(),
        raw_text=raw,
        resolution=R.RESOLVED,
        severity_declared="UNSPECIFIED",
    )


def test_gluten_alone_is_the_wheat_allergen(k: Knowledge) -> None:
    r = normalize("gluten allergy", k)
    assert r.kind == "AVOID_ALLERGEN"
    assert r.allergen_ids == frozenset({"WHEAT"})


# --- severity -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "severity"),
    [
        ("milk allergy", "STATED_ALLERGY"),
        ("allergic to eggs", "STATED_ALLERGY"),
        ("lactose intolerant", "STATED_ALLERGY"),
        ("no dairy", "STATED_PREFERENCE"),
        ("without mayo", "STATED_PREFERENCE"),
        ("dislikes onion", "UNSPECIFIED"),
        ("prefer no cheese", "STATED_PREFERENCE"),
        ("dairy free", "UNSPECIFIED"),
        ("sesame", "UNSPECIFIED"),
        ("no peanuts, peanut allergy", "STATED_ALLERGY"),
    ],
)
def test_severity_declared(k: Knowledge, raw: str, severity: str) -> None:
    assert normalize(raw, k).severity_declared == severity


# --- the threshold gate (17: the normalizer may never guess) ------------------------------


def test_fuzzy_match_scores_below_default_threshold(k: Knowledge) -> None:
    s = _score("pinenut allergy", k)
    assert s.confidence == FUZZY_SCORE < DEFAULT_THRESHOLD
    assert s.allergen_ids == frozenset({"PINE_NUT"})


def test_below_threshold_is_ambiguous_never_resolved(k: Knowledge) -> None:
    r = normalize("pinenut allergy", k)
    assert r.resolution is R.AMBIGUOUS
    assert r.allergen_ids == frozenset()  # no best-effort allergen leaks out
    assert r.severity_declared == "STATED_ALLERGY"


def test_lowering_the_threshold_admits_the_fuzzy_match(k: Knowledge) -> None:
    r = normalize("pinenut allergy", k, threshold=0.5)
    assert r.resolution is R.RESOLVED
    assert r.allergen_ids == frozenset({"PINE_NUT"})


@pytest.mark.parametrize("threshold", [0.61, 0.8, 0.95, 1.0])
def test_threshold_gate_is_strict(k: Knowledge, threshold: float) -> None:
    assert normalize("pinenut allergy", k, threshold=threshold).resolution is R.AMBIGUOUS


@pytest.mark.parametrize("raw", ["pinenuts", "pignol", "almon allergy", "no pesto or pinenuts"])
def test_fuzzy_inputs_are_ambiguous_at_default(k: Knowledge, raw: str) -> None:
    """A fuzzy token anywhere drags the whole note down (confidence = min over matches)."""
    r = normalize(raw, k)
    assert r.resolution is R.AMBIGUOUS
    assert r.allergen_ids == frozenset()


def test_short_or_disagreeing_fuzzy_never_resolves(k: Knowledge) -> None:
    # "nut" is 3 chars: below FUZZY_MIN_CHARS, so it is an unknown word, not a guess.
    assert normalize("nut free", k).resolution is R.UNRESOLVABLE
    # "pean" prefixes peanut (PEANUT) and peanut butter (PEANUT, TREE_NUT): candidates
    # disagree -> 0.0, AMBIGUOUS even with the gate wide open.
    s = _score("pean allergy", k)
    assert s.confidence == 0.0
    assert normalize("pean allergy", k, threshold=0.01).resolution is R.AMBIGUOUS


def test_deterministic(k: Knowledge) -> None:
    for raw in ("pine nut allergy", "no pesto", "pinenut allergy", "vegan", "no durian"):
        assert normalize(raw, k) == normalize(raw, k)
        assert _score(raw, k) == _score(raw, k)


# --- properties -----------------------------------------------------------------------------

# fmt: off
WORDS = [
    "pine", "nut", "nuts", "pinenuts", "pinenut", "allergy", "allergic", "no", "without",
    "pesto", "durian", "severe", "vegan", "gluten-free", "gluten", "free", "PINE_NUT", "milk",
    "dairy", "table", "4", "can't", "?", "!", "extra", "napkins", "tuna", "salad", "peanut",
    "butter", "pean", "almon", "celiac", "Pine", "NUT", "sesame", "bagel", "", ",",
]
# fmt: on


@settings(max_examples=300, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    words=st.lists(st.sampled_from(WORDS), max_size=8),
    threshold=st.floats(min_value=0.0, max_value=1.0),
)
def test_never_resolved_below_threshold(k: Knowledge, words: list[str], threshold: float) -> None:
    raw = " ".join(words)
    r = normalize(raw, k, threshold)
    s = _score(raw, k)
    assert r.raw_text == raw
    if r.resolution is R.RESOLVED:
        assert s.matched
        assert s.confidence >= threshold
        assert r.allergen_ids == s.allergen_ids
    else:
        assert r.allergen_ids == frozenset()
    assert normalize(raw, k, threshold) == r  # deterministic


@settings(max_examples=200, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(raw=st.text())
def test_never_raises_on_arbitrary_text(k: Knowledge, raw: str) -> None:
    r = normalize(raw, k)
    assert r.raw_text == raw
    assert isinstance(r.resolution, Resolution)
