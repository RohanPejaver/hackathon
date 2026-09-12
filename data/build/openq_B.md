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
| OQ-B8 | `22` `WorkerDisplay.render(..., state_summary: StationSummary)` — `StationSummary` is not defined in `11` | n/a — A defines it | Consume A's `snapshot.schema.json` verbatim as the wire shape; build payload-agnostic until T+90 | BUILD_B §1.5. |
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
