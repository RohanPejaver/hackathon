# Failure Modes

## Governing principle

> Every perception failure maps to an **epistemic degradation**; every epistemic degradation
> maps to the **cheapest intervention**.

That single rule contains most of this taxonomy. The system is designed so that being wrong
is inexpensive, rather than trying to be right more often.

## Taxonomy

Legend — **D**etection, **C**onsequence, **Ct**ainment, **F**allback, **L**og, **R**ecovery.

### P1 Missed detection (contact occurred, no event emitted)
- **D** Not directly detectable at runtime. Measured offline against annotated fixtures (`34`).
- **C** Taint not recorded -> potential silent miss.
- **Ct** Tier 0 fires on *preconditions*, not on detections, so the most common hazard
  (starting a restricted ticket on a dirty station) is caught by **policy**, which has no
  miss rate. Pessimistic closure covers unobserved periods.
- **F** `PROTOCOL_ONLY` if misses correlate with a health signal.
- **L** Offline: event-level recall per fixture.
- **R** Retune thresholds; add fixture; re-run gate.

### P2 False detection (event emitted, nothing happened)
- **D** Offline precision; runtime proxy = alert-per-hour rate.
- **C** Spurious taint -> Tier 0 prompt (8s) or, if `OBSERVED`, a Tier 1 interrupt.
- **Ct** Grade thresholds; `t_dwell`; hysteresis; episode collapsing.
- **F** Worker taps "Already clean" -> `OPERATOR_ASSERTION`, one tap, logged.
- **L** Assertion rate per carrier is the nuisance signal; a spike localizes a bad zone.
- **R** Re-author the zone polygon; raise `t_dwell`.

### P3 Identity switch (tracker swaps two carriers)
- **D** Implausible motion, re-entry after occlusion, overlapping bounding regions.
- **C** **Taint attributed to the wrong carrier — the most dangerous perception failure**,
  because it can make a dirty tool appear clean.
- **Ct** `TRACK_IDENTITY_SUSPECT` -> **pessimistic merge** of both taint sets, both -> `STALE`.
  Never a silent reassignment.
- **F** Merge makes both carriers suspect -> Tier 0 on next bind.
- **L** Suspect rate; merged-carrier pairs.
- **R** Increase visual distinctiveness of tools (colour-coded allergen equipment, which
  operators already use); add a fixture.

### P4 Occlusion
- **D** Track lost > `t_occlusion_max`.
- **C** Unobserved interval.
- **Ct** -> `UNKNOWN` -> pessimistic closure -> Tier 0. **This is scenario H and it is a
  designed-for path, not an error.**
- **L** Occlusion duration histogram per carrier; a persistently occluded zone is a camera
  placement defect, surfaced in the inspector.

### P5 Camera fault / obstruction / lighting collapse
- **D** Frame starvation, exposure statistics, static-frame detection.
- **C** Total loss of perception.
- **Ct/F** `HEALTH_DEGRADED` -> `PROTOCOL_ONLY`. **Tier 0 continues; the product retains
  its primary value.** UI states plainly that vision is unavailable.
- **R** Automatic return to `FULL` after `t_recover` of healthy frames, via
  `STATION_MODE_CHANGED`. All carriers remain `UNKNOWN` until individually re-observed —
  recovery never restores trust it did not earn.

### P6 Unknown ingredient in a zone
- **C** Cannot resolve allergens.
- **Ct** `UNKNOWN_ALLERGEN_PROFILE` — treated as possibly containing **any** restricted
  allergen. Tier 0.
- **R** Setup-time validation refuses to start a station whose zone contents are unresolvable
  against the knowledge bundle, so this is caught at calibration rather than service.

### P7 Missing / ambiguous order information
- **Ct** `AMBIGUOUS` -> binding blocked -> resolution request. Scenario G. **Never guess.**

### P8 Ambiguous action (was that a wipe or a swap?)
- **Ct** Below-threshold reset events are **not emitted**. An unrecognized reset therefore
  leaves taint in place -> a prompt the worker can clear in one tap.
- **Rationale** A missed reset costs 8 seconds; a falsely-detected reset silently clears real
  contamination. The asymmetry dictates the threshold direction, and it must be documented
  because it looks like over-conservatism until you see why.

### P9 Stale state
- **Ct** Epistemic axis (`13`); `t_stale` per carrier kind.

### P10 Corrupted / schema-invalid event
- **Ct** Rejected at `append`, `HEALTH_DEGRADED` emitted, runtime continues. A malformed
  perception event may never crash the safety core.
- **R** Rejected events are written to a quarantine log for offline diagnosis.

### P11 Reducer / risk-engine exception
- **Ct** Catch at the runtime boundary -> `PROTOCOL_ONLY`, existing Tier 2 holds **persist**,
  incident logged with the triggering `event_id` for deterministic reproduction.
- **Never fail open to silence.** A crashed safety core that shows a clean screen is the
  worst possible outcome; the UI must visibly state that reasoning is down.

### P12 Config / knowledge mismatch
- **D** Checksum + version validation at load.
- **Ct** Refuse to enter `FULL`; remain in `CALIBRATION` with a clear error. Safety-critical
  config never loads partially.

## Failure-mode coverage matrix

Every row above has a corresponding fixture in `/scenarios/` or an offline metric in `34`.
`engineering/33-testing-strategy.md` asserts the mapping is total — a failure mode with no
test is itself a tracked defect.
