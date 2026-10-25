// Render one cut: node src/render.mjs <aspect> <reduced 0|1> <out.mp4> [fps override]
// Steps t = n / fps through window.seek and pipes PNG frames to ffmpeg (video only).
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const { chromium } = createRequire(import.meta.url)('playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const [aspect = '16x9', reduced = '0', out = 'out/video.mp4', fpsArg, extra = ''] = process.argv.slice(2);
const [W, H] = { '16x9': [1920, 1080], '9x16': [1080, 1920], '1x1': [1080, 1080] }[aspect];
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: W, height: H } });
await page.goto(`file://${here}/index.html?aspect=${aspect}&reduced=${reduced}${extra}`);
await page.evaluate(() => window.READY);
const { fps: fps0, duration } = await page.evaluate(() => window.TIMELINE);
const fps = fpsArg ? Number(fpsArg) : fps0;
const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-i', '-',
  '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-r', String(fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
const N = Math.round(fps * duration);
for (let n = 0; n < N; n++) {
  await page.evaluate(t => window.seek(t), n / fps);
  const buf = await page.screenshot({ type: 'png' });
  if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  if (n % 300 === 0) console.error(`${aspect}${reduced === '1' ? ' reduced' : ''}: ${n}/${N}`);
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
