# Implementation Plan

Source of truth for **technology selection and build order**. `32-dependency-policy.md` owns
the *principles*; this document owns the *choices* made under them. Architecture is fixed
(`docs/architecture/`); nothing here may change a contract.

---

## 1. Language and process

**Python 3.11+, single process, single language.**

The safety core is algebraic types, state machines, graph search, and property tests — all of
which Python does adequately with `frozen dataclass` + `Enum` + `mypy --strict`. Perception
is unavoidably Python (every vision library lives there). Splitting the core into a
better-typed language would buy stronger guarantees at the cost of an IPC boundary,
serialization, and two toolchains — a tax with no payoff at one station (`ADR-0012`).

**Concurrency model:**

```
  [perception thread]                    [asyncio event loop, main thread]
  capture -> detect -> assemble          drain queue -> reorder -> append log
         |                                      -> reduce -> risk -> policy
         +--> queue.Queue(DraftEvent) ---->     -> broadcast state over WebSocket
                                                -> serve UI, accept worker actions
```

One perception thread (OpenCV and MediaPipe release the GIL during native work, so this
genuinely parallelizes), one asyncio loop for runtime + web. No multiprocessing: shared
state across processes would undermine the determinism that `ADR-0001` depends on.

## 2. Dependencies

Small by design. **No PyTorch, no YOLO, no GPU.** The whole system runs on a laptop CPU.

| Group | Package | Version | Why |
|---|---|---|---|
| **core** | `pydantic` | ~2.9 | Event schemas, validation, JSON (de)serialization, discriminated unions on `type`, generated JSON Schema. Rust-backed, fast. |
| **core** | `pyyaml` | ~6.0 | Config + scenario files |
| **runtime** | `fastapi` | ~0.115 | HTTP + WebSocket |
| **runtime** | `uvicorn` | ~0.32 | ASGI server |
| **perception** | `opencv-python` | ~4.10 | Capture, homography, **ArUco**, HSV segmentation, contours |
| **perception** | `numpy` | ~2.1 | Array ops |
| **perception** *(optional)* | `mediapipe` | ~0.10 | Hand landmarks, only if HSV proves insufficient |
| **dev** | `pytest`, `pytest-asyncio` | — | Tests |
| **dev** | `hypothesis` | ~6.x | Property tests for `11` invariants |
| **dev** | `import-linter` | ~2.0 | **Enforces the layer DAG** (`30`) |
| **dev** | `mypy` | ~1.11 | `--strict` on `domain/ events/ state/ risk/ policy/` |
| **dev** | `ruff` | ~0.7 | Lint + format |

`pip install -e .` installs core + runtime only. Perception and dev are extras:
`.[perception]`, `.[dev]`. **The safety core must be testable without a camera library
installed** — this is the practical test of `ADR-0001`, and CI runs the core suite in an
environment where `opencv` is absent.

## 3. Perception: how each obligation in `21` is met

The architecture removed food recognition (`ADR-0007`), which collapses this to geometry.

| Obligation | Technique | Why this, not a learned model |
|---|---|---|
| **Station frame** | 4 ArUco markers taped at table corners -> `cv2.findHomography` -> pixel↔mm | 20 lines, sub-mm stable, recalibrates in seconds |
| **Zones** | Polygons in mm, authored once; `cv2.pointPolygonTest` | Config, not perception (`ADR-0007`) |
| **Gloves / hands** | **HSV colour segmentation** + contour + centroid | Nitrile gloves are strongly saturated (blue/purple) against a white/steel surface. Deterministic, ~2ms/frame, explainable, zero training data. Kitchens already colour-code allergen equipment — we exploit the environment instead of fighting it. |
| **Tools** | **ArUco marker (4x4, 25mm) on each handle** | Gives *guaranteed identity*, which nearly eliminates failure mode P3 (identity switch) and therefore the pessimistic merges that drive Tier 0 noise — a direct mitigation of risk **A6**. |
| **Boards / containers** | Fixed zones + ArUco for swappable boards | Same |
| **Contact** | Blob centroid ∈ polygon, or blob∩blob, held ≥ `t_dwell` with hysteresis | Directly implements the predicate in `20` |
| **Occlusion** | Track absent > `t_occlusion_max` -> `CARRIER_OBSERVABILITY_CHANGED` | The honesty obligation in `21` |
| **Glove change** | `ZONE_ENTRY(glove_dispenser)` + hand-absence ≥ 2s + reappearance -> `GLOVE_CHANGE` at **`INFERRED`** grade | Weakest detector in the system; graded honestly. Operator assertion is always the fallback. Tracked as `EXP-004`. |
| **Health** | Frame starvation, static-frame, exposure stats -> `HEALTH_DEGRADED` | Drives `PROTOCOL_ONLY` (`ADR-0011`) |

