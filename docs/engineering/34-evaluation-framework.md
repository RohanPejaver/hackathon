# Evaluation Framework

## The distinction that governs everything

> "The model recognized the ingredient correctly" is **not** the metric.
> "The system produced a timely, correct-tier intervention before the food could be served"
> is.

Perception metrics are diagnostic. Intervention metrics are the verdict.

## Primary metrics

### 1. Intervention Recall (IR) — the headline number
Fraction of scripted hazard scenarios in which the system produced a **correct-tier**
intervention **before** the target item reached `COMPLETE`.
`IR = correct_timely_interventions / total_hazard_scenarios`. **Target: >= 0.90 on the
scenario suite.**

### 2. Silent Miss Rate (SMR) — the number that matters most
Fraction of hazard scenarios where the system produced **no intervention** *and* asserted
the relevant carriers were `TRACKED`-clean.

This is the only genuinely bad outcome. A miss where the system had already said
"unverified" and fired Tier 0 is **not** a silent miss — declining to claim is
architecturally distinct from being wrong (`product/03`, scenario E).
**Target: 0 on the scenario suite. Any non-zero SMR blocks the phase gate.**

### 3. Nuisance Rate (NR)
Tier 1 + Tier 2 alerts per hour of normal, non-hazard preparation.
**Tier 0 is excluded by definition** — it is designed to fire liberally at ~8 seconds of
cost, and counting it as nuisance would create pressure to weaken the mechanism that carries
most of the safety value. **Target: < 1.0/hr.**

### 4. Intervention Lead Time
Seconds between alert emission and the moment the item would otherwise have been released.
Larger is better; negative is a failure regardless of correctness.
**Target: p50 > 20s, p05 > 0s.**

### 5. Tier 0 Compliance Rate
Fraction of Tier 0 prompts whose required resets were completed (observed or asserted) before
`TICKET_PREP_STARTED`. **This is the closest thing to a real-world outcome metric the system
has** — Tier 0 carries most of the safety value, and a prompt that is routinely ignored
carries none of it. **Target: > 0.80.** Falling compliance is the earliest signal that the
system has become noise.

### 6. Pessimistic Closure Rate
Fraction of Tier 0 prompts triggered **only** by `STALE`/`UNKNOWN` epistemic status rather
than by actual recorded taint. Directly instruments assumption **A6** in `PROJECT_STATE.md`,
the project's highest open risk. **Target: < 0.40.** Above that, `t_stale` is too aggressive
or camera placement is producing avoidable occlusion, and Tier 0 fatigue is imminent.

## Secondary — perception (diagnostic only)

Event-level precision/recall per event type; identity-consistency (switches per minute);
**occlusion-reporting recall** — of intervals where a carrier was truly unobservable, the
fraction perception correctly reported. *This last one is the most important perception
metric in the system*, because the safety core's conservatism depends entirely on being told
when it is blind. A pipeline with excellent detection and poor occlusion reporting is more
dangerous than the reverse.

## Secondary — reasoning

Carrier-state accuracy vs. annotated ground truth (taint set + epistemic status); pathway
reconstruction F1; tier-assignment accuracy.

## Secondary — UX and system

Time-to-comprehension and taps-to-resolve per alert tier (**target: <= 2 taps**, measured on
teammates, not self); reducer latency p99 (**< 50ms**); end-to-end contact-to-alert latency
(**< 1.5s**); frame-to-event latency; uptime in `FULL` mode.

## Benchmark sets

| Set | Contents | Used for |
|---|---|---|
| `scenarios/` A-M | Hand-authored event logs | IR, SMR, tier accuracy, determinism |
| `data/fixtures/video/` | 10-20 recorded prep sequences, annotated | Perception metrics |
| `data/fixtures/normal/` | 30+ min of ordinary prep, no hazards | Nuisance Rate |
| Adversarial | Occlusion, identity switch, camera fault | Degradation behavior |

The **normal-prep set is not optional.** Without it, every threshold optimizes toward
sensitivity, and the resulting system is the one that gets ignored in a real kitchen.

## Acceptance

A phase gate requires metrics **recorded as artifacts** in `data/eval/<date>/`, not
asserted in prose. `PROJECT_STATE.md` links the artifact that justifies each `VERIFIED`.
