import React, { useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import { Html, ContactShadows, Environment, Lightformer, Preload, RoundedBox } from '@react-three/drei'
import * as THREE from 'three'
import { ZONES, center, size, POSES, stationAt, PATHWAY } from './scenes.js'

const AMBER = new THREE.Color('#ffb340')
const STEEL = '#1f1c2b'
// floral, food-representative colours
const C = { pesto: '#6f9d4f', pestoLid: '#3f5e2c', mayo: '#f3e9c9', mayoLid: '#c9b27a', turkey: '#e8a2a9', turkeyTray: '#2b2637', bread: '#d9b56f', board: '#8b6a4f', plate: '#e9e4f0', tool: '#c9cbd6', glove: '#8aa0ff', rack: '#2a2538', stock: '#2a2538', sink: '#23202f' }

function CameraRig({ pose }) {
  const { camera } = useThree()
  const target = useMemo(() => new THREE.Vector3(...POSES.overhead.look), [])
  const goal = useRef({ pos: new THREE.Vector3(...POSES.overhead.pos), look: new THREE.Vector3(...POSES.overhead.look) })
  const p = POSES[pose] || POSES.overhead
  goal.current.pos.set(...p.pos)
  goal.current.look.set(...p.look)
  useFrame((_, dt) => {
    const k = 1 - Math.exp(-dt * 4.2)
    camera.position.lerp(goal.current.pos, k)
    target.lerp(goal.current.look, k)
    camera.lookAt(target)
  })
  return null
}

// Material that blends toward amber with `taint` and greys out when `unknown`.
function useTaintMaterial(base, taint, unknown) {
  const ref = useRef()
  const baseC = useMemo(() => new THREE.Color(base), [base])
  const grey = useMemo(() => new THREE.Color('#3b3748'), [])
  useFrame(() => {
    const m = ref.current
    if (!m) return
    const c = unknown ? grey : baseC.clone().lerp(AMBER, taint * 0.75)
    m.color.lerp(c, 0.12)
    m.emissive.lerp(unknown ? new THREE.Color('#000') : AMBER.clone().multiplyScalar(taint * 0.5), 0.12)
    m.opacity += ((unknown ? 0.55 : 1) - m.opacity) * 0.12
  })
  return ref
}
function TaintMaterial({ base, taint, unknown, roughness = 0.75 }) {
  const ref = useTaintMaterial(base, taint, unknown)
  return <meshStandardMaterial ref={ref} color={base} roughness={roughness} metalness={0.05} transparent />
}

function Jar({ zone, taint, unknown, body, lid, open = false }) {
  const [x, z] = center(zone)
  const r = Math.min(...size(zone)) * 0.38
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.5, 0]} castShadow receiveShadow>
        <cylinderGeometry args={[r, r * 0.92, 1.0, 40]} />
        <TaintMaterial base={body} taint={taint} unknown={unknown} />
      </mesh>
      {open ? (
        <mesh position={[0, 1.001, 0]} rotation={[-Math.PI / 2, 0, 0]}><circleGeometry args={[r * 0.86, 40]} /><meshStandardMaterial color={lid} roughness={1} /></mesh>
      ) : (
        <mesh position={[0, 1.08, 0]} castShadow><cylinderGeometry args={[r * 1.04, r * 1.04, 0.16, 40]} /><meshStandardMaterial color={lid} roughness={0.6} /></mesh>
      )}
    </group>
  )
}
function Tray({ zone, taint, unknown }) {
  const [x, z] = center(zone); const [w, d] = size(zone)
  return (
    <group position={[x, 0, z]}>
      <mesh position={[0, 0.15, 0]} castShadow receiveShadow><boxGeometry args={[w - 0.4, 0.3, d - 0.4]} /><meshStandardMaterial color={C.turkeyTray} roughness={0.8} /></mesh>
      {[0, 1, 2].map((i) => (
        <mesh key={i} position={[(i - 1) * 0.42, 0.34 + i * 0.03, (i - 1) * -0.18]} rotation={[0, i * 0.25, 0]} castShadow>
          <cylinderGeometry args={[0.62, 0.62, 0.06, 32]} />
          <TaintMaterial base={C.turkey} taint={taint} unknown={unknown} roughness={0.9} />
        </mesh>
      ))}
    </group>
  )
}
function Loaf({ zone, taint, unknown }) {
  const [x, z] = center(zone); const [w, d] = size(zone)
  return (
    <group position={[x, 0, z]}>
      <RoundedBox args={[w - 0.6, 0.7, d - 0.7]} radius={0.28} smoothness={6} position={[0, 0.35, 0]} castShadow receiveShadow>
        <TaintMaterial base={C.bread} taint={taint} unknown={unknown} roughness={0.95} />
      </RoundedBox>
    </group>
  )
}
function Slab({ zone, taint, unknown, color, h = 0.12, inset = 0.4, y = 0, dims }) {
  const [x, z] = center(zone); const [w, d] = dims || size(zone)
  return (
    <mesh position={[x, y + h / 2, z]} castShadow receiveShadow>
      <boxGeometry args={[w - inset, h, d - inset]} />
      <TaintMaterial base={color} taint={taint} unknown={unknown} />
    </mesh>
  )
}
function Box({ zone, color, h, inset = 0.3 }) {
  const [x, z] = center(zone); const [w, d] = size(zone)
  return (
    <mesh position={[x, h / 2, z]} castShadow receiveShadow><boxGeometry args={[w - inset, h, d - inset]} /><meshStandardMaterial color={color} roughness={0.85} /></mesh>
  )
}

