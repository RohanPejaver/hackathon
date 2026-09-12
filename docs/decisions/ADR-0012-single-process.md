# ADR-0012: Single process; no microservices

**Status:** ACCEPTED

## Context
One station, one camera, one operator.

## Decision
One process. Multi-station aggregation, if ever built, is a read-only consumer of exported
event logs rather than a decomposition of the runtime.

## Consequences
+ No serialization boundaries, partial failure, or clock skew to undermine determinism
+ Dramatically simpler to run, test, and demo
- Would need revisiting for a genuine multi-station deployment

## Rationale
Distribution buys scaling we do not need at the cost of the determinism we depend on.
