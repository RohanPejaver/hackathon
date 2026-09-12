import React, { useCallback, useEffect, useRef, useState } from 'react'
import { SCENE_TEXT, BACKUP_TEXT, STEPS, Brand } from './content.jsx'

const API = `http://127.0.0.1:5174`
export const DEMO_URL = 'http://127.0.0.1:8001/?stage=1'
export const LIVE_URL = 'http://127.0.0.1:8000/?stage=1'

// Slide 3: one sequence of five actions; step 1 introduces pine nut and it spreads step by step.
// Deterministic from scene entry: a step lights every 1.1 s, holds 3 s, then replays.
function Sequence({ t }) {
  const period = STEPS.length * 1.1 + 3.2
  const local = ((t - 0.8) % period + period) % period
  const lit = t < 0.8 ? -1 : Math.min(STEPS.length - 1, Math.floor(local / 1.1))
  return (
    <>
      <div className="corner-tl"><Brand /></div>
      <div className="corner-tl" style={{ top: '13vh' }}>
        <div className="frost petal-edge" style={{ maxWidth: '70vw' }}>
          <h1 className="h2" style={{ maxWidth: '22ch' }}>Contamination happens over a <span className="petal">sequence of actions,</span> not one picture.</h1>
        </div>
      </div>
      <div className="corner-bl">
        <div className="seq">
          {STEPS.map((s, i) => (
            <div key={i} className={'step' + (s.src ? ' src' : '') + (s.target ? ' target' : '') + (i <= lit ? ' hot' : '')}>
              <div className="n">STEP {i + 1}</div>
              <div className="t">{s.t}</div>
              <div className="c">{i <= lit ? s.c : ''}</div>
              {i < STEPS.length - 1 ? <div className={'arrow' + (i < lit ? ' hot' : '')}>→</div> : null}
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

function How({ t }) {
  const on = Math.floor(Math.max(0, t - 0.2) / 1.4)
  useEffect(() => {
    document.querySelectorAll('.arch-row').forEach((el) => el.classList.toggle('on', Number(el.dataset.i) <= on))
    document.querySelectorAll('.arch-boundary, .arch-foot').forEach((el) => el.classList.toggle('on', on >= 1))
  }, [on])
  return SCENE_TEXT.how
}

export function Demo({ mode, still, interact, zoom = 1, onStatus }) {
  const [src, setSrc] = useState(null)
  const [status, setStatus] = useState('starting replay')
  const [stillsN, setStillsN] = useState(0)
  const [ready, setReady] = useState(false)
  useEffect(() => { fetch('/fallback/stills.json').then((r) => r.json()).then((j) => setStillsN(j.count || 0)).catch(() => {}) }, [])
  // Split mode starts the recording at the same instant the replay server comes up, so the
  // worker display on the right is showing the same run the video on the left is showing.
  const videoRef = useRef(null)
  const startVideo = useCallback(() => {
    const v = videoRef.current
    if (!v) return
    try { v.currentTime = 0; const p = v.play(); if (p && p.catch) p.catch(() => {}) } catch {}
  }, [])
  useEffect(() => {
    if (mode !== 'replay' && mode !== 'live' && mode !== 'split') return
    if (mode === 'live') { setSrc(LIVE_URL + '&ts=' + Date.now()); setStatus('live · :8000'); return }
    let alive = true
    setSrc(null); setReady(false); setStatus('starting replay')
    fetch(API + '/api/replay/restart', { method: 'POST' })
      .then((r) => r.json())
      .then((j) => {
        if (!alive) return
        setSrc(DEMO_URL + '&ts=' + Date.now())
        if (mode === 'split') { setStatus(j.ok ? 'same run · recording left, live reasoning right' : 'replay restart failed: press V'); startVideo() }
        else setStatus(j.ok ? 'replay · deck/demo_stage.yaml' : 'replay restart failed: press V')
      })
      .catch(() => {
        if (!alive) return
        setSrc(DEMO_URL + '&ts=' + Date.now())
        setStatus('no stage server: replay may be mid-run, V for video')
        if (mode === 'split') startVideo()
      })
    return () => { alive = false }
  }, [mode, startVideo])
  useEffect(() => { onStatus && onStatus(status) }, [status])

  const splitZoom = zoom === 1 ? 0.5 : zoom
  if (mode === 'split') return (
    <div className={'demo split' + (interact ? ' interact' : '') + (ready ? ' ready' : '')}>
      <div className="pane">
        <div className="pane-label">the recording</div>
        <video ref={videoRef} src="/fallback/demo.webm" playsInline muted key="split-v" />
      </div>
      <div className="pane">
        <div className="pane-label">what Sequence sees</div>
        {src ? (
          <iframe src={src} title="worker display" allow="autoplay" onLoad={() => setTimeout(() => setReady(true), 350)} style={{ width: `${100 / splitZoom}%`, height: `${100 / splitZoom}%`, transform: `scale(${splitZoom})`, transformOrigin: '0 0' }} />
        ) : null}
      </div>
      <div className="strip" />
      <div className="status amber">{status}{interact ? ' · INTERACT (click top strip to exit)' : ''}</div>
    </div>
  )

  return (
    <div className={'demo' + (interact ? ' interact' : '') + (ready || mode !== 'replay' ? ' ready' : '')}>
      {mode === 'video' ? (
        <video src="/fallback/demo.webm" autoPlay playsInline muted key="v" />
      ) : mode === 'stills' ? (
        <img className="still" src={`/fallback/still-${Math.min(Math.max(1, still), Math.max(1, stillsN))}.png`} alt="" />
      ) : src ? (
        <iframe src={src} title="worker display" allow="autoplay" onLoad={() => setTimeout(() => setReady(true), 350)} style={{ width: `${100 / zoom}%`, height: `${100 / zoom}%`, transform: `scale(${zoom})`, transformOrigin: '0 0' }} />
      ) : null}
      <div className="strip" />
      <div className={'status' + (mode === 'replay' ? ' amber' : '')}>{mode === 'video' ? 'recording of the same run' : mode === 'stills' ? `stills · ${still}/${stillsN}` : status}{interact ? ' · INTERACT (click top strip to exit)' : ''}</div>
    </div>
  )
}

export function Overlay({ scene, t }) {
  if (!scene) return null
  const id = scene.id
  let body = null
  if (id === 'insight') body = <Sequence t={t} />
  else if (id === 'how') body = <How t={t} />
  else if (id.startsWith('b-')) body = BACKUP_TEXT[id]
  else body = SCENE_TEXT[id]
  return <div className="overlay">{body}</div>
}
