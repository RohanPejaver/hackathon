"""Read-only query surface over a `Knowledge` bundle (22 §KnowledgeProvider, 18)."""

from __future__ import annotations

from src.domain import Knowledge

UNKNOWN_ALLERGEN_PROFILE = "UNKNOWN_ALLERGEN_PROFILE"


def matches(taint_allergen: str, restricted: frozenset[str]) -> bool:
    """Does a taint of `taint_allergen` fall inside `restricted` (a closure set)?

    18: an unknown ingredient profile is treated as possibly containing any restricted
    allergen, so it matches every non-empty restriction.
    """
    if not restricted:
        return False
    return taint_allergen == UNKNOWN_ALLERGEN_PROFILE or taint_allergen in restricted


class KnowledgeProvider:
    def __init__(self, k: Knowledge) -> None:
        self._k = k
        self._children: dict[str, list[str]] = {}
        for node in k.allergens.values():
            for parent in node.parents:
                self._children.setdefault(parent, []).append(node.id)
        self._alias_index: dict[str, str] = {}
        for ing in k.ingredients.values():
            for text in (ing.ingredient_id, ing.display_name, *ing.aliases):
                self._alias_index.setdefault(text.strip().lower(), ing.ingredient_id)

    def allergens_for(self, ingredient_id: str) -> tuple[frozenset[str], frozenset[str]]:
        rec = self._k.ingredients.get(ingredient_id)
        if rec is None:
            return frozenset({UNKNOWN_ALLERGEN_PROFILE}), frozenset()
        return rec.contains, rec.may_contain

    def closure(self, allergen_id: str) -> frozenset[str]:
        """self ∪ ancestors ∪ descendants over the `parents` graph (15 §Allergen matching).

        Siblings are not included: closure(PINE_NUT) is {PINE_NUT, TREE_NUT}, not ALMOND.
        """
        allergens = self._k.allergens
        if allergen_id not in allergens:
            return frozenset({allergen_id})
        out = {allergen_id}
        stack = [allergen_id]
        while stack:
            current = stack.pop()
            for parent in allergens[current].parents if current in allergens else ():
                if parent not in out:
                    out.add(parent)
                    stack.append(parent)
        stack = [allergen_id]
        while stack:
            current = stack.pop()
            for child in self._children.get(current, ()):
                if child not in out:
                    out.add(child)
                    stack.append(child)
        return frozenset(out)

    def zones_for(self, item_id: str) -> list[str]:
        rec = self._k.menu_items.get(item_id)
        return list(rec.required_zones) if rec is not None else []

    def resolve_alias(self, text: str) -> str | None:
        return self._alias_index.get(text.strip().lower())

    def version(self) -> str:
        return self._k.knowledge_version
