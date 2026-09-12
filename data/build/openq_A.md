# Device A open questions and channel notice

## CHANNEL: CONTRACT FREEZE BLOCKED — 2026-09-12

Device B: do not bind to Python types yet. FREEZE-1 and HANDSHAKE-2 have NOT been published. Continue independently owned harness/content work. P0 contract review identified Q1–Q4 below. No locked specification or B-owned path has been edited. This notice is transported through origin/main because no Device B task is visible to this Codex host. Delivery/read acknowledgment is not confirmed.

## Q1 — Policy inputs omit the lifecycle needed to choose a tier [BLOCKED]

Readings: `22-interfaces.md` § InterventionPolicy accepts only assessments, AlertState and cfg. `15-risk-engine.md` § Output lists RiskAssessment fields without ticket lifecycle. `15` § Tier selection requires IN_PREP versus COMPLETE. Two otherwise identical assessments for a newly observed pathway require different output based on an input the policy does not receive; AlertState cannot provide the lifecycle of a previously unseen ticket.

Recommended proposal: document `ticket_lifecycle` on RiskAssessment, and fully specify AlertCommand fields including explicit operator resolution provenance. Keep evaluate's registered parameter list if that payload amendment is approved. This changes a shared contract and must be agreed before freeze. Applied default: stop the policy/assessment contract workstream; no field invented and no code written.

## Q2 — EventLog draft ingestion/reorder commitment contract [BLOCKED]

Readings: `22` § EventLog says `append(e: Event) -> Seq`; § EventSink says DraftEvent lacks seq/t_committed and the log assigns them at append. `19` § Ordering and the reorder window requires buffering and sorting before a final gapless seq is assigned. The registry provides no draft-ingestion/drain operation or injected-time signature for finishing a quiet reorder window. Committing every append immediately would not satisfy the reorder requirement; returning a provisional final sequence could violate immutable ordering.

Recommended proposal: explicitly define the pending-draft ingestion, event-time/commit-time injection and reorder drain API, or document how the existing synchronous append contract handles those requirements without an added method. Applied default: do not invent a flush/drain interface; stop EventLog freeze pending the registry owner's decision. This is a required-signature gap under build prompt §0/§3.3.

## Q3 — Snapshot vocabulary and shape [BLOCKED for Handshake 2]

Readings: build prompt §1.5 requires UNOBSERVED and SUSPECT carriers. `13-state-model.md` § Epistemic status defines TRACKED, STALE, UNKNOWN; identity suspicion is an event and pessimistic merge, not a fourth epistemic value. `22` names StationSummary but never defines its wire fields.

Recommended proposal: retain the three canonical epistemic values; represent requested examples using UNKNOWN plus a STALE carrier with an identity-suspect evidence trace, and agree the StationSummary wire payload explicitly. Applied default: no invented enum members, no example/schema published as frozen. This is not a unilateral remapping of the requested handshake.

## Q4 — Incomplete event payload/catalog definitions [BLOCKED for complete freeze]

Readings: `12-event-model.md` lists ticket/system/alert event names but omits their detailed required fields; `17` requires TICKET_ITEM_SUBSTITUTED, absent from `12`; `16` requires a logged suppression event, while `12` has no suppression event type. `26` requires dismiss/hold resolution provenance that is not specified in that catalog. `22` names WorkerAction, AlertCommand and StationSummary without field schemas.

Recommended proposal: have the specification owner complete the event payloads and decide whether suppression/dismissal is a distinct event or a documented ALERT_UPDATED payload. Applied default: do not add new event types or publish a guessed cross-device schema. Adding an event requires the `38` documentation-maintenance procedure; A is forbidden from performing those doc edits.

## Q5 — Tier escalation conflicts [OPEN; precedence default recorded]

Readings: `13` § Grade lattice permits INFERRED/ASSERTED to Tier 1; `16` § Escalation sends unmet Tier 0 preconditions to Tier 1 when prep starts. `ADR-0005` and product `02` require weak evidence to remain at the cheapest tier and Tier 1/2 to mean observed evidence. `16` also adds an unacknowledged 20s escalation condition whereas `15` and scenario C require a hold on unresolved completion.

Recommended/default: follow ADR-0005 and product scenarios: weak evidence never escalates beyond Tier 0; observed unresolved pathways produce a hold at completion. Applied only as a ledger/review default; no implementation exists. If the specification owner requires both contradictory behaviors, stop this demo-critical path rather than choose silently.

## Q6 — Wipe bookkeeping conflicts [RESOLVED DEFAULT]

Readings: `13` § Transition table records last_wiped_at; `12` declares SURFACE_WIPE nonmutating; `33` explicitly requires no state change and build prompt scenario J says changes nothing. ADR-0009 requires recording and clearing nothing.

Default: record the event in the log; derive the UI explanation from the log instead of mutating reducer state. No implementation yet. This satisfies audit visibility without weakening scenario J.

## Q7 — Configuration defaults absent from authoritative home [OPEN]

Readings: `13`/`19` identify `31-configuration.md` as the only authoritative defaults table, but that file has no numeric defaults table. `19` gives informative windows without mapping every carrier kind (including FOOD); raw grade and normalizer thresholds are unspecified.

Recommended/default: require explicit validated config values until the owner publishes defaults; reuse documented informative values only after agreement with B. Do not silently invent threshold values. Existing PROJECT_STATE assumptions A1 (max_hops), A3 (glove detector) and A6 (closure noise) remain tracked there and are not new discoveries.

## Q8 — Seeded scenario taint lacks full causal records [OPEN]

Readings: `36` initial_state example supplies grade/hops only; `11` requires every taint's source_event_id to exist in the log.

Recommended/default: author fixture histories with explicit acquisition events rather than unsupported initial taints; ask the specification owner how shorthand initial-state provenance is to be expanded if supporting that shorthand is required. No scenario parser has been implemented.

## Already resolved by the two-device build prompt

1. **Content ownership:** B owns all config content, A owns knowledge code and scenarios. This overrides `40` Session 1 config/knowledge ownership; exclusive file ownership avoids collisions.
2. **Gate versus start:** `38` prerequisites govern gates, `39` concurrency governs starts after frozen schemas. A4 still waits until reducer compiles.
3. **Data ignore exceptions:** track data/build and data/eval while ignoring recordings. The build prompt's literal `data/` plus child negations cannot reopen children of an excluded directory in Git. Recommended implementation for B: ignore `data/*`, then unignore build/ and eval/, or explicitly reopen parent data/. A does not edit .gitignore.
4. **Branch deviation:** both devices use main per explicit prompt, overriding `40`'s branch split. Never force-push; stage only owned paths.

## Assumptions reaching code

None. No implementation code has been written. No additional dependencies, speculative subsystem interfaces, or post-freeze changes have been introduced.
