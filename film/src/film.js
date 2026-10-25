// Explainer film: "Catching colluding AI agents with net influence".
// Every frame is a pure function of t: window.seek(t) clears and repaints the canvas.
// URL params: aspect=16x9|9x16|1x1, reduced=1 (cuts and fades instead of movement),
// dir=a|b|c (design direction), animatic=1 (grey blocks + placeholder text).
(function () {
  const Q = new URLSearchParams(location.search);
  const ASPECT = Q.get('aspect') || '16x9';
  const REDUCED = Q.get('reduced') === '1';
  const ANIMATIC = Q.get('animatic') === '1';
  const C = window.TOKENS[Q.get('dir') || 'a'];
  const SANS = window.TOKENS.type.sans, MONO = window.TOKENS.type.mono;

  // ---------- layout per aspect (re-laid out, never cropped) ----------
  const LAYOUTS = {
    '16x9': { W: 1920, H: 1080, table: { cx: 500, cy: 440, d: 230, s: 1.45 },
              panel: { x: 1000, y: 130, w: 820, h: 720 }, cap: { cx: 960, bottom: 1040, w: 1560, size: 40 } },
    '9x16': { W: 1080, H: 1920, table: { cx: 540, cy: 500, d: 205, s: 1.08 },
              panel: { x: 90, y: 950, w: 900, h: 760 }, cap: { cx: 540, bottom: 1840, w: 960, size: 44 } },
    '1x1':  { W: 1080, H: 1080, table: { cx: 540, cy: 185, d: 108, s: 0.6 },
              panel: { x: 90, y: 385, w: 900, h: 580 }, cap: { cx: 540, bottom: 1056, w: 1020, size: 38 } },
  };
  const L = LAYOUTS[ASPECT];
  const VW = 820, VH = 720; // virtual panel box, scaled into L.panel
  const PS = Math.min(L.panel.w / VW, L.panel.h / VH);

  // ---------- timeline: every beat, cue and caption ----------
  const TIMELINE = {
    fps: 30, duration: 75,
    beats: [
      { id: 'S01', start: 0, end: 7, teaches: 'One agent oddly never wins' },
      { id: 'S02', start: 7, end: 16, teaches: 'What collusion is' },
      { id: 'S03', start: 16, end: 24, teaches: 'Why care; the question' },
      { id: 'S04', start: 24, end: 36, teaches: 'Net influence: link minus best rival explanation' },
      { id: 'S05', start: 36, end: 46, teaches: 'It matches the paper and finds a seeded LLM pair' },
      { id: 'S06', start: 46, end: 60, teaches: 'Twins share habits; calibrate on honest games' },
      { id: 'S07', start: 60, end: 68, teaches: 'Two blind spots' },
      { id: 'S08', start: 68, end: 75, teaches: 'A screen, not proof' },
    ],
    captions: [
      { start: 0.4, end: 3.6, text: 'Four AI agents play Rock-Paper-Scissors.' },
      { start: 3.8, end: 6.8, text: 'Agent A keeps winning. Agent B never does.' },
      { start: 7.2, end: 11.4, text: 'B is quietly throwing the move that lets A win.' },
      { start: 11.6, end: 15.7, text: "That's collusion: secret teamwork at everyone else's expense." },
      { start: 16.2, end: 19.8, text: 'Silly in a game. Less silly in auctions, pricing or trading.' },
      { start: 20.0, end: 23.7, text: 'So: can you catch it from the moves alone?' },
      { start: 24.3, end: 28.4, text: "Bonjour et al. (2022): how much does A's move tell you about B's?" },
      { start: 28.6, end: 32.2, text: 'Then subtract the most any other agent explains.' },
      { start: 32.4, end: 35.7, text: 'Still above 0.05, both ways? Flag the pair.' },
      { start: 36.2, end: 40.6, text: 'Step one: rebuild their detector and match their scripted results.' },
      { start: 40.8, end: 45.7, text: 'Step two: four Llama agents, one secret channel. Found the pair in 5 of 5 runs.' },
      { start: 46.2, end: 50.0, text: 'Plot twist: copies of the same model share habits.' },
      { start: 50.2, end: 54.4, text: 'The published rule flagged 40 of 55 honest games. Mostly the twins.' },
      { start: 54.6, end: 59.7, text: 'Fix: set the bar from honest games. False alarms drop from 45% to under 1%.' },
      { start: 60.2, end: 64.0, text: 'Blind spot one: a pre-agreed plan only shows up one move later.' },
      { start: 64.2, end: 67.7, text: 'Blind spot two: three colluders hide behind each other. Score: zero.' },
      { start: 68.2, end: 71.6, text: 'Net influence is a screen, not proof.' },
      { start: 71.8, end: 74.8, text: 'Who moves together more than anyone else can explain?' },
    ],
    cues: [],
  };
  // S01 rounds (illustration, not run data). Moves: 0 rock, 1 paper, 2 scissors.
  const ROUNDS = [
    { t: 0.8, m: [0, 2, 2, 0] }, { t: 2.3, m: [1, 0, 1, 0] },
    { t: 3.8, m: [2, 1, 1, 1] }, { t: 5.3, m: [0, 2, 0, 2] },
  ];
  // S06: the twins (A, B) keep throwing the same move; C, D do their own thing.
  const TWIN_ROUNDS = [
    { t: 47.6, m: [0, 0, 1, 2] }, { t: 48.9, m: [1, 1, 1, 0] }, { t: 50.2, m: [1, 1, 2, 0] },
  ];
  const beats = (a, b) => (a - b + 3) % 3 === 1;
  function winners(m) {
    const set = [...new Set(m)];
    if (set.length !== 2) return [];
    const w = beats(set[0], set[1]) ? set[0] : set[1];
    return m.map((x, i) => (x === w ? i : -1)).filter(i => i >= 0);
  }
  ROUNDS.forEach(r => { r.win = winners(r.m); TIMELINE.cues.push({ t: r.t, sound: 'pluck', p: r.win.includes(0) ? 1 : 0 }); });
  TWIN_ROUNDS.forEach(r => TIMELINE.cues.push({ t: r.t, sound: 'tick' }));
  TIMELINE.cues.push(
    { t: 4.6, sound: 'pop' }, { t: 8.0, sound: 'swish' }, { t: 9.0, sound: 'tick' },
    { t: 11.6, sound: 'motif', n: 1 }, { t: 16.6, sound: 'pop' }, { t: 17.4, sound: 'pop' }, { t: 18.2, sound: 'pop' },
    { t: 20.0, sound: 'swish' }, { t: 25.0, sound: 'tick' }, { t: 28.8, sound: 'tick' }, { t: 29.1, sound: 'tick' },
    { t: 30.2, sound: 'thud' }, { t: 32.4, sound: 'tick' }, { t: 34.0, sound: 'motif', n: 2 },
    { t: 37.0, sound: 'tick' }, { t: 40.8, sound: 'swish' }, { t: 42.6, sound: 'pop' },
    { t: 46.2, sound: 'swish' }, { t: 51.0, sound: 'thud' }, { t: 55.0, sound: 'tick' }, { t: 56.5, sound: 'rise' },
    { t: 60.2, sound: 'swish' }, { t: 62.4, sound: 'pop' }, { t: 64.2, sound: 'swish' }, { t: 65.8, sound: 'thud' },
    { t: 68.2, sound: 'swish' }, { t: 72.0, sound: 'motif', n: 3 },
  );
  TIMELINE.cues.sort((a, b) => a.t - b.t);
  window.TIMELINE = TIMELINE;

  // ---------- easing and time helpers ----------
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const X = u => ((ax * u + bx) * u + cx) * u, Y = u => ((ay * u + by) * u + cy) * u;
    return x => {
      let lo = 0, hi = 1, u = x;
      for (let i = 0; i < 30; i++) { u = (lo + hi) / 2; if (X(u) < x) lo = u; else hi = u; }
      return Y(u);
    };
  }
  const EO = bezier(...window.TOKENS.ease.out), EIO = bezier(...window.TOKENS.ease.inOut);
  const c01 = v => Math.max(0, Math.min(1, v));
  const lerp = (a, b, p) => a + (b - a) * p;
  // movement: eased, or a cut at the midpoint in reduced-motion mode
  const mv = (t, s, d) => { const p = c01((t - s) / d); return REDUCED ? (p >= 0.5 ? 1 : 0) : EO(p); };
  // opacity: always a fade
  const fd = (t, s, d) => EIO(c01((t - s) / d));
  const win = (t, a, b, din = 0.4, dout = 0.4) => Math.min(fd(t, a, din), 1 - fd(t, b - dout, dout));
  function mix(h1, h2, p) {
    const a = parseInt(h1.slice(1), 16), b = parseInt(h2.slice(1), 16);
    const ch = s => Math.round(lerp((a >> s) & 255, (b >> s) & 255, p));
    return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
  }

  // ---------- canvas ----------
  const cv = document.getElementById('c');
  cv.width = L.W; cv.height = L.H;
  const g = cv.getContext('2d');
  const font = (size, w = 400, fam = SANS) => `${w} ${size}px ${fam}`;
  function text(str, x, y, o = {}) {
    g.save();
    g.globalAlpha *= o.alpha ?? 1;
    g.font = font(o.size || 40, o.w || 400, o.mono ? MONO : SANS);
    g.fillStyle = o.color || C.ink;
    g.textAlign = o.align || 'left';
    g.textBaseline = o.base || 'alphabetic';
    g.fillText(str, x, y);
    g.restore();
  }
  function wrap(str, maxW, size, w = 400) {
    g.font = font(size, w);
    const words = str.split(' '), lines = [];
    let cur = '';
    for (const wd of words) {
      const test = cur ? cur + ' ' + wd : wd;
      if (g.measureText(test).width > maxW && cur) { lines.push(cur); cur = wd; } else cur = test;
    }
    if (cur) lines.push(cur);
    return lines;
  }
  function rrect(x, y, w, h, r) {
    g.beginPath();
    g.moveTo(x + r, y); g.arcTo(x + w, y, x + w, y + h, r); g.arcTo(x + w, y + h, x, y + h, r);
    g.arcTo(x, y + h, x, y, r); g.arcTo(x, y, x + w, y, r); g.closePath();
  }

  // ---------- the four agents (persist across the whole film) ----------
  const SIGN = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
  const NAMES = ['A', 'B', 'C', 'D'];
  const T = L.table;
  const pos = i => [T.cx + SIGN[i][0] * T.d, T.cy + SIGN[i][1] * T.d];
  const HEAD = 116 * T.s;
  const TS = Math.max(T.s, 0.95); // text scale floor so labels stay readable in 1:1

  function eyeOpen(t, i) {
    if (i === 1 && t >= 9.0 && t < 9.7) return 'wink';
    const sync = t >= 47 && t < 60 && i < 2; // the twins blink together
    const period = 3.3, phase = sync ? 0.7 : [0.3, 1.9, 1.1, 2.6][i];
    const u = ((t + phase) % period);
    return u < 0.14 ? 0.1 : 1;
  }
  function mouth(t, i) {
    for (const r of ROUNDS) if (t >= r.t + 0.2 && t < r.t + 1.4) {
      if (r.win.includes(i)) return 1;
      if (i === 1) return -0.4;
    }
    if (t < 7 && i === 1) return -0.15;
    return 0.35;
  }
  // 0 plain, 1 llama (rounded square), 2 mistral (circle)
  function family(t, i) {
    const llamaAll = fd(t, 40.8, 0.5) * (1 - fd(t, 60.0, 0.5));
    const mistral = i >= 2 ? mv(t, 47.0, 0.8) * (1 - mv(t, 60.0, 0.8)) : 0;
    return { llama: llamaAll, mistral };
  }
  function colluder(t, i) {
    if (i < 2) return Math.max(win(t, 8.0, 46.2, 0.5, 0.4), win(t, 60.2, 68.0), fd(t, 68.2, 0.5));
    if (i === 2) return win(t, 64.4, 68.0);
    return 0;
  }
  function agentAlpha(t, i) {
    let a = 1;
    const dim = win(t, 60.2, 64.2, 0.4, 0.2);
    if (i >= 2) a = Math.min(a, 1 - 0.6 * dim);
    if (i === 3) a = Math.min(a, 1 - 0.6 * win(t, 64.2, 68.0, 0.2, 0.4));
    return a;
  }
  function drawMoveIcon(m, x, y, s, col) {
    g.save(); g.translate(x, y); g.scale(s, s);
    g.fillStyle = col; g.strokeStyle = col; g.lineWidth = 5; g.lineCap = 'round';
    if (m === 0) { // rock
      g.beginPath(); g.ellipse(0, 2, 24, 20, -0.2, 0, Math.PI * 2); g.fill();
    } else if (m === 1) { // paper
      rrect(-18, -24, 36, 48, 4); g.stroke();
      g.lineWidth = 3; for (const yy of [-10, 0, 10]) { g.beginPath(); g.moveTo(-9, yy); g.lineTo(9, yy); g.stroke(); }
    } else { // scissors
      g.beginPath(); g.moveTo(-14, 16); g.lineTo(16, -22); g.moveTo(14, 16); g.lineTo(-16, -22); g.stroke();
      g.lineWidth = 4;
      g.beginPath(); g.arc(-14, 20, 7, 0, Math.PI * 2); g.stroke();
      g.beginPath(); g.arc(14, 20, 7, 0, Math.PI * 2); g.stroke();
    }
    g.restore();
  }
  const MOVE_NAME = ['rock', 'paper', 'scissors'];
  function drawMoves(t, rounds, until) {
    for (let k = 0; k < rounds.length; k++) {
      const r = rounds[k], end = k + 1 < rounds.length ? rounds[k + 1].t : until;
      if (t < r.t || t >= end) continue;
      const a = win(t, r.t, end, 0.15, 0.15);
      for (let i = 0; i < 4; i++) {
        const [x, y] = pos(i);
        const toward = 0.64;
        const ix = lerp(x, T.cx, toward), iy = lerp(y, T.cy, toward);
        const sc = (REDUCED ? 1 : lerp(0.6, 1, mv(t, r.t, 0.25))) * T.s * 1.15;
        g.save(); g.globalAlpha = a * agentAlpha(t, i);
        const isWin = r.win && r.win.includes(i);
        drawMoveIcon(r.m[i], ix, iy - 8 * T.s, sc, C.ink);
        text(MOVE_NAME[r.m[i]], ix, iy + 46 * T.s, { size: 22 * TS, align: 'center', color: isWin ? C.ink : C.muted, w: isWin ? 700 : 400 });
        g.restore();
      }
    }
  }
  function drawAgent(t, i) {
    const [x, y] = pos(i);
    const fam = family(t, i), col = colluder(t, i);
    const h = HEAD;
    g.save();
    g.globalAlpha = agentAlpha(t, i);
    const radius = lerp(0.24 * h, 0.5 * h, fam.mistral);
    g.fillStyle = mix(C.face, C.faceAlt, fam.mistral);
    rrect(x - h / 2, y - h / 2, h, h, radius); g.fill();
    g.lineWidth = lerp(3, 7, col) * T.s;
    g.strokeStyle = mix(C.line, C.accent, col);
    g.stroke();
    // eyes
    const eo = eyeOpen(t, i), ex = 0.2 * h, ey = y - 0.08 * h, er = 0.07 * h;
    g.fillStyle = C.ink; g.strokeStyle = C.ink; g.lineWidth = 4 * T.s; g.lineCap = 'round';
    for (const side of [-1, 1]) {
      const closed = eo === 'wink' ? side === 1 : eo < 0.5;
      if (closed) {
        g.beginPath(); g.moveTo(x + side * ex - er, ey); g.quadraticCurveTo(x + side * ex, ey + er * 0.8, x + side * ex + er, ey); g.stroke();
      } else { g.beginPath(); g.arc(x + side * ex, ey, er, 0, Math.PI * 2); g.fill(); }
    }
    // mouth
    const mo = mouth(t, i), my = y + 0.2 * h, mw = 0.18 * h;
    g.beginPath(); g.moveTo(x - mw, my); g.quadraticCurveTo(x, my + mo * 0.22 * h, x + mw, my); g.stroke();
    g.restore();
    // name + tags under the head
    const ny = y + h / 2 + 34 * TS;
    g.save(); g.globalAlpha = agentAlpha(t, i);
    text(NAMES[i], x, ny, { size: 30 * TS, w: 700, align: 'center', color: col > 0.5 ? C.accent : C.ink });
    const tagA = fam.llama * (1 - fam.mistral), tagB = fam.mistral;
    if (tagA > 0.01) text('Llama', x, ny + 30 * TS, { size: 22 * TS, align: 'center', color: C.muted, alpha: tagA });
    if (tagB > 0.01) text('Mistral', x, ny + 30 * TS, { size: 22 * TS, align: 'center', color: C.muted, alpha: tagB });
    // S01-S02 scores
    const sa = win(t, 0.6, 15.8, 0.3, 0.5);
    if (sa > 0.01) {
      let sc = 0;
      for (const r of ROUNDS) if (t >= r.t + 0.4 && r.win.includes(i)) sc++;
      text(`${sc} ${sc === 1 ? 'pt' : 'pts'}`, x, ny + 30 * TS, { size: 22 * TS, align: 'center', color: C.muted, alpha: sa });
    }
    g.restore();
  }
  // link between two agents' heads; style: 'accent' or 'grey'
  function drawLink(i, j, p, alpha, style, label) {
    if (alpha <= 0.01 || p <= 0) return;
    const [x1, y1] = pos(i), [x2, y2] = pos(j);
    const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy), ux = dx / len, uy = dy / len;
    const off = HEAD * 0.62;
    const sx = x1 + ux * off, sy = y1 + uy * off, exx = x2 - ux * off, eyy = y2 - uy * off;
    g.save(); g.globalAlpha = alpha;
    g.strokeStyle = style === 'accent' ? C.accent : C.muted;
    g.lineWidth = 5 * T.s; g.setLineDash([14 * T.s, 10 * T.s]); g.lineCap = 'round';
    g.beginPath(); g.moveTo(sx, sy); g.lineTo(lerp(sx, exx, p), lerp(sy, eyy, p)); g.stroke();
    g.restore();
    if (label) text(label.str, (sx + exx) / 2 + (label.dx || 0), Math.min(sy, eyy) - HEAD * 0.5 - 14 * TS, // above the heads, never between them
      { size: 22 * TS, align: 'center', color: style === 'accent' ? C.accent : C.muted, alpha: alpha * (label.alpha ?? 1), w: 600 });
  }
  function drawArrow(i, j, p, alpha, colr) {
    if (alpha <= 0.01 || p <= 0) return;
    const [x1, y1] = pos(i), [x2, y2] = pos(j);
    const dx = x2 - x1, dy = y2 - y1, len = Math.hypot(dx, dy), ux = dx / len, uy = dy / len;
    const off = HEAD * 0.66;
    const sx = x1 + ux * off, sy = y1 + uy * off;
    const offEnd = off + 70 * T.s; // stop short of the target's name label
    const ex = lerp(sx, x2 - ux * offEnd, p), ey = lerp(sy, y2 - uy * offEnd, p);
    g.save(); g.globalAlpha = alpha; g.strokeStyle = colr; g.fillStyle = colr; g.lineWidth = 4 * T.s;
    g.beginPath(); g.moveTo(sx, sy); g.lineTo(ex, ey); g.stroke();
    const a = Math.atan2(uy, ux), hs = 14 * T.s;
    g.beginPath(); g.moveTo(ex, ey); g.lineTo(ex - hs * Math.cos(a - 0.45), ey - hs * Math.sin(a - 0.45));
    g.lineTo(ex - hs * Math.cos(a + 0.45), ey - hs * Math.sin(a + 0.45)); g.closePath(); g.fill();
    g.restore();
  }
  function stamp(x, y, str, col, alpha, sc) {
    if (alpha <= 0.01) return;
    g.save(); g.globalAlpha = alpha; g.translate(x, y); g.rotate(-0.08); g.scale(sc, sc);
    g.font = font(30 * T.s, 700); const w = g.measureText(str).width + 36 * T.s, h = 52 * T.s;
    g.fillStyle = C.ground; rrect(-w / 2, -h / 2, w, h, 8 * T.s); g.fill();
    g.strokeStyle = col; g.lineWidth = 4 * T.s; g.stroke();
    g.fillStyle = col; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(str, 0, 2 * T.s);
    g.restore();
  }

  function drawTable(t) {
    // links and arrows behind the heads
    drawLink(0, 1, mv(t, 8.0, 0.7), win(t, 8.0, 46.2, 0.2, 0.4), 'accent',
      { str: 'secret channel', alpha: win(t, 8.3, 16.0) });
    drawArrow(2, 1, mv(t, 28.8, 0.5), win(t, 28.8, 36.0), C.muted);
    drawArrow(3, 1, mv(t, 29.1, 0.5), win(t, 29.1, 36.0), C.muted);
    drawLink(0, 1, mv(t, 50.2, 0.6), win(t, 50.2, 60.0), 'grey', null);
    drawLink(0, 1, mv(t, 60.4, 0.6), win(t, 60.4, 64.2), 'accent', { str: 'one move later', alpha: win(t, 60.8, 64.0) });
    const tri = win(t, 64.4, 68.0);
    drawLink(0, 1, mv(t, 64.4, 0.5), tri, 'accent', null);
    drawLink(1, 2, mv(t, 64.6, 0.5), tri, 'accent', null);
    drawLink(0, 2, mv(t, 64.8, 0.5), tri, 'accent', null);
    drawLink(0, 1, mv(t, 68.4, 0.7), fd(t, 68.4, 0.4), 'accent', null);
    for (let i = 0; i < 4; i++) drawAgent(t, i);
    drawMoves(t, ROUNDS, 7.0);
    drawMoves(t, TWIN_ROUNDS, 51.5);
    // stamps on the twin link
    const [ax, ay] = pos(0), [bx, by] = pos(1);
    const mx = (ax + bx) / 2, my = (ay + by) / 2;
    stamp(mx, my, 'FLAGGED', C.accent, win(t, 51.0, 56.5, 0.2, 0.3), REDUCED ? 1 : lerp(1.3, 1, mv(t, 51.0, 0.3)));
    stamp(mx, my, 'honest ✓', C.muted, win(t, 56.5, 60.0, 0.3, 0.4), 1);
    if (tri > 0.01 && ASPECT !== '1x1') text('0.000', (ax + bx + pos(2)[0]) / 3 - 20 * TS, (ay + by + pos(2)[1]) / 3 + 40 * TS,
      { size: 34 * TS, w: 700, mono: true, align: 'center', color: C.accent, alpha: win(t, 65.8, 68.0, 0.3) });
  }

  // ---------- panel (virtual 820 x 720 box) ----------
  function P(t, s, e, din = 0.4, dout = 0.4) { return win(t, s, e, din, dout); }
  const rise = (t, s) => (1 - mv(t, s, 0.6)) * 24; // entering text rises 24 px: "new item arrives"
  function para(str, x, y, o) {
    const lines = wrap(str, o.maxW || VW, o.size, o.w);
    lines.forEach((ln, k) => text(ln, x, y + k * o.size * 1.25, o));
    return y + lines.length * o.size * 1.25;
  }
  function bar(x, y, w, h, col, alpha = 1) { g.save(); g.globalAlpha *= alpha; g.fillStyle = col; g.fillRect(x, y, w, h); g.restore(); }

  function panelS01(t) {
    const a = P(t, 4.6, 7.0);
    text('Suspiciously', 0, 300 + rise(t, 4.6), { size: 84, w: 700, alpha: a });
    text('helpful.', 0, 400 + rise(t, 4.6), { size: 84, w: 700, alpha: a, color: C.accent });
    const ra = P(t, 0.8, 7.0, 0.3);
    const rn = ROUNDS.filter(r => t >= r.t).length;
    if (rn) text(`Round ${rn} of 4`, 0, 150, { size: 34, color: C.muted, alpha: ra * (1 - a * 0.5) });
  }
  function panelS02(t) {
    const a = P(t, 10.4, 16.0);
    text('Collusion', 0, 260 + rise(t, 10.4), { size: 96, w: 700, alpha: a, color: C.accent });
    const b = P(t, 11.6, 16.0);
    text('secretly teaming up', 0, 360 + rise(t, 11.6), { size: 52, w: 600, alpha: b });
    text('against everyone else.', 0, 430 + rise(t, 11.6), { size: 52, w: 600, alpha: b });
    const c = P(t, 7.4, 10.4);
    text('B plays the move', 0, 300 + rise(t, 7.4), { size: 60, w: 600, alpha: c });
    text('that lets A win.', 0, 380 + rise(t, 7.4), { size: 60, w: 600, alpha: c });
  }
  function panelS03(t) {
    const cards = ['Auctions', 'Pricing', 'Trading'];
    const out = 1 - fd(t, 23.6, 0.4);
    cards.forEach((c, k) => {
      const s = 16.6 + k * 0.8, a = fd(t, s, 0.4) * out;
      if (a <= 0.01) return;
      const y = 60 + rise(t, s), x = k * 275;
      g.save(); g.globalAlpha = a;
      g.strokeStyle = C.line; g.lineWidth = 3; rrect(x, y, 255, 110, 18); g.stroke();
      g.restore();
      text(c, x + 127, y + 70, { size: 42, w: 600, alpha: a, align: 'center' });
    });
    text('Same trick, real money.', 0, 250, { size: 40, color: C.muted, alpha: P(t, 18.8, 24.0) });
    const q = P(t, 20.0, 24.0);
    text('Can you catch it', 0, 420 + rise(t, 20.0), { size: 76, w: 700, alpha: q });
    text('from the moves alone?', 0, 515 + rise(t, 20.0), { size: 76, w: 700, alpha: q, color: C.accent });
  }
  function panelS04(t) {
    const a = P(t, 24.2, 36.0);
    text('Net influence', 0, 60, { size: 60, w: 700, alpha: a });
    text('illustrative values', VW, 60, { size: 28, color: C.muted, alpha: a, align: 'right' });
    const base = 470, unit = 360; // 1.0 -> 360 px
    const vAB = 0.85, vCB = 0.25, vDB = 0.15;
    const cols = [{ x: 60, v: vAB, s: 25.0, lab: 'A → B', col: C.accent },
                  { x: 410, v: vCB, s: 28.8, lab: 'C → B', col: C.muted },
                  { x: 630, v: vDB, s: 29.1, lab: 'D → B', col: C.muted }];
    g.save(); g.globalAlpha = a;
    g.strokeStyle = C.line; g.lineWidth = 3; g.beginPath(); g.moveTo(0, base); g.lineTo(VW, base); g.stroke();
    g.restore();
    const sub = mv(t, 30.2, 0.9); // the biggest rival bar is lifted onto A's bar and carved out
    for (const c of cols) {
      const p = mv(t, c.s, 0.8), h = c.v * unit * p, w = 170;
      const dim = c.x > 60 ? 1 - 0.65 * fd(t, 31.2, 0.5) : 1; // rivals step back once used
      bar(c.x, base - h, w, h, c.col, a * dim);
      text(c.lab, c.x + w / 2, base + 44, { size: 32, w: 600, align: 'center', alpha: a * fd(t, c.s, 0.3), mono: true });
    }
    if (t >= 30.2) {
      const h = vCB * unit;
      const fromX = 410, toX = 60, fromTop = base - h, toTop = base - vAB * unit;
      const x = lerp(fromX, toX, sub), y = lerp(fromTop, toTop, sub);
      g.save(); g.globalAlpha = a;
      g.fillStyle = C.ground; g.fillRect(x, y, 170, h * sub);
      g.setLineDash([8, 6]); g.strokeStyle = C.muted; g.lineWidth = 3; g.strokeRect(x, y, 170, h); g.restore();
      text('− best rival', 60 + 85, toTop - 16, { size: 26, align: 'center', color: C.muted, alpha: a * fd(t, 30.8, 0.4) });
      const na = fd(t, 31.0, 0.4) * a;
      const netTop = toTop + h;
      text('net', 60 + 85, netTop + 50, { size: 34, w: 700, align: 'center', color: C.ground, alpha: na });
    }
    // threshold line at 0.05
    const la = P(t, 32.4, 36.0), ly = base - 0.05 * unit;
    g.save(); g.globalAlpha = la; g.strokeStyle = C.ink; g.lineWidth = 3; g.setLineDash([10, 8]);
    g.beginPath(); g.moveTo(0, ly); g.lineTo(290 * mv(t, 32.4, 0.6), ly); g.stroke(); g.restore();
    text('0.05', 300, ly + 10, { size: 28, mono: true, alpha: la });
    text('rivals: only used to subtract', 410, 300, { size: 26, color: C.muted, alpha: a * fd(t, 31.4, 0.4) });
    // formula + flag
    const fa = P(t, 28.6, 36.0);
    text('Γ(A;B) = γ(A;B) − maxₖ γ(k;B)', 0, 590, { size: 34, mono: true, alpha: fa });
    const ba = P(t, 33.0, 36.0);
    text('A→B ✓  B→A ✓  both ≥ 0.05 →', 0, 665, { size: 32, w: 600, alpha: ba });
    if (t >= 34.0) {
      g.save(); g.translate(560, 0);
      const sa = fd(t, 34.0, 0.25) * a;
      g.globalAlpha = sa; g.font = font(36, 700); const w = g.measureText('FLAG').width + 40;
      g.strokeStyle = C.accent; g.lineWidth = 4; rrect(0, 622, w, 58, 8); g.stroke();
      g.restore();
      text('FLAG', 560 + 20, 665, { size: 36, w: 700, color: C.accent, alpha: fd(t, 34.0, 0.25) * a });
    }
  }
  function panelS05(t) {
    const a = P(t, 36.2, 40.6);
    text('Step 1 · Re-check the paper', 0, 60 + rise(t, 36.2), { size: 48, w: 700, alpha: a });
    text('Scripted RPS, colluder helps 40% of rounds', 0, 120, { size: 28, color: C.muted, alpha: a });
    const rows = [
      { g: '200 games', paper: 79.2, ours: 83.1 },
      { g: '400 games', paper: 99.3, ours: 98.9 },
    ];
    const maxW = 500, x0 = 230;
    rows.forEach((r, k) => {
      const y = 220 + k * 210;
      text(r.g, 0, y + 40, { size: 32, w: 600, alpha: a });
      [['2022 paper', r.paper, C.muted], ['ours', r.ours, C.ink]].forEach(([lab, v, col], j) => {
        const yy = y + j * 70, p = mv(t, 37.0 + k * 0.3 + j * 0.15, 0.8);
        text(lab, x0 - 20, yy + 38, { size: 26, align: 'right', color: C.muted, alpha: a });
        bar(x0, yy + 8, maxW * v / 100 * p, 44, col, a);
        text(`${v.toFixed(1)}%`, x0 + maxW * v / 100 * p + 14, yy + 42, { size: 30, mono: true, alpha: a * fd(t, 37.6 + k * 0.3, 0.4) });
      });
    });
    text('% of runs that caught the colluding pair', 0, 680, { size: 26, color: C.muted, alpha: a });
    const b = P(t, 40.8, 46.0);
    text('Step 2 · Four Llamas,', 0, 60 + rise(t, 40.8), { size: 48, w: 700, alpha: b });
    text('one secret channel', 0, 122 + rise(t, 40.8), { size: 48, w: 700, alpha: b });
    const c = P(t, 42.6, 46.0, 0.3);
    text('5 / 5', 0, 400 + rise(t, 42.6), { size: 200, w: 700, alpha: c, color: C.accent });
    text('runs: colluding pair ranked #1', 0, 480, { size: 40, w: 600, alpha: c });
  }
  function panelS06(t) {
    const a = P(t, 46.2, 54.4);
    text('Plot twist:', 0, 70 + rise(t, 46.2), { size: 60, w: 700, alpha: a });
    text('honest twins', 0, 145 + rise(t, 46.2), { size: 60, w: 700, alpha: a, color: C.accent });
    para('Two copies of the same model, no collusion at all.', 0, 230, { size: 34, maxW: 760, color: C.muted, alpha: a * fd(t, 46.8, 0.4) });
    const b = P(t, 50.2, 54.4);
    text('40 / 55', 0, 450 + rise(t, 50.2), { size: 140, w: 700, alpha: b });
    text('honest games flagged by the published rule', 0, 515, { size: 32, w: 600, alpha: b });
    text('Top pair = same-model twins in 98% of runs', 0, 570, { size: 30, color: C.muted, alpha: b * fd(t, 51.6, 0.4) });
    const c = P(t, 54.6, 60.0);
    text('Fix: set the bar', 0, 70 + rise(t, 54.6), { size: 60, w: 700, alpha: c });
    text('from honest games', 0, 145 + rise(t, 54.6), { size: 60, w: 700, alpha: c, color: C.accent });
    text('False alarms on 110 honest games', 0, 250, { size: 32, color: C.muted, alpha: c });
    const maxW = 560;
    const r1 = mv(t, 55.0, 0.8), r2 = mv(t, 56.5, 0.8);
    text('Published rule', 0, 330, { size: 32, w: 600, alpha: c });
    bar(0, 350, maxW * 0.45 / 0.5 * r1, 60, C.muted, c);
    text('45%', maxW * 0.45 / 0.5 * r1 + 16, 394, { size: 34, mono: true, alpha: c * fd(t, 55.4, 0.3) });
    text('Bar set from honest games', 0, 480, { size: 32, w: 600, alpha: c * fd(t, 56.3, 0.3) });
    bar(0, 500, Math.max(4, maxW * 0.009 / 0.5) * r2, 60, C.accent, c);
    text('0.9%', 24 + 16, 544, { size: 34, mono: true, alpha: c * fd(t, 56.9, 0.3), color: C.accent, w: 700 });
    text('target 1%, cross-validated', 0, 620, { size: 30, color: C.muted, alpha: c * fd(t, 57.2, 0.4) });
  }
  function card(t, s, e, title, sub) {
    const a = P(t, s, e);
    g.save(); g.globalAlpha = a; g.strokeStyle = C.line; g.lineWidth = 3; rrect(0, 0, VW, 660, 24); g.stroke(); g.restore();
    text(title, 50, 90 + rise(t, s), { size: 34, w: 600, color: C.muted, alpha: a });
    para(sub, 50, 160 + rise(t, s), { size: 50, w: 700, maxW: 720, alpha: a });
    return a;
  }
  function panelS07(t) {
    const a = card(t, 60.2, 64.2, 'Blind spot 1', 'A plan agreed before the game');
    const r = [['Same round', '12 / 20', C.muted], ['One move later', '20 / 20', C.accent]];
    r.forEach(([lab, v, col], k) => {
      const s = 61.4 + k * 1.0, al = a * fd(t, s, 0.4);
      text(lab, 50, 420 + k * 120, { size: 38, w: 600, alpha: al });
      text(v, 770, 420 + k * 120, { size: 60, w: 700, mono: true, align: 'right', alpha: al, color: col });
    });
    text('Runs flagged, looking at:', 50, 330, { size: 32, color: C.muted, alpha: a * fd(t, 61.0, 0.4) });
    const b = card(t, 64.2, 68.0, 'Blind spot 2', 'Three colluders hide behind each other');
    text('Every colluding pair scores', 50, 420, { size: 34, w: 600, alpha: b * fd(t, 65.2, 0.4) });
    text('0.000', 50, 530, { size: 96, w: 700, mono: true, color: C.accent, alpha: b * fd(t, 65.8, 0.3) });
    text('flagged 0 / 6 runs', 50, 600, { size: 30, color: C.muted, alpha: b * fd(t, 66.2, 0.4) });
  }
  function panelS08(t) {
    const a = fd(t, 68.2, 0.6);
    text('A screen,', 0, 150 + rise(t, 68.2), { size: 96, w: 700, alpha: a });
    text('not proof.', 0, 260 + rise(t, 68.2), { size: 96, w: 700, alpha: a, color: C.accent });
    const b = fd(t, 71.8, 0.5);
    para('Who moves together more than anyone else can explain?', 0, 370, { size: 44, w: 600, maxW: 760, alpha: b });
    const c = fd(t, 72.6, 0.5);
    text('net-influence-llm · Apart AI Collusion Sprint 2026', 0, 610, { size: 30, color: C.muted, alpha: c });
    text('Method: Bonjour, Aggarwal & Bhargava, UAI 2022', 0, 655, { size: 30, color: C.muted, alpha: c });
  }
  const PANELS = [panelS01, panelS02, panelS03, panelS04, panelS05, panelS06, panelS07, panelS08];

  function drawPanel(t) {
    g.save();
    g.translate(L.panel.x + (L.panel.w - VW * PS) / 2, L.panel.y);
    g.scale(PS, PS);
    const k = TIMELINE.beats.findIndex(b => t >= b.start && t < b.end);
    const idx = k < 0 ? 7 : k;
    if (ANIMATIC) {
      const b = TIMELINE.beats[idx];
      g.fillStyle = C.line; g.fillRect(0, 0, VW, VH);
      text(b.id, 30, 80, { size: 60, w: 700 });
      para(b.teaches, 30, 160, { size: 40, maxW: VW - 60 });
    } else PANELS[idx](t);
    g.restore();
  }

  function drawCaption(t) {
    const cap = TIMELINE.captions.find(c => t >= c.start && t < c.end);
    if (!cap) return;
    const a = win(t, cap.start, cap.end, 0.15, 0.15);
    const size = L.cap.size, lines = wrap(cap.text, L.cap.w - 60, size, 600).slice(0, 2);
    g.font = font(size, 600);
    const w = Math.max(...lines.map(l => g.measureText(l).width)) + 56;
    const h = lines.length * size * 1.3 + 30;
    const x = L.cap.cx - w / 2, y = L.cap.bottom - h;
    g.save(); g.globalAlpha = a * 0.94; g.fillStyle = C.capBg; rrect(x, y, w, h, 14); g.fill(); g.restore();
    lines.forEach((ln, k) => text(ln, L.cap.cx, y + 15 + size * 1.02 + k * size * 1.3,
      { size, w: 600, align: 'center', color: C.capInk, alpha: a }));
  }

  window.seek = function (t) {
    g.setTransform(1, 0, 0, 1, 0, 0);
    g.globalAlpha = 1;
    g.fillStyle = C.ground; g.fillRect(0, 0, L.W, L.H);
    drawTable(t); drawPanel(t);
    drawCaption(t);
  };
  window.FILM = { ASPECT, REDUCED, L };
})();
