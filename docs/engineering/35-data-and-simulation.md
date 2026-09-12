# Data and Simulation Strategy

Designed before model selection. The guiding question is not "how do we get a big dataset"
but "what is the smallest dataset that proves the thesis."

## What each layer needs

| Layer | Data | Volume | Source |
|---|---|---|---|
| Reasoning core | Structured event logs | ~15 fixtures | **Hand-authored.** No video required. |
| Knowledge | Taxonomy + ~25 ingredients + ~8 menu items | 1 bundle | Hand-authored |
| Zone/contact detection | Annotated overhead video | 10-20 sequences, 30-90s each | **Self-recorded** |
| Reset detection (glove change) | Annotated clips | ~40 glove-change instances | Self-recorded |
| Nuisance measurement | Normal prep, unannotated except hazard-free label | 30+ min | Self-recorded |

**The entire safety core requires zero video.** That is the point of the event-log boundary
and it is what makes P1 completable in hours.

## Annotation schema

```
VideoAnnotation {
  clip_id, station_config_version,
  events: List<{ t_ms, type, participants, zone_id?, ground_truth: true }>,
  occlusion_intervals: List<{ carrier_id, t_start, t_end }>,
  hazard_label: NONE | DIRECT | TOOL | SURFACE | BACK_CONTAMINATION
}
```

Annotation is at the **event** level, not the frame level. Frame-level labeling is an order
of magnitude more work and the contract (`21`) is defined in events, so frame labels would
not be the thing under test.

`occlusion_intervals` must be annotated even though it is tedious — it is the ground truth
for the occlusion-reporting metric (`34`), which is the perception metric that matters most.

## Simulation: what to simulate, what to record

**Simulate (hand-authored event logs):** all reasoning scenarios, temporal edge cases, hop
limits, concurrency, ambiguity, mode changes, alert storms. These are *combinatorial* and
cheap in text, expensive on video.

**Record (real video):** zone-contact geometry, occlusion realism, glove-change appearance,
lighting. These are *perceptual* and cannot be faked convincingly.

**Do not build a 3D synthetic kitchen renderer.** The sim-to-real gap for hands and
specular surfaces would consume the entire build window and produce a perception model that
works only in simulation. Recorded fixtures of the actual demo station are both cheaper and
more representative. Recorded here because "let's make a simulator" is the most seductive
wrong turn available on this project.

## Minimum viable dataset

- 13 hand-authored scenario fixtures (A-M)
- 1 knowledge bundle, 1 station config
- 12 annotated video clips covering: clean prep, direct transfer, tool transfer, surface
  transfer, back-contamination, glove change, tool swap, wipe, occlusion, identity-confusion,
  two concurrent tickets, camera obstruction
- 30 minutes of normal prep for Nuisance Rate

That is a one-afternoon recording session with a folding table and an overhead phone mount.
