// Render stills: node src/stills.mjs <outdir> <aspect> [dir] [reduced] t1 t2 ...
// "beats" as the only time renders the midpoint of every beat.
import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('playwright');
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const [outDir, aspect = '16x9', dir = 'a', reduced = '0', ...times] = process.argv.slice(2);
const SIZE = { '16x9': [1920, 1080], '9x16': [1080, 1920], '1x1': [1080, 1080] }[aspect];
mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: SIZE[0], height: SIZE[1] } });
await page.goto(`file://${here}/index.html?aspect=${aspect}&dir=${dir}&reduced=${reduced}`);
await page.evaluate(() => window.READY);
let ts = times.map(Number);
if (times[0] === 'beats') ts = await page.evaluate(() => window.TIMELINE.beats.map(b => +(((b.start + b.end) / 2).toFixed(2))));
for (const t of ts) {
  await page.evaluate(t => window.seek(t), t);
  await page.screenshot({ path: path.join(outDir, `${aspect}_${dir}${reduced === '1' ? '_r' : ''}_t${t.toFixed(2)}.png`) });
}
await browser.close();
console.log(ts.join(' '));
