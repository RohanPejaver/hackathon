# Allergen Knowledge

## Why not a universal ingredient database

There isn't one that is correct for a given kitchen. The pesto in *this* shop has *this*
supplier's recipe. Knowledge is therefore **restaurant-scoped, versioned configuration**,
and the runtime depends only on an interface (`22`), never on a particular source.

## Three layers

### 1. Allergen taxonomy (a graph, not a list)

```
AllergenNode { id, display_name, parents: List<AllergenId>, regulatory_class? }
```

Ships with the Big-9 as roots; specific allergens hang beneath. Matching uses transitive
closure (`15`). **Grouping policy is data.** Whether `PINE_NUT` sits under `TREE_NUT` is a
per-restaurant configuration decision, defaulted to the conservative (broader) grouping,
because it is a domain policy question with legitimate disagreement and it must never
require a code change.

### 2. Ingredient -> allergen mapping

```
IngredientRecord {
  ingredient_id, display_name, aliases: List<str>,
  contains:    Set<AllergenId>,     # -> taint strength PRESENT
  may_contain: Set<AllergenId>,     # -> taint strength POSSIBLE
  source: SUPPLIER_LABEL | HOUSE_RECIPE | MANUAL,
  verified_at, verified_by_role
}
```

`contains` vs `may_contain` is preserved all the way through to the taint record and into
the alert copy, because "contains pine nuts" and "may contain pine nuts" warrant different
worker responses and collapsing them destroys information the kitchen already has.

Unknown ingredient -> `UNKNOWN_ALLERGEN_PROFILE`, which is treated as **possibly containing
any restricted allergen**. Fails conservative, routes to Tier 0.

### 3. Recipe -> required zones

```
MenuItemRecord { item_id, ingredient_ids, required_zones: List<ZoneId>, station_id }
```

This is what lets the Tier 0 precondition check know *which* carriers matter for *this*
ticket, instead of demanding a total station reset for every restricted order. Without it,
Tier 0 becomes "reset everything," which is expensive enough that workers would start
ignoring it — which would take the system's primary value with it.

## Versioning

Every knowledge bundle has a `knowledge_version`, stamped into `CONFIG_LOADED` and into
every `RiskAssessment`. A replay loads the version recorded in its log, so a knowledge
update cannot retroactively change what a past scenario should have concluded.

## Explicitly deferred

Supplier API integration, barcode/label OCR, automatic recipe extraction, cross-reactivity
modeling beyond the taxonomy graph. All are real; none are required to prove the thesis.
