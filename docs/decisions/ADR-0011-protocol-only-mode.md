# ADR-0011: PROTOCOL_ONLY is a supported mode, not an error path

**Status:** ACCEPTED

## Context
Vision will fail — occlusion, obstruction, lighting, hardware. The naive response is to stop
or to fail silently.

## Decision
On perception or reasoning failure the station enters `PROTOCOL_ONLY`: all carriers
`UNKNOWN`, Tier 0 fires on every restricted bind, Tier 1 disabled, existing Tier 2 holds
persist, UI plainly states vision is unavailable. Automatic recovery to `FULL` restores no
carrier trust until each is independently re-observed.

## Consequences
+ The product retains its primary value with zero perception
+ Gives the demo a truthful, rehearsed fallback
+ Makes the honest claim testable: most safety value is order-driven, not camera-driven
- Requires the UI to represent degradation as a first-class state

## Rationale
A safety layer that stops protecting people when a component fails is not a safety layer.
