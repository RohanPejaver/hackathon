# ADR-0002: Raw detections may not drive alerts

**Status:** ACCEPTED

## Context
Coupling vision output directly to safety output means any perception change can silently
alter safety behavior, and no safety claim can be stated independently of a model version.

## Alternatives
1. Detections feed risk logic directly.
2. **A discrete, versioned semantic event layer between them.**

## Decision
Option 2. Detections and tracks are transient and never cross the log boundary. Layers 6-11
may not import layers 1-4; enforced by import lint in CI.

## Consequences
+ "Perception believes X with 0.87 confidence" can never itself conclude "the food is
  contaminated"
+ Perception is swappable without re-verifying the safety core
- An assembly layer must exist (dwell, hysteresis, episodes)

## Rationale
This is the separation the product thesis depends on. Left to convention it decays within
days, so it is mechanically enforced.
