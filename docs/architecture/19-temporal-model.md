# Temporal Model

Time is load-bearing here: the entire product distinguishes sequences that contain the same
events in different orders.

## Clocks

| Clock | Source | Used for |
|---|---|---|
| `t_occurred` | Station monotonic clock, captured at frame acquisition | **All reasoning.** Ordering, windows, staleness |
| `t_committed` | Log commit time | Latency measurement and debugging only |
| Wall clock | OS | Display and audit export only |

> **Invariant: no code in layers 6-11 may read a wall clock.** Time is injected as a `Clock`
> interface and, in replay, is driven entirely by `t_occurred` in the log. This is what
> makes replay bit-deterministic, and it is extremely painful to retrofit — it is enforced
> from P0 by a lint rule banning direct clock imports outside `runtime/`.

## Ordering and the reorder window

Perception can emit slightly out of order (variable inference latency across parallel
detectors). The log holds incoming events for `t_reorder` (default 500ms), sorts by
`t_occurred`, then commits with a gapless `seq`.

After commit, order is **final**. An event arriving later than `t_reorder` is committed at
the tail with `late: true` and flagged; the reducer processes it normally but the
observability layer surfaces late events because a rising late-rate is the leading indicator
of perception falling behind.

## "Did B happen after A, and could A have caused B?"

The system answers this **structurally, not heuristically**:

- `t(A) < t(B)` strictly, using `t_occurred`
- A and B share a carrier node
- No valid reset on that carrier in `(t(A), t(B))`

That conjunction *is* the pathway edge condition (`14`). There is no correlation window, no
"within N seconds" fuzz, and no learned causality. A reset at any point in between breaks
the chain regardless of how close in time the events were — which is the correct semantics
and also the reason the model needs no tuning parameter here.

## Windows

> **Values below are informative.** `engineering/31-configuration.md` is authoritative for
> defaults; this table exists to explain what each window *means*. If they disagree, `31`
> wins and this table is the defect.

| Window | Default | Purpose |
|---|---|---|
| `t_dwell` | 250ms | Minimum zone dwell to emit `ZONE_ENTRY` — rejects pass-throughs |
| `t_hysteresis` | 400ms | Contact must be absent this long before `CONTACT_END` — prevents flicker |
| `t_reorder` | 500ms | Log reorder buffer |
| `t_stale[kind]` | 20s / 120s / 300s / 600s | Epistemic decay (`13`) |
| `t_occlusion_max` | 3s | Occlusion beyond this -> `UNKNOWN`, not `STALE` |
| `station_recent_window` | 30m | Pessimistic closure scope |
| `t_escalate` | 20s | Tier 1 -> Tier 2 |
| `t_cooldown` | 120s | Post-assertion suppression |
| `t_abandon` | 15m | Ticket auto-void |

All are configuration (`31`), all are recorded in `CONFIG_LOADED`, and a replay uses the
recorded values — otherwise retuning a threshold would silently change what old fixtures
assert.

## Concurrent preparation

No temporal interleaving logic is required, because taint is carrier-held (`17`). Two
overlapping tickets share one carrier timeline; each ticket queries that timeline through
its own restriction filter.