**On ArUco markers.** They are an implementation choice, not an architectural dependency —
`20` explicitly lists fiducials as *not required*, so a learned detector can be swapped in
behind the same contract. The defence is not convenience: guaranteed tool identity removes
the most dangerous perception failure (taint attributed to the wrong tool), and a sticker on
a handle is a smaller operational ask than the colour-coded allergen equipment kitchens
already buy. If time permits, add a marker-free detector as a *second* path so the demo can
show both.

Resolution 1280x720 @ 15fps. `t_dwell` = 250ms gives ~4 frames of confirmation.

## 4. Core data structures

```python
# events/ — pydantic discriminated union
Event = Annotated[Union[ZoneEntry, ContactBegin, GloveChange, ...],
                  Field(discriminator="type")]

# state/ — the ADR-0004 enforcement mechanism
@dataclass(frozen=True)
class GradedEvent:          # projection of Event with `confidence` REMOVED
    ...                     # the reducer's signature is what enforces the rule

def reduce(state: WorldState, e: GradedEvent, cfg: Config) -> tuple[WorldState, list[StateDelta]]

# risk/ — the contact graph, kept incrementally by the reducer
contacts: dict[CarrierId, list[ContactEdge]]   # (t, other, event_id), time-ordered
resets:   dict[CarrierId, list[Timestamp]]
```

**Pathway search** (backward BFS, ~60 lines, bounded by `max_hops` × ~10 active carriers):

```
find_pathways(target, allergens, t_now):
  frontier = [(target, t_now, [])]
  for hop in range(max_hops):
    for (carrier, t_upper, path) in frontier:
      for (t, other, eid) in contacts[carrier] where t < t_upper:
        if any reset on carrier within (t, t_upper): continue      # path broken
        if other is INGREDIENT zone and allergens_of(other) ∩ allergens:
            yield path + [edge]                                     # source reached
        else: extend frontier with (other, t, path + [edge])
```

Time ordering and reset-breaking are the loop conditions — there is no correlation window and
no tuned fuzz factor, which is why this needs no training and no calibration.

## 5. Storage and formats

| Artifact | Format | Why |
|---|---|---|
| Event log | **JSONL**, one file per session | Append-only by construction, human-readable, git-diffable, replayable with `cat`. No database needed. |
| Scenarios | YAML (`36`) | Hand-authored specification |
| Station + knowledge config | YAML + Pydantic validation | `31` |
| Eval reports | JSON in `data/eval/<date>/` | The gate evidence artifacts (`38`) |
| Frames | **Never written** (prod) | `24` |

## 6. UI

**FastAPI + WebSocket + a single vanilla HTML/CSS/JS page.** No build step — a bundler is
pure tax for three surfaces and a carrier grid.

- Server pushes **full state** at 5Hz over WebSocket (~2KB; deltas are premature optimization)
- Client posts `/action` -> becomes an `OPERATOR_ASSERTION` event in the log (`10`)
- Two routes: `/` worker display, `/inspector` read-only state + event timeline (`25`)

The carrier grid — tiles going amber as taint spreads — is the demo's core visual and is
built in **P3, not P6** (`37`).

### 6.1 Toolkit — and what we are deliberately avoiding

**No component library.** Component libraries are the thing that produces the generic
"AI-generated app" look — Tailwind defaults, shadcn cards, `rounded-lg` everywhere, Inter,
a purple-blue gradient. Distinctiveness comes from palette and type, which we already have.

| Need | Choice | Note |
|---|---|---|
| Design tokens | **Open Props** (single CSS file, no build) | Gives a coherent scale of sizes, easings, shadows without imposing components |
| Icons | **Phosphor Icons** | Deliberately *not* Lucide — Lucide is shadcn's default and is the single most recognisable marker of generated UI |
| Type | Archivo + IBM Plex Sans/Mono | Already chosen (`39.1`); the strongest anti-default signal on the page |
| Video overlay | **Plain SVG**, absolutely positioned over the `<video>` element | Animates with CSS classes. No library. The published mockup proves the approach. |
| Charts | none | This UI has no charts. Do not add one. |
| Live updates | WebSocket + full state at 5Hz | No library |

**Vendor every asset into `ui/static/`.** Venue wifi fails, and a CDN miss during the demo
is a black screen. No runtime network dependency of any kind.

### 6.2 The aesthetic direction

