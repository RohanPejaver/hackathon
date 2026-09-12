# Domain Model

Classification of every candidate entity. **Not everything listed in ideation becomes a
first-class entity** — several are derived state, transient observations, or external data,
and promoting them would create duplicate sources of truth.

## Classification

| Entity | Class | Rationale |
|---|---|---|
| **Carrier** | **First-class** | The central abstraction. Holds taint + epistemic status. |
| **Zone** | **First-class** | Named spatial region; configuration-defined identity. |
| **Ticket** | **First-class** | Unit of restriction + binding. (Replaces "Order".) |
| **Restriction** | **First-class** | Has its own resolution lifecycle incl. `AMBIGUOUS`. |
| **Allergen** | **First-class** | Node in a configurable taxonomy. |
| **Event** | **First-class** | Immutable, the sole inter-layer contract. |
| **Alert** | **First-class** | Has identity, lifecycle, and acknowledgment state. |
| **Station** | **First-class** | Owns config version, mode, and the carrier set. |
| Taint | **Derived state** | A property of a Carrier, computed by the reducer. |
| Contamination state | **Derived state** | = Carrier taint + epistemic status. Not stored separately. |
| Risk state | **Derived state** | Recomputed from `WorldState`; never persisted as truth. |
| Preparation state | **Derived state** | = Ticket lifecycle + bound carriers. No separate entity. |
| Contact event / Cleaning event / Transfer event | **Event subtypes** | Not separate entities; see `12`. |
| Observation / Detection / Track | **Transient** | Layers 2-3 only. Never cross the log boundary. |
| Evidence | **Derived** | A projection over the log; see `25`. |
| Ingredient, FoodItem, Recipe | **External data** | Owned by the knowledge provider (`18`), not the runtime. |
| Customer | **Excluded** | Deliberately not modeled. Tickets carry restrictions, never people. |
| Worker | **Degenerate** | Modeled only as `worker_slot: int`. No name, no id, no metrics (`24`). |
| Hand | **Not an entity** | Hands *are* the `GLOVES` carrier. Modeling them separately duplicates taint. |
| Utensil / Surface / Container | **Carrier kinds** | Discriminated variants of `Carrier`, not sibling types. |
| FoodItem (in progress) | **Ephemeral carrier** | A `FOOD`-kind carrier `food:<ticket_id>`, created at `TICKET_PREP_STARTED`, bound to the ticket's landing zone, destroyed at `TICKET_RELEASED`/`VOIDED`. This is the **target node** of every pathway search (`15`); without it "pathway into the target food" has no referent. It holds taint like any carrier but is never reset — food cannot be cleaned. |
| Intervention | **= Alert + tier** | Not a separate entity; the Alert carries its tier. |

Two of these deserve emphasis because they are the most likely to be "helpfully" re-added
by a future contributor:

- **There is no `Customer` entity.** If one appears, the privacy model in `24` is void.
- **A hand is not distinct from its gloves.** Taint lives on one carrier; a `Hand` entity
  would immediately create two places to ask "is this contaminated?"

## Core types

```
Station
  station_id, config_version, knowledge_version
  mode: FULL | PROTOCOL_ONLY | REPLAY | CALIBRATION
  carriers: Map<CarrierId, Carrier>
  zones: Map<ZoneId, Zone>                    # from config
  bound_tickets: List<TicketId>
  worker_slots: int                           # count only; never identity
  recent_allergen_exposure: Map<AllergenId, Timestamp>
      # rolling last-contact time per allergen at this station.
      # Maintained by the reducer; the backing state for pessimistic closure (`13`).
      # Queried per-allergen, never enumerated.

Carrier
  carrier_id
  kind: GLOVES | TOOL | SURFACE | CONTAINER | FOOD
  taints: Map<AllergenId, TaintRecord>
  epistemic: TRACKED | STALE | UNKNOWN
  last_observed_at: Timestamp?
  home_zone: ZoneId?                          # CONTAINER/SURFACE are usually zone-fixed
  resettable_by: Set<ResetKind>               # e.g. GLOVES -> {GLOVE_CHANGE}

TaintRecord
  allergen_id
  acquired_at: Timestamp
  source_event_id, source_carrier_id
  grade: OBSERVED | INFERRED | ASSERTED | PESSIMISTIC
  hops: int                                   # distance from the originating source
  strength: PRESENT | POSSIBLE                # from `contains` vs `may_contain`

Zone
  zone_id, polygon (station frame), kind: INGREDIENT | TOOL_RACK | WORK | LANDING
                                          | GLOVE_DISPENSER | WASH | CLEAN_STOCK
  contents: List<IngredientRef>               # config; the source of allergen identity
  bound_carrier: CarrierId?

Ticket
  ticket_id, items: List<MenuItemRef>
  restrictions: List<Restriction>
  source: OrderSourceRef
  lifecycle: RECEIVED | BLOCKED | BOUND | IN_PREP | COMPLETE | HELD | RELEASED | VOIDED
  bound_station: StationId?, bound_at: Timestamp?
  rework_of: TicketId?

Restriction
  kind: AVOID_ALLERGEN | AVOID_INGREDIENT | DIETARY
  allergen_ids: Set<AllergenId>
  raw_text: str
  resolution: RESOLVED | AMBIGUOUS | UNRESOLVABLE
  severity_declared: STATED_ALLERGY | STATED_PREFERENCE | UNSPECIFIED
```

## Relationships

```
Station  1--* Carrier          (carriers belong to exactly one station)
Station  1--* Zone             (from versioned config)
Zone     0..1--0..1 Carrier     (a bin is both a zone and a container-carrier)
Zone     *--* Ingredient       (config: what is in this bin)
Ingredient *--* Allergen       (knowledge provider; contains | may_contain)
Allergen *--* Allergen         (taxonomy: parent/child, e.g. TREE_NUT -> PINE_NUT)
Ticket   1--* Restriction
Restriction *--* Allergen       (after normalization; empty while AMBIGUOUS)
Ticket   *--1 Station           (binding; explicit, never inferred)
MenuItem *--* Zone             (recipe -> required zones; drives Tier 0 preconditions)
Event    *--* Carrier           (participants)
Carrier  1--* TaintRecord
Alert    *--1 Ticket
Alert    1--* Event             (derivation chain -> evidence trace)
```

## Invariants (property-tested, see `33`)

1. A `Ticket` may not enter `BOUND` while any `Restriction.resolution == AMBIGUOUS`.
2. `TaintRecord` sets are **monotonically non-decreasing** between reset events.
   Only a valid reset (`14`) removes entries.
3. Every `TaintRecord` has a `source_event_id` present in the log. No taint without cause.
4. `epistemic == TRACKED` implies an observation within `t_stale[kind]`.
5. No type in `domain/` carries a field capable of identifying a person.
6. `hops` strictly increases along any propagation chain; propagation halts at `max_hops`.
7. A `FOOD` carrier has an empty `resettable_by` set. No reset event may clear its taint —
   the only remediation for contaminated food is remake, which is a ticket action, not a
   carrier action.
