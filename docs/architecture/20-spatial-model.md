# Spatial Model

Stated as **requirements on information**, not as a choice of vision method. Any technique
that satisfies this contract is acceptable (`21`).

## Station frame

A 2D planar coordinate system fixed to the work surface, in millimetres, origin at a
physical fiducial on the station. All spatial reasoning happens in this frame — never in
pixel coordinates — so that camera movement, resolution changes, or a different lens are
recalibration, not a data-model change.

Established once during `CALIBRATION` mode and stored as `station_config.calibration`,
versioned. A calibration change invalidates recorded fixtures and must bump
`config_version`.

## Zones

```
Zone { zone_id, polygon: List<Point2D>, kind, contents, bound_carrier }
```

Zone kinds: `INGREDIENT`, `TOOL_RACK`, `CLEAN_STOCK`, `WORK`, `LANDING`,
`GLOVE_DISPENSER`, `WASH`.

Zones are **configuration, authored once**. This is the decision that makes the whole
perception problem tractable: the system never asks "what substance is this," it asks "did a
tracked entity enter polygon 7," and configuration supplies the meaning (`ADR-0007`).

Zones may overlap. When a contact point falls in multiple zones, **all** matching zones
receive a contact event; the reducer's union semantics make this safe by construction rather
than requiring a tie-break rule.

## What the architecture requires

| Requirement | Why |
|---|---|
| Stable planar coordinate frame | Zone membership must mean the same thing over time |
| Polygonal zone membership test | Contact predicate |
| A contact point (or small region) per tracked entity | The thing tested against zones |
| Stable entity identity across frames | Taint must follow the right carrier |
| Occlusion signal | Drives epistemic degradation (`13`) |

## What it explicitly does **not** require

Depth sensing, 3D pose, hand keypoints, food classification, material recognition, multiple
cameras, or fiducial markers on tools. Each of these is a possible improvement; none may
become a hidden dependency. If a design begins to need one, that is an ADR, not an
implementation detail.

## Contact predicate

```
contact(entity, zone) := point_in_polygon(entity.contact_point, zone.polygon)
                         AND dwell >= t_dwell
                         AND hysteresis satisfied
```

Carrier-to-carrier contact uses region intersection over `t_dwell` in the same frame.

## Known spatial limitations (recorded, not hidden)

- A hand passing **over** a bin without entering it is indistinguishable from entering it
  under a purely 2D overhead projection. Mitigated by `t_dwell` and, if needed, a depth
  signal — deferred, tracked in `experiments/`.
- Zone boundaries are crisp; physical reality is not. Contact near an edge is decided by the
  polygon, which can be wrong in both directions. Zones should be authored slightly
  **generous** for `INGREDIENT` kinds (false contact -> Tier 0, cheap) and slightly
  **conservative** for `CLEAN_STOCK` (false reset would be dangerous). This asymmetry is a
  documented authoring rule in `31`.
