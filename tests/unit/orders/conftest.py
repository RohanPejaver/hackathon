"""Builds a ``Knowledge`` from ``config/knowledge/demo/*.yaml`` without importing
``src.knowledge`` (stream S2 owns that loader; the orders tests depend only on the shape of
``src.domain.Knowledge``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from src.domain import AllergenNode, IngredientRecord, Knowledge, MenuItemRecord

ROOT = Path(__file__).resolve().parents[3]
DEMO = ROOT / "config" / "knowledge" / "demo"


def _load(name: str) -> dict[str, Any]:
    data = yaml.safe_load((DEMO / name).read_text())
    assert isinstance(data, dict)
    return data


def load_demo_knowledge() -> Knowledge:
    taxonomy = _load("taxonomy.yaml")
    ingredients = _load("ingredients.yaml")
    menu = _load("menu_items.yaml")
    return Knowledge(
        knowledge_version=str(taxonomy["knowledge_version"]),
        allergens={
            a["id"]: AllergenNode(
                id=a["id"],
                display_name=a["display_name"],
                parents=list(a.get("parents", [])),
                regulatory_class=a.get("regulatory_class"),
                aliases=list(a.get("aliases", [])),
            )
            for a in taxonomy["allergens"]
        },
        ingredients={
            r["ingredient_id"]: IngredientRecord(
                ingredient_id=r["ingredient_id"],
                display_name=r["display_name"],
                aliases=list(r.get("aliases", [])),
                contains=frozenset(r.get("contains", [])),
                may_contain=frozenset(r.get("may_contain", [])),
                source=r["source"],
                verified_at=str(r["verified_at"]),
                verified_by_role=r["verified_by_role"],
            )
            for r in ingredients["ingredients"]
        },
        menu_items={
            m["item_id"]: MenuItemRecord(
                item_id=m["item_id"],
                ingredient_ids=list(m["ingredient_ids"]),
                required_zones=list(m["required_zones"]),
                station_id=m["station_id"],
            )
            for m in menu["menu_items"]
        },
    )


@pytest.fixture(scope="session")
def k() -> Knowledge:
    return load_demo_knowledge()
