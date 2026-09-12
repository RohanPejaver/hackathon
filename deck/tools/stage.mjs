// Stage server: serves dist/ on :5174 and controls the product's replay server on :8001.
// POST /api/replay/restart  -> kill anything on :8001, spawn uvicorn with STATION_REPLAY, wait until /snapshot answers.
// GET  /api/replay/status
import http from 'node:http'
import { spawn, execSync } from 'node:child_process'
import { readFileSync, existsSync, statSync } from 'node:fs'
import { join, extname, resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const ROOT = resolve(HERE, '..', '..')            // repo root
const DIST = resolve(HERE, '..', 'dist')
const PORT = 5174
const REPLAY_PORT = 8001
const SCENARIO = process.env.STATION_REPLAY || 'deck/demo_stage.yaml'   // 2x slower copy of scenarios/demo.yaml
const UVICORN = join(ROOT, '.venv', 'bin', 'uvicorn')

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.webm': 'video/webm', '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' }
let child = null

function killPort(port) {
  try { execSync(`lsof -ti tcp:${port} | xargs kill -9`, { stdio: 'ignore' }) } catch {}
}
async function waitUp(port, ms = 8000) {
  const t0 = Date.now()
  while (Date.now() - t0 < ms) {
    try { const r = await fetch(`http://127.0.0.1:${port}/snapshot`); if (r.ok) return true } catch {}
    await new Promise((r) => setTimeout(r, 120))
  }
  return false
}
export async function restartReplay() {
  if (child) { try { child.kill('SIGKILL') } catch {} ; child = null }
  killPort(REPLAY_PORT)
  await new Promise((r) => setTimeout(r, 150))
  child = spawn(UVICORN, ['src.runtime.app:app', '--host', '127.0.0.1', '--port', String(REPLAY_PORT), '--log-level', 'warning'], {
    cwd: ROOT, env: { ...process.env, STATION_REPLAY: SCENARIO }, stdio: 'ignore',
  })
  const ok = await waitUp(REPLAY_PORT)
  return { ok, scenario: SCENARIO, port: REPLAY_PORT }
}

const cors = { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': '*' }
const server = http.createServer(async (req, res) => {
  if (req.method === 'OPTIONS') { res.writeHead(204, cors); return res.end() }
  if (req.url.startsWith('/api/replay/restart')) {
    const r = await restartReplay()
    res.writeHead(200, { 'content-type': 'application/json', ...cors }); return res.end(JSON.stringify(r))
  }
  if (req.url.startsWith('/api/replay/status')) {
    const up = await waitUp(REPLAY_PORT, 300)
    res.writeHead(200, { 'content-type': 'application/json', ...cors }); return res.end(JSON.stringify({ up, running: !!child }))
  }
  // static
  let p = decodeURIComponent(req.url.split('?')[0])
  if (p === '/' || !extname(p)) p = '/index.html'
  const f = join(DIST, p)
  if (!f.startsWith(DIST) || !existsSync(f) || statSync(f).isDirectory()) { res.writeHead(404); return res.end('not found') }
  res.writeHead(200, { 'content-type': MIME[extname(f)] || 'application/octet-stream', 'cache-control': 'no-cache' })
  res.end(readFileSync(f))
})
if (process.argv[1] === fileURLToPath(import.meta.url)) {
  server.listen(PORT, '127.0.0.1', () => {
    console.log(`deck  http://127.0.0.1:${PORT}/#0`)
    console.log(`api   POST http://127.0.0.1:${PORT}/api/replay/restart  (uvicorn ${SCENARIO} on :${REPLAY_PORT})`)
    if (!existsSync(DIST)) console.log('!! dist/ missing — run `npm run build` first')
  })
}
