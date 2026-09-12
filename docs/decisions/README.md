# Architecture Decision Records

## When to write one

See the threshold in `engineering/38-workflow.md`. Summary: layer/interface changes, changes
to what the system claims, invariant changes, core dependencies, expensive-to-reverse
choices, and contested calls whose reasoning would otherwise be lost.

Not for naming, file placement, or anything reversible in an hour.

## Format

`context -> alternatives considered -> decision -> consequences -> rationale`.
Status: `PROPOSED | ACCEPTED | SUPERSEDED BY ADR-NNNN`. ADRs are **immutable** once accepted
— supersede, never edit.

## Index

| ADR | Title | Status |
|---|---|---|
| 0001 | Observation log as the architectural spine; reasoning is a pure fold | ACCEPTED |
| 0002 | Raw detections may not drive alerts; events are the sole boundary | ACCEPTED |
| 0003 | No learned model between the event log and an intervention | ACCEPTED |
| 0004 | Confidence is thresholded into a grade at the boundary; never a float downstream | ACCEPTED |
| 0005 | Low confidence lowers the intervention tier; it never lowers the alert bar | ACCEPTED |
| 0006 | Ticket-to-station binding is an explicit human action, never inferred | ACCEPTED |
| 0007 | Identity from configured zones, not from food recognition | ACCEPTED |
| 0008 | Taint is carried by carriers, never by dishes or tickets | ACCEPTED |
| 0009 | Wiping is not a valid reset | ACCEPTED |
| 0010 | No worker or customer identity in the data model | ACCEPTED |
| 0011 | `PROTOCOL_ONLY` is a supported product mode, not an error path | ACCEPTED |
| 0012 | Single process; no microservices | ACCEPTED |

## Pending / deferred decisions

Recorded so they are not silently resolved by whoever writes the code first:

| Question | Owner doc | Resolution path |
|---|---|---|
| Correct value of `max_hops` | `14` | Config now; `experiments/EXP-001` |
| Should `PINE_NUT` group under `TREE_NUT` by default? | `18` | Restaurant config; default conservative |
| Depth signal to disambiguate reach-over vs reach-in | `20` | `experiments/EXP-002` |
| Learned action segmentation vs. fixed dwell thresholds | `15` | `experiments/EXP-003`; deterministic until evidence |
