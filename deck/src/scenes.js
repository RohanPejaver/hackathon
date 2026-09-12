// Scene list + camera poses + station timelines. Deterministic: every animation is a pure
// function of (scene, seconds since scene entry). Going back replays it identically.

// Station frame from config/station/demo.yaml (mm). 1 unit = 100 mm. x right, z toward camera.
export const mm = (x, y) => [(x - 600) / 100, -(y - 300) / 100]
export const ZONES = {
  pesto:  { x: [70, 270],   y: [370, 570], kind: 'jar',   label: 'Pesto',  sub: 'contains pine nut', carrier: 'bin:pesto' },
  mayo:   { x: [330, 530],  y: [370, 570], kind: 'jar',   label: 'Mayo',   sub: 'shared jar',        carrier: 'bin:mayo' },
  turkey: { x: [590, 790],  y: [370, 570], kind: 'tray',  label: 'Turkey', sub: 'sliced',            carrier: 'bin:turkey' },
  bread:  { x: [850, 1050], y: [370, 570], kind: 'loaf',  label: 'Bread',  sub: '',                  carrier: 'bin:bread' },
  work:   { x: [300, 700],  y: [60, 320],  kind: 'board', label: 'Board',  sub: 'cutting board',     carrier: 'board' },
  landing:{ x: [740, 1000], y: [60, 320],  kind: 'plate', label: 'Plate',  sub: 'finished order',    carrier: 'landing' },
  rack:   { x: [40, 260],   y: [200, 320], kind: 'rack',  label: 'Spreader', sub: 'shared tool',     carrier: 'spreader' },
  stock:  { x: [60, 240],   y: [80, 180],  kind: 'stock', label: 'Clean stock', sub: '' },
  gloves: { x: [1080, 1180],y: [380, 560], kind: 'dispenser', label: 'Glove box', sub: '' },
  wash:   { x: [1040, 1180],y: [60, 320],  kind: 'wash',  label: 'Sink', sub: '' },
}
export const center = (z) => {
  const [x, zz] = mm((z.x[0] + z.x[1]) / 2, (z.y[0] + z.y[1]) / 2)
  return [x, zz]
}
export const size = (z) => [(z.x[1] - z.x[0]) / 100, (z.y[1] - z.y[0]) / 100]

export const POSES = {
  overhead:      { pos: [0, 14.6, 0.1],  look: [0, 0, -1.0] },
  overheadFar:   { pos: [0, 19, 1],      look: [0, 0, 0] },
  overheadFit:   { pos: [0, 17.5, 2.5],  look: [0, 0, 0.6] },
  overheadClose: { pos: [0.4, 9.5, 3.2], look: [0.4, 0, -0.8] },
  threeQuarter:  { pos: [7.5, 6.5, 8.5], look: [0.2, 0, -0.4] },
  lowInside:     { pos: [-3.0, 4.2, 10.5],look: [-0.6, 0.3, -1.6] },
  diagram:       { pos: [1, 15.5, 13.5], look: [4.6, 0, -0.3] },
  overheadUp:    { pos: [0, 14.2, 1.8],  look: [0, 0, 1.0] },
  side:          { pos: [12, 5.5, 5.5],  look: [4.2, 0, -0.6] },
}

const P = {
  board:  center(ZONES.work),
  pesto:  center(ZONES.pesto),
  mayo:   center(ZONES.mayo),
  bread:  center(ZONES.bread),
  landing: center(ZONES.landing),
  rack:   center(ZONES.rack),
  park:   [2.2, 2.6],
}
const smooth = (t) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t))
const lerp2 = (a, b, k) => [a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k]

function pathAt(keys, t) {
  if (t <= keys[0].t) return { xz: P[keys[0].at], y: 1.6, dip: 0 }
  for (let i = 0; i < keys.length - 1; i++) {
    const a = keys[i], b = keys[i + 1]
    if (t >= a.t && t < b.t) {
      const k = smooth((t - a.t) / (b.t - a.t))
      const xz = lerp2(P[a.at], P[b.at], k)
      const moving = a.at !== b.at
      const arc = moving ? Math.sin(k * Math.PI) * 0.9 : 0
      const dipA = a.dip ? 1 : 0, dipB = b.dip ? 1 : 0
      const y = 0.55 + arc + (moving ? 0.9 : dipA ? 0.35 : 0.9)
      return { xz, y, dip: moving ? 0 : dipA * dipB }
    }
  }
  const last = keys[keys.length - 1]
  return { xz: P[last.at], y: last.dip ? 0.9 : 1.5, dip: last.dip ? 1 : 0 }
}

