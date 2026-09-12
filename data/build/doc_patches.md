# Proposed human-applied patches — no docs were edited

Apply to docs/architecture/12-event-model.md after its ticket catalog:

- `TICKET_ITEM_SUBSTITUTED`: ticket id and replacement items list; mutates state and triggers recipe-scoped reassessment (`17`).

Apply to the alert catalog:

- `ALERT_SUPPRESSED`: alert_id, pathway_signature, optional AlertCommand containing cooldown_until and cause_event_id; records suppression without clearing carrier state (`16`, `22` SUPPRESS).

Complete catalog payload documentation from `src/events/catalog.py`: ticket/system/alert payload fields are explicit, extra fields rejected, serialized evidence holds references only. All are schema v1 because no prior executable schema was published. The draft, committed and confidence-omitted semantic projections share payload schemas.

Approved Q1 adds `ticket_lifecycle` to RiskAssessment without changing evaluate's parameter list. Q2 retains append(Event) and emit(DraftEvent); private `_ingest` and `_drain` buffer drafts and receive injected commit time. `read(from_seq, to)` is a half-open range; `from` is a Python keyword.

---

## Proposed by the sole driver (Device B) — docs remain unedited

- `31-configuration.md`: add the numeric defaults table (it says it is the authoritative home
  but has none). Source of values: `config/defaults.yaml` (every `19` window, `14` parameters,
  `21` thresholds per event type, `orders.normalizer_threshold`, `capture`, `retention`,
  `runtime`). Add: `t_recover` (10 s) and FOOD carriers' `t_stale` = SURFACE value.
- `30-repository-layout.md`: name a home for the mechanical-enforcement tests (`39` §7); B uses
  `tests/integration/meta/` and `tests/property/test_architecture.py`.
- `22-interfaces.md` (lock-protected; no signature changes): note that `StationSummary` is
  `DisplayPayload.state_summary` (`src/domain/models.py`) and that the wire pushed at 5Hz is
  `{state_summary, interventions}` plus a runtime block (`src/ui/wire.py`).
- `37-demo-plan.md` beats 0 and 4: "green" → "quiet/unflagged"; `02`/`39` §6.2 forbid green.
- `16-alert-model.md` §Escalation: per ADR-0005 (Q5), Tier 1 → Tier 2 at `COMPLETE` while an
  OBSERVED pathway is open, with no `t_escalate` wait; Tier 0 never escalates on weak evidence.
- `12-event-model.md`: the reorder pump is driven by the runtime tick with an injected commit
  time (`EventLog._drain(now)`); derived `ALERT_*` and `TICKET_HELD` events are `source: SYSTEM`
  and are re-derived, not replayed, by `ReplayRunner`.
