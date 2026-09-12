# Configuration

## Principle

Anything a restaurant, a deployment, or an experiment would legitimately change is
configuration. Anything that changes the **meaning** of a safety claim is code, reviewed,
and tested.

| In config | In code |
|---|---|
| Zone polygons, contents, kinds | Contact predicate semantics |
| Allergen taxonomy + grouping policy | Closure algorithm |
| Ingredient -> allergen maps, recipes | Grade lattice |
| All time windows (`19`) | Reset validity rules (`14`) |
| Grade thresholds per event type | Tier selection logic |
| `max_hops`, pessimistic-closure window | Pathway definition |
| Alert copy templates | Prohibited-claim lint |
| Camera/runtime parameters | Layer boundaries |

`SURFACE_WIPE` being a non-reset is **code**, not config. It is a safety semantic, and it
must not be switchable by editing a YAML file.

## Hierarchy

```
defaults.yaml  <-  profiles/<profile>.yaml  <-  station/<id>.yaml  <-  env overrides
                                                                       (dev only)
```

Later layers override earlier ones. `prod` and `demo` profiles **reject** env overrides, so
a demo cannot be accidentally running with a stray local variable.

## Validation

At startup, before entering `FULL`:
- schema validation of every layer
- referential integrity: every `zone.contents` ingredient resolves in the knowledge bundle;
  every `menu_item.required_zones` exists in the station map
- range checks on all time windows
- checksum of station + knowledge bundles

Any failure -> remain in `CALIBRATION` with a specific error. **Safety-critical config never
loads partially** (`23` P12).

## Versioning

`config_version` and `knowledge_version` are emitted in `CONFIG_LOADED` at the head of every
session log. Replay loads the versions recorded in the log, not current files — so retuning
a threshold cannot silently change what an old fixture asserts.

## Zone authoring rule (asymmetric, from `20`)

Author `INGREDIENT` zones **generously** (a false contact costs 8 seconds) and `CLEAN_STOCK`
zones **conservatively** (a false reset silently clears real taint). The asymmetry follows
from the cost structure and is easy to get backwards.
