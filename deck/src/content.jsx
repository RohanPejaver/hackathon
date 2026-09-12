// Every word on screen, by scene id. No em dashes anywhere in this file.
import React from 'react'

export const PRODUCT = 'Sequence'
export const TAG = 'allergen safety layer for one prep station'

export const Brand = ({ big = false }) => (
  <div className={'brand' + (big ? ' big' : '')}><span className="b1">Se</span><span className="b2">que</span><span className="b3">nce</span><span className="dot">.</span></div>
)

// Slide 3: the sequence of actions. Step 1 introduces pine nut; it spreads forward.
export const STEPS = [
  { t: 'Gloves into the pesto', c: 'pine nut on the gloves', src: true },
  { t: 'Gloves pick up the spreader', c: 'pine nut on the spreader' },
  { t: 'Spreader spreads on the board', c: 'pine nut on the board' },
  { t: 'Same gloves into the shared mayo', c: 'pine nut in the mayo' },
  { t: 'That mayo goes on ticket 48', c: 'pine-nut allergy: pathway open', target: true },
]
export const STEP_DT = 1.6   // seconds per step (0.5 s slower than before)

export const SCENE_TEXT = {
  intrigue: (
    <div className="corner-tl" style={{ gap: 6 }}>
      <Brand big />
      <div className="micro" style={{ fontSize: 'clamp(20px, 1.6vw, 28px)', color: 'var(--ink-1)' }}>{TAG}</div>
    </div>
  ),
  failure: (
    <>
      <div className="corner-tl">
        <div className="frost amber-edge" style={{ maxWidth: '52vw' }}>
          <h1 className="h2">The shared mayo is now a <span className="amber">pine-nut carrier.</span></h1>
          <p className="lede" style={{ marginTop: 16 }}>In a restaurant, this is never tracked. Not by the ticket, not by the POS, not by the cook.</p>
        </div>
      </div>
      <div className="corner-bl">
        <div className="micro petal" style={{ fontSize: "clamp(17px, min(1.4vw, 2.4vh), 24px)" }}>The two tickets</div>
        <div className="tickets">
          <div className="ticket">
            <span className="id">#47</span><span className="life">done</span>
            <div className="items">Pesto sandwich</div>
            <div className="restr none">no restriction</div>
          </div>
          <div className="ticket restricted">
            <span className="id">#48</span><span className="life">10 min later</span>
            <div className="items">Turkey sandwich with mayo</div>
            <div className="restr">PINE_NUT <span className="raw">"pine nut allergy"</span></div>
          </div>
        </div>
      </div>
      <div className="corner-tr">
        <div className="frost" style={{ maxWidth: '30vw', textAlign: 'right' }}>
          <div className="h3"><span className="petal">1 in 3</span> adult food-allergy reactions happen in a restaurant.</div>
          <div className="micro" style={{ marginTop: 10 }}>FARE patient registry</div>
        </div>
      </div>
    </>
  ),
  insight: null,   // Sequence component (animated)
  reveal: (
    <>
      <div className="corner-tl"><Brand /></div>
      <div className="corner-bl">
        <div className="frost petal-edge" style={{ maxWidth: '62vw' }}>
          <div className="micro petal" style={{ marginBottom: 14 }}>{TAG} · food track</div>
          <h2 className="h2" style={{ maxWidth: 'none', fontWeight: 600 }}>
            A live model of what every <span className="petal">glove</span>, <span className="petal">tool</span>, <span className="petal">surface</span> and <span className="petal">shared container</span> is carrying, and a check that the glove reset actually happened before an <span className="leaf">allergen-free</span> order starts.
          </h2>
        </div>
      </div>
    </>
  ),
  how: (
    <div className="arch">
      <div className="arch-head">
        <div className="micro petal">Why it was hard</div>
        <h1 className="h2" style={{ maxWidth: 'none' }}>One boundary. One pure fold. AI only after the fact.</h1>
      </div>
      <div className="arch-row" data-i="0">
        <div className="arch-lbl">Perception<span>probabilistic, ephemeral, never stored</span></div>
        <div className="arch-box"><b>Station frame</b><span>4 ArUco fiducials, homography, pixel to mm</span></div><i>→</i>
        <div className="arch-box"><b>Segmentation</b><span>HSV glove blobs, ArUco tool ids, polygon zones</span></div><i>→</i>
        <div className="arch-box"><b>Tracker</b><span>occlusion reported as an event, identity-suspect merges</span></div><i>→</i>
        <div className="arch-box"><b>Assembler</b><span>dwell + hysteresis episodes, confidence thresholded to a grade</span></div>
      </div>
      <div className="arch-boundary"><i>↓</i> committed events only: 33 typed events, discriminated unions, the import graph is linted <i>↓</i></div>
      <div className="arch-row" data-i="1">
        <div className="arch-lbl">Reasoning<span>deterministic, pure, no clock, no I/O</span></div>
        <div className="arch-box hard"><b>Append-only log</b><span>reorder buffer, JSONL, byte-identical replay</span></div><i>→</i>
        <div className="arch-box hard"><b>Reducer fold</b><span>taint × epistemic state per carrier, pessimistic closure, wipe ≠ reset</span></div><i>→</i>
        <div className="arch-box hard"><b>Risk engine</b><span>bounded backward search over the temporal contact graph, reset breaks the path</span></div><i>→</i>
        <div className="arch-box hard"><b>Policy + display</b><span>tier by evidence grade, dedup by pathway signature, 5 Hz, ≤ 2 taps</span></div>
      </div>
      <div className="arch-row ai" data-i="2">
        <div className="arch-lbl">AI, read-only<span>after service, over the log, never in the alert path</span></div>
        <div className="arch-box ai"><b>Ask the audit log in plain English</b><span>An LLM compiles "every near-miss at station 3 last week" into a typed query over the event log. Answers are event ids, never a verdict.</span></div><i>→</i>
        <div className="arch-box ai"><b>Retrospective incident summaries</b><span>Tier 1 and 2 incidents clustered per shift and summarised for the shift lead. Every sentence cites the events behind it.</span></div>
        <div className="arch-note">The model reads the log. It never writes to it and never touches a live alert.</div>
      </div>
    </div>
  ),
  receipt: (
    <div className="impact">
      <div className="micro petal">What changes at scale</div>
      <h1 className="h2" style={{ maxWidth: 'none' }}>Every one of these starts as an 8-second prompt.</h1>
      <div className="numbers">
        <div className="num amber"><div className="v">200,000<small>+</small></div><div className="k">emergency visits a year in the US from food allergy reactions</div><div className="s">one every 3 minutes · FARE</div></div>
        <div className="num petal"><div className="v">1<small> in </small>3</div><div className="k">adult reactions happen in a restaurant</div><div className="s">FARE patient registry</div></div>
        <div className="num leaf"><div className="v">8<small> s</small></div><div className="k">the cost of a Sequence reset prompt</div><div className="s">versus a remake, or an ambulance</div></div>
      </div>
      <div className="proj">
        <div className="proj-k">Projection</div>
        <div className="proj-v">At <b>10%</b> of US restaurant prep stations, catching <b>1 in 4</b> kitchen cross-contact reactions: <b className="petal">about 1,700 emergency visits a year</b> that never happen.</div>
        <div className="proj-s">200,000 × ⅓ in restaurants × 10% coverage × 25% caught. Assumptions on the slide on purpose.</div>
      </div>
      <div className="proven">Proven today, on the scenario suite: <b>14/14</b> hazard scenarios caught · <b>0</b> silent misses · <b>533</b> tests, same answer every run.</div>
    </div>
  ),
  different: (
    <div className="cmp-wrap">
      <div className="corner-tl"><Brand /></div>
      <div className="cmp-head">
        <div className="micro petal">Versus the status quo</div>
        <h1 className="h2" style={{ maxWidth: 'none' }}>Today's tools trust memory. Sequence checks the record.</h1>
      </div>
      <div className="cmp">
        <div className="cmp-h"></div>
        <div className="cmp-h">Training + checklists</div>
        <div className="cmp-h">POS allergy flag</div>
        <div className="cmp-h">Food-recognition camera</div>
        <div className="cmp-h us">Sequence</div>
        {[
          ['Knows what each glove, tool and container is carrying right now', 0, 0, 0, 1],
          ['Knows a shared container just became a carrier', 0, 0, 0, 1],
          ['Checks the reset actually happened before the order starts', 0, 0, 0, 1],
          ['Every alert is a rule chain a cook can dispute in one tap', 0, 0, 0, 1],
          ['Keeps working with the camera unplugged', 1, 1, 0, 1],
          ['Replays any incident byte-for-byte', 0, 0, 0, 1],
        ].map(([r, a, b, c, d], i) => (
          <React.Fragment key={i}>
            <div className="cmp-r">{r}</div>
            <div className={'cmp-c' + (a ? ' y' : '')}>{a ? '✓' : '✗'}</div>
            <div className={'cmp-c' + (b ? ' y' : '')}>{b ? '✓' : '✗'}</div>
            <div className={'cmp-c' + (c ? ' y' : '')}>{c ? '✓' : '✗'}</div>
            <div className={'cmp-c us' + (d ? ' y' : '')}>{d ? '✓' : '✗'}</div>
          </React.Fragment>
        ))}
      </div>
      <div className="micro petal cmp-foot">Uncertainty lowers the tier. It never lowers the bar.</div>
    </div>
  ),
  implication: (
    <>
      <div className="corner-tl">
        <div className="micro amber">bin:pesto → gloves → bin:mayo → ticket #48</div>
      </div>
      <div className="corner-bl" style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 40, bottom: '4vh' }}>
        <div className="frost petal-edge" style={{ maxWidth: '56vw', padding: '22px 30px' }}>
          <h1 className="h3" style={{ fontSize: 'clamp(26px, min(2.4vw, 4.2vh), 42px)' }}>It doesn't replace the protocol.<br /><span className="petal">It checks that the protocol happened.</span></h1>
        </div>
        <div className="brand big" style={{ fontSize: 'clamp(64px, min(6.5vw, 11vh), 118px)' }}><span className="b1">Se</span><span className="b2">que</span><span className="b3">nce</span><span className="dot">.</span></div>
      </div>
    </>
  ),
}

