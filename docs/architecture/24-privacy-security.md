# Privacy and Security

Privacy here is an **adoption requirement**, not a compliance checkbox. A camera over a
worker's hands that reports their mistakes is, from that worker's perspective, a
disciplinary instrument — and systems perceived that way get unplugged. The data model is
built so the system is structurally incapable of being one.

## Data lifecycle — exhaustive

| Data | Exists where | Persisted | Retention | Leaves the host |
|---|---|---|---|---|
| Raw frames | Process memory, ring buffer | **No** (production) | `frame_buffer_seconds`, default 3 | **Never** |
| Detections / tracks | Process memory | No | Frame lifetime | Never |
| **Events** | Log | Yes | Service period + `audit_days` (7) | Only via explicit export |
| `WorldState` snapshots | Log store | Yes | Same as events | Never |
| Alerts + derivations | Log | Yes | Same as events | Only via export |
| Station / knowledge config | Disk | Yes | Until changed | Read-only inbound |
| Ticket restriction + items | Log | Yes | Service period | Never |
| Worker identity | **Nowhere** | — | — | — |
| Customer identity | **Nowhere** | — | — | — |

## Structural guarantees

1. **No worker identity exists.** The only worker field anywhere is `worker_slot: int`, a
   position at the station. No names, ids, biometrics, or per-person metrics. A future
   "which worker causes the most alerts" feature is **architecturally unavailable**, which is
   deliberate — the moment it exists, staff cooperation ends.
2. **No customer identity exists.** Tickets carry restriction + items. No name, contact,
   payment, or address. Ticket ids are opaque and rotate per service period.
3. **No pixels cross a process boundary.** Events carry zone ids, carrier ids, timestamps,
   confidences. `EvidenceRef` holds track ids and a frame *range*, never image data. Tested
   by a serialization test asserting no event type can carry a binary blob.
4. **Frame persistence is off by default**, gated behind `capture.persist_frames`, which is
   only settable in dev/eval profiles, writes to a gitignored path, and logs a loud warning
   at startup.

## A deliberate rejection: evidence video clips

Attaching a short clip to each alert would make alerts far more persuasive to a manager. It
is **rejected for MVP** because it requires persisting frames, which voids guarantee 4 and
converts the system into a recording device — the exact thing that makes staff hostile.
The **evidence trace** (`25`) is the substitute: structural rather than visual.

Recorded here rather than left implicit because this is the first feature a stakeholder will
request, and reversing it should require an ADR.

## Threat model

| Asset | Threat | MVP control | Production path |
|---|---|---|---|
| Station config / zone map | Silent tamper -> wrong allergen mapping -> silent failure | Checksum + version, `CONFIG_LOADED` in log, startup validation | Signed bundles, change approval |
| Knowledge bundle | Same — **highest-value target in the system** | Same | Same + independent review |
| Event log | Tamper to erase a hazard | Append-only in-process, gapless `seq` | Append-only store, hash chain |
| Alert channel | Suppression -> safety event | Single process, no network | Authenticated transport, heartbeat |
| Video stream | Exfiltration | Never leaves the process; no network egress path exists in code | Same, plus attestation |
| Admin/config UI | Highest-privilege surface | **Not exposed in MVP**; config is files on disk | AuthN/Z, audit trail |

**Deliberately out of scope for MVP:** authentication, multi-tenancy, TLS, RBAC, network
transport. The MVP is single-host, loopback-only, with no network egress of any media. This
is appropriate for a hackathon *and* it is the honest security posture: fewer surfaces
rather than shallow controls over many.

## The line that is never crossed

Nothing in the safety core may depend on a network. `PROTOCOL_ONLY` runs fully offline. A
system that stops protecting people when the WiFi drops is not a safety layer.
