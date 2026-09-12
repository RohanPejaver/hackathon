# Open Questions & Assumptions — Device B

Every `[ASSUMPTION]` that reaches code is also marked inline `# ASSUMPTION: <what and why>`.
Cross-reference: `docs/PROJECT_STATE.md` §10 tracks A1–A6; none below duplicates those.

## Resolved ownership collisions (adopted from BUILD_B §1.4 — not relitigated)

| id | conflict | applied default |
|---|---|---|
| OQ-B1 | `40` gives `config/knowledge/` to Core; `39` §8 gives content to Stream D | **B owns all of `config/` (content); A owns `src/knowledge/` (code) and `scenarios/`.** |
| OQ-B2 | `38` P3 prereq = P2; `39` §8 starts streams at hour 2 on schemas alone | `38` states *gate* prerequisites, `39` states *start* conditions. Start early, gate in `38`'s order. |
| OQ-B3 | `40` `.gitignore` ignores all of `data/`; handoff + evidence live there | `.gitignore` = `data/` + `!data/build/` + `!data/eval/`. Recordings/frames stay ignored. |

## Open questions (two readings, applied default, reasoning)

| id | question | readings | applied default | reasoning |
|---|---|---|---|---|
| OQ-B4 | `30` lists no home for meta-enforcement tests (`39` §7) | (a) `tests/unit/`; (b) a new `tests/integration/meta/` | **(b)** `tests/integration/meta/` | `tests/unit/**` is A's; enforcement tests exercise the whole tree, which is integration-shaped. Directory is a leaf under a listed one. |
| OQ-B5 | `37` beats 0 and 4 say carriers are "green"; `02`, `39` §6.2, `40` Session 3 prompt and BUILD_B §0 invariant 4 say **no green anywhere** | (a) render TRACKED-clean as green; (b) render it as a neutral cool tone | **(b)** neutral (slate/blue-white), no green hue | `product/02` outranks `engineering/37`. Green reads as a "safe" claim the system is forbidden from making. `37`'s "green" is read as "quiet/unflagged". |
| OQ-B6 | `39` §6.2 and `40` reference "the published station-display mockup / demo-screen artifact" as the approved layout. **No such artifact exists** in this account's artifact gallery (checked 06:38). | (a) block until found; (b) derive the layout from `39` §6.2 + `26` + `37` beats + `40`'s prompt ("four panes in dataflow order; worker surface at the bottom") | **(b)** | The written constraints are complete enough to build against. If the artifact surfaces, reconcile. |
| OQ-B7 | `31` names `defaults.yaml` at the base of the hierarchy but `30`'s tree lists only `config/station/`, `config/knowledge/`, `config/profiles/` | (a) fold defaults into each profile; (b) `config/defaults.yaml` as a file (not a directory) | **(b)** `config/defaults.yaml` | `31` is authoritative for config; a file adds no directory `30` did not list. |
| OQ-B8 | `22` `WorkerDisplay.render(..., state_summary: StationSummary)` — `StationSummary` is not defined in `11` | n/a — A defined it | **Resolved**: A's `DisplayPayload{state_summary, interventions}` (generated from `src/domain`) is the core of the wire; B's `runtime` block sits beside it (`src/ui/wire.py`). B's earlier competing shape was withdrawn. | BUILD_B §1.5; late publisher adopts the early shape. |
| OQ-B9 | `38` P0 lists "config loader + validation" in P0 (A's phase) but BUILD_B §4 assigns the loader to `src/runtime/config.py` (B) | n/a — resolved by the prompt | B owns loading + I/O + validation; A owns `Config` **types** in `src/domain/` | `runtime/` is the only layer permitted I/O. |
| OQ-B10 | Alert copy templates live in `src/policy/` (A) but the claim-word lint must also cover B's static UI copy (banners, disclaimer, labels) | (a) rely on A's lint only; (b) B adds a UI copy lint over `src/ui/static/**` | **(b)** | `02` prohibits the claims in *any* surface; B's copy is not in A's template table. |
| OQ-B11 | Branch model: `40` prescribes `core/perception/interface` branches; BUILD_B §1.2 says both devices commit to `main` | n/a — resolved by the prompt | `main` only, `pull --rebase` before every push | Ownership is exclusive at file granularity; branches isolate nothing here. |
| OQ-B12 | Event log JSONL location (`39` §5: "one file per session") — path unspecified | (a) `data/logs/<session>.jsonl`; (b) `data/sessions/<session>.jsonl` | **(a)** `data/logs/<timestamp>.jsonl`, gitignored | `data/` is the doc'd home for recordings/outputs; `logs` matches `25`'s vocabulary. |
| OQ-B13 | `37` fallback ladder step 2 "recorded log replay" — with no camera there is no perception-recorded log | (a) skip level 2; (b) treat any JSONL produced by a `PROTOCOL_ONLY` or fixture-driven session as the recorded log and replay it | **(b)** | Keeps all three ladder levels exercisable and identical without hardware. |
| OQ-B14 | Python toolchain: system `python3` is 3.9.6; `39` §1 requires 3.11+ | n/a | Use uv-managed CPython 3.11.16 in `.venv` | Environment fact, not a design choice. |

## Assumptions (`[ASSUMPTION]`, each also inline in code)

| id | assumption | why | where |
|---|---|---|---|
| AS-B1 | The UI push loop runs on a 200ms asyncio timer (5Hz) driven by `SystemClock`; in `REPLAY` the broadcast cadence is wall-clock paced for display while all *reasoning* time comes from `t_occurred` | `39` §6 fixes 5Hz; `19` forbids wall clock only in layers 6–11 (display is layer 11 rendering, driven by `runtime/`) | `src/runtime/app.py` |
| AS-B2 | Worker actions (`Acknowledge`, `Dismiss`, `Remake`, `Resolve hold`) map to the A-owned event types in `12` (`ALERT_ACKNOWLEDGED`, `OPERATOR_ASSERTION`, `TICKET_VOIDED`/`TICKET_REWORK_OPENED`, `TICKET_RELEASED`) via `contracts.md`; if a mapping is absent it is reported, not invented | `26` names the actions; `12` names the events | `src/ui/server.py` |
| AS-B3 | `ManualEntrySource` is fed by a `POST /action` of kind `NEW_TICKET` from the display (a cashier types it) | `17` "a cashier types it"; `40` Session 3 owns the display | `src/runtime/app.py` |
| AS-B4 | Health checks in `PROTOCOL_ONLY`-only builds: with no perception thread, health is `{vision: UNAVAILABLE, reasoning: OK}` and the runtime starts directly in `PROTOCOL_ONLY` under the `demo` profile unless a perception pipeline is configured | `ADR-0011`; `37` "the demo still runs live in PROTOCOL_ONLY" | `src/runtime/controller.py` |

## Status drift noted for A (B does not edit `PROJECT_STATE.md`)

- `PROJECT_STATE.md` §2 says "no git repository" — one exists with remote `origin` → `github.com/RohanPejaver/hackathon`, one commit `b83eeff`.

---

## CHANNEL → Device A: answers to openq_A Q1–Q8 (B, early publisher) — 2026-09-12 07:05 EDT

There is no specification owner and no message channel. **The late publisher adopts the early
publisher's shape.** B publishes the following now; A conforms. Nothing below changes a
signature in `22`. Read `data/build/status_B.md` for the wire-shape location.

| Q | B's decision (applied) | Reading |
|---|---|---|
| **Q1** lifecycle for tier selection | `RiskAssessment` carries `ticket_lifecycle: TicketLifecycle` (derived from the `tickets` input `assess` already receives). `evaluate(assessments, alerts, cfg)` keeps its `22` parameter list. `AlertCommand = {kind: RAISE\|UPDATE\|RESOLVE\|ESCALATE\|SUPPRESS, alert_key, tier, ticket_id, allergen_id, headline, body?, required_actions, derivation, reason?: RESOLVED_BY_RESET\|RESOLVED_BY_ASSERTION\|RESOLVED_BY_REMAKE\|EXPIRED\|DISMISSED\|SUPPRESSED, cause_event_id}`. Human provenance reaches `AlertState` the only way anything does: as log events (`ALERT_ACKNOWLEDGED`, `OPERATOR_ASSERTION`, `TICKET_RELEASED`, `TICKET_VOIDED`) folded by A's alert-state reducer before `evaluate` runs. | `15` §Output is an architecture *payload*, not a `22` signature; adding a projected field is not a contract change. `16` §Lifecycle already names the reasons. |
| **Q2** draft ingestion / reorder | `EventSink.emit(DraftEvent)` enqueues (in-memory `queue.Queue`, never raises). **The reorder window is the runtime's job** (`39` §1: *drain queue → reorder → append log* — that loop is B's `src/runtime/app.py`). The runtime holds drafts for `t_reorder` on the injected `Clock`, sorts by `t_occurred`, then calls `EventLog.append(e: Event)` which assigns `seq`/`t_committed` synchronously and returns the final `Seq`. Drafts arriving after `t_reorder` are appended at the tail with `late: true`. No flush/drain method is added to `EventLog`. A's `append` needs only: validate schema (reject → `HEALTH_DEGRADED`, quarantine), stamp `seq`, store. | `19` §Ordering; `22` EventLog/EventSink; `39` §1 puts reorder in the runtime loop. |
| **Q3** snapshot vocabulary/shape | Three epistemic values only: `TRACKED \| STALE \| UNKNOWN`. Identity suspicion = `TRACK_IDENTITY_SUSPECT` event + pessimistic merge, both carriers `STALE`. **B has published the wire shape**: `src/ui/wire.py` (pydantic, `extra="forbid"`), `src/ui/static/mock/snapshot.schema.json` (generated from it), `src/ui/static/mock/snapshot.example.json` (validated). `StationSummary` **is** `src.ui.wire.Snapshot`. A's runtime-facing types need only be *convertible* to it; B's runtime does the conversion. If A needs a field, ask in `openq_A.md`; do not fork the shape. | `13` §Epistemic status; `22` WorkerDisplay; BUILD_B §1.5 (shape frozen once published). |
| **Q4** event payloads | Minimal payloads, from `11`/`12`/`16`/`17`/`26`: ticket events carry `{ticket_id, lifecycle_after}` plus per type: `TICKET_RECEIVED {items: [item_id], restrictions: [{raw_text}]}`, `TICKET_RESTRICTION_RESOLVED {restrictions: [Restriction]}`, `TICKET_BLOCKED {reason: AMBIGUOUS\|UNRESOLVABLE}`, `TICKET_BOUND {station_id, worker_slot}`, `TICKET_REWORK_OPENED {rework_of}`. Alert events carry `{alert_id, alert_key, pathway_signature, tier, ticket_id, allergen_id, reason?}`. **No new event types**: suppression and dismissal are `ALERT_UPDATED {reason: SUPPRESSED\|DISMISSED, until}`; `TICKET_ITEM_SUBSTITUTED` is off the demo path — `[DEFER]`. Worker action → event map (B's `POST /action` body is `WorkerAction {kind, worker_slot, alert_id?, carrier_id?, ticket_id?, items?, restrictions?}`): `ACKNOWLEDGE→ALERT_ACKNOWLEDGED`, `ASSERT_CLEAN→OPERATOR_ASSERTION{claim:CLEAN}`, `ASSERT_REPLACED→OPERATOR_ASSERTION{claim:REPLACED}`, `DISMISS→ALERT_UPDATED{reason:DISMISSED}`, `REMAKE→TICKET_VOIDED + TICKET_REWORK_OPENED`, `RESOLVE_HOLD→TICKET_RELEASED`, `NEW_TICKET→TICKET_RECEIVED` (via `ManualEntrySource`), `BIND_TICKET→TICKET_BOUND`, `PREP_STARTED→TICKET_PREP_STARTED`, `ITEM_COMPLETE→TICKET_ITEM_COMPLETE`. | `12` §Catalog; `16` §Cooldown ("logged as a suppression event" — satisfied by a typed `ALERT_UPDATED`); `26` §Worker actions. |
| **Q5** tier escalation | Agree with A's default: `ADR-0005` outranks `16`. Weak evidence never leaves Tier 0. `16`'s Tier 0→Tier 1 on `IN_PREP` applies **only when an `OBSERVED` pathway exists**; otherwise Tier 0 persists. Observed unresolved pathway at `COMPLETE` → Tier 2, no 20s wait. | ADR > architecture. Demo beat 5 needs exactly this. |
| **Q6** wipe | Agree: `SURFACE_WIPE` clears nothing; the UI explanation is derived from the log (B renders `last_wiped_at` from the event stream in the snapshot, not from reducer state). | `ADR-0009`. |
| **Q7** defaults | **Published**: `config/defaults.yaml` is the value source (every `19` window, `14` params, `21` thresholds per type incl. `GLOVE_CHANGE` observed-unreachable per `39` §3/EXP-004). `t_stale_s` has GLOVES/TOOL/SURFACE/CONTAINER; **FOOD carriers use the SURFACE value** (`# ASSUMPTION` in the file). A's `Config` types conform to these keys. | `31` names the file; B owns content. |
| **Q8** seeded taint provenance | Fixture `initial_state` shorthand is A's parser concern; B's recommendation: expand shorthand into synthetic `ZONE_ENTRY` events at `t < 0` with `source: SYSTEM` so `11` invariant 3 holds and the trace stays honest. | `11` §Invariants 3; `36` §Format. |

**Timestamp**: integer milliseconds. `WALL` = Unix epoch ms (`SystemClock`); `LOG` = ms from
scenario/log start (`LogClock`). `Snapshot.time.kind` says which. Event `t_occurred` uses the
same basis as the snapshot that carries it.


---

## Sole-driver decisions (after Device A stopped) — every one is a CONTRACT-GAP resolution, not a doc edit

| id | gap (docs silent) | decision | where |
|---|---|---|---|
| CG-B1 | Who runs the reorder pump | The runtime tick calls the log's private `_drain(now)` every 100 ms with the injected clock (39 §1 puts reorder in the runtime loop; Q2 keeps the buffer inside `events/`). | `src/runtime/app.py::Runtime.tick` |
| CG-B2 | How derived alert events and holds enter the log | After `evaluate`, each `AlertCommand` is emitted as `ALERT_<KIND>` (`source=SYSTEM`) carrying the command; a Tier 2 RAISE/ESCALATE also emits `TICKET_HELD` so the hold is state (16 Tier 2, 17 HELD). Replay re-derives these; a recorded log's derived events are inputs to nothing. | `app.py::_assess`; S3 runner |
| CG-B3 | When risk is evaluated | Synchronously after every committed `mutates_state` event (37 req 3: Tier 0 before any motion). | `app.py::_on_committed` |
| CG-B4 | Ticket intake | `TICKET_RECEIVED` is immediately followed by `src.orders.intake` → `TICKET_RESTRICTION_RESOLVED` or `TICKET_BLOCKED`, in the runtime and in replay alike (17: normalization cached on the ticket as events). | `app.py::tick`; S4 `intake` |
| CG-B5 | Worker action → event map | NEW_TICKET→ManualEntrySource→TICKET_RECEIVED(+intake); BIND_TICKET→TICKET_BOUND (refused unless RECEIVED, all RESOLVED, mode≠CALIBRATION); PREP_STARTED; ITEM_COMPLETE; RESOLVE_HOLD→TICKET_RELEASED; REMAKE→TICKET_VOIDED+TICKET_REWORK_OPENED(`<id>R`); ASSERT_CLEAN/REPLACED→OPERATOR_ASSERTION per carrier (ASSERTED); ACKNOWLEDGE→ALERT_ACKNOWLEDGED; DISMISS→ALERT_UPDATED with worker_slot (Tier 2 refused). | `app.py::on_action` |
| CG-B6 | Start mode with no camera | `report_vision(UNAVAILABLE)` then `request_mode(PROTOCOL_ONLY)`; REPLAY when `STATION_REPLAY` is set. | `app.py::build` |
| CG-B7 | Camera-unplug drill without a camera | Rehearsed as scenario L replayed through the UI (HEALTH→PROTOCOL_ONLY mid-ticket, hold persists, Tier 0 still fires). Level 1 of the ladder is N/A. | `runbook_B.md` |
| CG-B8 | Staleness by time | `src/domain/epistemic.py::effective_epistemic(carrier, now, cfg)`: computed at query time by risk and the snapshot projection; the reducer never runs a timer. | domain |
| CG-B9 | FOOD carriers' `t_stale` | SURFACE value. | `config.py::to_domain` |
| CG-B10 | Alert headline honesty | `domain.Alert` validators: ≤ 6 alnum words, no prohibited claim word — structural, per 02. | `src/domain/models.py` |
| CG-B11 | Tier 0 checklist ticking | `done` = `carrier_id not in alert.blocking_carriers`; policy shrinks the list via UPDATE as resets land. | UI + S2 |
| CG-B12 | Q5 ruling adopted | Tier 1 → Tier 2 at `COMPLETE` while the OBSERVED pathway is open; no 20 s timer. Weak evidence never leaves Tier 0. | S2 packet |
| CG-B13 | Recipe scoping vs `03`'s "spreader" | Required carriers = carriers bound to the recipe's `required_zones` + gloves (15/18). A tool whose home is `tool_rack` is not recipe-required; fixtures B/D use the board. | S3 packet |

| CG-B14 | `uvicorn` alone has no WebSocket implementation; `39` §6 mandates FastAPI + WebSocket and `39` §2 lists `uvicorn ~0.32` | Pin `uvicorn[standard]~=0.32` (same package; the extra supplies `websockets`). Not a new dependency line; recorded per `32` §Selection gate. Found only when the real server was driven from a browser — the FastAPI TestClient speaks WebSocket itself and hid it. | `pyproject.toml` |
| CG-B15 | `15` §1: "if c.epistemic != TRACKED → reset required", unconditional. With zero perception nothing is ever TRACKED, so a Tier 0 checklist could never be satisfied — contradicting `03` D and `37` beat 4 | A non-TRACKED required carrier is satisfied by a valid reset (observed or `OPERATOR_ASSERTION`) at or after the ticket's `bound_at`; a reset clears taint, so anything acquired afterwards re-blocks; every new restricted bind asks again (`10`: Tier 0 on every restricted bind in PROTOCOL_ONLY). | `src/risk/preconditions.py::needs_reset`; `tests/unit/risk/test_preconditions.py::test_reset_since_bind_*` |
| CG-B16 | `15` §1 required carriers = `carriers_for(required_zones) ∪ {GLOVES}`, but `03` B/D, `25`, `36`'s example and `37` beat 3 all put the spreader on the checklist (tools have no recipe zone) | TOOL-kind carriers are always required, like gloves (product docs outrank `15`). Order: gloves → tools → recipe zone carriers. | `src/risk/preconditions.py::required_carriers` (S2) |
| CG-B17 | `36` `initial_state` has no event form; a recorded log of a fixture replay must be self-contained (`37` ladder level 2) | Epistemic seeds become `CARRIER_OBSERVABILITY_CHANGED(cause="scenario seed")` events at the log origin; taint seeds stay a state patch (a recorded log of a taint-seeded fixture is not self-contained — level 3 covers those; the demo seeds epistemic only). | `src/runtime/feed.py::scenario_feed` |
| CG-B18 | `22` `evaluate(assessments, alerts, cfg)` cannot see carrier kinds or edge times needed for required-action labels and per-step trace timestamps | `evaluate(..., state: WorldState | None = None)` — an optional keyword; the registered parameter list is unchanged; runtime and runner pass `state=`. | `src/policy/build.py`, `src/runtime/app.py::_assess` |
| CG-B19 | `22` `ReplayResult` names four fields; the determinism diff and the assertion vocabulary need the command timeline, mode timeline, state snapshots, rejections | `ReplayResult` extended (superset; the four named fields kept). | `src/replay/schema.py` (S3) |
| CG-B20 | `36` assertion vocabulary lacks silence-before-t, held, open-alert-at-t, raise counts | Added `silence`, `held`, `alert_open`, `raise_count`, `no_alerts_of_tier.before/after`, `alert.blocking_carriers_include`, `alert.headline_contains`, `pathway.includes/target`; all listed in `src/replay/assertions.py::VOCABULARY`. | S3 |
| CG-B21 | `fastapi.testclient` needs `httpx`; `39` §2 lists neither | `httpx` declared in the **dev** extra only (never installed by `pip install -e .`). | `pyproject.toml` |
| CG-B22 | Tier 0 checklist in PROTOCOL_ONLY names every required carrier incl. untainted-but-UNKNOWN containers ("Bread container flagged — use sealed backup") | Kept: with no camera the honest ask for an unobserved shared container is the same protocol step; copy is the policy's per-kind label. Worth a product decision on softer copy for UNKNOWN-only containers. | `src/policy/copy.py` |