const REACH = [
  { t: 0.0, at: 'board' }, { t: 0.9, at: 'board' },
  { t: 1.8, at: 'pesto' }, { t: 2.6, at: 'pesto', dip: 1 },
  { t: 3.5, at: 'mayo' }, { t: 4.4, at: 'mayo', dip: 1 },
  { t: 5.3, at: 'park' },
]

export function stationAt(sceneId, t) {
  const out = { hand: null, taint: {}, unknown: false, pathway: 0, labels: 'all', dim: 0 }
  const ramp = (t0, dur = 0.5) => Math.min(1, Math.max(0, (t - t0) / dur))
  switch (sceneId) {
    case 'intrigue': {
      out.hand = pathAt(REACH, t)
      out.taint = { gloves: ramp(2.3), 'bin:mayo': ramp(4.1) }
      out.labels = 'all'
      return out
    }
    case 'failure': {
      out.hand = { xz: P.park, y: 1.5 }
      out.taint = { gloves: 1, 'bin:mayo': 1 }
      out.labels = 'all'
      return out
    }
    case 'insight': {
      out.hand = null
      out.taint = { gloves: 1, 'bin:mayo': 1, spreader: 1, board: 1 }
      out.labels = 'none'
      out.dim = 0.6
      return out
    }
    case 'reveal': {
      out.hand = { xz: P.park, y: 1.5 }
      out.taint = { gloves: 1, 'bin:mayo': 1, spreader: 1, board: 1 }
      out.labels = 'all'
      out.dim = 0.15
      return out
    }
    case 'how': {
      out.hand = null
      out.labels = 'none'
      out.dim = 1
      return out
    }
    case 'receipt': {
      out.hand = null
      out.labels = 'none'
      out.dim = 1
      return out
    }
    case 'different': {
      out.hand = null
      out.unknown = t > 0.8
      out.labels = 'none'
      out.dim = 0.45
      return out
    }
    case 'implication': {
      out.hand = { xz: [P.mayo[0] - 0.9, P.mayo[1] + 1.25], y: 1.05 }
      out.taint = { gloves: 1, 'bin:mayo': 1 }
      out.labels = 'taint'
      out.pathway = ramp(0.6, 2.4)
      out.dim = 0.25
      return out
    }
    default: {
      out.hand = null
      out.labels = 'none'
      out.dim = 1
      return out
    }
  }
}

export const PATHWAY = [
  [...center(ZONES.pesto)],
  [P.mayo[0] - 1.3, P.mayo[1] + 1.3],
  [...center(ZONES.mayo)],
  [...center(ZONES.landing)],
]

export const SCENES = [
  { id: 'intrigue',    pose: 'overhead',      hud: '0:00 intrigue' },
  { id: 'failure',     pose: 'threeQuarter',  hud: '0:10 failure' },
  { id: 'insight',     pose: 'lowInside',     hud: '0:25 sequence' },
  { id: 'reveal',      pose: 'overheadFit',   hud: '0:40 reveal' },
  { id: 'demo',        pose: 'overheadClose', hud: '0:50 DEMO', demo: true },
  { id: 'how',         pose: 'diagram',       hud: '1:45 how' },
  { id: 'receipt',     pose: 'overheadFar',   hud: '2:10 receipt' },
  { id: 'different',   pose: 'side',          hud: '2:25 differentiation' },
  { id: 'implication', pose: 'overheadUp',    hud: '2:38 close' },
]
export const BACKUP = [
  { id: 'b-arch',     pose: 'overheadFar', hud: 'backup · architecture' },
  { id: 'b-built',    pose: 'overheadFar', hud: 'backup · what we built' },
  { id: 'b-eval',     pose: 'overheadFar', hud: 'backup · evaluation' },
  { id: 'b-fail',     pose: 'overheadFar', hud: 'backup · failure modes' },
  { id: 'b-percep',   pose: 'overheadFar', hud: 'backup · perception' },
  { id: 'b-privacy',  pose: 'overheadFar', hud: 'backup · privacy & boundaries' },
  { id: 'b-next',     pose: 'overheadFar', hud: 'backup · next' },
]
