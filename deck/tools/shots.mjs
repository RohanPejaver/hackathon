// Screenshot every scene of the BUILT deck (stage server on :5174) at 1920x1080 with system Chrome.
//   node tools/shots.mjs [outdir]
import { chromium } from 'playwright-core'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'
const OUT = process.argv[2] || 'shots'
mkdirSync(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome', headless: true, args: ['--use-gl=angle', '--use-angle=metal', '--enable-webgl', '--ignore-gpu-blocklist'] })
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } })
page.on('pageerror', (e) => console.log('PAGEERROR', e.message))
page.on('console', (m) => { if (m.type() === 'error') console.log('CONSOLE', m.text()) })
const plan = [
  ['0', [1.2, 3.0, 5.0, 7.0]], ['1', [2.5]], ['2', [1.5, 4.5, 7.0]], ['3', [2]],
  ['5', [5.5]], ['6', [2]], ['7', [3]], ['8', [4.5]], ['9', [1.5]], ['11', [1.5]],
]
await page.goto('http://127.0.0.1:5174/#0', { waitUntil: 'load' })
await page.waitForTimeout(2500)
for (const [n, times] of plan) {
  await page.keyboard.press(n === '11' ? 'b' : n)
  if (n === '11') { await page.keyboard.press('ArrowRight'); await page.keyboard.press('ArrowRight') }
  let t = 0
  for (const at of times) {
    await page.waitForTimeout((at - t) * 1000); t = at
    const f = join(OUT, `scene-${n.padStart(2, '0')}-${at.toFixed(1)}s.png`)
    await page.screenshot({ path: f }); console.log(f)
  }
}
// demo beats through the real handoff
await page.keyboard.press('4')
const t0 = Date.now()
for (const at of [1.0, 4.0, 9.5, 12.0, 17.5, 24.5, 28.5]) {
  const w = at * 1000 - (Date.now() - t0); if (w > 0) await page.waitForTimeout(w)
  const f = join(OUT, `scene-04-demo-${at.toFixed(1)}s.png`); await page.screenshot({ path: f }); console.log(f)
}
await page.keyboard.press('v'); await page.waitForTimeout(9000)
await page.screenshot({ path: join(OUT, 'scene-04-video-fallback.png') })
await page.keyboard.press('s'); await page.keyboard.press('ArrowRight'); await page.waitForTimeout(600)
await page.screenshot({ path: join(OUT, 'scene-04-stills-fallback.png') })
const perf = await page.evaluate(() => new Promise((r) => { let n = 0; const t0 = performance.now(); (function f() { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(n / 2) })() }))
console.log('fps (demo scene, canvas under iframe):', perf)
await page.keyboard.press('8'); await page.waitForTimeout(1500)
const perf2 = await page.evaluate(() => new Promise((r) => { let n = 0; const t0 = performance.now(); (function f() { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(n / 2) })() }))
console.log('fps (scene 8):', perf2)
await browser.close()