function Label({ zone, taint, unknown, show }) {
  if (!show) return null
  const [x, z] = center(zone)
  const cls = 'lbl' + (taint > 0.5 ? ' taint' : '') + (unknown ? ' unknown' : '')
  const sub = unknown ? 'unknown' : taint > 0.5 ? 'carries pine nut' : zone.sub
  return (
    <Html position={[x, 1.2, z + size(zone)[1] / 2 + 0.1]} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
      <div className={cls}>{zone.label}{sub ? <span className="sub">{sub}</span> : null}</div>
    </Html>
  )
}

// A nitrile glove: flat palm, four tapered fingers pointing away from the camera, a thumb.
function Hand({ hand, taint, unknown, showLabel }) {
  const g = useRef()
  const cur = useMemo(() => new THREE.Vector3(2.2, 1.5, 1.4), [])
  const mat = useTaintMaterial(C.glove, taint, unknown)
  const matF = useTaintMaterial(C.glove, taint, unknown)
  useFrame(() => {
    if (!g.current) return
    if (hand) { cur.lerp(new THREE.Vector3(hand.xz[0], hand.y, hand.xz[1]), 0.25); g.current.visible = true } else g.current.visible = false
    g.current.position.copy(cur)
  })
  const fingers = [[-0.33, 0.62, 0.075], [-0.11, 0.7, 0.08], [0.11, 0.68, 0.078], [0.33, 0.56, 0.07]]
  return (
    <group ref={g}>
      <RoundedBox args={[0.95, 0.22, 0.95]} radius={0.1} smoothness={4} castShadow>
        <meshStandardMaterial ref={mat} color={C.glove} roughness={0.5} transparent />
      </RoundedBox>
      {fingers.map(([dx, len, r], i) => (
        <mesh key={i} position={[dx, 0, -0.45 - len / 2]} rotation={[Math.PI / 2, 0, 0]} castShadow>
          <capsuleGeometry args={[r, len, 4, 10]} />
          <meshStandardMaterial ref={i === 0 ? matF : undefined} color={C.glove} roughness={0.5} transparent />
        </mesh>
      ))}
      {/* thumb */}
      <mesh position={[0.62, 0, 0.05]} rotation={[Math.PI / 2, 0, -0.9]} castShadow>
        <capsuleGeometry args={[0.085, 0.5, 4, 10]} />
        <meshStandardMaterial color={C.glove} roughness={0.5} transparent />
      </mesh>
      {/* cuff */}
      <mesh position={[0, 0, 0.62]} rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[0.42, 0.46, 0.3, 24]} />
        <meshStandardMaterial color={C.glove} roughness={0.5} transparent />
      </mesh>
      {showLabel ? (
        <Html position={[0, -0.2, -1.35]} center zIndexRange={[10, 0]} style={{ pointerEvents: 'none' }}>
          <div className={'lbl' + (taint > 0.5 ? ' taint' : '') + (unknown ? ' unknown' : '')}>Gloves<span className="sub">{taint > 0.5 ? 'carries pine nut' : unknown ? 'unknown' : 'nitrile'}</span></div>
        </Html>
      ) : null}
    </group>
  )
}

function Segment({ a, b }) {
  const { pos, quat, len } = useMemo(() => {
    const dir = new THREE.Vector3().subVectors(b, a)
    const len = dir.length()
    const pos = new THREE.Vector3().addVectors(a, b).multiplyScalar(0.5)
    const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize())
    return { pos, quat, len }
  }, [a, b])
  if (len < 0.01) return null
  return (
    <mesh position={pos} quaternion={quat}>
      <cylinderGeometry args={[0.07, 0.07, len, 8]} />
      <meshBasicMaterial color="#ffb340" />
    </mesh>
  )
}
function Pathway({ k }) {
  const pts = useMemo(() => PATHWAY.map(([x, z]) => new THREE.Vector3(x, 1.35, z)), [])
  if (k <= 0) return null
  const segs = pts.length - 1
  const total = k * segs
  const parts = []
  for (let i = 0; i < segs; i++) {
    const f = Math.min(1, Math.max(0, total - i))
    if (f <= 0) break
    parts.push(<Segment key={i} a={pts[i]} b={pts[i].clone().lerp(pts[i + 1], f)} />)
  }
  return (
    <group>
      {parts}
      {pts.map((p, i) => (total >= i ? (
        <mesh key={'n' + i} position={p}><sphereGeometry args={[0.18, 12, 12]} /><meshBasicMaterial color="#ffb340" /></mesh>
      ) : null))}
    </group>
  )
}

