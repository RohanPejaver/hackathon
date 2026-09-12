// Fallback assets from the REAL display: restart the replay, record 30 s of the worker display
// at 1920x1080 as webm, and save stills at the decisive beats. Uses the installed Google Chrome.
//   node tools/capture.mjs            -> public/fallback/demo.webm, still-1..N.png, stills.json
import { chromium } from 'playwright-core'
import { mkdirSync, renameSync, readdirSync, writeFileSync, rmSync } from 'node:fs'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { restartReplay } from './stage.mjs'

const HERE = dirname(fileURLToPath(import.meta.url))
const OUT = resolve(HERE, '..', 'public', 'fallback')
mkdirSync(OUT, { recursive: true })
const BEATS = [   // demo_stage.yaml is 0.7x of scenarios/demo.yaml
  { at: 2.4, name: 'ticket 47 · silence, amber spreads' },
  { at: 5.3, name: 'the reach · mayo shared container' },
  { at: 7.3, name: 'ticket 48 · Tier 0 before any motion' },
  { at: 10.8, name: 'compliance · checklist ticks itself off' },
  { at: 16.4, name: 'Tier 1 · STOP' },
  { at: 19.2, name: 'Tier 2 · HOLD' },
]
const r = await restartReplay()
if (!r.ok) { console.error('replay server did not come up'); process.exit(1) }
const browser = await chromium.launch({ channel: 'chrome', headless: true })
const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, recordVideo: { dir: OUT, size: { width: 1920, height: 1080 } } })
const page = await ctx.newPage()
const t0 = Date.now()
await page.goto('http://127.0.0.1:8001/?stage=1', { waitUntil: 'load' })
let n = 0
for (const b of BEATS) {
  const wait = b.at * 1000 - (Date.now() - t0)
  if (wait > 0) await page.waitForTimeout(wait)
  n += 1
  await page.screenshot({ path: join(OUT, `still-${n}.png`) })
  console.log(`still-${n}.png  +${b.at}s  ${b.name}`)
}
const rest = 22000 - (Date.now() - t0)
if (rest > 0) await page.waitForTimeout(rest)
await ctx.close()
await browser.close()
const vids = readdirSync(OUT).filter((f) => f.endsWith('.webm') && f !== 'demo.webm')
for (const v of vids) { rmSync(join(OUT, 'demo.webm'), { force: true }); renameSync(join(OUT, v), join(OUT, 'demo.webm')) }
writeFileSync(join(OUT, 'stills.json'), JSON.stringify({ count: n, beats: BEATS }, null, 2))
console.log('wrote', join(OUT, 'demo.webm'), 'and', n, 'stills')
process.exit(0)
