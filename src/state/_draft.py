"""Mutable working copy used while folding one event, then frozen back into a WorldState.

`WorldState` is frozen; the reducer never mutates it. Each `reduce` call opens a `Draft`
(shallow copies of the containers it may touch), applies the transition, and `finalize`
assembles a brand-new `WorldState`. Every change is routed through `Draft.delta`, so the
evidence trace is a by-product of reduction rather than a separate logging concern (13).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import JsonValue

from src.domain import (
    Carrier,
    ContactEdge,
    EpistemicStatus,
    EvidenceGrade,
    Mode,
    ResetRecord,
    StateDelta,
    TaintRecord,
    Ticket,
    WorldState,
    Zone,
)


@dataclass
class Draft:
    base: WorldState
    event_id: str
    t: int
    carriers: dict[str, Carrier]
    zones: dict[str, Zone]
    tickets: dict[str, Ticket]
    bound_tickets: list[str]
    recent_allergen_exposure: dict[str, int]
    acquisitions: dict[str, list[TaintRecord]]
    mode: Mode
    config_version: str
    knowledge_version: str
    conditions: list[str]
    new_contacts: list[ContactEdge] = field(default_factory=list)
    new_resets: list[ResetRecord] = field(default_factory=list)
    deltas: list[StateDelta] = field(default_factory=list)

    @classmethod
    def open(cls, state: WorldState, event_id: str, t: int) -> Draft:
        station = state.station
        return cls(
            base=state,
            event_id=event_id,
            t=t,
            carriers=dict(station.carriers),
            zones=dict(station.zones),
            tickets=dict(state.tickets),
            bound_tickets=list(station.bound_tickets),
            recent_allergen_exposure=dict(station.recent_allergen_exposure),
            acquisitions={k: list(v) for k, v in state.acquisitions.items()},
            mode=station.mode,
            config_version=station.config_version,
            knowledge_version=station.knowledge_version,
            conditions=list(state.conditions),
        )

    # -- evidence trace ---------------------------------------------------------------------

    def delta(
        self,
        rule_id: str,
        field_name: str,
        before: JsonValue,
        after: JsonValue,
        carrier_id: str | None = None,
    ) -> None:
        self.deltas.append(
            StateDelta(
                event_id=self.event_id,
                rule_id=rule_id,
                carrier_id=carrier_id,
                field=field_name,
                before=before,
                after=after,
            )
        )

    # -- carriers ---------------------------------------------------------------------------

    def set_carrier(self, rule_id: str, carrier: Carrier, **update: object) -> Carrier:
        """Replace scalar carrier fields, emitting one delta per field that actually changes."""
        changes = {k: v for k, v in update.items() if getattr(carrier, k) != v}
        if not changes:
            return carrier
        new = carrier.model_copy(update=changes)
        for k in changes:
            self.delta(
                rule_id,
                k,
                as_json(getattr(carrier, k)),
                as_json(getattr(new, k)),
                carrier_id=carrier.carrier_id,
            )
        self.carriers[carrier.carrier_id] = new
        return new

    def observe(self, carrier_id: str) -> None:
        """A physical event named this carrier: it was just seen (13 §Epistemic status)."""
        carrier = self.carriers.get(carrier_id)
        if carrier is None:
            return
        self.set_carrier(
            "observation", carrier, epistemic=EpistemicStatus.TRACKED, last_observed_at=self.t
        )

    def clear_taints(self, rule_id: str, carrier: Carrier, **update: object) -> Carrier:
        """A valid reset (14): taint set becomes empty; other fields per the reset kind."""
        if carrier.taints:
            before: JsonValue = {k: v.model_dump(mode="json") for k, v in carrier.taints.items()}
            self.delta(rule_id, "taints", before, {}, carrier_id=carrier.carrier_id)
            carrier = carrier.model_copy(update={"taints": {}})
            self.carriers[carrier.carrier_id] = carrier
        return self.set_carrier(rule_id, carrier, **update)

    def put_taint(self, rule_id: str, carrier_id: str, record: TaintRecord) -> bool:
        """Keep/replace rule — never lose evidence: fewer hops win; equal hops keep the
        existing (earlier) record. Returns True when the record was stored."""
        carrier = self.carriers[carrier_id]
        existing = carrier.taints.get(record.allergen_id)
        if existing is not None and existing.hops <= record.hops:
            return False
        taints = dict(carrier.taints)
        taints[record.allergen_id] = record
        self.carriers[carrier_id] = carrier.model_copy(update={"taints": taints})
        self.delta(
            rule_id,
            f"taints.{record.allergen_id}",
            None if existing is None else existing.model_dump(mode="json"),
            record.model_dump(mode="json"),
            carrier_id=carrier_id,
        )
        self.acquisitions.setdefault(carrier_id, []).append(record)
        return True

    def add_carrier(self, rule_id: str, carrier: Carrier) -> None:
        before = self.carriers.get(carrier.carrier_id)
        self.carriers[carrier.carrier_id] = carrier
        self.delta(
            rule_id,
            "carriers",
            None if before is None else before.model_dump(mode="json"),
            carrier.model_dump(mode="json"),
            carrier_id=carrier.carrier_id,
        )

    def remove_carrier(self, rule_id: str, carrier_id: str) -> None:
        before = self.carriers.pop(carrier_id, None)
        if before is not None:
            self.delta(
                rule_id, "carriers", before.model_dump(mode="json"), None, carrier_id=carrier_id
            )

    # -- records ----------------------------------------------------------------------------

    def record_reset(
        self, rule_id: str, carrier_id: str, grade: EvidenceGrade, operator: bool
    ) -> None:
        record = ResetRecord(
            event_id=self.event_id,
            t_occurred=self.t,
            carrier_id=carrier_id,
            grade=grade,
            operator=operator,
        )
        self.new_resets.append(record)
        self.delta(rule_id, "resets", None, record.model_dump(mode="json"), carrier_id=carrier_id)

    def record_contact(self, a: str, b: str, grade: EvidenceGrade) -> None:
        edge = ContactEdge(event_id=self.event_id, t_occurred=self.t, a=a, b=b, grade=grade)
        self.new_contacts.append(edge)
        self.delta("contact_edge", "contacts", None, edge.model_dump(mode="json"))

    # -- tickets ----------------------------------------------------------------------------

    def set_ticket(self, rule_id: str, ticket: Ticket, **update: object) -> Ticket:
        changes = {k: v for k, v in update.items() if getattr(ticket, k) != v}
        if not changes:
            return ticket
        new = ticket.model_copy(update=changes)
        for k in changes:
            self.delta(
                rule_id,
                f"tickets.{ticket.ticket_id}.{k}",
                as_json(getattr(ticket, k)),
                as_json(getattr(new, k)),
            )
        self.tickets[ticket.ticket_id] = new
        return new

    def add_ticket(self, rule_id: str, ticket: Ticket) -> None:
        self.tickets[ticket.ticket_id] = ticket
        self.delta(rule_id, f"tickets.{ticket.ticket_id}", None, ticket.model_dump(mode="json"))

    def set_station_field(self, rule_id: str, field_name: str, value: object) -> None:
        before = getattr(self, field_name)
        if before == value:
            return
        setattr(self, field_name, value)
        self.delta(rule_id, field_name, as_json(before), as_json(value))

    # -- assembly ---------------------------------------------------------------------------

    def finalize(self, event_type: str, event_source: str) -> tuple[WorldState, list[StateDelta]]:
        base = self.base
        station = base.station.model_copy(
            update={
                "config_version": self.config_version,
                "knowledge_version": self.knowledge_version,
                "mode": self.mode,
                "carriers": self.carriers,
                "zones": self.zones,
                "bound_tickets": self.bound_tickets,
                "recent_allergen_exposure": self.recent_allergen_exposure,
            }
        )
        state = base.model_copy(
            update={
                "station": station,
                "tickets": self.tickets,
                "contacts": [*base.contacts, *self.new_contacts],
                "resets": [*base.resets, *self.new_resets],
                "acquisitions": self.acquisitions,
                "event_ids": [*base.event_ids, self.event_id],
                "deltas": [*base.deltas, *self.deltas],
                "t_occurred": max(base.t_occurred, self.t),
                "last_event_type": event_type,
                "last_event_id": self.event_id,
                "last_event_source": event_source,
                "conditions": self.conditions,
            }
        )
        return state, list(self.deltas)


def as_json(value: object) -> JsonValue:
    """Project a model field into a JSON value for a StateDelta (before/after must be JSON)."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):  # StrEnum members are str
        return str(value)
    if isinstance(value, (frozenset, set)):
        members: list[JsonValue] = [str(v) for v in sorted(str(m) for m in value)]
        return members
    if isinstance(value, (list, tuple)):
        return [as_json(v) for v in value]
    if isinstance(value, dict):
        return {str(k): as_json(v) for k, v in value.items()}
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        dumped: JsonValue = dump(mode="json")
        return dumped
    return str(value)
