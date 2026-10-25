// Procedural sound, rendered offline so audio is as deterministic as video.
// window.renderAudio() -> base64 16-bit stereo WAV, TIMELINE.duration long.
(function () {
  function mulberry32(a) {
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);

  window.renderAudio = async function () {
    const TL = window.TIMELINE, SR = 44100, DUR = TL.duration;
    const ctx = new OfflineAudioContext(2, SR * DUR, SR);
    const rnd = mulberry32(20261025);
    const master = ctx.createGain(); master.gain.value = 0.8; master.connect(ctx.destination);
    master.gain.setValueAtTime(0.8, DUR - 1.2); master.gain.linearRampToValueAtTime(0, DUR);
    const bed = ctx.createGain(); bed.gain.value = 0.5; bed.connect(master);
    const fx = ctx.createGain(); fx.gain.value = 0.9; fx.connect(master);
    const noise = ctx.createBuffer(1, SR, SR);
    { const d = noise.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = rnd() * 2 - 1; }

    function tone(t, f, dur, { type = 'sine', gain = 0.2, attack = 0.005, out = fx, pan = 0, glide = 0 } = {}) {
      const o = ctx.createOscillator(), gn = ctx.createGain(), p = ctx.createStereoPanner();
      o.type = type; o.frequency.setValueAtTime(f, t);
      if (glide) o.frequency.exponentialRampToValueAtTime(glide, t + dur * 0.6);
      gn.gain.setValueAtTime(0, t); gn.gain.linearRampToValueAtTime(gain, t + attack);
      gn.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      p.pan.value = pan;
      o.connect(gn).connect(p).connect(out); o.start(t); o.stop(t + dur + 0.05);
    }
    function noiseHit(t, dur, { gain = 0.1, f1 = 800, f2 = 3000, q = 1.2 } = {}) {
      const s = ctx.createBufferSource(); s.buffer = noise;
      const bp = ctx.createBiquadFilter(); bp.type = 'bandpass'; bp.Q.value = q;
      bp.frequency.setValueAtTime(f1, t); bp.frequency.exponentialRampToValueAtTime(f2, t + dur);
      const gn = ctx.createGain();
      gn.gain.setValueAtTime(0, t); gn.gain.linearRampToValueAtTime(gain, t + dur * 0.4);
      gn.gain.linearRampToValueAtTime(0, t + dur);
      s.connect(bp).connect(gn).connect(fx); s.start(t); s.stop(t + dur + 0.05);
    }

    // Bed: 96 BPM, four chords x 2 bars, soft pad + sparse pentatonic plucks.
    const beat = 60 / 96, bar = beat * 4;
    const chords = [[48, 55, 64, 71], [45, 52, 60, 67], [41, 48, 57, 64], [43, 50, 59, 62]];
    const penta = [72, 74, 76, 79, 81];
    const padLp = ctx.createBiquadFilter(); padLp.type = 'lowpass'; padLp.frequency.value = 1200; padLp.connect(bed);
    for (let k = 0, t0 = 0; t0 < DUR; k++, t0 += bar * 2) {
      const ch = chords[k % 4], len = Math.min(bar * 2, DUR - t0) + 0.6;
      for (const m of ch) for (const det of [-4, 4]) {
        const o = ctx.createOscillator(), gn = ctx.createGain();
        o.type = 'triangle'; o.frequency.value = hz(m); o.detune.value = det;
        gn.gain.setValueAtTime(0, t0); gn.gain.linearRampToValueAtTime(0.035, t0 + 0.8);
        gn.gain.setValueAtTime(0.035, t0 + len - 0.9); gn.gain.linearRampToValueAtTime(0, t0 + len);
        o.connect(gn).connect(padLp); o.start(t0); o.stop(t0 + len + 0.05);
      }
      for (let e = 0; e < 16; e++) {
        const t = t0 + e * beat / 2;
        if (t >= DUR - 1) break;
        if (e % 2 === 1 && rnd() < 0.55) continue;
        if (rnd() < 0.35) continue;
        tone(t, hz(penta[Math.floor(rnd() * penta.length)]), 0.5, { type: 'sine', gain: 0.05, out: bed, pan: rnd() * 0.6 - 0.3 });
      }
      // soft low pulse on beats 1 and 3
      for (let b = 0; b < 8; b += 2) { const t = t0 + b * beat; if (t < DUR - 1) tone(t, hz(ch[0] - 12), 0.4, { gain: 0.09, out: bed }); }
    }

    // Motif: the "that's collusion / flag it" idea. Same three notes each time, a fourth on the last.
    const motif = [67, 72, 76];
    for (const c of TL.cues) {
      const t = c.t;
      switch (c.sound) {
        case 'pluck': tone(t, hz(c.p ? 79 : 72), 0.35, { type: 'triangle', gain: 0.16 }); break;
        case 'tick': tone(t, 1800, 0.05, { type: 'square', gain: 0.03 }); break;
        case 'pop': tone(t, 900, 0.14, { gain: 0.18, glide: 520 }); break;
        case 'rise': tone(t, 600, 0.14, { gain: 0.16, glide: 700 }); tone(t + 0.12, 800, 0.2, { gain: 0.16, glide: 1000 }); break;
        case 'swish': noiseHit(t, 0.45, { gain: 0.08 }); break;
        case 'thud': tone(t, 140, 0.3, { gain: 0.35, glide: 60 }); noiseHit(t, 0.06, { gain: 0.05, f1: 2000, f2: 1500 }); break;
        case 'motif':
          motif.forEach((m, k) => { tone(t + k * 0.16, hz(m), 1.4, { gain: 0.14 }); tone(t + k * 0.16, hz(m + 12), 0.8, { gain: 0.04 }); });
          if (c.n === 3) tone(t + 0.48, hz(79), 2.0, { gain: 0.14 });
          break;
      }
    }

    const buf = await ctx.startRendering();
    const n = buf.length, L = buf.getChannelData(0), R = buf.getChannelData(1);
    const out = new DataView(new ArrayBuffer(44 + n * 4));
    const w = (o, s) => { for (let i = 0; i < s.length; i++) out.setUint8(o + i, s.charCodeAt(i)); };
    w(0, 'RIFF'); out.setUint32(4, 36 + n * 4, true); w(8, 'WAVE'); w(12, 'fmt ');
    out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 2, true);
    out.setUint32(24, SR, true); out.setUint32(28, SR * 4, true); out.setUint16(32, 4, true); out.setUint16(34, 16, true);
    w(36, 'data'); out.setUint32(40, n * 4, true);
    for (let i = 0; i < n; i++) {
      out.setInt16(44 + i * 4, Math.max(-1, Math.min(1, L[i])) * 32767, true);
      out.setInt16(46 + i * 4, Math.max(-1, Math.min(1, R[i])) * 32767, true);
    }
    const bytes = new Uint8Array(out.buffer);
    let bin = '';
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(bin);
  };
})();
