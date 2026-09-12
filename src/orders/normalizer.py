"""Restriction normalizer (17 §Restriction normalization; 22 §RestrictionNormalizer).

Deterministic string matching against the vocabulary carried by ``Knowledge``. No model, no
network, no clock, no randomness — the normalizer is auditable end to end (15 §Where ML
belongs allows a learned normalizer *with* a mandatory AMBIGUOUS fallback; a deterministic
matcher with an explicit confidence score satisfies that contract and is explainable).

The one invariant that matters (17, 33): **a below-threshold match is AMBIGUOUS, never a
best-effort RESOLVED.** ``normalize`` may never guess.

Matching rule (every clause is a unit test in ``tests/unit/orders/test_normalizer.py``):

1. Preprocess: lowercase; ``_`` and every punctuation mark except ``-`` and ``'`` become a
   space; whitespace collapses. The original text is kept verbatim in ``raw_text``.
2. Tokenize on whitespace and hyphens, so ``pine_nut`` / ``pine-nut`` / ``pine nut`` /
   ``PINE NUT`` are the same phrase ``("pine", "nut")``.
3. Vocabulary from ``Knowledge``: every ``AllergenNode`` ``id``, ``display_name`` and alias
   maps to that allergen; every ``IngredientRecord`` ``ingredient_id``, ``display_name`` and
   alias maps to ``contains | may_contain``; a fixed dietary vocabulary (vegan, vegetarian,
   halal, kosher, gluten free, celiac, coeliac) maps to the allergen behind the ``gluten``
   alias when the taxonomy has one, else to nothing.
4. Whole-phrase matches are found greedily, longest phrase first, left to right, on token
   boundaries; each token is consumed by at most one match. A whole-phrase match scores 1.0.
   When one phrase is in several vocabularies the span resolves DIETARY > allergen >
   ingredient ("tuna" is the allergen TUNA, not the tuna-salad ingredient; "gluten free" is
   dietary, not the gluten-free-bread ingredient).
5. Fuzzy: a leftover token of >= 4 characters that (a) is a prefix of, or is prefixed by, a
   vocabulary phrase with its spaces removed ("pinenut" vs "pine nuts"), or (b) is a prefix
   of one word of a multi-word phrase ("nuts" vs "tree nuts"), scores 0.6 — below the default
   threshold, so it is AMBIGUOUS unless the operator lowers the gate. If the candidate
   phrases disagree on what the token names ("nuts": tree nuts? pine nuts?) it scores 0.0:
   ambiguous under any gate.
6. Confidence of the whole note is the minimum over its matches. ``matched and confidence
   >= threshold`` is RESOLVED with the union of matched allergen ids; ``matched`` but below
   threshold is AMBIGUOUS; nothing matched and a content word the knowledge base does not
   know is left over ("no durian", "extra napkins") is UNRESOLVABLE; nothing matched and
   nothing unknown ("", "ALLERGY", "severe allergies") is AMBIGUOUS. AMBIGUOUS and
   UNRESOLVABLE restrictions carry no allergen ids at all.
7. A specific allergen never widens to its taxonomy parents here — closure is the risk
   engine's job (15 §Allergen matching).
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Final, Literal, NamedTuple

from src.domain import Knowledge, Resolution, Restriction

DEFAULT_THRESHOLD: Final = 0.8
WHOLE_PHRASE_SCORE: Final = 1.0
FUZZY_SCORE: Final = 0.6
FUZZY_MIN_CHARS: Final = 4

Kind = Literal["AVOID_ALLERGEN", "AVOID_INGREDIENT", "DIETARY"]
Severity = Literal["STATED_ALLERGY", "STATED_PREFERENCE", "UNSPECIFIED"]
Phrase = tuple[str, ...]

ALLERGY_WORDS: Final[frozenset[str]] = frozenset(
    {
        "allergy",
        "allergic",
        "allergies",
        "anaphylaxis",
        "celiac",
        "coeliac",
        "intolerance",
        "intolerant",
    }
)
PREFERENCE_WORDS: Final[frozenset[str]] = frozenset(
    {"prefer", "preference", "no", "without", "dislike"}
)
INTENT_WORDS: Final[frozenset[str]] = (
    ALLERGY_WORDS
    | PREFERENCE_WORDS
    | frozenset({"free", "avoid", "none", "can't", "cannot", "sensitive", "sensitivity"})
)

# Words that qualify a restriction without naming a food. They never make a note
# UNRESOLVABLE on their own ("severe allergies" is AMBIGUOUS, not "severe is unknown").
# fmt: off
FILLER_WORDS: Final[frozenset[str]] = frozenset(
    {
        # qualifiers
        "severe", "serious", "mild", "very", "extremely", "strict", "strictly", "really",
        "super", "major", "minor", "bad", "big", "extra", "side",
        # politeness / emphasis
        "please", "pls", "plz", "thanks", "thank", "you", "important", "urgent", "note",
        "notes", "warning", "caution", "attention",
        # grammar
        "a", "an", "the", "to", "of", "with", "for", "and", "or", "is", "are", "has", "have",
        "had", "be", "it", "in", "on", "at", "by", "as", "this", "that", "any", "all", "some",
        "not", "don't", "dont", "do", "does", "doesn't", "doesnt", "if", "so", "but", "also",
        "too", "only", "just",
        # people / places
        "i", "we", "my", "our", "he", "she", "they", "his", "her", "their", "customer",
        "guest", "kid", "child", "son", "daughter", "table", "order", "ticket",
        # allergy-adjacent nouns that name no food
        "reaction", "reactions", "epipen", "epi", "pen", "life", "threatening", "diet",
        "dietary", "restriction", "restrictions", "food", "foods", "contain", "contains",
        "containing", "ingredient", "ingredients", "eat", "eats", "cross", "contact",
        "careful", "care",
    }
)
# fmt: on

# Dietary vocabulary -> alias words looked up in the allergen vocabulary (17: gluten-free /
# celiac resolve to WHEAT because the taxonomy carries a "gluten" alias; vegan et al. map to
# nothing the station map can check and bind with an empty allergen set).
DIETARY_PHRASES: Final[dict[str, tuple[str, ...]]] = {
    "vegan": (),
    "vegetarian": (),
    "halal": (),
    "kosher": (),
    "gluten free": ("gluten",),
    "celiac": ("gluten",),
    "coeliac": ("gluten",),
}

_SPAN_PRECEDENCE: Final[tuple[Kind, ...]] = ("DIETARY", "AVOID_ALLERGEN", "AVOID_INGREDIENT")
_KIND_PRECEDENCE: Final[tuple[Kind, ...]] = ("AVOID_ALLERGEN", "AVOID_INGREDIENT", "DIETARY")

_PUNCT: Final = re.compile(r"[^\w\s'-]")
_SPLIT: Final = re.compile(r"[\s\-]+")


def preprocess(raw_text: str) -> str:
    """Rule 1. Lowercase, punctuation (except ``-``/``'``) and ``_`` to spaces, collapse."""
    text = raw_text.lower().replace("’", "'").replace("_", " ")
    return " ".join(_PUNCT.sub(" ", text).split())


def tokenize(text: str) -> Phrase:
    """Rule 2. Split on whitespace and hyphens; drop empty and apostrophe-only pieces."""
    return tuple(t for t in (piece.strip("'") for piece in _SPLIT.split(text)) if t)


class Match(NamedTuple):
    phrase: Phrase
    kind: Kind
    allergen_ids: frozenset[str]
    confidence: float


class Score(NamedTuple):
    """Everything ``normalize`` decides from, exposed for property tests and audit."""

    allergen_ids: frozenset[str]
    confidence: float
    kind: Kind
    severity: Severity
    matched: tuple[Match, ...]
    unknown: tuple[str, ...]


class Vocabulary(NamedTuple):
    phrases: dict[Phrase, dict[Kind, frozenset[str]]]
    squashed: tuple[tuple[str, Phrase], ...]
    max_len: int


def build_vocabulary(k: Knowledge) -> Vocabulary:
    """Rule 3. Deterministic: iteration order is sorted, never dict-insertion order."""
    phrases: dict[Phrase, dict[Kind, set[str]]] = {}

    def add(phrase: str, kind: Kind, ids: Iterable[str]) -> None:
        tokens = tokenize(preprocess(phrase))
        if tokens:
            phrases.setdefault(tokens, {}).setdefault(kind, set()).update(ids)

    for allergen_id in sorted(k.allergens):
        node = k.allergens[allergen_id]
        for phrase in (node.id, node.display_name, *node.aliases):
            add(phrase, "AVOID_ALLERGEN", {node.id})
    for ingredient_id in sorted(k.ingredients):
        record = k.ingredients[ingredient_id]
        for phrase in (record.ingredient_id, record.display_name, *record.aliases):
            add(phrase, "AVOID_INGREDIENT", record.contains | record.may_contain)
    for phrase, alias_words in DIETARY_PHRASES.items():
        ids: set[str] = set()
        for word in alias_words:
            ids |= phrases.get(tokenize(preprocess(word)), {}).get("AVOID_ALLERGEN", set())
        add(phrase, "DIETARY", ids)

    frozen = {
        phrase: {kind: frozenset(ids) for kind, ids in kinds.items()}
        for phrase, kinds in sorted(phrases.items())
    }
    squashed = tuple(
        ("".join(phrase), phrase)
        for phrase in sorted(frozen)
        if len("".join(phrase)) >= FUZZY_MIN_CHARS
    )
    return Vocabulary(frozen, squashed, max((len(p) for p in frozen), default=0))


def _span_entry(kinds: dict[Kind, frozenset[str]]) -> tuple[Kind, frozenset[str]]:
    for kind in _SPAN_PRECEDENCE:
        if kind in kinds:
            return kind, kinds[kind]
    raise AssertionError("vocabulary entry without a kind")  # unreachable by construction


def _fuzzy(token: str, vocab: Vocabulary) -> Match | None:
    """Rule 5. Prefix agreement (>= 4 chars) against space-less phrases or against one word
    of a multi-word phrase; 0.6, or 0.0 if the candidates disagree on what the token names."""
    if len(token) < FUZZY_MIN_CHARS:
        return None
    candidates = [
        phrase
        for squash, phrase in vocab.squashed
        if squash.startswith(token)
        or token.startswith(squash)
        or (len(phrase) > 1 and any(word.startswith(token) for word in phrase))
    ]
    if not candidates:
        return None
    entries = {_span_entry(vocab.phrases[phrase]) for phrase in candidates}
    if len(entries) == 1:
        kind, ids = next(iter(entries))
        return Match((token,), kind, ids, FUZZY_SCORE)
    return Match((token,), "AVOID_ALLERGEN", frozenset(), 0.0)


def _score(raw_text: str, k: Knowledge) -> Score:
    """Rules 3-6 without the threshold gate; ``normalize`` applies the gate."""
    vocab = build_vocabulary(k)
    tokens = tokenize(preprocess(raw_text))
    consumed = [False] * len(tokens)
    matches: list[Match] = []

    for length in range(min(vocab.max_len, len(tokens)), 0, -1):  # rule 4: longest first
        for start in range(len(tokens) - length + 1):
            if any(consumed[start : start + length]):
                continue
            kinds = vocab.phrases.get(tokens[start : start + length])
            if kinds is None:
                continue
            span_kind, span_ids = _span_entry(kinds)
            span = tokens[start : start + length]
            matches.append(Match(span, span_kind, span_ids, WHOLE_PHRASE_SCORE))
            consumed[start : start + length] = [True] * length

    unknown: list[str] = []
    for token, used in zip(tokens, consumed, strict=True):
        if used or token in INTENT_WORDS or token in FILLER_WORDS or token.isdigit():
            continue
        fuzzy = _fuzzy(token, vocab)
        if fuzzy is None:
            unknown.append(token)
        else:
            matches.append(fuzzy)

    allergen_ids = frozenset().union(*(m.allergen_ids for m in matches))
    confidence = min((m.confidence for m in matches), default=0.0)
    kinds_present = {m.kind for m in matches}
    kind: Kind = next((kd for kd in _KIND_PRECEDENCE if kd in kinds_present), "AVOID_ALLERGEN")
    words = set(tokens)
    severity: Severity = (
        "STATED_ALLERGY"
        if words & ALLERGY_WORDS
        else "STATED_PREFERENCE"
        if words & PREFERENCE_WORDS
        else "UNSPECIFIED"
    )
    return Score(allergen_ids, confidence, kind, severity, tuple(matches), tuple(unknown))


def _restriction(raw_text: str, score: Score, threshold: float) -> Restriction:
    """Rule 6. The threshold gate. Below it: AMBIGUOUS and no allergen ids — never a guess."""
    if score.matched:
        if score.confidence >= threshold:
            return Restriction(
                kind=score.kind,
                allergen_ids=score.allergen_ids,
                raw_text=raw_text,
                resolution=Resolution.RESOLVED,
                severity_declared=score.severity,
            )
        resolution = Resolution.AMBIGUOUS
    elif score.unknown:
        resolution = Resolution.UNRESOLVABLE
    else:
        resolution = Resolution.AMBIGUOUS
    return Restriction(
        kind=score.kind,
        allergen_ids=frozenset(),
        raw_text=raw_text,
        resolution=resolution,
        severity_declared=score.severity,
    )


def normalize(raw_text: str, k: Knowledge, threshold: float = DEFAULT_THRESHOLD) -> Restriction:
    """22 §RestrictionNormalizer. ``threshold`` is ``Config.normalizer_threshold``."""
    return _restriction(raw_text, _score(raw_text, k), threshold)
