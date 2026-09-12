# Experiments

Experimental work is separated from production architecture so that testing a competing
approach cannot destabilize the core.

**Rule:** `experiments/` may import `src/`. `src/` may **never** import `experiments/`
(CI-enforced, `30`). An experiment that graduates is reimplemented in `src/` behind the
existing interface (`22`), not promoted in place.

## Protocol

Each experiment is one file, `EXP-NNN-slug.md`:

```
Hypothesis    — a falsifiable statement
Configuration — exact config + versions
Dataset       — which fixtures/scenarios, with checksums
Metric        — which metric from `34` decides it, and the threshold, stated BEFORE running
Result        — numbers, artifact path
Conclusion    — ACCEPT | REJECT | INCONCLUSIVE, and what changes as a result
```

The metric and threshold are recorded **before** the run. An experiment whose success
criterion is written afterward is not an experiment.

## Open experiments

| Id | Hypothesis | Decides |
|---|---|---|
| **EXP-001** | `max_hops = 2` vs `3` materially changes Intervention Recall and Nuisance Rate | Default in `14` |
| **EXP-002** | A depth or height signal meaningfully separates reach-over from reach-in | Whether `20`'s known 2D limitation needs addressing |
| **EXP-003** | Learned action segmentation beats fixed dwell thresholds on event-level F1 | Whether `15`'s deterministic-first stance should change |
| **EXP-004** | Glove-change detection is reliable enough to be `OBSERVED` rather than `ASSERTED` | Grade assignment in `12` |

EXP-004 matters more than it looks: if glove-change detection cannot reach `OBSERVED` grade,
Tier 0 checklists cannot self-tick, and demo beat 4 (`37`) loses its payoff.