The reference is **industrial HMI — a glass cockpit or a kitchen display terminal — not web
SaaS.** That direction is what actually prevents the templated look, more than any library
choice. Concretely:

- Border radius **2-3px maximum**. Never 8-12px.
- **No box-shadows** on data surfaces; separate with 1px borders instead.
- **No gradients** anywhere.
- Monospace for every number and identifier, with `tabular-nums`.
- State encoded as **thick left borders and fills**, not rounded badge pills.
- Uppercase micro-labels with wide letter-spacing for field names.
- High-contrast dark ground — the station display commits to dark deliberately, because
  that is what a real kitchen display is. It is the one surface that does not follow the
  viewer's theme.

The published station-display mockup already implements all of this and is the approved
reference; match it rather than re-deriving it.

## 7. Enforcing the architecture mechanically

| Rule | Mechanism |
|---|---|
| Layer DAG (`22`) | `import-linter` contract in `pyproject.toml`; CI failure |
| No clock outside `runtime/` (`19`) | pytest AST walk over core packages for `time.*`/`datetime.now` |
| No `confidence` in the reducer (`ADR-0004`) | `GradedEvent` type + property test: mutate confidence, assert identical output |
| No binary data in events (`24`) | Serialization test over every event type |
| No prohibited claim words (`02`) | Lint over alert copy templates |
| Determinism (`36`) | Every fixture run twice in CI, outputs diffed |

Each is a test, not a review convention. Conventions decay within days.

## 8. Build order and parallelization

The event-log boundary is what makes this parallel. After schemas land (~2h), **four streams
run independently** and only meet at integration.

| Stream | Phases | Depends on | Can start |
|---|---|---|---|
| **A — Core** | P0 -> P1 -> P2 | — | hour 0 |
| **B — Perception** | P4 -> P5 | event schemas only | hour 2 |
| **C — Interface** | P3 | event schemas only (mock state) | hour 2 |
| **D — Content** | scenarios, knowledge bundle, station build, recordings | — | hour 0 |

| Phase | Est. | Output |
|---|---:|---|
| P0 Contracts | 2h | Types, schemas, log, config loader, lints |
| **P1 Reasoning core** | **5h** | Reducer, pathway search, tiers, alerts, replay runner, 13 fixtures green |
| P2 Orders & knowledge | 2h | Normalizer with `AMBIGUOUS`, taxonomy, recipes |
| P3 UI + `PROTOCOL_ONLY` | 4h | Three surfaces, carrier grid, evidence trace |
| P4 Perception: zones/contact | 5h | Calibration, HSV gloves, contact episodes, occlusion |
| P5 Perception: tools/resets | 3h | ArUco tools, swaps, glove change |
| P6 Demo hardening | 3h | Frozen calibration, fallbacks, 5 clean runs |

~24 focused hours; ~14h on the critical path with four people.

**Estimated total: ~3,900 LOC** (core ~1,700, perception ~600, UI ~400, tests ~800,
scripts ~400).

## 9. The cut line

> **Ship P0-P3. Everything after is upside.**

At the end of P3 there is a complete, demoable, honest product running in `PROTOCOL_ONLY`
with no camera attached: tickets bind, Tier 0 fires with recipe-scoped checklists, workers
resolve in one tap, Tier 2 holds work, evidence traces render. That is a real product and a
real demo.

P4-P5 add the observation that makes it compelling. They are **not** load-bearing for having
something to show — which is the entire point of building the core first.

## 10. Hardware

Folding table · overhead camera (USB webcam on a boom, or an iPhone via Continuity Camera —
better optics, free) · 4 labelled bins · cutting board · spreader · glove box · clean-tool
rack · printed ArUco markers · laptop or tablet for the display. **Marginal cost ≈ $0.**

## 11. Top implementation risks

| Risk | Mitigation | Fallback |
|---|---|---|
| HSV glove segmentation fails under venue lighting | `scripts/tune_hsv.py` live slider tool; calibrate at the venue, not at home | MediaPipe Hands; failing that, ArUco wristband |
| Glove-change detection unreliable (`EXP-004`) | Graded `INFERRED`, never `OBSERVED` | Operator assertion — already a designed path, not a patch |
| Camera dies during the demo | Rehearsed drill | `PROTOCOL_ONLY` -> recorded log -> `scenarios/demo.yaml`, all producing identical UI |
| P1 overruns | It is the critical path and the novel part; staff it with the strongest person | Nothing else may start before it — this is deliberate |
| Scope creep into food recognition | `ADR-0007`; reviewers reject on sight | — |
