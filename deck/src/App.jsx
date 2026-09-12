import React, { useEffect, useRef, useState, useCallback } from 'react'
import { Canvas } from '@react-three/fiber'
import Station from './Station.jsx'
import { Overlay, Demo } from './Overlay.jsx'
import { SCENES, BACKUP } from './scenes.js'

const ALL = [...SCENES, ...BACKUP]

export default function App() {
  const [i, setI] = useState(() => {
    const h = parseInt(location.hash.slice(1), 10)
    return Number.isFinite(h) && h >= 0 && h < ALL.length ? h : 0
  })
  const LOCAL = /^(127\.0\.0\.1|localhost)$/.test(location.hostname)   // hosted copies have no product server: use the recording
  const [demoMode, setDemoMode] = useState(LOCAL ? 'replay' : 'video')   // replay | video | stills | live
  const [still, setStill] = useState(1)
  const [interact, setInteract] = useState(false)
  const [tick, setTick] = useState(0)
  const [hud, setHud] = useState(true)
  const [zoom, setZoom] = useState(1)
  const tRef = useRef(performance.now() / 1000)        // scene entry time (seconds, same clock as R3F elapsed? no , see below)
  const entryRef = useRef(0)                            // R3F clock time at scene entry; set by Station via callback
  const scene = ALL[i]

  // Scene entry: reset local timers, hash, interaction.
  useEffect(() => {
    tRef.current = performance.now() / 1000
    entryRef.current = null
    setInteract(false)
    setStill(1)
    if (scene.demo) setDemoMode(LOCAL ? 'replay' : 'video')
    location.hash = String(i)
    document.body.classList.remove('pointer')
  }, [i])

  // Nudge layout/measure after mount so the canvas never sits at its 300x150 default.
  useEffect(() => {
    const ids = [150, 600, 1500, 3000].map((ms) => setTimeout(() => window.dispatchEvent(new Event('resize')), ms))
    return () => ids.forEach(clearTimeout)
  }, [])
  // 30 Hz tick for the HTML overlay animations (chain, layers).
  useEffect(() => {
    const id = setInterval(() => setTick((x) => x + 1), 33)
    return () => clearInterval(id)
  }, [])
  const t = performance.now() / 1000 - tRef.current

  const go = useCallback((n) => setI((cur) => Math.max(0, Math.min(ALL.length - 1, typeof n === 'function' ? n(cur) : n))), [])

  useEffect(() => {
    const onKey = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const k = e.key
      if (k === 'ArrowRight' || k === ' ' || k === 'PageDown') {
        e.preventDefault()
        if (scene.demo && demoMode === 'stills') { setStill((s) => s + 1); return }
        go((c) => (c < SCENES.length - 1 ? c + 1 : c === SCENES.length - 1 ? c : c + 1))
      } else if (k === 'ArrowLeft' || k === 'PageUp') {
        e.preventDefault()
        if (scene.demo && demoMode === 'stills' && still > 1) { setStill((s) => s - 1); return }
        go((c) => c - 1)
      } else if (k === 'Escape') { go(0) }
      else if (k >= '0' && k <= '9') { go(parseInt(k, 10)) }
      else if (k === 'b' || k === 'B') { go(SCENES.length) }
      else if (k === 'Home') { go(0) }
      else if (k === 'f' || k === 'F') { document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen() }
      else if (k === 'h' || k === 'H') { setHud((x) => !x) }
      else if (k === 'End') { go(SCENES.length - 1) }
      else if (scene.demo) {
        if (k === 'r' || k === 'R') { setDemoMode('x'); setTimeout(() => setDemoMode('replay'), 0) }
        else if (k === 'v' || k === 'V') setDemoMode('video')
        else if (k === 's' || k === 'S') { setDemoMode('stills'); setStill(1) }
        else if (k === 'l' || k === 'L') setDemoMode('live')
        else if (k === 'p' || k === 'P') { setInteract((x) => !x); document.body.classList.toggle('pointer') }
        else if (k === 'z' || k === 'Z') setZoom((z) => (z >= 1.35 ? 1 : z === 1 ? 1.2 : 1.35))
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [scene, demoMode, still, go])

  // Keep keyboard focus on the deck unless interaction with the product was requested.
  useEffect(() => {
    const onBlur = () => { if (!interact) setTimeout(() => window.focus(), 50) }
    window.addEventListener('blur', onBlur)
    return () => window.removeEventListener('blur', onBlur)
  }, [interact])
  // Clicking the top strip in interact mode hands focus back to the deck.
  useEffect(() => {
    const onClick = (e) => { if (e.target.classList?.contains('strip')) { setInteract(false); document.body.classList.remove('pointer'); window.focus() } }
    window.addEventListener('click', onClick)
    return () => window.removeEventListener('click', onClick)
  }, [])

  const isBackup = i >= SCENES.length
  return (
    <>
      <div className="stage">
        <Canvas style={{ width: '100vw', height: '100vh' }} resize={{ debounce: 0, scroll: false }} shadows dpr={[1, 1.5]} camera={{ fov: 38, near: 0.1, far: 60, position: [0, 13.5, 0.6] }} gl={{ antialias: true, powerPreference: 'high-performance' }}>
          <StationClocked scene={scene} sceneKey={i} />
        </Canvas>
      </div>
      {!scene.demo && <Overlay scene={scene} t={t} />}
      {scene.demo && <Demo mode={demoMode} still={still} interact={interact} zoom={zoom} />}
      {hud && <div className="hud"><b>{i}</b> · {scene.hud} · {isBackup ? 'B' : `${i + 1}/${SCENES.length}`} · → next · ← prev · 0-9 jump · B backup · Esc reset{scene.demo ? ' · R restart · V video · S stills · L live · P interact · Z zoom' : ''} · F fullscreen · H hud</div>}
      <div className="progress"><i style={{ width: `${((Math.min(i, SCENES.length - 1) + 1) / SCENES.length) * 100}%` }} /></div>
    </>
  )
}

// Wraps Station with an R3F-clock entry timestamp that resets on scene change.
import { useThree } from '@react-three/fiber'
function StationClocked({ scene, sceneKey }) {
  const { clock } = useThree()
  const tRef = useRef(null)
  useEffect(() => { tRef.current = null }, [sceneKey])
  return <Station scene={scene} tRef={tRef} />
}
