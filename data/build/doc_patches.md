# Proposed human-applied patches — no docs were edited

Apply to docs/architecture/12-event-model.md after its ticket catalog:

- `TICKET_ITEM_SUBSTITUTED`: ticket id and replacement items list; mutates state and triggers recipe-scoped reassessment (`17`).

Apply to the alert catalog:

- `ALERT_SUPPRESSED`: alert_id, pathway_signature, optional AlertCommand containing cooldown_until and cause_event_id; records suppression without clearing carrier state (`16`, `22` SUPPRESS).

Complete catalog payload documentation from `src/events/catalog.py`: ticket/system/alert payload fields are explicit, extra fields rejected, serialized evidence holds references only. All are schema v1 because no prior executable schema was published. The draft, committed and confidence-omitted semantic projections share payload schemas.

Approved Q1 adds `ticket_lifecycle` to RiskAssessment without changing evaluate's parameter list. Q2 retains append(Event) and emit(DraftEvent); private `_ingest` and `_drain` buffer drafts and receive injected commit time. `read(from_seq, to)` is a half-open range; `from` is a Python keyword.
