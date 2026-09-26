/* viz.js: figures for the SGS gridworld explainer. Plain SVG, no deps. */
(function () {
  'use strict';
  const E = window.SGSEngine;
  const NS = 'http://www.w3.org/2000/svg';
  const $ = (id) => document.getElementById(id);

  function el(tag, attrs, parent) {
    const e = document.createElementNS(NS, tag);
    if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  }
  const fmt = (x, d = 2) => Number(x).toFixed(d);
  const fmtInt = (x) => Math.round(x).toLocaleString('en-US');

  // ------------------------------------------------------------ colors
  const isDark = () => document.documentElement.getAttribute('data-theme') === 'dark';
  function succColor(p) {
    p = Math.max(0, Math.min(1, p));
    const L = isDark() ? 0.25 + 0.50 * p : 0.945 - 0.50 * p;
    return `oklch(${fmt(L, 3)} ${fmt(0.010 + 0.125 * p, 3)} 250)`;
  }
  function neutralColor(t) {
    t = Math.max(0, Math.min(1, t));
    const L = isDark() ? 0.23 + 0.30 * t : 0.95 - 0.30 * t;
    return `oklch(${fmt(L, 3)} 0.012 80)`;
  }
  function bandColor(p) {
    if (p < 0.1) return isDark() ? 'oklch(0.27 0.01 80)' : 'oklch(0.90 0.01 80)';
    if (p > 0.9) return isDark() ? 'oklch(0.40 0.07 250)' : 'oklch(0.85 0.05 250)';
    return isDark() ? 'oklch(0.66 0.14 88)' : 'oklch(0.84 0.15 88)';   // gold: frontier
  }
  const themeHooks = [];

  // ------------------------------------------------------------ grid component
  function makeGrid(svg, world) {
    const W = world.cols, H = world.rows;
    svg.setAttribute('viewBox', `-0.05 -0.05 ${W + 0.1} ${H + 0.1}`);
    const g = {
      svg, world,
      cells: el('g', {}, svg), over: el('g', {}, svg), paths: el('g', {}, svg),
      robots: el('g', {}, svg), top: el('g', {}, svg),
      rects: new Array(W * H), dots: null,
    };
    for (let r = 0; r < H; r++) {
      for (let c = 0; c < W; c++) {
        const id = r * W + c;
        if (world.blocked[id]) {
          el('rect', { x: c + 0.03, y: r + 0.03, width: 0.94, height: 0.94, rx: 0.08, class: 'wall' }, g.cells);
        } else {
          g.rects[id] = el('rect', { x: c, y: r, width: 1, height: 1, class: 'cellbg', fill: succColor(0) }, g.cells);
        }
      }
    }
    const hc = world.home % W, hr = (world.home / W) | 0;
    el('rect', { x: hc + 0.12, y: hr + 0.12, width: 0.76, height: 0.76, rx: 0.12, class: 'home-mark' }, g.top);
    el('text', { x: hc + 0.5, y: hr + 0.53, class: 'home-text' }, g.top).textContent = 's₀';

    g.fill = function (fn) {
      for (let i = 0; i < world.N; i++) g.rects[world.goals[i]].setAttribute('fill', fn(i));
      g.rects[world.home].setAttribute('fill', neutralColor(0));
    };
    g.cellAt = function (evt) {
      const pt = svg.createSVGPoint();
      pt.x = evt.clientX; pt.y = evt.clientY;
      const p = pt.matrixTransform(svg.getScreenCTM().inverse());
      return E.cellOf(world, p.x, p.y);
    };
    // sampling-probability dots, absolute scale: uniform (P = 1/N) -> r = 0.15
    g.initDots = function () {
      g.dots = world.goals.map((cell) =>
        el('circle', { cx: (cell % W) + 0.5, cy: ((cell / W) | 0) + 0.5, r: 0, class: 'probdot' }, g.over));
    };
    g.setDots = function (probs) {
      const N = world.N;
      for (let i = 0; i < N; i++) g.dots[i].setAttribute('r', fmt(Math.min(0.36, 0.14 * Math.sqrt(probs[i] * N)), 3));
    };
    return g;
  }

  // robots + trails + goal rings for a Trainer's envs
  function makeRobots(grid, n, opts) {
    opts = opts || {};
    const W = grid.world.cols;
    const items = [];
    for (let i = 0; i < n; i++) {
      items.push({
        trail: el('polyline', { class: 'trail' }, grid.paths),
        ring: opts.rings === false ? null : el('circle', { r: 0.2, class: 'goal-ring', opacity: 0.3 }, grid.paths),
        dot: el('circle', { r: opts.r || 0.13, class: 'robot' }, grid.robots),
      });
    }
    return function update(envs) {
      for (let i = 0; i < n; i++) {
        const env = envs[i], it = items[i], s = env.s;
        it.dot.setAttribute('cx', fmt(s.x, 3)); it.dot.setAttribute('cy', fmt(s.y, 3));
        let pts = '';
        const t = env.trail;
        for (let j = 0; j < t.length; j += 2) pts += fmt(t[j], 2) + ',' + fmt(t[j + 1], 2) + ' ';
        it.trail.setAttribute('points', pts);
        if (it.ring) {
          const cell = grid.world.goals[env.goal];
          it.ring.setAttribute('cx', (cell % W) + 0.5); it.ring.setAttribute('cy', ((cell / W) | 0) + 0.5);
        }
      }
    };
  }

  // ------------------------------------------------------------ plot helpers
  function scales(x0, x1, y0, y1, box) {
    return {
      x: (v) => box.l + ((v - x0) / (x1 - x0)) * (box.w - box.l - box.r),
      y: (v) => box.h - box.b - ((v - y0) / (y1 - y0)) * (box.h - box.t - box.b),
    };
  }
  function axes(svg, S, box, xt, yt, xl, yl) {
    const g = el('g', {}, svg);
    el('path', { d: `M${box.l},${box.t} V${box.h - box.b} H${box.w - box.r}`, class: 'axis' }, g);
    for (const v of xt) {
      el('text', { x: S.x(v), y: box.h - box.b + 13, 'font-size': 10, 'text-anchor': 'middle' }, g).textContent = v;
    }
    for (const v of yt) {
      el('text', { x: box.l - 5, y: S.y(v) + 3, 'font-size': 10, 'text-anchor': 'end' }, g).textContent = v;
      if (v !== yt[0]) el('line', { x1: box.l, x2: box.w - box.r, y1: S.y(v), y2: S.y(v), class: 'gridline' }, g);
    }
    if (xl) el('text', { x: box.w - box.r, y: box.h - 2, 'font-size': 10, 'text-anchor': 'end' }, g).textContent = xl;
    if (yl) el('text', { x: box.l + 4, y: box.t - 4, 'font-size': 10 }, g).textContent = yl;
    return g;
  }
  const polyPts = (xs, ys, S) => xs.map((x, i) => fmt(S.x(x), 1) + ',' + fmt(S.y(ys[i]), 1)).join(' ');

  // ------------------------------------------------------------ animation loop
  const figs = [];
  function register(node, frame) {
    const f = { node, frame, visible: false };
    figs.push(f);
    new IntersectionObserver((es) => { for (const e of es) f.visible = e.isIntersecting; }, { rootMargin: '80px' }).observe(node);
    return f;
  }
  let last = performance.now();
  function loop(now) {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    for (const f of figs) if (f.visible) f.frame(dt, now);
    requestAnimationFrame(loop);
  }

  const world = E.makeWorld();
  if ($('n-configs')) $('n-configs').textContent = world.N;

  // ============================================================ 0 · hero
  (function hero() {
    if (!$('fig-hero')) return;   // figure not on this page (e.g. held from the garage post)
    const grid = makeGrid($('hero-grid'), world);
    grid.initDots();
    const N_ENV = 48, WARM_EPISODES = 2500;
    let heroFc = 0;
    let tr, robots;
    function restart() {
      tr = new E.Trainer({ mode: 'sgs', envs: N_ENV, seed: 7 });
      // skip the cold start (a few lucky cells hogging mass); open on a formed frontier
      while (tr.episodes < WARM_EPISODES) tr.tick(false);
      if (!robots) robots = makeRobots(grid, N_ENV, { rings: false });
    }
    restart();
    $('hero-restart').onclick = restart;
    // playback speed in simulated seconds per real second: 1x is real time
    let heroSpeed = 1, heroAcc = 0;
    document.querySelectorAll('[data-hero-speed]').forEach((btn, _, all) => (btn.onclick = () => {
      heroSpeed = +btn.dataset.heroSpeed;
      all.forEach((b) => b.setAttribute('aria-pressed', b === btn));
    }));

    // inlay: histogram of tracked p-hat over goals, overlaid with the sampler curve
    const inlay = $('hero-inlay'), NB = 10;
    const ibox = { l: 8, r: 8, t: 10, b: 18, w: 300, h: 104 };
    const IS = scales(0, 1, 0, 1, ibox);
    el('line', { x1: ibox.l, x2: ibox.w - ibox.r, y1: IS.y(0), y2: IS.y(0), class: 'axis' }, inlay);
    [0, 0.5, 1].forEach((v) => (el('text', { x: IS.x(v), y: ibox.h - 4, 'font-size': 9.5, 'text-anchor': 'middle' }, inlay).textContent = v));
    el('text', { x: ibox.w - ibox.r, y: ibox.h - 4, 'font-size': 9.5, 'text-anchor': 'end' }, inlay).textContent = '';
    const bw = IS.x(1 / NB) - IS.x(0);
    const bins = Array.from({ length: NB }, (_, j) => ({
      rect: el('rect', { x: IS.x(j / NB) + 1, width: bw - 2, rx: 1.5 }, inlay),
      lab: el('text', { x: IS.x((j + 0.5) / NB), 'font-size': 8.5, 'text-anchor': 'middle' }, inlay),
    }));
    const curve = el('polyline', { class: 'curve-prob' }, inlay);
    const xsI = Array.from({ length: 101 }, (_, i) => i / 100);
    const hoverBand = el('rect', { y: ibox.t - 6, height: IS.y(0) - ibox.t + 6, width: bw, fill: 'var(--fg)', opacity: 0, 'pointer-events': 'none' }, inlay);
    let hoverBin = -1;
    function drawInlay() {
      const c = tr.cfg, counts = new Array(NB).fill(0);
      const rates = tr.monitor.rate;
      for (let i = 0; i < world.N; i++) counts[Math.min(NB - 1, Math.floor(rates[i] * NB))]++;
      const cap = Math.max(12, ...counts.slice(1));   // p-hat=0 bin can dwarf the rest; clip it
      bins.forEach((b, j) => {
        const hgt = Math.min(1, counts[j] / cap) * 0.92;
        b.rect.setAttribute('y', IS.y(hgt)); b.rect.setAttribute('height', Math.max(0, IS.y(0) - IS.y(hgt)));
        b.rect.setAttribute('fill', succColor((j + 0.5) / NB));
        b.lab.setAttribute('y', IS.y(hgt) - 2);
        b.lab.textContent = counts[j] ? (counts[j] > cap ? counts[j] + '↑' : counts[j]) : '';
      });
      const pr = xsI.map((x) => Math.pow(E.betaWeight(x, c) + c.eps, 1 / c.T));
      const pm = Math.max(...pr);
      curve.setAttribute('points', polyPts(xsI, pr.map((v) => (v / pm) * 0.92), IS));
      let band = 0;
      for (let i = 0; i < world.N; i++) if (rates[i] >= 0.1 && rates[i] <= 0.9) band += tr.probs[i];
      $('inlay-mass').textContent = `${Math.round(band * 100)}% of sampling on the frontier`;
      if (hoverBin >= 0) markBin(hoverBin);
    }
    function markBin(j) {
      const rates = tr.monitor.rate;
      for (let i = 0; i < world.N; i++) grid.rects[world.goals[i]].classList.toggle('inbin', Math.min(NB - 1, Math.floor(rates[i] * NB)) === j);
    }
    const heroSvgEl = $('hero-grid');
    inlay.addEventListener('mousemove', (e) => {
      const pt = inlay.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
      const x = pt.matrixTransform(inlay.getScreenCTM().inverse()).x;
      const j = Math.max(0, Math.min(NB - 1, Math.floor(((x - ibox.l) / (ibox.w - ibox.l - ibox.r)) * NB)));
      if (j !== hoverBin) { hoverBin = j; markBin(j); }
      hoverBand.setAttribute('x', IS.x(j / NB)); hoverBand.setAttribute('opacity', 0.07);
      heroSvgEl.dataset.focus = 'bin';
    });
    inlay.addEventListener('mouseleave', () => { hoverBin = -1; hoverBand.setAttribute('opacity', 0); delete heroSvgEl.dataset.focus; });
    // key rows spotlight their symbol on the map
    const heroSvg = $('hero-grid');
    document.querySelectorAll('#fig-hero .key-row').forEach((row) => {
      const on = () => (heroSvg.dataset.focus = row.dataset.key);
      const off = () => delete heroSvg.dataset.focus;
      row.addEventListener('mouseenter', on); row.addEventListener('focus', on);
      row.addEventListener('mouseleave', off); row.addEventListener('blur', off);
    });
    // key swatches share the live color functions so they track the theme
    const keyRamp = $('key-ramp');
    const rampRects = [0, 1, 2, 3].map((j) => el('rect', { x: 0, y: j * 0.25, width: 1, height: 0.25 }, keyRamp));
    const setRamp = () => {
      rampRects.forEach((r, j) => r.setAttribute('fill', succColor(j / 3)));
      ['key-free', 'key-dot'].forEach((id) => $(id).setAttribute('fill', succColor(0)));
      $('key-home').setAttribute('fill', neutralColor(0));
    };
    setRamp(); themeHooks.push(setRamp);
    register($('fig-hero'), (dt) => {
      // cap the backlog at 2 s of sim per frame (enough headroom for 100x at 60 fps)
      heroAcc = Math.min(heroAcc + dt * heroSpeed, 2);
      while (heroAcc >= E.PHYS.dt) { tr.tick(true); heroAcc -= E.PHYS.dt; }
      if (tr.episodes > 36000) restart();
      grid.fill((i) => succColor(tr.monitor.rate[i]));
      grid.setDots(tr.probs);
      robots(tr.envs);
      $('hero-ep').textContent = 'episode ' + fmtInt(tr.episodes);
      if (++heroFc % 6 === 0) drawInlay();
    });
  })();

  // ============================================================ 1 · robot
  // Gaussian policy view: the PD law is the mean action, sigma the noise scale.
  // "8 rollouts" runs independent samples from the same start, goal and gains.
  (function robot() {
    if (!$('fig-robot')) return;   // figure not on this page (e.g. held from the garage post)
    const grid = makeGrid($('robot-grid'), world);
    grid.fill(() => neutralColor(0));
    const W = world.cols;
    const K = new Float64Array(world.rows * W);
    const rng = E.mulberry32(3);
    let goal = world.goalIndexOfCell[5 * W + 8];
    let M = 1, bots = [], hold = 0, tried = 0, reached = 0, acc = 0, prevSpeeds = [];
    const P = Object.assign({}, E.PHYS);
    const pathEl = el('polyline', { class: 'path' }, grid.paths);
    const ring = el('circle', { r: E.PHYS.goalTol, class: 'goal-ring' }, grid.paths);
    const trailG = el('g', {}, grid.paths), botG = el('g', {}, grid.robots);
    const force = el('line', { class: 'force' }, grid.robots);
    const vel = el('line', { class: 'vel' }, grid.robots);

    // speed plot: first rollout bold, the other samples faint
    const sp = $('robot-speed'), box = { l: 28, r: 6, t: 12, b: 18, w: 300, h: 120 };
    const S = scales(0, 8, 0, 3, box);
    axes(sp, S, box, [0, 2, 4, 6, 8], [0, 1, 2, 3], 't (s)', '|v|');
    const prevLine = el('polyline', { class: 'curve-muted' }, sp);
    const sampleG = el('g', {}, sp);
    const line = el('polyline', { class: 'curve-accent' }, sp);

    function setK() {
      const v = +$('robot-k').value;
      $('robot-k-out').textContent = fmt(v, 1);
      $('robot-kd').innerHTML = `K<sub>d</sub> = 2√K<sub>p</sub> = ${fmt(2 * Math.sqrt(v), 1)}`;
      for (let c = 0; c < K.length; c++) K[c] = world.blocked[c] ? 0 : v;
    }
    function setSigma() {
      P.noise = +$('robot-sigma').value;
      $('robot-sigma-out').textContent = fmt(P.noise, 1) + (P.noise === E.PHYS.noise ? ' (training)' : P.noise === 0 ? ' (deterministic)' : '');
    }
    function drawPath() {
      let u = world.home, p = [];
      const g = world.goals[goal];
      p.push((u % W) + 0.5, ((u / W) | 0) + 0.5);
      for (let n = 0; n < 60 && u !== g; n++) { u = E.nextCell(world, goal, u); p.push((u % W) + 0.5, ((u / W) | 0) + 0.5); }
      let str = '';
      for (let j = 0; j < p.length; j += 2) str += p[j] + ',' + p[j + 1] + ' ';
      pathEl.setAttribute('points', str);
      ring.setAttribute('cx', (g % W) + 0.5); ring.setAttribute('cy', ((g / W) | 0) + 0.5);
    }
    function start() {
      trailG.replaceChildren(); botG.replaceChildren(); sampleG.replaceChildren();
      bots = Array.from({ length: M }, (_, j) => ({
        s: E.newState(world, rng), pts: [], speeds: [], done: 0,
        trail: el('polyline', { class: 'trail', style: `opacity:${M > 1 ? 0.4 : 0.55}` }, trailG),
        dot: el('circle', { r: E.PHYS.radius * (M > 1 ? 0.8 : 1), class: 'robot' }, botG),
        sline: j > 0 ? el('polyline', { class: 'curve-accent', style: 'stroke-width:1;opacity:.3' }, sampleG) : null,
      }));
      hold = 0;
      $('robot-status').textContent = 'running';
    }
    // debug: ?rollouts=8 opens in the fan view (review screenshots)
    if (+new URLSearchParams(location.search).get('rollouts') > 1) {
      M = 8; document.querySelectorAll('[data-robot-n]').forEach((b) => b.setAttribute('aria-pressed', b.dataset.robotN === '8'));
    }
    setK(); setSigma(); drawPath(); start();
    $('robot-k').oninput = setK;
    $('robot-sigma').oninput = setSigma;
    document.querySelectorAll('[data-robot-n]').forEach((btn, _, all) => (btn.onclick = () => {
      M = +btn.dataset.robotN;
      all.forEach((b) => b.setAttribute('aria-pressed', b === btn));
      prevSpeeds = []; start();
    }));
    $('robot-grid').addEventListener('click', (e) => {
      const c = grid.cellAt(e);
      if (c >= 0 && world.goalIndexOfCell[c] >= 0) { goal = world.goalIndexOfCell[c]; tried = reached = 0; prevSpeeds = []; drawPath(); start(); }
    });
    $('robot-grid').style.cursor = 'crosshair';

    const toLine = (a) => { let q = ''; for (let j = 0; j < a.length; j += 2) q += fmt(S.x(a[j]), 1) + ',' + fmt(S.y(Math.min(3, a[j + 1])), 1) + ' '; return q; };
    register($('fig-robot'), (dt) => {
      const allDone = bots.every((b) => b.done);
      if (allDone) {
        hold -= dt;
        if (hold <= 0) { prevSpeeds = bots[0].speeds; start(); }
        return;
      }
      acc += dt * 1.5;
      const g = world.goals[goal];
      const gx = (g % W) + 0.5, gy = ((g / W) | 0) + 0.5;
      while (acc >= P.dt) {
        acc -= P.dt;
        for (const b of bots) {
          if (b.done) continue;
          const s = b.s;
          const [ax, ay] = E.policyAccel(world, K, goal, s, rng, P);
          E.integrate(world, s, ax, ay);
          s.t += P.dt;
          b.pts.push(s.x, s.y); b.speeds.push(s.t, Math.hypot(s.vx, s.vy));
          if (Math.hypot(s.x - gx, s.y - gy) < P.goalTol) b.done = 1;
          else if (s.t >= P.horizon) b.done = 2;
          if (b.done) { tried++; if (b.done === 1) reached++; b.dot.setAttribute('opacity', b.done === 1 ? 1 : 0.35); }
        }
      }
      const nOk = bots.filter((b) => b.done === 1).length, nOut = bots.filter((b) => b.done === 2).length;
      if (bots.every((b) => b.done)) {
        hold = 1.1;
        $('robot-status').textContent = M === 1
          ? (nOk ? `reached in ${fmt(bots[0].s.t, 1)} s` : 'timed out')
          : `${nOk} / ${M} reached · ${nOut} timed out`;
      } else if (M > 1) $('robot-status').textContent = `running · ${nOk} / ${M} reached`;
      $('robot-rec').textContent = `${reached} / ${tried}`;
      for (const b of bots) {
        let str = '';
        for (let j = 0; j < b.pts.length; j += 2) str += fmt(b.pts[j], 2) + ',' + fmt(b.pts[j + 1], 2) + ' ';
        b.trail.setAttribute('points', str);
        b.dot.setAttribute('cx', b.s.x); b.dot.setAttribute('cy', b.s.y);
        if (b.sline) b.sline.setAttribute('points', toLine(b.speeds));
      }
      const s = bots[0].s;
      force.setAttribute('x1', s.x); force.setAttribute('y1', s.y);
      force.setAttribute('x2', s.x + s.ax * 0.09); force.setAttribute('y2', s.y + s.ay * 0.09);
      vel.setAttribute('x1', s.x); vel.setAttribute('y1', s.y);
      vel.setAttribute('x2', s.x + s.vx * 0.35); vel.setAttribute('y2', s.y + s.vy * 0.35);
      line.setAttribute('points', toLine(bots[0].speeds));
      prevLine.setAttribute('points', M === 1 ? toLine(prevSpeeds) : '');
      $('robot-t').textContent = fmt(s.t, 1) + ' s';
      $('robot-v').textContent = fmt(Math.hypot(s.vx, s.vy));
    });
  })();

  // ============================================================ 2 · task configurations
  (function tasks() {
    if (!$('fig-tasks')) return;   // figure not on this page (e.g. held from the garage post)
    const grid = makeGrid($('tasks-grid'), world);
    const W = world.cols;
    const maxL = Math.max(...world.pathLen);
    const paint = () => grid.fill((i) => neutralColor(world.pathLen[i] / maxL));
    paint(); themeHooks.push(paint);
    const k0 = new Float64Array(world.rows * W);   // initial gains Kp, before any training
    for (let c = 0; c < k0.length; c++) k0[c] = world.blocked[c] ? 0 : E.LEARN.K0;
    const pathEl = el('polyline', { class: 'path' }, grid.top);
    const ghostG = el('g', {}, grid.paths);
    const hl = el('rect', { width: 1, height: 1, class: 'hl', visibility: 'hidden' }, grid.top);
    const cache = {};

    // untrained success per config (8 rollouts each)
    const rng = E.mulberry32(21);
    const succ = world.goals.map((_, i) => { let s = 0; for (let m = 0; m < 8; m++) s += E.rollout(world, k0, i, rng).ok; return s / 8; });

    const sc = $('tasks-scatter'), box = { l: 30, r: 8, t: 14, b: 22, w: 300, h: 200 };
    const S = scales(0, Math.ceil(maxL), 0, 1, box);
    axes(sc, S, box, [0, 4, 8, 12, 16], [0, 0.5, 1], 'path length (cells)', 'success');
    const jr = E.mulberry32(4);
    const dots = world.goals.map((_, i) =>
      el('circle', { cx: S.x(world.pathLen[i]), cy: S.y(Math.max(0, Math.min(1, succ[i] + (jr() - 0.5) * 0.03))), r: 2.6, fill: 'var(--fg-faint)', opacity: 0.7 }, sc));
    const hiDot = el('circle', { r: 5, fill: 'none', stroke: 'var(--fg)', 'stroke-width': 1.5, visibility: 'hidden' }, sc);

    function show(i) {
      const g = world.goals[i];
      hl.setAttribute('x', g % W); hl.setAttribute('y', (g / W) | 0); hl.setAttribute('visibility', 'visible');
      let u = world.home, str = `${(u % W) + 0.5},${((u / W) | 0) + 0.5} `;
      for (let n = 0; n < 60 && u !== g; n++) { u = E.nextCell(world, i, u); str += `${(u % W) + 0.5},${((u / W) | 0) + 0.5} `; }
      pathEl.setAttribute('points', str);
      if (!cache[i]) { const r = E.mulberry32(100 + i); cache[i] = Array.from({ length: 12 }, () => E.rollout(world, k0, i, r)); }
      ghostG.replaceChildren();
      let ok = 0;
      for (const ro of cache[i]) {
        ok += ro.ok;
        let q = '';
        for (let j = 0; j < ro.pts.length; j += 3 * 2) q += fmt(ro.pts[j], 2) + ',' + fmt(ro.pts[j + 1], 2) + ' ';
        el('polyline', { points: q, class: ro.ok ? 'ghost-ok' : 'ghost-fail' }, ghostG);
      }
      $('tasks-readout').textContent = `path ${fmt(world.pathLen[i], 1)} cells · ${ok}/12 reached`;
      hiDot.setAttribute('cx', dots[i].getAttribute('cx')); hiDot.setAttribute('cy', dots[i].getAttribute('cy'));
      hiDot.setAttribute('visibility', 'visible');
    }
    $('tasks-grid').addEventListener('mousemove', (e) => {
      const c = grid.cellAt(e);
      if (c >= 0 && world.goalIndexOfCell[c] >= 0) show(world.goalIndexOfCell[c]);
    });
    show(world.goalIndexOfCell[3 * W + 7]);
  })();

  // ============================================================ 3 · signal
  (function signal() {
    if (!$('fig-signal')) return;   // figure not on this page (e.g. held from the garage post)
    const EPS = 12000;
    $('signal-eps').textContent = fmtInt(EPS);
    const grid = makeGrid($('signal-grid'), world);
    const tr = new E.Trainer({ mode: 'uniform', envs: 64, seed: 3 });
    while (tr.episodes < EPS) tr.tick(false);
    const p = tr.evaluate(8, 777);
    const paint = () => grid.fill((i) => bandColor(p[i]));
    paint(); themeHooks.push(paint);

    const cv = $('signal-curve'), box = { l: 34, r: 8, t: 14, b: 22, w: 300, h: 170 };
    const S = scales(0, 1, 0, 0.27, box);
    el('rect', { x: S.x(0.1), y: box.t, width: S.x(0.9) - S.x(0.1), height: box.h - box.t - box.b, class: 'bandrect' }, cv);
    axes(cv, S, box, [0, 0.5, 1], [0, 0.1, 0.2], 'success rate p', 'signal');
    const xs = Array.from({ length: 101 }, (_, i) => i / 100);
    el('polyline', { points: polyPts(xs, xs.map((x) => x * (1 - x)), S), class: 'curve-accent' }, cv);
    const jr = E.mulberry32(8);
    for (let i = 0; i < world.N; i++) {
      el('circle', { cx: S.x(p[i]) + (jr() - 0.5) * 5, cy: S.y(p[i] * (1 - p[i])) + (jr() - 0.5) * 3, r: 2.4,
        fill: p[i] < 0.1 || p[i] > 0.9 ? 'var(--fg-faint)' : 'var(--prob)', opacity: 0.75 }, cv);
    }

    // where each sampler spends: uniform = area fractions; SGS = paper-kernel mass on the same p
    const cat = (x) => (x < 0.1 ? 0 : x > 0.9 ? 2 : 1);
    const uni = [0, 0, 0], sgs = [0, 0, 0];
    const probs = E.kernelProbs(p, E.PRESETS.paper);
    for (let i = 0; i < world.N; i++) { uni[cat(p[i])] += 1 / world.N; sgs[cat(p[i])] += probs[i]; }
    drawSpendBars($('signal-bars'), [['uniform', uni], ['SGS', sgs]]);
  })();

  function drawSpendBars(svg, rows, labels) {
    svg.replaceChildren();
    labels = labels || ['too hard', 'frontier', 'mastered'];
    const fills = ['var(--fg-faint)', 'var(--band)', 'var(--accent)'];
    const ops = [0.35, 1, 0.35];
    const x0 = 58, x1 = 296, bh = 20;
    rows.forEach(([name, v], r) => {
      const y = 6 + r * (bh + 10);
      el('text', { x: x0 - 6, y: y + bh / 2 + 4, 'font-size': 11, 'text-anchor': 'end', style: 'fill:var(--fg)' }, svg).textContent = name;
      let x = x0;
      v.forEach((f, j) => {
        const w = f * (x1 - x0);
        el('rect', { x, y, width: Math.max(0, w), height: bh, fill: fills[j], opacity: ops[j] }, svg);
        if (w > 26) el('text', { x: x + w / 2, y: y + bh / 2 + 4, 'font-size': 10, 'text-anchor': 'middle', style: 'fill:var(--fg)' }, svg).textContent = Math.round(f * 100) + '%';
        x += w;
      });
    });
    const yl = 6 + rows.length * (bh + 10) + 2;
    if (svg.viewBox.baseVal && yl + 6 > svg.viewBox.baseVal.height) svg.setAttribute('viewBox', `0 0 300 ${yl + 8}`);
    labels.forEach((l, j) => {
      el('rect', { x: x0 + j * 80, y: yl - 7, width: 8, height: 8, fill: fills[j], opacity: ops[j] }, svg);
      el('text', { x: x0 + j * 80 + 12, y: yl, 'font-size': 10 }, svg).textContent = l;
    });
  }

  // ============================================================ 6 · loop diagram (built before 4 so 4 can pulse it)
  const pulseLoop = (function loopDiagram() {
    if (!$('fig-loop')) return () => {};   // figure not on this page (e.g. held from the garage post)
    const svg = $('loop-svg');
    const steps = [
      ['episode ends', 'outcome o ∈ {0,1}'],
      ['attribute', 'monitor.update(i, o)'],
      ['score', 'w = beta(p̂; t, κ, ε)'],
      ['normalize', 'softmax(log w / T)'],
      ['sample', "i' ~ multinomial(P)"],
      ['apply', "domain.apply(env, i')"],
    ];
    // size every box to its own text (measured), with padding, then fit the row
    const PAD_X = 14, bh = 52, gap = 26, y = 18;
    const nodes = steps.map(([a, b]) => {
      const g = el('g', { class: 'loop-node' }, svg);
      const rect = el('rect', { y, height: bh }, g);
      const t1 = el('text', { y: y + 19 }, g); t1.textContent = a;
      const t2 = el('text', { y: y + 37, class: 'sub' }, g); t2.textContent = b;
      const tw = (t) => { const w = t.getComputedTextLength(); return w > 0 ? w : t.textContent.length * 6.2; };
      return { g, rect, t1, t2, w: Math.ceil(Math.max(tw(t1), tw(t2))) + 2 * PAD_X };
    });
    const total = nodes.reduce((acc, n) => acc + n.w, 0) + gap * (nodes.length - 1);
    const VBW = Math.max(760, total + 8), VBH = 150;
    svg.setAttribute('viewBox', `0 0 ${VBW} ${VBH}`);
    let x = (VBW - total) / 2;
    nodes.forEach((n, j) => {
      n.rect.setAttribute('x', x); n.rect.setAttribute('width', n.w);
      n.t1.setAttribute('x', x + n.w / 2); n.t2.setAttribute('x', x + n.w / 2);
      n.cx = x + n.w / 2;
      if (j < nodes.length - 1) el('path', { d: `M${x + n.w + 3},${y + bh / 2} H${x + n.w + gap - 4}`, class: 'loop-edge' }, svg);
      x += n.w + gap;
    });
    const xl = nodes[nodes.length - 1].cx, xf = nodes[0].cx;
    el('path', { d: `M${xl},${y + bh + 3} V${y + bh + 34} H${xf} V${y + bh + 5}`, class: 'loop-edge' }, svg);
    el('text', { x: VBW / 2, y: y + bh + 30, 'font-size': 11, 'text-anchor': 'middle' }, svg).textContent =
      'rollout: the policy acts until success or timeout (other envs keep running in parallel)';
    const ret = svg.querySelectorAll('.loop-edge');
    const retEdge = ret[ret.length - 1];
    retEdge.classList.add('loop-return');

    // One slow wave every PERIOD seconds, driven by the figure clock (so it pauses
    // off-screen): each box fades in and bumps up, holds, then settles back; the
    // rollout edge lights last. The wave takes ~8 s, then the diagram rests.
    const PERIOD = 20, STAGGER = 1.0, HOLD = 1.6;
    let t = 0;
    register($('fig-loop'), (dt) => {
      t += dt;
      if (t >= PERIOD) t -= PERIOD;
      nodes.forEach((n, j) => n.g.classList.toggle('on', t >= j * STAGGER && t < j * STAGGER + HOLD));
      const jr = nodes.length;
      retEdge.classList.toggle('on', t >= jr * STAGGER && t < jr * STAGGER + HOLD);
    });
    return () => {};   // episode ends no longer drive the diagram
  })();

  // ============================================================ 4 · monitor + 5 · kernel (shared live trainer)
  const mon = (function monitor() {
    if (!$('fig-monitor')) return null;   // figure not on this page (e.g. held from the garage post)
    const grid = makeGrid($('mon-grid'), world);
    grid.initDots();
    const W = world.cols;
    const tr = new E.Trainer({ mode: 'sgs', envs: 24, seed: 11 });
    // open with all three categories present (mastered / frontier / unsolved)
    while (tr.episodes < 1500) tr.tick(false);
    const robots = makeRobots(grid, 24);
    const H = tr.cfg.H, m = tr.monitor;
    let playing = true;
    tr.onEpisode = () => pulseLoop();

    // ---- three sliding-window strips: mastered, frontier, unsolved (or the user's pick)
    const svg = $('mon-strips');
    const X0 = 16, STEP = 17.2, R = 6.2, BAR_X = 300, BAR_W = 52, ROW_H = 64, TOP = 22;
    el('text', { x: X0 - R, y: 11, 'font-size': 9.5 }, svg).textContent = 'oldest';
    el('text', { x: X0 + (H - 1) * STEP + R, y: 11, 'font-size': 9.5, 'text-anchor': 'end' }, svg).textContent = 'newest →';
    el('text', { x: BAR_X, y: 11, 'font-size': 9.5 }, svg).textContent = 'p̂ = filled / H';
    const clip = el('clipPath', { id: 'strip-clip' }, el('defs', {}, svg));
    el('rect', { x: X0 - R - 1.5, y: 0, width: (H - 1) * STEP + 2 * R + 3, height: 214 }, clip);
    const DASH = ['', '5 3', '1.5 3'];     // sparkline style per row
    const rows = [0, 1, 2].map((r) => {
      const y = TOP + r * ROW_H, cy = y + 24;
      const g = el('g', {}, svg);
      const o = {
        r, cell: -1, lastCount: -1, anim: 0, dropped: null, picked: false, hist: [],
        label: el('text', { x: X0 - R, y: y + 6, 'font-size': 11, style: 'fill:var(--fg)' }, g),
        sub: el('text', { x: X0 - R, y: cy + 21, 'font-size': 9.5 }, g),
        strip: el('g', { 'clip-path': 'url(#strip-clip)' }, g),
        pval: el('text', { x: BAR_X, y: cy + 4, 'font-size': 14, style: 'fill:var(--fg)' }, g),
        barBg: el('rect', { x: BAR_X, y: cy + 9, width: BAR_W, height: 5, rx: 1.5, fill: 'var(--rule)' }, g),
        bar: el('rect', { x: BAR_X, y: cy + 9, width: 0, height: 5, rx: 1.5, fill: 'var(--accent)' }, g),
        cy,
      };
      o.dots = Array.from({ length: H + 1 }, () => el('circle', { r: R, cy, 'stroke-width': 1.4 }, o.strip));
      // map badge: outline + row number
      o.mark = el('rect', { width: 1, height: 1, class: 'hl', visibility: 'hidden' }, grid.top);
      o.badge = el('text', { 'font-size': 0.36, 'font-weight': 700, style: 'fill:var(--fg)', visibility: 'hidden' }, grid.top);
      o.badge.textContent = r + 1;
      return o;
    });
    const ROLE = ['mastered', 'frontier', 'unsolved'];
    const cat = (i) => (m.rate[i] > 0.9 ? 'mastered' : m.rate[i] >= 0.1 ? 'frontier' : 'unsolved');

    // Keep a row's cell while it still fits its role; otherwise pick a well-sampled replacement.
    function choose(role, cur) {
      const r = m.rate, c = m.count;
      if (role === 'mastered' && cur >= 0 && r[cur] > 0.9 && c[cur] >= H) return cur;
      if (role === 'frontier' && cur >= 0 && r[cur] >= 0.1 && r[cur] <= 0.9) return cur;
      if (role === 'unsolved' && cur >= 0 && r[cur] < 0.1) return cur;
      let best = -1, bs = -Infinity;
      for (let i = 0; i < world.N; i++) {
        let score = -Infinity;
        if (role === 'mastered' && r[i] > 0.9 && c[i] >= H) score = c[i];
        if (role === 'frontier' && r[i] >= 0.25 && r[i] <= 0.75) score = tr.probs[i];
        if (role === 'unsolved' && r[i] === 0 && c[i] > 0) score = c[i];
        if (score > bs) { bs = score; best = i; }
      }
      return best;
    }
    function setCell(o, i) {
      if (o.cell === i) return;
      o.cell = i; o.lastCount = i >= 0 ? m.count[i] : -1; o.anim = 0; o.dropped = null; o.hist = [];
    }
    // window contents, oldest -> newest: 1 success, 0 failure, -1 initial zero never written
    function windowOf(i) {
      const out = [], base = i * H, p = m.ptr[i], n = m.count[i];
      for (let j = 0; j < H; j++) {
        const slot = (p + j) % H;
        out.push(n >= H || j >= H - n ? m.buf[base + slot] : -1);
      }
      return out;
    }
    function styleDot(d, v, op) {
      d.setAttribute('fill', v === 1 ? 'var(--accent)' : 'var(--bg)');
      d.setAttribute('stroke', v === 1 ? 'var(--accent)' : v === 0 ? 'var(--fg-muted)' : 'var(--rule)');
      d.setAttribute('stroke-dasharray', v === -1 ? '2 2' : '');
      d.setAttribute('opacity', fmt(op, 2));
    }

    $('mon-grid').addEventListener('click', (e) => {
      const c = grid.cellAt(e);
      if (c >= 0 && world.goalIndexOfCell[c] >= 0) { rows[2].picked = true; setCell(rows[2], world.goalIndexOfCell[c]); }
    });
    $('mon-grid').style.cursor = 'pointer';
    $('mon-play').onclick = function () { playing = !playing; this.setAttribute('aria-pressed', playing); this.textContent = playing ? 'playing' : 'paused'; };
    $('mon-speed').oninput = function () { $('mon-speed-out').textContent = this.value + '×'; };

    const spark = $('mon-spark'), sbox = { l: 28, r: 18, t: 8, b: 14, w: 300, h: 70 };
    const SS = scales(0, 150, 0, 1, sbox);
    axes(spark, SS, sbox, [], [0, 1]);
    rows.forEach((o) => {
      o.line = el('polyline', { class: 'curve-accent', style: `stroke-width:1.5;stroke-dasharray:${DASH[o.r] || 'none'}` }, spark);
      o.tag = el('text', { 'font-size': 9.5, style: 'fill:var(--fg)' }, spark);
      o.tag.textContent = o.r + 1;
    });

    let fcount = 0;
    register($('fig-monitor'), (dt) => {
      if (playing) for (let i = 0, n = +$('mon-speed').value; i < n; i++) tr.tick(true);
      grid.fill((i) => succColor(m.rate[i]));
      grid.setDots(tr.probs);
      robots(tr.envs);
      $('mon-ep').textContent = 'episode ' + fmtInt(tr.episodes);
      const sampleHist = playing && ++fcount % 4 === 0;
      for (const o of rows) {
        const role = ROLE[o.r];
        if (!(o.r === 2 && o.picked)) setCell(o, choose(role, o.cell));
        const i = o.cell;
        const vis = i >= 0 ? 'visible' : 'hidden';
        o.mark.setAttribute('visibility', vis); o.badge.setAttribute('visibility', vis);
        if (i < 0) {
          o.label.textContent = `${o.r + 1} · ${role}: none yet`;
          o.sub.textContent = ''; o.pval.textContent = ''; o.bar.setAttribute('width', 0);
          o.dots.forEach((d) => d.setAttribute('opacity', 0));
          o.line.setAttribute('points', '');
          continue;
        }
        const gc = world.goals[i], gx = gc % W, gy = (gc / W) | 0;
        o.mark.setAttribute('x', gx); o.mark.setAttribute('y', gy);
        o.badge.setAttribute('x', gx + 0.07); o.badge.setAttribute('y', gy + 0.34);
        // a new outcome arrived: remember the one falling off, start the slide
        if (m.count[i] !== o.lastCount) {
          const w = windowOf(i);
          o.dropped = o.prevFirst !== undefined ? o.prevFirst : null;
          o.anim = m.count[i] - o.lastCount > 0 ? 1 : 0;
          o.lastCount = m.count[i];
          o.prevFirst = w[0];
        }
        o.anim = Math.max(0, o.anim - dt * 5);
        const w = windowOf(i);
        o.prevFirst = w[0];
        const shift = o.anim * STEP;
        // dot 0 = the outcome sliding out on the left; dots 1..H = the window
        styleDot(o.dots[0], o.dropped == null ? -1 : o.dropped, o.dropped == null ? 0 : o.anim);
        o.dots[0].setAttribute('cx', fmt(X0 - STEP + shift, 1));
        for (let j = 0; j < H; j++) {
          const d = o.dots[j + 1];
          d.setAttribute('cx', fmt(X0 + j * STEP + shift, 1));
          styleDot(d, w[j], j === H - 1 ? 1 - 0.7 * o.anim : 1);
        }
        const tag = o.r === 2 && o.picked ? `your pick (${cat(i)})` : role;
        o.label.textContent = `${o.r + 1} · ${tag} · cell (${gx}, ${gy})`;
        o.sub.textContent = `sampled ${fmt(tr.probs[i] * world.N, 1)}× as often as uniform · ${fmtInt(m.count[i])} outcomes so far`;
        o.pval.textContent = fmt(m.rate[i]);
        o.bar.setAttribute('width', fmt(BAR_W * m.rate[i], 1));
        if (sampleHist) { o.hist.push(m.rate[i]); if (o.hist.length > 150) o.hist.shift(); }
        o.line.setAttribute('points', o.hist.map((h, j) => fmt(SS.x(j), 1) + ',' + fmt(SS.y(h), 1)).join(' '));
        if (o.hist.length) { const j = o.hist.length - 1; o.tag.setAttribute('x', SS.x(j) + 3); o.tag.setAttribute('y', SS.y(o.hist[j]) + 3); }
      }
    });
    return tr;
  })();

  // ============================================================ 5 · kernel
  (function kernel() {
    if (!$('fig-kernel') || !mon) return;   // figure not on this page (e.g. held from the garage post)
    const plot = $('k-plot'), box = { l: 36, r: 10, t: 16, b: 24, w: 420, h: 250 };
    const S = scales(0, 1, 0, 1.05, box);
    const band = el('rect', { y: box.t, height: box.h - box.t - box.b, class: 'bandrect' }, plot);
    band.setAttribute('x', S.x(0.1)); band.setAttribute('width', S.x(0.9) - S.x(0.1));
    axes(plot, S, box, [0, 0.25, 0.5, 0.75, 1], [0, 0.5, 1], 'tracked success rate p̂', 'relative weight');
    const histG = el('g', {}, plot);
    const wLine = el('polyline', { class: 'curve-accent' }, plot);
    const pLine = el('polyline', { class: 'curve-prob' }, plot);
    const tMark = el('line', { y1: box.t, y2: box.h - box.b, stroke: 'var(--fg-faint)', 'stroke-dasharray': '3 3' }, plot);
    const rugG = el('g', {}, plot);
    const rug = world.goals.map(() => el('circle', { r: 2.6, class: 'probdot', opacity: 0.65 }, rugG));
    const NB = 20;
    const bars = Array.from({ length: NB }, (_, j) => el('rect', { x: S.x(j / NB) + 0.5, width: S.x(1 / NB) - S.x(0) - 1, fill: 'var(--fg-faint)', opacity: 0.25 }, histG));

    const grid = makeGrid($('k-grid'), world);
    grid.initDots();
    const probs = new Float64Array(world.N);
    const xs = Array.from({ length: 201 }, (_, i) => i / 200);

    const ids = ['t', 'kappa', 'T', 'eps'];
    function cfg() {
      return { target: +$('k-t').value, kappa: +$('k-kappa').value, T: +$('k-T').value, eps: Math.pow(10, +$('k-eps').value) };
    }
    function labels() {
      const c = cfg();
      $('k-t-out').textContent = fmt(c.target);
      $('k-kappa-out').textContent = fmt(c.kappa, 1);
      $('k-T-out').textContent = fmt(c.T);
      $('k-eps-out').textContent = c.eps.toExponential(0);
    }
    ids.forEach((id) => ($('k-' + id).oninput = () => { labels(); draw(); }));
    const PRE = { paper: E.PRESETS.paper, loco: E.PRESETS.loco, manip: E.PRESETS.manip, sharp: { target: 0.5, kappa: 20, T: 1, eps: 1e-8 } };
    document.querySelectorAll('[data-preset]').forEach((b) => (b.onclick = () => {
      const p = PRE[b.dataset.preset];
      $('k-t').value = p.target; $('k-kappa').value = p.kappa; $('k-T').value = p.T; $('k-eps').value = Math.log10(p.eps);
      labels(); draw();
    }));

    function draw() {
      const c = cfg();
      const w = xs.map((x) => E.betaWeight(x, c));
      const wmax = Math.max(...w);
      const pr = w.map((v) => Math.pow(v + c.eps, 1 / c.T));
      const pmax = Math.max(...pr);
      wLine.setAttribute('points', polyPts(xs, w.map((v) => v / wmax), S));
      pLine.setAttribute('points', polyPts(xs, pr.map((v) => v / pmax), S));
      tMark.setAttribute('x1', S.x(c.target)); tMark.setAttribute('x2', S.x(c.target));
      const rates = mon.monitor.rate;
      E.kernelProbs(rates, c, probs);
      const counts = new Array(NB).fill(0);
      let band = 0, mn = Infinity, mx = 0, ent = 0;
      for (let i = 0; i < world.N; i++) {
        const r = rates[i];
        const rel = Math.pow(E.betaWeight(r, c) + c.eps, 1 / c.T) / pmax;
        rug[i].setAttribute('cx', fmt(S.x(r), 1)); rug[i].setAttribute('cy', fmt(S.y(rel), 1));
        counts[Math.min(NB - 1, Math.floor(r * NB))]++;
        if (r >= 0.1 && r <= 0.9) band += probs[i];
        mn = Math.min(mn, probs[i]); mx = Math.max(mx, probs[i]);
        if (probs[i] > 0) ent -= probs[i] * Math.log(probs[i]);
      }
      const cmax = Math.max(...counts, 1);
      bars.forEach((b, j) => { const hgt = (counts[j] / cmax) * 0.35; b.setAttribute('y', S.y(hgt)); b.setAttribute('height', S.y(0) - S.y(hgt)); });
      grid.fill((i) => succColor(rates[i]));
      grid.setDots(probs);
      $('k-ess').textContent = `${fmt(Math.exp(ent), 0)} / ${world.N}`;
      $('k-band').textContent = Math.round(band * 100) + '%';
      $('k-floor').textContent = mx > 0 ? `1 : ${fmtInt(mx / mn)}` : '·';
      $('k-readout').textContent = `peak at p̂ = ${fmt(c.target)}`;
    }
    labels(); draw();
    let fc = 0;
    register($('fig-kernel'), () => { if (++fc % 6 === 0) draw(); });
  })();

  // ============================================================ 7 · race
  (function race() {
    if (!$('fig-race')) return;   // figure not on this page (e.g. held from the garage post)
    const BUDGET = 40000, EVAL_EVERY = 2000, N_ENV = 64;
    const gu = makeGrid($('race-u-grid'), world), gs = makeGrid($('race-s-grid'), world);
    gu.initDots(); gs.initDots();
    const ru = makeRobots(gu, N_ENV, { rings: false, r: 0.11 }), rs = makeRobots(gs, N_ENV, { rings: false, r: 0.11 });
    let U, Sg, evU, evS, curveU, curveS, playing = false;

    const cv = $('race-curve'), box = { l: 34, r: 10, t: 14, b: 24, w: 420, h: 200 };
    const S = scales(0, BUDGET, 0, 1, box);
    axes(cv, S, box, [0, 10000, 20000, 30000, 40000].map((v) => v), [0, 0.5, 1], 'episodes', 'mean success');
    // relabel x ticks as 0, 10k, ...
    cv.querySelectorAll('text').forEach((t) => { if (/^\d{5}$/.test(t.textContent)) t.textContent = t.textContent / 1000 + 'k'; });
    const lu = el('polyline', { class: 'curve-muted', style: 'stroke-dasharray:none;stroke:var(--fg-muted)' }, cv);
    const ls = el('polyline', { class: 'curve-accent' }, cv);
    const labU = el('text', { 'font-size': 11, style: 'fill:var(--fg-muted)' }, cv);
    const labS = el('text', { 'font-size': 11, style: 'fill:var(--accent)' }, cv);

    function evalMean(tr) { const ev = tr.evaluate(4, 4242); return [ev, ev.reduce((a, b) => a + b, 0) / world.N]; }
    function reset() {
      U = new E.Trainer({ mode: 'uniform', envs: N_ENV, seed: 5 });
      Sg = new E.Trainer({ mode: 'sgs', envs: N_ENV, seed: 5 });
      let m;
      [evU, m] = evalMean(U); curveU = [[0, m]];
      [evS, m] = evalMean(Sg); curveS = [[0, m]];
      paint(); drawCurves(); drawBars();
    }
    function paint() {
      gu.fill((i) => succColor(evU[i])); gs.fill((i) => succColor(evS[i]));
      gu.setDots(U.probs); gs.setDots(Sg.probs);
      ru(U.envs); rs(Sg.envs);
      $('race-u-stat').textContent = 'mean ' + fmt(curveU[curveU.length - 1][1]);
      $('race-s-stat').textContent = 'mean ' + fmt(curveS[curveS.length - 1][1]);
      $('race-ep').textContent = `${fmtInt(Math.min(U.episodes, BUDGET))} / ${fmtInt(BUDGET)} episodes`;
      $('race-sig-u').textContent = fmtInt(U.signal);
      $('race-sig-s').textContent = fmtInt(Sg.signal);
    }
    function drawCurves() {
      const f = (c) => c.map(([x, y]) => fmt(S.x(x), 1) + ',' + fmt(S.y(y), 1)).join(' ');
      lu.setAttribute('points', f(curveU)); ls.setAttribute('points', f(curveS));
      const [xu, yu] = curveU[curveU.length - 1], [xs, ys] = curveS[curveS.length - 1];
      labU.setAttribute('x', S.x(xu) + 4); labU.setAttribute('y', S.y(yu) + 12); labU.textContent = 'uniform';
      labS.setAttribute('x', S.x(xs) + 4); labS.setAttribute('y', S.y(ys) - 5); labS.textContent = 'SGS';
    }
    function drawBars() {
      const frac = (b) => { const s = b[0] + b[1] + b[2] || 1; return b.map((x) => x / s); };
      drawSpendBars($('race-bars'), [['uniform', frac(U.band)], ['SGS', frac(Sg.band)]], ['p̂ < 0.1', 'frontier', 'p̂ > 0.9']);
    }
    function step(tr, curve, which) {
      const nextEval = curve.length * EVAL_EVERY;
      tr.tick(true);
      if (tr.episodes >= nextEval) {
        const [ev, m] = evalMean(tr);
        curve.push([nextEval, m]);
        if (which === 'u') evU = ev; else evS = ev;
        return true;
      }
      return false;
    }
    reset();
    const btn = $('race-play');
    function setPlaying(v) { playing = v; btn.setAttribute('aria-pressed', v); btn.textContent = v ? 'pause' : 'play'; }
    btn.onclick = () => { if (U.episodes >= BUDGET && Sg.episodes >= BUDGET) reset(); setPlaying(!playing); };
    $('race-reset').onclick = () => { reset(); };
    $('race-speed').oninput = function () { $('race-speed-out').textContent = this.value + '×'; };
    let autostarted = false, fc = 0;
    const f = register($('fig-race'), () => {
      if (!autostarted) { autostarted = true; setPlaying(true); }
      if (!playing) return;
      let changed = false;
      for (let i = 0, n = +$('race-speed').value; i < n; i++) {
        if (U.episodes < BUDGET) changed = step(U, curveU, 'u') || changed;
        if (Sg.episodes < BUDGET) changed = step(Sg, curveS, 's') || changed;
      }
      paint();
      if (changed) drawCurves();
      if (++fc % 10 === 0) drawBars();
      if (U.episodes >= BUDGET && Sg.episodes >= BUDGET) { setPlaying(false); btn.textContent = 'replay'; drawCurves(); drawBars(); }
    });
  })();

  // ============================================================ 8 · scale
  (function scale() {
    if (!$('fig-scale')) return;   // figure not on this page (e.g. held from the garage post)
    const ENVS = [16, 32, 64, 128, 256, 512], TICKS = 3000, PER_FRAME = 10, MODES = ['uniform', 'sgs'];
    const dt = E.PHYS.dt, SIM_S = TICKS * dt;
    const gridEl = $('scale-grid');
    // header row
    gridEl.appendChild(document.createElement('div'));
    for (const n of ENVS) { const d = document.createElement('div'); d.className = 'hdr'; d.textContent = n + ' envs'; gridEl.appendChild(d); }
    const cells = {};
    for (const mode of MODES) {
      const lab = document.createElement('div'); lab.className = 'rowlab'; lab.textContent = mode === 'sgs' ? 'SGS' : 'uniform';
      gridEl.appendChild(lab);
      for (const n of ENVS) {
        const box = document.createElement('div');
        const svg = document.createElementNS(NS, 'svg'); svg.setAttribute('class', 'grid');
        box.appendChild(svg);
        const cap = document.createElement('div'); cap.className = 'cap'; box.appendChild(cap);
        gridEl.appendChild(box);
        cells[mode + n] = { grid: makeGrid(svg, world), cap };
      }
    }

    // charts (log2 x axis)
    function chart(svg, ymax, yt, ylab) {
      const box = { l: 38, r: 12, t: 16, b: 24, w: 360, h: 190 };
      const S = scales(4, 9, 0, ymax, box);
      axes(svg, S, box, [4, 5, 6, 7, 8, 9], yt, 'parallel envs', ylab);
      svg.querySelectorAll('text').forEach((t) => { if (/^[4-9]$/.test(t.textContent)) t.textContent = String(2 ** +t.textContent); });
      const mk = (cls) => ({ line: el('polyline', { class: cls }, svg), dots: ENVS.map(() => el('circle', { r: 3, visibility: 'hidden' }, svg)) });
      const u = mk('curve-muted'), g = mk('curve-accent');
      u.line.setAttribute('style', 'stroke-dasharray:none;stroke:var(--fg-muted)');
      u.dots.forEach((d) => d.setAttribute('fill', 'var(--fg-muted)'));
      g.dots.forEach((d) => d.setAttribute('fill', 'var(--accent)'));
      return {
        set(mode, vals) {   // vals: array aligned with ENVS, null = not yet
          const o = mode === 'sgs' ? g : u, pts = [];
          vals.forEach((v, j) => {
            if (v == null) { o.dots[j].setAttribute('visibility', 'hidden'); return; }
            const x = S.x(Math.log2(ENVS[j])), y = S.y(Math.min(ymax, v));
            o.dots[j].setAttribute('cx', x); o.dots[j].setAttribute('cy', y); o.dots[j].setAttribute('visibility', 'visible');
            pts.push(fmt(x, 1) + ',' + fmt(y, 1));
          });
          o.line.setAttribute('points', pts.join(' '));
        },
      };
    }
    const succ = chart($('scale-succ'), 1, [0, 0.5, 1], 'success');
    // headless sweep: SGS at 512 envs ≈ 55 frontier eps/s, uniform ≈ 20
    const rate = chart($('scale-rate'), 60, [0, 30, 60], 'eps / s');

    let jobs = [], ticks = 0, running = false;
    function start() {
      jobs = [];
      for (const mode of MODES) for (const n of ENVS) jobs.push({ mode, n, tr: new E.Trainer({ mode, envs: n, seed: 5 }), ev: null, c: cells[mode + n] });
      ticks = 0; running = true;
      succ.set('uniform', ENVS.map(() => null)); succ.set('sgs', ENVS.map(() => null));
      paint();
    }
    function frontierRate(j) { return ticks ? j.tr.band[1] / (ticks * dt) : 0; }
    function paint() {
      for (const j of jobs) {
        const src = j.ev || j.tr.monitor.rate;
        j.c.grid.fill((i) => succColor(src[i]));
        j.c.cap.textContent = j.ev
          ? `${fmtInt(j.tr.episodes)} eps · success ${fmt(j.ev.reduce((a, b) => a + b, 0) / world.N)}`
          : `${fmtInt(j.tr.episodes)} eps`;
      }
      for (const mode of MODES) rate.set(mode, jobs.filter((j) => j.mode === mode).map(frontierRate));
      $('scale-clock').textContent = `${fmt(ticks * dt, 1)} / ${fmt(SIM_S, 0)} s simulated`;
    }
    function finish() {
      running = false;
      for (const j of jobs) j.ev = j.tr.evaluate(4, 4242);
      for (const mode of MODES) succ.set(mode, jobs.filter((j) => j.mode === mode).map((j) => j.ev.reduce((a, b) => a + b, 0) / world.N));
      paint();
    }
    $('scale-run').onclick = start;
    let started = false, fc = 0;
    register($('fig-scale'), () => {
      if (!started) { started = true; start(); }
      if (!running) return;
      for (let k = 0; k < PER_FRAME && ticks < TICKS; k++) { for (const j of jobs) j.tr.tick(false); ticks++; }
      if (ticks >= TICKS) finish();
      else if (++fc % 3 === 0) paint();
    });
  })();

  // ------------------------------------------------------------ theme toggle
  // Any theme change (our standalone button, or the portfolio's own toggle) flips
  // data-theme on <html>; repaint the JS-colored figures when it does.
  new MutationObserver(() => themeHooks.forEach((h) => h()))
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  const tbtn = $('theme-toggle');
  if (tbtn) {
    const syncBtn = () => (tbtn.textContent = isDark() ? 'light' : 'dark');
    syncBtn();
    tbtn.onclick = () => {
      const d = !isDark();
      if (d) document.documentElement.setAttribute('data-theme', 'dark');
      else document.documentElement.removeAttribute('data-theme');
      try { localStorage.setItem('theme', d ? 'dark' : 'light'); } catch (e) {}
      syncBtn();
    };
  }

  // debug: ?warm=N runs every figure's frame N times up front (review screenshots)
  const warm = +new URLSearchParams(location.search).get('warm') || 0;
  for (let i = 0; i < warm; i++) for (const f of figs) f.frame(1 / 60, performance.now());
  // debug: ?focus=free|obs|start|shade|dot|robot pins a hero key spotlight (review screenshots)
  const pin = new URLSearchParams(location.search).get('focus');
  if (pin) $('hero-grid').dataset.focus = pin;

  requestAnimationFrame(loop);
})();
