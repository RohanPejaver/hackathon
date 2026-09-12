# Perception Contract

Defines what perception **must produce**. It deliberately says nothing about how.

## Obligations

Perception must emit, into the log, with `t_occurred` in station time:

1. `ZONE_ENTRY` / `ZONE_EXIT` for tracked entities against configured zones
2. `CONTACT_BEGIN` / `CONTACT_END` between tracked carriers
3. `CARRIER_OBSERVABILITY_CHANGED` whenever a carrier becomes unobservable or re-observed
4. `TRACK_IDENTITY_SUSPECT` whenever it cannot distinguish two carriers
5. `GLOVE_CHANGE`, `TOOL_SWAP`, `SURFACE_SWAP`, `SURFACE_WIPE`, `WASH_CYCLE` where detectable
6. `HEALTH_DEGRADED` on frame starvation, exposure failure, or occlusion of the station

## Obligations of honesty (the important half)

- Perception must report **not knowing**. Failing to emit
  `CARRIER_OBSERVABILITY_CHANGED` when a carrier is lost is a **more serious defect** than a
  false detection, because the safety core's conservatism depends entirely on being told.
- Perception must never suppress an observation because it seems implausible. Plausibility
  is the reasoning layer's concern.
- Every emitted event carries an honest `confidence` (metadata) and a `grade` derived from
  configured thresholds.

## Grade assignment

```
confidence >= threshold_observed[type]  -> OBSERVED
confidence >= threshold_inferred[type]  -> INFERRED
otherwise                                -> not emitted
```

Thresholds are per-event-type configuration, tuned against the evaluation fixtures (`34`),
and recorded in `CONFIG_LOADED`. **Below-threshold observations are dropped, not
downgraded** — because an unbounded stream of low-grade events would inflate the pessimistic
closure into permanent noise. The safety net for what perception drops is epistemic
degradation, not weak events.

## Non-obligations

Perception is **not** responsible for: identifying substances, knowing allergens, knowing
which ticket is active, deciding whether contamination occurred, judging cleaning efficacy,
or any tier decision. If a perception module imports from `state/`, `risk/`, `policy/`, or
`orders/`, the import lint fails the build (`30`).

## Degradation ladder

| Condition | Emission |
|---|---|
| Entity occluded < `t_occlusion_max` | nothing; tracker interpolates |
| Occluded >= `t_occlusion_max` | `CARRIER_OBSERVABILITY_CHANGED -> UNKNOWN` |
| Two carriers confusable after occlusion | `TRACK_IDENTITY_SUSPECT` |
| Frame rate below floor / camera fault | `HEALTH_DEGRADED` -> runtime enters `PROTOCOL_ONLY` |
