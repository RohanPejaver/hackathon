"""Every human-facing string the policy emits (16 §Alert payload, 26). Templates are module
constants with small formatters; nothing here is free text. This file is linted by
tests/property/test_architecture.py::test_alert_copy_guard for prohibited claim words
(product/02): the system reports what it observed and did not observe, nothing more."""

from __future__ import annotations

# ---- headlines (<= 6 words, 26 §Design constraints) ------------------------------------
TIER0_HEADLINE = "{allergen} — station not clean"
MULTI_HEADLINE = "Two active restrictions — sequence them"
TIER1_HEADLINE = "STOP — {carrier} touched {source}"
TIER2_HEADLINE = "HOLD — TICKET {ticket_id} — DO NOT SEND"

# ---- bodies (one explanatory line; the UI appends the Tier 2 disclaimer itself) ------
TIER1_BODY = "{carrier} last observed contacting {source}. Replacement not observed."
TIER2_BODY = "{allergen}. {carrier} contacted {source} at {t}. Replacement not observed."

# ---- action labels --------------------------------------------------------------------
LABEL_NEW_GLOVES = "New gloves"
LABEL_CLEAN_TOOL = "Clean {carrier}"
LABEL_FRESH_SURFACE = "Fresh {carrier}"
LABEL_SEALED_BACKUP = "{container} flagged — use sealed backup"
LABEL_SEQUENCE_TICKETS = "Two active restrictions — sequence them"
LABEL_SWAP_TOOL = "Swap tool"
LABEL_CONFIRM = "Confirm with the cook"
LABEL_REMAKE = "Remake"

# ---- evidence-trace narratives (25 §The evidence trace) --------------------------------
NARRATIVE_ZONE_ACQUIRE = "{carrier} -> {zone}"
NARRATIVE_CONTACT_TRANSFER = "{a} <-> {b}"
NARRATIVE_ABSENCE = "no {reset_kind} observed on {carrier} in window"
NARRATIVE_UNVERIFIED = "{carrier} {status}: not observed for {duration}"
NARRATIVE_NEVER_OBSERVED = "{carrier} {status}: never observed"
NARRATIVE_PRECONDITION_UNMET = "blocking: [{blocking}]"
NARRATIVE_CONDITION = "station condition {condition}"
NARRATIVE_PATHWAY_OPEN = "{path} ({hops} hops, unbroken)"
NARRATIVE_ALERT = 'tier={tier} "{headline}"'

CONTAINER_PREFIX = "bin:"
CONTAINER_SUFFIX = " container"


def allergen_display(allergen_id: str) -> str:
    return allergen_id.replace("_", " ")


def container_display(carrier_id: str) -> str:
    name = carrier_id.removeprefix(CONTAINER_PREFIX).replace("_", " ").title()
    return f"{name}{CONTAINER_SUFFIX}"


def offset(t_ms: int) -> str:
    minutes, seconds = divmod(max(t_ms, 0) // 1000, 60)
    return f"+{minutes}:{seconds:02d}"


def duration(ms: int) -> str:
    return f"{max(ms, 0) // 1000}s"


def tier0_headline(allergen_id: str) -> str:
    return TIER0_HEADLINE.format(allergen=allergen_display(allergen_id))


def tier1_headline(carrier: str, source: str) -> str:
    return TIER1_HEADLINE.format(carrier=carrier, source=source)


def tier2_headline(ticket_id: str) -> str:
    return TIER2_HEADLINE.format(ticket_id=ticket_id)


def tier1_body(carrier: str, source: str) -> str:
    return TIER1_BODY.format(carrier=carrier, source=source)


def tier2_body(allergen_id: str, carrier: str, source: str, t_ms: int) -> str:
    return TIER2_BODY.format(
        allergen=allergen_display(allergen_id), carrier=carrier, source=source, t=offset(t_ms)
    )
