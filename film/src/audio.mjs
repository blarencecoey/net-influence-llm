// Render the sound bed + cues offline in Chromium: node src/audio.mjs out/audio.wav
import { createRequire } from 'node:module';
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const { chromium } = createRequire(import.meta.url)('playwright');
const here = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(`file://${here}/index.html`);
await page.evaluate(() => window.READY);
const b64 = await page.evaluate(() => window.renderAudio());
writeFileSync(process.argv[2] || 'out/audio.wav', Buffer.from(b64, 'base64'));
await browser.close();
