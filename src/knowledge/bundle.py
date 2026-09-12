"""Load a versioned knowledge bundle (18) from YAML into the domain `Knowledge` model.

This is the only I/O in the reasoning core: static configuration, read once. The layout is
`<path>/taxonomy.yaml`, `<path>/ingredients.yaml`, `<path>/menu_items.yaml` exactly as in
`config/knowledge/demo/`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.domain import AllergenNode, IngredientRecord, Knowledge, MenuItemRecord


def _read(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: top level must be a mapping")
    return data


def load_bundle(path: str | Path) -> Knowledge:
    root = Path(path)
    taxonomy = _read(root / "taxonomy.yaml")
    ingredients = _read(root / "ingredients.yaml")
    menu = _read(root / "menu_items.yaml")
    return Knowledge(
        knowledge_version=str(taxonomy["knowledge_version"]),
        allergens={
            a["id"]: AllergenNode(
                id=a["id"],
                display_name=a["display_name"],
                parents=list(a.get("parents") or []),
                regulatory_class=a.get("regulatory_class"),
                aliases=list(a.get("aliases") or []),
            )
            for a in taxonomy["allergens"]
        },
        ingredients={
            i["ingredient_id"]: IngredientRecord(
                ingredient_id=i["ingredient_id"],
                display_name=i["display_name"],
                aliases=list(i.get("aliases") or []),
                contains=frozenset(i.get("contains") or []),
                may_contain=frozenset(i.get("may_contain") or []),
                source=i["source"],
                verified_at=str(i["verified_at"]),
                verified_by_role=i["verified_by_role"],
            )
            for i in ingredients["ingredients"]
        },
        # CONTRACT-GAP: menu_items.yaml carries display_name; MenuItemRecord has no such
        # field, so it is dropped here.
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