export default function Station({ scene, tRef }) {
  const [state, setState] = React.useState(() => stationAt(scene.id, 0))
  const last = useRef(0)
  useFrame(({ clock }) => {
    if (tRef.current == null) tRef.current = clock.elapsedTime
    const t = clock.elapsedTime - tRef.current
    if (clock.elapsedTime - last.current > 1 / 30) {
      last.current = clock.elapsedTime
      setState(stationAt(scene.id, t))
    }
  })
  const T = (id) => state.taint[id] || 0
  const show = (id) => state.labels === 'all' || (state.labels === 'taint' && T(id) > 0.5)
  const dimK = 1 - state.dim
  const U = state.unknown

  return (
    <>
      <CameraRig pose={scene.pose} />
      <color attach="background" args={['#0b0a10']} />
      <fog attach="fog" args={['#0b0a10', 18, 36]} />
      <ambientLight intensity={0.45 * dimK} />
      <directionalLight position={[4, 12, 6]} intensity={2.4 * dimK} castShadow shadow-mapSize={[2048, 2048]} shadow-bias={-0.0005}>
        <orthographicCamera attach="shadow-camera" args={[-9, 9, 6, -6, 1, 30]} />
      </directionalLight>
      <directionalLight position={[-6, 6, -4]} intensity={0.6 * dimK} color="#ffd6e6" />
      <Environment resolution={64} frames={1}>
        <Lightformer intensity={1.2 * Math.max(0.05, dimK)} rotation-x={Math.PI / 2} position={[0, 6, 0]} scale={[14, 8, 1]} />
        <Lightformer intensity={0.5 * Math.max(0.05, dimK)} rotation-y={Math.PI / 2} position={[-10, 2, 0]} scale={[6, 3, 1]} color="#ffc4d6" />
      </Environment>

      <group visible={state.dim < 0.95}>
        <mesh position={[0, -0.12, 0]} receiveShadow><boxGeometry args={[12.6, 0.24, 6.6]} /><meshStandardMaterial color={STEEL} roughness={0.6} metalness={0.4} /></mesh>
        {[[0, -3, 12, 0.03], [0, 3, 12, 0.03], [-6, 0, 0.03, 6], [6, 0, 0.03, 6]].map(([x, z, w, d], i) => (
          <mesh key={'f' + i} position={[x, 0.012, z]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[w, d]} /><meshBasicMaterial color="#5a5470" /></mesh>
        ))}
        {[[-5.7, -2.7], [5.7, -2.7], [5.7, 2.7], [-5.7, 2.7]].map(([x, z], i) => (
          <mesh key={i} position={[x, 0.012, z]} rotation={[-Math.PI / 2, 0, 0]}><planeGeometry args={[0.4, 0.4]} /><meshBasicMaterial color="#d8d3e6" /></mesh>
        ))}

        <Jar zone={ZONES.pesto} taint={T('bin:pesto')} unknown={U} body={C.pesto} lid={C.pestoLid} open />
        <Jar zone={ZONES.mayo} taint={T('bin:mayo')} unknown={U} body={C.mayo} lid={C.mayoLid} />
        <Tray zone={ZONES.turkey} taint={T('bin:turkey')} unknown={U} />
        <Loaf zone={ZONES.bread} taint={T('bin:bread')} unknown={U} />
        <Slab zone={ZONES.work} taint={T('board')} unknown={U} color={C.board} h={0.14} />
        <mesh position={[center(ZONES.landing)[0], 0.04, center(ZONES.landing)[1]]} castShadow receiveShadow>
          <cylinderGeometry args={[1.15, 1.0, 0.08, 48]} />
          <TaintMaterial base={C.plate} taint={T('landing')} unknown={U} roughness={0.4} />
        </mesh>
        <Box zone={ZONES.rack} color={C.rack} h={0.1} />
        <Slab zone={ZONES.rack} taint={T('spreader')} unknown={U} color={C.tool} h={0.08} y={0.12} dims={[1.9, 0.26]} inset={0} />
        <Box zone={ZONES.stock} color={C.stock} h={0.5} />
        <Box zone={ZONES.gloves} color="#3b3550" h={0.9} inset={0.2} />
        <Box zone={ZONES.wash} color={C.sink} h={0.3} />
      </group>

      {Object.values(ZONES).map((z) => (
        <Label key={z.label} zone={z} taint={z.carrier ? T(z.carrier) : 0} unknown={U && !!z.carrier} show={state.dim < 0.95 && (z.carrier ? show(z.carrier) : state.labels === 'all')} />
      ))}
      <Hand hand={state.hand} taint={T('gloves')} unknown={U} showLabel={state.labels === 'all' || (state.labels === 'taint' && T('gloves') > 0.5)} />
      <Pathway k={state.pathway} />
      <Preload all />
      <ContactShadows position={[0, 0.005, 0]} opacity={0.55} scale={16} blur={2.2} far={3} resolution={512} frames={1} />
    </>
  )
}
