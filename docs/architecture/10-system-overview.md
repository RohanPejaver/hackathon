# System Overview

## The one architectural idea

**The Observation Log is the spine. Everything downstream of it is a pure, deterministic
fold.**

```
                    PROBABILISTIC                 |            DETERMINISTIC
                                                  |
 Frames -> Detection -> Tracking -> Assembly  ==>  OBSERVATION LOG  ==>  Reduce -> Risk -> Policy -> UI
 (ephemeral)                                      |   (append-only,
                                                  |    versioned,
                                                  |    serializable)
```

Formally:

```
WorldState(t) = fold(reduce, ObservationLog[0..t], InitialState, Config)
RiskAssessment = f(WorldState, ActiveTickets, Knowledge, Config)     -- pure
Interventions  = g(RiskAssessment, AlertState, Config)               -- pure
```

Consequences that fall out **by construction** rather than by discipline:

- Deterministic replay is guaranteed, not aspirational
- The safety core is fully testable with zero camera hardware
- The evidence trace is free: every state mutation carries the event id that caused it
- Perception and reasoning can be built in parallel by different people
- The demo can be driven from a recorded log if live perception degrades

This is `decisions/ADR-0001`. Nearly every other decision serves it.

## Layers

| # | Layer | Responsibility | Produces | May depend on |
|---|---|---|---|---|
| 1 | **Sensing** | Physical station -> frames + timestamps | `Frame` (ephemeral, never persisted) | — |
| 2 | **Perception** | Frame -> detections in station coordinates | `Detection` (confidence-bearing) | sensing |
| 3 | **Tracking** | Detections -> stable entity identities over time | `Track` | perception |
| 4 | **Assembly** | Tracks -> discrete semantic events, with dwell/hysteresis/debounce | **`Event`** | tracking, `domain` |
| 5 | **Log** | Ordering, reorder window, commit, persistence | committed `Event` stream | `domain` |
| 6 | **State** | `(State, Event) -> State`. Carrier taint + epistemic status | `WorldState` | log, `domain` |
| 7 | **Knowledge** | Allergen taxonomy, ingredient map, recipes | resolution queries | config |
| 8 | **Orders** | Ticket intake, restriction normalization, binding lifecycle | `Ticket` | knowledge, `domain` |
| 9 | **Risk** | Pathway search over the temporal contact graph | `RiskAssessment` | state, knowledge, orders |
| 10 | **Policy** | Tier selection, alert identity, lifecycle, suppression | `Intervention` | risk |
| 11 | **Presentation** | Worker display, assertion capture, inspector | UI + `OPERATOR_ASSERTION` events | policy |
| 12 | **Observability** | Evidence trace, structured logs, replay export | traces | all (read-only) |

## The mandatory boundary

> **Layers 6-11 may not import layers 1-4. The only thing that crosses is a committed `Event`.**

Enforced mechanically by an import-lint rule in CI (`engineering/30-repository-layout.md`),
not by convention. A perception change must never be able to alter a safety decision except
by changing which events it emits.

This is what makes it possible for the system to say *"perception believes the pesto
container was handled, confidence 0.87"* without that sentence being able to reach the
conclusion *"the customer's food is contaminated."* Confidence is thresholded into an
`EvidenceGrade` at layer 4 and never reappears as a float in layers 6-11 (`ADR-0004`).

## Feedback edges (the only ones permitted)

1. **Worker assertion** — layer 11 emits `OPERATOR_ASSERTION` into layer 5. Human
   corrections are ordinary events, replayable and auditable. Not a side channel.
2. **Mode change** — layer 12 health monitoring emits `STATION_MODE_CHANGED` into layer 5
   (e.g. entering `PROTOCOL_ONLY`). Mode is state, so it must be an event.

No other backward edge exists. There is no path by which risk output influences perception.

## Runtime modes

| Mode | Trigger | Behavior |
|---|---|---|
| `FULL` | Normal | All tiers active |
| `PROTOCOL_ONLY` | Vision unavailable / reasoning fault | All carriers `UNKNOWN`; Tier 0 on every restricted bind; Tier 1 disabled; existing Tier 2 holds persist; UI states vision is down |
| `REPLAY` | Scenario or recorded log | Layers 1-4 replaced by a log reader; layers 5-12 byte-identical |
| `CALIBRATION` | Setup | Zone authoring; no tickets may bind |

`PROTOCOL_ONLY` is a **supported product mode, not an error path.** It delivers the
majority of the safety value with no perception at all, which is both the honest assessment
of where value sits and the demo's safety net.