const B = ({ title, items }) => (
  <div className="backup">
    <div><div className="micro petal" style={{ marginBottom: 12 }}>backup · for questions</div><h2 className="h2">{title}</h2></div>
    <ul>{items.map((it, i) => <li key={i} className={it.amber ? 'amber' : ''} dangerouslySetInnerHTML={{ __html: it.t }} />)}</ul>
  </div>
)

export const BACKUP_TEXT = {
  'b-arch': <B title="Architecture: twelve layers, one boundary" items={[
    { t: '<b>Sensing, Perception, Tracking, Assembly</b> are probabilistic and ephemeral; they emit <b>committed Events</b> and nothing else crosses.', amber: true },
    { t: '<b>Log, State, Risk, Policy, UI</b> is a pure fold: <code>WorldState(t) = fold(reduce, Log[0..t], Init, Config)</code>.' },
    { t: 'Import-linter enforces the DAG (8 contracts): <b>state/risk/policy/orders can never import perception</b>. CI rejects a planted violation.' },
    { t: 'Confidence is thresholded into a <b>grade</b> at the boundary (OBSERVED > INFERRED > ASSERTED > PESSIMISTIC). The reducer type omits the float.' },
    { t: 'Two axes per carrier: <b>taint</b> (what it may hold) and <b>epistemic</b> (TRACKED / STALE / UNKNOWN). Never collapsed.' },
    { t: 'Two algorithms, two tiers: cheap precondition check at bind (Tier 0, no evidence needed); bounded backward pathway search on contact (Tier 1/2, OBSERVED only).' },
    { t: 'Single Python process, FastAPI + WebSocket at 5 Hz, vanilla display. No database: the log is JSONL.' },
    { t: 'Runtime modes: FULL, PROTOCOL_ONLY, REPLAY, CALIBRATION. REPLAY replaces layers 1 to 4 only; layers 5 to 12 are byte-identical.' },
  ]} />,
  'b-built': <B title="What we built, and what is pending" items={[
    { t: '<b>Built and verified:</b> domain + 33-type event catalog, reducer with the full transition table, knowledge closure, pathway search, tier policy with dedup/escalation/cooldown, orders with mandatory AMBIGUOUS, replay runner, 14 fixtures, runtime, worker display + inspector.', amber: true },
    { t: '<b>Implemented, gate pending:</b> perception (ArUco station frame, HSV glove segmentation, marker identity, tracker with occlusion honesty, dwell/hysteresis), 59 synthetic-frame tests; real-footage gate needs the 12 annotated clips.' },
    { t: '<b>Not built (by design):</b> rag/wipe-cloth tracking, wash efficacy, multi-station, POS integration, manager dashboard, any "verified safe" signal.' },
    { t: 'Spec first: 17 architecture docs and 12 ADRs before code; every phase gate has an evidence artifact in <b>data/eval/2026-09-12/</b>.' },
    { t: '533 tests (unit, property, replay, integration, perception); mypy --strict on the core; ruff; lint-imports.' },
    { t: 'First commit today 05:22; a bug report is a scenario file, and the fixture becomes a permanent regression test.' },
  ]} />,
  'b-eval': <B title="Evaluation: intervention metrics, not detection metrics" items={[
    { t: '<b>Intervention Recall</b>: correct-tier intervention before the item completes. Target 0.90 or better. <b>Measured 1.0</b> on the scenario suite.', amber: true },
    { t: '<b>Silent Miss Rate</b>: no intervention AND the system claimed TRACKED-clean. Target 0, gate-blocking. <b>Measured 0.</b>', amber: true },
    { t: '<b>Nuisance Rate</b>: Tier 1+2 per hour of normal prep. Tier 0 excluded by design. Target under 1.0/h. <b>Not yet measured</b> (needs 30 min of recorded normal prep).' },
    { t: '<b>Tier 0 compliance</b> and <b>pessimistic-closure rate</b> instrument the real adoption risk: prompt fatigue (assumption A6).' },
    { t: 'Determinism: every fixture is run twice in CI and the outputs diffed. Level 2 (recorded log) and level 3 (fixture) of the fallback ladder produce identical UI.' },
    { t: 'Latency targets: reducer p99 under 50 ms, contact-to-alert under 1.5 s. Targets, not measured on hardware.' },
  ]} />,
  'b-fail': <B title="Failure modes: degraded perception raises conservatism, lowers cost" items={[
    { t: '<b>Carrier not observed</b>: STALE/UNKNOWN, pessimistic closure, Tier 0 at next bind. Occlusion is an input, not a failure.', amber: true },
    { t: '<b>Camera fault</b>: PROTOCOL_ONLY. All carriers UNKNOWN, Tier 0 on every restricted bind, Tier 1 disabled, Tier 2 holds persist (scenario L).' },
    { t: '<b>Tracker identity ambiguity</b>: taint sets merged pessimistically, both STALE. Never reassigned silently (scenario K).' },
    { t: '<b>False positive</b> (swap happened off camera): "Replacement not observed." One tap, ASSERTED grade, never promoted to OBSERVED (scenario D).' },
    { t: '<b>False negative</b> (unmodelled transfer, e.g. a splash): not a silent miss if the carriers were already reported unverified and Tier 0 fired (scenario E).' },
    { t: '<b>Ambiguous restriction</b> ("ALLERGY"): binding blocked, routed to front of house. The system asks; it never guesses (scenario G).' },
    { t: '<b>Alert storm</b>: one alert per pathway signature, cooldown, escalation at COMPLETE (scenario M).' },
  ]} />,
  'b-percep': <B title="Perception: deterministic, explainable, honest about blindness" items={[
    { t: 'Station frame from <b>4 ArUco corner markers and a homography</b> (pixel to mm). Zones are polygons in mm from config, not detections.', amber: true },
    { t: 'Gloves by <b>HSV colour segmentation</b> (nitrile blue/purple), tools by <b>ArUco markers on handles</b>: guaranteed identity, no training data.' },
    { t: 'Contact = centroid inside polygon held for t_dwell with hysteresis. Occlusion over t_max emits CARRIER_OBSERVABILITY_CHANGED. Glove change is graded INFERRED, never OBSERVED.' },
    { t: 'Status: <b>verified on synthetic frames</b> (59 tests, synthetic video to ZONE_ENTRY to gloves tainted). Real-footage gate pending the recorded clips.' },
    { t: 'Frames are never persisted. Confidence never leaves the boundary as a float.' },
  ]} />,
  'b-privacy': <B title="Boundaries and privacy" items={[
    { t: 'The system may say: "a hand entered the pesto zone at T", "no glove change was observed between T1 and T2", "this station\'s state is not currently verifiable".', amber: true },
    { t: 'It is structurally unable to say "safe", "allergen-free", "contamination occurred", or anything about a named person. No identity fields exist; copy is linted.' },
    { t: 'The human decides at every tier: the system proposes, holds, records. It never releases a hold and never contacts a customer.' },
    { t: 'One configured station. Not food recognition. Not cleaning efficacy. Not a replacement for training, labelling, or existing allergy protocol.' },
    { t: 'Data: event log (no images), evidence traces, health. Retained for the audit window; no frames, no identities.' },
  ]} />,
  'b-next': <B title="Next, in order" items={[
    { t: 'Record the 12 annotated clips + 30 min normal prep; run the P4 gate; measure nuisance rate and pessimistic-closure rate (assumption A6, the real adoption risk).', amber: true },
    { t: 'Five consecutive clean live runs before any live demo is trusted (P6 gate).' },
    { t: 'EXP-001 max_hops; EXP-002 depth signal for reach-over vs reach-in; EXP-004 glove-change detectability.' },
    { t: 'Manager escalation on unresolved Tier 2 (transition already reserved in the alert model).' },
    { t: 'Rag as a TOOL-kind carrier (schema supports it today; perception does not detect it).' },
  ]} />,
}
