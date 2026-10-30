/* viz.js: phase portraits of x' = Ax for the "Nine Ways a Matrix Can Flow" garage post.
   Particles are advanced with the exact matrix exponential (closed form for 2x2), so a
   stable spiral really is a stable spiral at any frame rate. No dependencies. */
(() => {
  'use strict';

  // ------------------------------------------------------------------ the nine kinds
  const KINDS = {
    snode:   { name: 'Stable node',           v: '--k-snode',   blurb: 'Two real negative eigenvalues. Everything sinks into the origin, hugging the slow eigendirection on the way in.' },
    unode:   { name: 'Unstable node',         v: '--k-unode',   blurb: 'Two real positive eigenvalues. Everything leaves the origin, peeling toward the fast eigendirection on the way out.' },
    saddle:  { name: 'Saddle',                v: '--k-saddle',  blurb: 'Real eigenvalues of opposite sign. One line comes in, one line goes out, and every other orbit is a hyperbola that does both.' },
    sspiral: { name: 'Stable spiral',         v: '--k-sspiral', blurb: 'Complex eigenvalues α ± iβ with α < 0. Orbits turn at rate β and shrink by a factor e^(2πα/β) every lap.' },
    uspiral: { name: 'Unstable spiral',       v: '--k-uspiral', blurb: 'Complex eigenvalues α ± iβ with α > 0. Orbits turn at rate β and grow by a factor e^(2πα/β) every lap.' },
    center:  { name: 'Center',                v: '--k-center',  blurb: 'Purely imaginary eigenvalues ±iβ. Every orbit is a closed ellipse with period 2π/β. Nothing grows, nothing decays.' },
    star:    { name: 'Star',                  v: '--k-star',    blurb: 'A = λI. Every direction is an eigendirection, so every orbit is a straight ray through the origin.' },
    degen:   { name: 'Degenerate node',       v: '--k-degen',   blurb: 'A repeated eigenvalue with only one eigendirection. Orbits swing around and line up with it: a spiral that ran out of turning.' },
    line:    { name: 'Line of fixed points',  v: '--k-line',    blurb: 'One eigenvalue is zero. Its eigenline is frozen in place, and every other point slides parallel to the other eigenvector.' },
    shear:   { name: 'Uniform shear',         v: '--k-none',    blurb: 'Both eigenvalues are zero but A ≠ 0. Points move along parallel lines at a speed proportional to their distance from the fixed line.' },
    zero:    { name: 'Everything fixed',      v: '--k-none',    blurb: 'A = 0. No point moves.' },
  };
  const ORDER = ['snode', 'unode', 'saddle', 'sspiral', 'uspiral', 'center', 'star', 'degen', 'line'];
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim() || '#999';

  // ------------------------------------------------------------------ 2x2 algebra
  const deg = (d) => (d * Math.PI) / 180;
  const mul = (P, Q) => [P[0]*Q[0] + P[1]*Q[2], P[0]*Q[1] + P[1]*Q[3], P[2]*Q[0] + P[3]*Q[2], P[2]*Q[1] + P[3]*Q[3]];
  const inv = (P) => { const dt = P[0]*P[3] - P[1]*P[2]; return [P[3]/dt, -P[1]/dt, -P[2]/dt, P[0]/dt]; };
  const conj = (P, D) => mul(mul(P, D), inv(P));
  const basis = (t1, t2) => [Math.cos(deg(t1)), Math.cos(deg(t2)), Math.sin(deg(t1)), Math.sin(deg(t2))];
  // eigenvalue l1 along direction t1 (degrees), l2 along t2
  const fromEig = (l1, l2, t1, t2) => conj(basis(t1, t2), [l1, 0, 0, l2]);
  // alpha +- i beta, elliptical orbits via a mild shear
  const fromSpiral = (a, b, P = [1, 0.28, 0, 0.82]) => conj(P, [a, -b, b, a]);
  const fromJordan = (l, t1, t2, k = 1) => conj(basis(t1, t2), [l, k, 0, l]);

  // e^{At} = e^{st} (C I + S M), M = A - sI, M^2 = delta I (Cayley-Hamilton, tr M = 0)
  function expm(A, t) {
    const s = (A[0] + A[3]) / 2, m0 = A[0] - s, m3 = A[3] - s;
    const delta = m0*m0 + A[1]*A[2];
    let C, S;
    if (delta > 1e-12) { const r = Math.sqrt(delta); C = Math.cosh(r*t); S = Math.sinh(r*t) / r; }
    else if (delta < -1e-12) { const r = Math.sqrt(-delta); C = Math.cos(r*t); S = Math.sin(r*t) / r; }
    else { C = 1; S = t; }
    const e = Math.exp(s*t);
    return [e*(C + S*m0), e*S*A[1], e*S*A[2], e*(C + S*m3)];
  }

  const EPS = 1e-6;
  function eig(A) {
    const tr = A[0] + A[3], det = A[0]*A[3] - A[1]*A[2], disc = tr*tr - 4*det;
    if (disc >= -EPS) { const r = Math.sqrt(Math.max(disc, 0)) / 2; return { tr, det, disc, real: true, l1: tr/2 - r, l2: tr/2 + r }; }
    return { tr, det, disc, real: false, a: tr/2, b: Math.sqrt(-disc) / 2 };
  }
  function classify(A) {
    const e = eig(A), { tr, det, disc } = e;
    const sign = tr < -EPS ? 'stable' : tr > EPS ? 'unstable' : '';
    if (Math.abs(det) < EPS) {
      if (Math.abs(tr) > EPS) return { key: 'line', sub: tr < 0 ? 'attracting' : 'repelling', e };
      return { key: A.every((x) => Math.abs(x) < EPS) ? 'zero' : 'shear', sub: '', e };
    }
    if (det < 0) return { key: 'saddle', sub: '', e };
    if (Math.abs(disc) < EPS) {
      const scalar = Math.abs(A[1]) < EPS && Math.abs(A[2]) < EPS && Math.abs(A[0] - A[3]) < EPS;
      return { key: scalar ? 'star' : 'degen', sub: sign, e };
    }
    if (disc < 0) return { key: Math.abs(tr) < EPS ? 'center' : tr < 0 ? 'sspiral' : 'uspiral', sub: '', e };
    return { key: tr < 0 ? 'snode' : 'unode', sub: '', e };
  }
  // unit eigenvector(s) for real eigenvalues; [] for star / complex / zero
  function eigvecs(A, e) {
    if (!e.real) return [];
    const one = (l) => {
      let v = Math.abs(A[1]) > EPS ? [A[1], l - A[0]] : Math.abs(A[2]) > EPS ? [l - A[3], A[2]]
            : Math.abs(l - A[0]) < Math.abs(l - A[3]) ? [1, 0] : [0, 1];
      const n = Math.hypot(v[0], v[1]); return [v[0]/n, v[1]/n];
    };
    if (Math.abs(A[1]) < EPS && Math.abs(A[2]) < EPS && Math.abs(A[0] - A[3]) < EPS) return [];
    if (Math.abs(e.l1 - e.l2) < 1e-4) return [{ v: one(e.l1), l: e.l1 }];
    return [{ v: one(e.l1), l: e.l1 }, { v: one(e.l2), l: e.l2 }];
  }

  // ------------------------------------------------------------------ gallery presets
  const PRESETS = {
    snode:   { A: fromEig(-0.55, -2.2, 22, 112),  probe: [0.9, 0.62], speed: 0.9 },
    unode:   { A: fromEig(0.45, 1.6, 18, 98),     probe: [0.035, 0.05], speed: 0.9 },
    saddle:  { A: fromEig(-1.1, 1.0, 112, 28),    probe: [-0.95, -0.35], speed: 0.9 },
    sspiral: { A: [-0.5, -1.55, 1.55, -0.5],      probe: [0.55, -0.7], speed: 0.85 },
    uspiral: { A: fromSpiral(0.22, 1.5),          probe: [0.06, -0.04], speed: 0.85 },
    center:  { A: fromSpiral(0, 1.4, [1, 0.12, 0, 0.92]), probe: [-0.3, -0.45], speed: 0.9 },
    star:    { A: [-1, 0, 0, -1],                 probe: [0.85, 0.6], speed: 0.9 },
    degen:   { A: fromJordan(-1, 22, 110, 1.1),   probe: [0.4, 0.15], speed: 0.9 },
    line:    { A: fromEig(0, -1.4, 102, 18),      probe: [0.0, -0.75], speed: 0.9 },
  };

  // ------------------------------------------------------------------ flow view
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let paused = reduce;
  const views = [];
  const TRAIL = 14;           // history samples per particle
  const R = 1;                // world is [-R, R]^2

  class FlowView {
    constructor(host, o) {
      this.host = host; this.o = Object.assign({ density: 1, speed: 1, autoProbe: null, maxProbes: 1, label: '' }, o);
      this.bg = document.createElement('canvas'); this.fg = document.createElement('canvas'); this.top = document.createElement('canvas');
      host.append(this.bg, this.fg, this.top);
      this.color = '#fff'; this.A = [0, 0, 0, 0]; this.probes = []; this.hover = null; this.visible = false;
      new ResizeObserver(() => this.resize()).observe(host);
      new IntersectionObserver((es) => { this.visible = es[0].isIntersecting; }, { rootMargin: '80px' }).observe(host);
      host.addEventListener('pointerdown', (ev) => this.drop(ev));
      host.addEventListener('pointermove', (ev) => { this.hover = this.toWorld(ev); if (paused) this.drawTop(); });
      host.addEventListener('pointerleave', () => { this.hover = null; if (paused) this.drawTop(); });
      views.push(this);
    }
    toWorld(ev) {
      const r = this.host.getBoundingClientRect();
      return [((ev.clientX - r.left) / r.width * 2 - 1) * R, (1 - (ev.clientY - r.top) / r.height * 2) * R];
    }
    px(x, y) { return [(x / R * 0.5 + 0.5) * this.W, (0.5 - y / R * 0.5) * this.H]; }
    resize() {
      const dpr = Math.min(devicePixelRatio || 1, 2), r = this.host.getBoundingClientRect();
      if (!r.width) return;
      this.dpr = dpr; this.W = r.width * dpr; this.H = r.height * dpr;
      for (const c of [this.bg, this.fg, this.top]) { c.width = this.W; c.height = this.H; }
      const n = Math.round(Math.max(200, Math.min(1400, (r.width * r.height) / 190)) * this.o.density);
      this.k = Math.max(0.55, Math.min(1, r.width / 260));   // shrink marks on small panels
      this.parts = Array.from({ length: n }, () => this.spawn({}, true));
      this.drawBg(); this.drawFg(); this.drawTop();
    }
    spawn(p, fresh) {
      const x = (Math.random() * 2 - 1) * R, y = (Math.random() * 2 - 1) * R;
      p.h = new Float32Array(TRAIL * 2); for (let k = 0; k < TRAIL; k++) { p.h[2*k] = x; p.h[2*k+1] = y; }
      p.x = x; p.y = y; p.i = 0; p.n = 0;
      p.life = 0.9 + Math.random() * 2.4; p.age = fresh ? Math.random() * p.life : 0;
      return p;
    }
    setMatrix(A, color) {
      this.A = A.slice(); if (color) this.color = color;
      this.cls = classify(this.A);
      if (this.o.autoProbe) this.resetAutoProbe();
      this.drawBg(); if (paused) { this.drawFg(); this.drawTop(); }
    }
    resetAutoProbe() { this.probes = [{ pts: [this.o.autoProbe.slice()], t: 0, done: 0 }]; }
    drop(ev) {
      const w = this.toWorld(ev);
      if (this.o.maxProbes === 1) this.probes = [];
      this.probes.push({ pts: [w], t: 0, done: 0, user: true });
      if (this.probes.length > this.o.maxProbes) this.probes.shift();
      if (this.o.onDrop) this.o.onDrop();
      this.drawTop();
    }
    clearProbes() { this.probes = []; this.drawTop(); }

    // faint streamlines + eigenlines + fixed set: redrawn only when A changes
    drawBg() {
      if (!this.W) return;
      const g = this.bg.getContext('2d'), A = this.A, W = this.W, dpr = this.dpr;
      g.fillStyle = '#101011'; g.fillRect(0, 0, W, this.H);
      const h = 0.045, Ef = expm(A, h), Eb = expm(A, -h), N = 15;
      g.strokeStyle = 'rgba(255,255,255,0.075)'; g.lineWidth = 0.8 * dpr; g.beginPath();
      for (let i = 0; i < N; i++) for (let j = 0; j < N; j++) {
        const sx = ((i + 0.5 + (((i * 7 + j * 13) % 10) / 10 - 0.5) * 0.6) / N * 2 - 1) * R;
        const sy = ((j + 0.5 + (((i * 11 + j * 5) % 10) / 10 - 0.5) * 0.6) / N * 2 - 1) * R;
        for (const E of [Ef, Eb]) {
          let x = sx, y = sy; g.moveTo(...this.px(x, y));
          for (let k = 0; k < 70; k++) {
            const nx = E[0]*x + E[1]*y, ny = E[2]*x + E[3]*y;
            if (Math.abs(nx) > 1.3*R || Math.abs(ny) > 1.3*R || Math.hypot(nx - x, ny - y) < 1e-4) break;
            x = nx; y = ny; g.lineTo(...this.px(x, y));
          }
        }
      }
      g.stroke();
      const c = this.cls;
      const [ox, oy] = this.px(0, 0);
      if (c.key === 'line' || c.key === 'shear') {
        const k = eigvecs(A, c.e).find((q) => Math.abs(q.l) < 1e-4) || { v: [1, 0] };
        g.strokeStyle = 'rgba(255,255,255,0.85)'; g.lineWidth = 1.6 * dpr; this.line(g, k.v);
        const o = eigvecs(A, c.e).find((q) => Math.abs(q.l) >= 1e-4);
        if (o) { g.strokeStyle = 'rgba(255,255,255,0.22)'; g.lineWidth = 1 * dpr; this.line(g, o.v); }
      } else if (c.key !== 'zero') {
        g.strokeStyle = 'rgba(255,255,255,0.32)'; g.lineWidth = 1 * dpr;
        for (const q of eigvecs(A, c.e)) this.line(g, q.v);
        g.fillStyle = '#fff'; g.beginPath(); g.arc(ox, oy, 2.6 * dpr, 0, 7); g.fill();
      }
    }
    line(g, v) {
      g.beginPath(); g.moveTo(...this.px(-v[0]*2*R, -v[1]*2*R)); g.lineTo(...this.px(v[0]*2*R, v[1]*2*R)); g.stroke();
    }

    step(dt) {
      if (!this.W) return;
      const t = dt * this.o.speed, E = expm(this.A, t);
      for (const p of this.parts) {
        p.age += dt;
        const x = E[0]*p.x + E[1]*p.y, y = E[2]*p.x + E[3]*p.y;
        if (p.age > p.life || Math.abs(x) > 1.05*R || Math.abs(y) > 1.05*R || !(Number.isFinite(x))) { this.spawn(p); continue; }
        p.x = x; p.y = y; p.i = (p.i + 1) % TRAIL; p.h[2*p.i] = x; p.h[2*p.i+1] = y; if (p.n < TRAIL) p.n++;
      }
      for (const pr of this.probes) {
        if (pr.done) { pr.done += dt; continue; }
        const [x0, y0] = pr.pts[pr.pts.length - 1];
        const x = E[0]*x0 + E[1]*y0, y = E[2]*x0 + E[3]*y0;
        pr.t += dt;
        const still = Math.hypot(x - x0, y - y0) < 1e-5;
        if (Math.abs(x) > 1.1*R || Math.abs(y) > 1.1*R || pr.t > 9 || still) pr.done = 1e-6;
        else if (pr.pts.length < 4000) pr.pts.push([x, y]);
      }
      if (this.o.autoProbe && this.probes.length && this.probes[0].done > 1.4) this.resetAutoProbe();
      if (this.o.maxProbes > 1) this.probes = this.probes.filter((pr) => pr.done < 2.5);
    }
    drawFg() {
      if (!this.W) return;
      const g = this.fg.getContext('2d'), dpr = this.dpr;
      g.clearRect(0, 0, this.W, this.H);
      g.strokeStyle = this.color; g.lineWidth = 1.15 * dpr; g.lineCap = 'round';
      // oldest segment first, faintest; one stroke per age bucket
      for (let k = 1; k < TRAIL; k++) {
        g.globalAlpha = (k / TRAIL) ** 1.6 * 0.85; g.beginPath();
        for (const p of this.parts) {
          if (p.n < TRAIL - k + 1) continue;
          const a = (p.i - (TRAIL - k) + TRAIL) % TRAIL, b = (a + 1) % TRAIL;
          g.moveTo(...this.px(p.h[2*a], p.h[2*a+1])); g.lineTo(...this.px(p.h[2*b], p.h[2*b+1]));
        }
        g.stroke();
      }
      g.globalAlpha = 1; g.fillStyle = this.color;
      const s = 2.3 * Math.max(0.8, this.k) * dpr;
      for (const p of this.parts) {
        const fade = Math.min(1, p.age * 3, (p.life - p.age) * 3);
        if (fade <= 0.05) continue;
        g.globalAlpha = fade; const [x, y] = this.px(p.x, p.y); g.fillRect(x - s/2, y - s/2, s, s);
      }
      g.globalAlpha = 1;
    }
    drawTop() {
      if (!this.W) return;
      const g = this.top.getContext('2d'), dpr = this.dpr;
      g.clearRect(0, 0, this.W, this.H);
      for (const pr of this.probes) {
        const a = pr.done ? Math.max(0, 1 - pr.done / (this.o.autoProbe ? 1.4 : 2.5)) : 1;
        g.globalAlpha = a; g.strokeStyle = '#fff'; g.lineWidth = 2.4 * this.k * dpr; g.lineJoin = g.lineCap = 'round';
        g.beginPath(); pr.pts.forEach(([x, y], i) => (i ? g.lineTo : g.moveTo).call(g, ...this.px(x, y))); g.stroke();
        const [hx, hy] = this.px(...pr.pts[pr.pts.length - 1]);
        g.fillStyle = '#fff'; g.beginPath(); g.arc(hx, hy, 4.6 * this.k * dpr, 0, 7); g.fill();
      }
      g.globalAlpha = 1;
      if (this.hover && this.o.arrow) {
        const [x, y] = this.hover, A = this.A, vx = A[0]*x + A[1]*y, vy = A[2]*x + A[3]*y;
        const sp = Math.hypot(vx, vy), L = Math.min(0.32, sp * 0.22) / (sp || 1);
        const [ax, ay] = this.px(x, y), [bx, by] = this.px(x + vx * L, y + vy * L);
        g.strokeStyle = '#fff'; g.fillStyle = '#fff'; g.lineWidth = 1.6 * dpr;
        g.beginPath(); g.moveTo(ax, ay); g.lineTo(bx, by); g.stroke();
        const ang = Math.atan2(by - ay, bx - ax), hl = 7 * dpr;
        if (sp > 1e-6) { g.beginPath(); g.moveTo(bx, by); g.lineTo(bx - hl*Math.cos(ang - 0.45), by - hl*Math.sin(ang - 0.45)); g.lineTo(bx - hl*Math.cos(ang + 0.45), by - hl*Math.sin(ang + 0.45)); g.fill(); }
        g.beginPath(); g.arc(ax, ay, 2.5 * dpr, 0, 7); g.fill();
        if (this.o.onHover) this.o.onHover(x, y, vx, vy);
      }
    }
  }

  let last = 0;
  function frame(t) {
    const dt = Math.min(0.05, (t - (last || t)) / 1000); last = t;
    if (!paused) for (const v of views) if (v.visible) { v.step(dt); v.drawFg(); v.drawTop(); }
    if (tour.on && !paused) tour.tick(dt);
    requestAnimationFrame(frame);
  }

  // ------------------------------------------------------------------ pause buttons (shared)
  const pauseBtns = [];
  function syncPause() {
    for (const b of pauseBtns) { b.setAttribute('aria-pressed', String(paused)); b.textContent = paused ? 'play' : 'pause'; b.title = paused ? 'Resume the animation' : 'Pause the animation'; }
  }
  function wirePause(b) { if (!b) return; pauseBtns.push(b); b.addEventListener('click', () => { paused = !paused; syncPause(); }); }

  // ------------------------------------------------------------------ gallery
  function initGallery() {
    for (const tile of document.querySelectorAll('.pp-tile[data-kind]')) {
      const k = tile.dataset.kind, P = PRESETS[k];
      tile.style.setProperty('--kc', `var(${KINDS[k].v})`);
      const v = new FlowView(tile.querySelector('.pp-view'), { autoProbe: P.probe, speed: P.speed, density: 0.9 });
      v.setMatrix(P.A, css(KINDS[k].v));
      tile.querySelector('.pp-name').addEventListener('click', () => {
        if (explorer) { explorer.load(k); document.getElementById('fig-explorer').scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' }); }
      });
    }
    wirePause(document.getElementById('gal-pause'));
  }

  // ------------------------------------------------------------------ explorer
  const SVGNS = 'http://www.w3.org/2000/svg';
  const el = (tag, attrs, parent) => { const n = document.createElementNS(SVGNS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.append(n); return n; };
  const fmt = (x) => (Math.abs(x) < 5e-3 ? '0.00' : x.toFixed(2)).replace('-', '−');
  let explorer = null;

  // (tr, det) -> a representative A with a fixed, tilted eigen-geometry
  function fromTrDet(tr, det, snapKind) {
    const disc = tr*tr - 4*det;
    if (snapKind === 'star') return [tr/2, 0, 0, tr/2];
    if (Math.abs(disc) < 1e-9) return fromJordan(tr/2, 24, 112, 1);
    if (disc > 0) { const r = Math.sqrt(disc) / 2; return fromEig(tr/2 - r, tr/2 + r, 112, 24); }
    return fromSpiral(tr/2, Math.sqrt(-disc) / 2);
  }

  const tour = {
    on: false, th: -Math.PI / 2,
    tick(dt) { this.th += dt * 0.22; explorer.setTrDet(2.5 * Math.cos(this.th), 1.15 + 2.35 * Math.sin(this.th), false); },
  };

  function initExplorer() {
    const fig = document.getElementById('fig-explorer');
    if (!fig) return;
    const $ = (s) => fig.querySelector(s);
    const kindEl = $('#ex-kind'), blurbEl = $('#ex-blurb'), readEl = $('#ex-read'), hoverEl = $('#ex-hover');
    let A = PRESETS.sspiral.A.slice();
    const view = new FlowView($('#ex-view'), {
      maxProbes: 8, arrow: true, density: 1.15, speed: 1,
      onDrop: () => stopTour(),
      onHover: (x, y, vx, vy) => { hoverEl.textContent = `x = (${fmt(x)}, ${fmt(y)})   Ax = (${fmt(vx)}, ${fmt(vy)})`; },
    });
    $('#ex-view').addEventListener('pointerleave', () => { hoverEl.textContent = 'hover: the arrow is Ax, the velocity at that point'; });

    // ---- trace-determinant plane
    const TD = { W: 360, H: 270, x0: -4, x1: 4, y0: -2.6, y1: 4.6, padL: 26, padB: 20, padT: 8, padR: 8 };
    const tx = (t) => TD.padL + (t - TD.x0) / (TD.x1 - TD.x0) * (TD.W - TD.padL - TD.padR);
    const ty = (d) => TD.padT + (TD.y1 - d) / (TD.y1 - TD.y0) * (TD.H - TD.padT - TD.padB);
    const svg = $('#ex-td');
    svg.setAttribute('viewBox', `0 0 ${TD.W} ${TD.H}`);
    const clipId = 'td-clip';
    const defs = el('defs', {}, svg); const cp = el('clipPath', { id: clipId }, defs);
    el('rect', { x: tx(TD.x0), y: ty(TD.y1), width: tx(TD.x1) - tx(TD.x0), height: ty(TD.y0) - ty(TD.y1) }, cp);
    const G = el('g', { 'clip-path': `url(#${clipId})` }, svg);
    const para = (a, b) => { let s = ''; for (let i = 0; i <= 60; i++) { const t = a + (b - a) * i / 60; s += `${tx(t)},${ty(t*t/4)} `; } return s; };
    const fillK = (k) => `color-mix(in srgb, var(${KINDS[k].v}) 20%, transparent)`;
    el('rect', { x: tx(TD.x0), y: ty(0), width: tx(TD.x1) - tx(TD.x0), height: ty(TD.y0) - ty(0), style: `fill:${fillK('saddle')}` }, G);
    el('polygon', { points: `${tx(TD.x0)},${ty(0)} ${para(TD.x0, 0)}`, style: `fill:${fillK('snode')}` }, G);
    el('polygon', { points: `${para(0, TD.x1)} ${tx(TD.x1)},${ty(0)}`, style: `fill:${fillK('unode')}` }, G);
    el('polygon', { points: `${para(TD.x0, 0)} ${tx(0)},${ty(TD.y1)} ${tx(TD.x0)},${ty(TD.y1)}`, style: `fill:${fillK('sspiral')}` }, G);
    el('polygon', { points: `${para(0, TD.x1)} ${tx(TD.x1)},${ty(TD.y1)} ${tx(0)},${ty(TD.y1)}`, style: `fill:${fillK('uspiral')}` }, G);
    for (let t = -4; t <= 4; t++) el('line', { x1: tx(t), x2: tx(t), y1: ty(TD.y0), y2: ty(TD.y1), class: 'tick', 'stroke-opacity': 0.35 }, G);
    for (let d = -2; d <= 4; d++) el('line', { x1: tx(TD.x0), x2: tx(TD.x1), y1: ty(d), y2: ty(d), class: 'tick', 'stroke-opacity': 0.35 }, G);
    el('line', { x1: tx(TD.x0), x2: tx(TD.x1), y1: ty(0), y2: ty(0), style: `stroke:var(${KINDS.line.v});stroke-width:2.2` }, G);
    el('line', { x1: tx(0), x2: tx(0), y1: ty(0), y2: ty(TD.y1), style: `stroke:var(${KINDS.center.v});stroke-width:2.2` }, G);
    el('polyline', { points: para(TD.x0, TD.x1), fill: 'none', style: `stroke:var(${KINDS.degen.v});stroke-width:2.2` }, G);
    el('line', { x1: tx(0), x2: tx(0), y1: ty(TD.y0), y2: ty(0), class: 'axis' }, G);
    const lab = (x, y, s, k) => { const n = el('text', { x: tx(x), y: ty(y), class: 'rlabel' }, svg); n.textContent = s; if (k) n.style.fill = `var(${KINDS[k].v})`; return n; };
    lab(-2.9, 3.5, 'stable spiral'); lab(2.9, 3.5, 'unstable spiral');
    lab(-3.25, 1.05, 'stable'); lab(-3.25, 0.55, 'node'); lab(3.25, 1.05, 'unstable'); lab(3.25, 0.55, 'node');
    lab(0, -1.5, 'saddle');
    const cl = lab(0.15, 3.3, 'center'); cl.setAttribute('text-anchor', 'start'); cl.style.textAnchor = 'start';
    const pl = lab(-1.55, 0.95, 'star / degenerate'); pl.setAttribute('transform', `rotate(38 ${tx(-1.55)} ${ty(0.95)})`);
    const ll = lab(-3.9, -0.42, 'line of fixed points'); ll.style.textAnchor = 'start';
    for (const t of [-4, -2, 2, 4]) { const n = el('text', { x: tx(t), y: TD.H - 6, 'text-anchor': 'middle' }, svg); n.textContent = String(t).replace('-', '−'); }
    for (const d of [-2, 2, 4]) { const n = el('text', { x: TD.padL - 6, y: ty(d) + 3.5, 'text-anchor': 'end' }, svg); n.textContent = String(d).replace('-', '−'); }
    { const n = el('text', { x: TD.W - TD.padR, y: ty(0) - 5, 'text-anchor': 'end', 'font-style': 'italic' }, svg); n.textContent = 'tr A'; }
    { const n = el('text', { x: tx(0) - 5, y: ty(TD.y1) + 10, 'text-anchor': 'end', 'font-style': 'italic' }, svg); n.textContent = 'det A'; }
    const ring = el('circle', { r: 11, class: 'handle-ring' }, svg);
    const handle = el('circle', { r: 7.5, class: 'handle', tabindex: 0, role: 'slider', 'aria-label': 'Trace and determinant of A. Drag, or use arrow keys.' }, svg);
    { const tt = el('title', {}, handle); tt.textContent = 'Drag to change tr A (left/right) and det A (up/down)'; }

    // ---- eigenvalue plane
    const EV = { W: 360, H: 120, x0: -3.2, x1: 3.2, y0: -2.2, y1: 2.2 };
    const ex = (x) => (x - EV.x0) / (EV.x1 - EV.x0) * EV.W, ey = (y) => (EV.y1 - y) / (EV.y1 - EV.y0) * EV.H;
    const esvg = $('#ex-ev'); esvg.setAttribute('viewBox', `0 0 ${EV.W} ${EV.H}`);
    el('rect', { x: 0, y: 0, width: ex(0), height: EV.H, style: 'fill:color-mix(in srgb, var(--k-sspiral) 9%, transparent)' }, esvg);
    el('rect', { x: ex(0), y: 0, width: EV.W - ex(0), height: EV.H, style: 'fill:color-mix(in srgb, var(--k-unode) 9%, transparent)' }, esvg);
    el('line', { x1: 0, x2: EV.W, y1: ey(0), y2: ey(0), class: 'axis' }, esvg);
    el('line', { x1: ex(0), x2: ex(0), y1: 0, y2: EV.H, style: 'stroke:var(--k-center);stroke-width:1.5' }, esvg);
    { const n = el('text', { x: 6, y: 13 }, esvg); n.textContent = 'decays (Re λ < 0)'; }
    { const n = el('text', { x: EV.W - 6, y: 13, 'text-anchor': 'end' }, esvg); n.textContent = 'grows (Re λ > 0)'; }
    { const n = el('text', { x: EV.W - 4, y: ey(0) - 4, 'text-anchor': 'end', 'font-style': 'italic' }, esvg); n.textContent = 'Re'; }
    { const n = el('text', { x: ex(0) + 4, y: EV.H - 5, 'font-style': 'italic' }, esvg); n.textContent = 'Im'; }
    const lam = [el('circle', { r: 6, stroke: 'var(--bg)', 'stroke-width': 2 }, esvg), el('circle', { r: 6, stroke: 'var(--bg)', 'stroke-width': 2 }, esvg)];

    // ---- matrix sliders
    const sliders = [...fig.querySelectorAll('.pp-matrix input')];
    const outs = [...fig.querySelectorAll('.pp-matrix output')];
    sliders.forEach((s, i) => s.addEventListener('input', () => { stopTour(); A[i] = +s.value; apply(false); }));

    // ---- chips
    const chips = $('#ex-chips');
    for (const k of ORDER) {
      const b = document.createElement('button');
      b.className = 'pp-chip'; b.type = 'button'; b.dataset.kind = k; b.textContent = KINDS[k].name;
      b.style.setProperty('--kc', `var(${KINDS[k].v})`); b.title = `Load the ${KINDS[k].name.toLowerCase()} from Figure 1`;
      b.addEventListener('click', () => { stopTour(); load(k); });
      chips.append(b);
    }

    let lastKey = null;
    function apply(fromPlane) {
      const c = classify(A), K = KINDS[c.key], col = css(K.v);
      if (lastKey && c.key !== lastKey) view.clearProbes();   // a trajectory from another kind of flow only confuses
      lastKey = c.key;
      view.setMatrix(A, col);
      if (!fromPlane) sliders.forEach((s, i) => { s.value = A[i]; });
      outs.forEach((o, i) => { o.value = fmt(A[i]); o.textContent = fmt(A[i]); });
      kindEl.style.setProperty('--kc', `var(${K.v})`);
      kindEl.innerHTML = `${K.name}${c.sub ? `<small>${c.sub}</small>` : ''}`;
      blurbEl.textContent = K.blurb;
      const e = c.e;
      const lamTxt = e.real ? (Math.abs(e.l1 - e.l2) < 1e-4 ? `λ₁ = λ₂ = ${fmt(e.l1)}` : `λ₁ = ${fmt(e.l1)},  λ₂ = ${fmt(e.l2)}`) : `λ = ${fmt(e.a)} ± ${fmt(e.b)}i`;
      let extra = '';
      if (!e.real && e.b > 1e-6) extra = `<dt>period</dt><dd>2π/β = ${(2*Math.PI/e.b).toFixed(2)}</dd><dt>per lap</dt><dd>` + (Math.abs(e.a) > 1e-4 ? `radius ×${Math.exp(2*Math.PI*e.a/e.b).toFixed(2)}` : 'closed orbit') + '</dd>';
      readEl.innerHTML = `<dt>tr A</dt><dd>${fmt(e.tr)}</dd><dt>det A</dt><dd>${fmt(e.det)}</dd><dt>(tr A)²/4</dt><dd>${fmt(e.tr*e.tr/4)}</dd><dt>eigenvalues</dt><dd>${lamTxt}</dd>${extra}`;
      const hx = Math.max(TD.x0, Math.min(TD.x1, e.tr)), hy = Math.max(TD.y0, Math.min(TD.y1, e.det));
      for (const n of [handle, ring]) { n.setAttribute('cx', tx(hx)); n.setAttribute('cy', ty(hy)); }
      handle.style.fill = col;
      handle.setAttribute('aria-valuetext', `trace ${fmt(e.tr)}, determinant ${fmt(e.det)}: ${K.name}`);
      const pts = e.real ? [[e.l1, 0], [e.l2, 0]] : [[e.a, e.b], [e.a, -e.b]];
      pts.forEach(([x, y], i) => {
        lam[i].setAttribute('cx', ex(Math.max(EV.x0, Math.min(EV.x1, x)))); lam[i].setAttribute('cy', ey(Math.max(EV.y0, Math.min(EV.y1, y))));
        lam[i].style.fill = col;
      });
      for (const b of chips.children) b.setAttribute('aria-pressed', String(b.dataset.kind === c.key));
    }
    function setTrDet(tr, det, snap) {
      let kind = null;
      if (snap) {
        const sx = (TD.x1 - TD.x0) / (TD.W - TD.padL - TD.padR) * 7, sy = (TD.y1 - TD.y0) / (TD.H - TD.padT - TD.padB) * 7;
        if (Math.abs(det) < sy) det = 0;
        else if (det > 0 && Math.abs(tr) < sx) tr = 0;
        if (det !== 0 && Math.abs(det - tr*tr/4) < sy * (1 + Math.abs(tr) / 2)) det = tr*tr/4;
      }
      A = fromTrDet(tr, det, kind);
      apply(false);
    }
    function load(k) { A = PRESETS[k].A.slice(); view.clearProbes(); apply(false); }

    // drag in the trace-determinant plane
    let dragging = false;
    const fromEvent = (ev) => {
      const r = svg.getBoundingClientRect(), sx = (ev.clientX - r.left) / r.width * TD.W, sy = (ev.clientY - r.top) / r.height * TD.H;
      return [TD.x0 + (sx - TD.padL) / (TD.W - TD.padL - TD.padR) * (TD.x1 - TD.x0), TD.y1 - (sy - TD.padT) / (TD.H - TD.padT - TD.padB) * (TD.y1 - TD.y0)];
    };
    svg.addEventListener('pointerdown', (ev) => { dragging = true; svg.setPointerCapture(ev.pointerId); stopTour(); setTrDet(...fromEvent(ev), true); ev.preventDefault(); });
    svg.addEventListener('pointermove', (ev) => { if (dragging) setTrDet(...fromEvent(ev), true); });
    svg.addEventListener('pointerup', () => { dragging = false; });
    handle.addEventListener('keydown', (ev) => {
      const e = eig(A), d = ev.shiftKey ? 0.5 : 0.1;
      const m = { ArrowLeft: [-d, 0], ArrowRight: [d, 0], ArrowUp: [0, d], ArrowDown: [0, -d] }[ev.key];
      if (!m) return; ev.preventDefault(); stopTour();
      setTrDet(Math.round((e.tr + m[0]) * 100) / 100, Math.round((e.det + m[1]) * 100) / 100, false);
    });

    const tourBtn = $('#ex-tour');
    function stopTour() { tour.on = false; tourBtn.setAttribute('aria-pressed', 'false'); }
    tourBtn.addEventListener('click', () => {
      tour.on = !tour.on; tourBtn.setAttribute('aria-pressed', String(tour.on));
      if (tour.on) { const e = eig(A); tour.th = Math.atan2((e.det - 1.15) / 2.35, e.tr / 2.5); if (paused) { paused = false; syncPause(); } }
    });
    $('#ex-clear').addEventListener('click', () => view.clearProbes());
    wirePause($('#ex-pause'));

    explorer = { load, setTrDet };
    apply(false);
  }

  function init() {
    initGallery(); initExplorer(); syncPause();
    requestAnimationFrame(frame);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
