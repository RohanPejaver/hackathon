"""Alert identity — the anti-spam mechanism (16 §Alert identity)."""

from __future__ import annotations

import hashlib

from src.domain import Pathway

PRECONDITION = "PRECONDITION"
MULTI_RESTRICTION = "MULTI_RESTRICTION"


def _signature(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


def precondition_signature(ticket_id: str, allergen_id: str) -> str:
    """Stable while the checklist shrinks: the same Tier 0 alert is updated, not re-raised."""
    return _signature(ticket_id, allergen_id, PRECONDITION)


def multi_restriction_signature(ticket_id: str) -> str:
    return _signature(ticket_id, MULTI_RESTRICTION)


def pathway_signature(ticket_id: str, allergen_id: str, pathway: Pathway) -> str:
    return _signature(ticket_id, allergen_id, pathway.nodes[0], ">".join(pathway.nodes))


def alert_key(station_id: str, signature: str) -> str:
    return f"{station_id}:{signature}"
