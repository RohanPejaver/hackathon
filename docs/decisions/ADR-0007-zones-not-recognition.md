# ADR-0007: Identity from configured zones, not food recognition

**Status:** ACCEPTED

## Context
Recognizing pesto from pixels is open-set, unreliable, and fails on visually identical
substances (almond vs. sunflower butter).

## Decision
Ingredient identity comes from a one-time station map: zone polygon -> contents -> allergens.
Perception only determines that a tracked entity entered a polygon and dwelled.

## Consequences
+ Converts open-set recognition into closed-set geometry; dramatically more robust
+ Requires per-station calibration and disciplined bin placement
- Moving a bin without recalibrating is a silent hazard -> mitigated by config checksums and
  startup validation (`31`)

## Rationale
The kitchen already organizes itself spatially. The architecture should exploit that rather
than re-derive it from pixels.
