/* sgs-engine.js: gridworld + point-mass dynamics + toy learner + SGS sampler.
 *
 * Shared by the browser page and headless node tuning (UMD). Nothing here
 * touches the DOM.
 *
 * SGS kernel is the exact production expression (uwrl/docs/DESIGN.md §3.2):
 *   a = 1 + kappa*t,  b = 1 + kappa*(1-t)
 *   w = ((p+eps)^(a-1) * (1-p+eps)^(b-1)).clamp_min(eps)
 *   probs = softmax(log(w+eps) / T)
 *
 * The learner is NOT PPO. It is a stand-in with one honest property of
 * sparse-reward policy gradient: an episode teaches in proportion to its
 * advantage (outcome - baseline), so configurations at p=0 (never succeed)
 * or p=1 (success is expected) carry ~no signal. Expected signal ~ p(1-p).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SGSEngine = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ---------------------------------------------------------------- rng
  function mulberry32(seed) {
    let a = seed >>> 0;
    const f = function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    f.normal = function () {
      let u = 0, v = 0;
      while (u === 0) u = f();
      v = f();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    };
    return f;
  }

  // ---------------------------------------------------------------- world
  // '#' wall, 'H' home (start), '.' free. Every free non-home cell is a goal,
  // i.e. one task configuration tau_i = (s0 = home, g = cell i).
  const DEFAULT_MAP = [
    '...............',
    '...............',
    '....#.....#....',
    '....#.....#....',
    '....#..####....',
    '.H..#.....#....',
    '....#.....#....',
    '.......####....',
    '....#..........',
    '....#..........',
    '...............',
  ];

  function makeWorld(map) {
    map = map || DEFAULT_MAP;
    const rows = map.length, cols = map[0].length;
    const blocked = new Uint8Array(rows * cols);
    let home = -1;
    const goals = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const ch = map[r][c], id = r * cols + c;
        if (ch === '#') blocked[id] = 1;
        else if (ch === 'H') home = id;
        else goals.push(id);
      }
    }
    const w = { rows, cols, blocked, home, goals, N: goals.length };
    w.goalIndexOfCell = new Int32Array(rows * cols).fill(-1);
    goals.forEach((cell, i) => (w.goalIndexOfCell[cell] = i));
    // One BFS distance field per goal (8-connected, no corner cutting).
    w.dist = goals.map((g) => bfs(w, g));
    w.pathLen = goals.map((g, i) => w.dist[i][home]);
    return w;
  }

  const NB = [[1, 0, 1], [-1, 0, 1], [0, 1, 1], [0, -1, 1],
              [1, 1, Math.SQRT2], [1, -1, Math.SQRT2], [-1, 1, Math.SQRT2], [-1, -1, Math.SQRT2]];

  function passable(w, c, r) {
    return c >= 0 && r >= 0 && c < w.cols && r < w.rows && !w.blocked[r * w.cols + c];
  }

  function bfs(w, goal) {
    // Dijkstra on a tiny grid; a sorted array is plenty.
    const d = new Float32Array(w.rows * w.cols).fill(Infinity);
    d[goal] = 0;
    const open = [goal];
    while (open.length) {
      let bi = 0;
      for (let i = 1; i < open.length; i++) if (d[open[i]] < d[open[bi]]) bi = i;
      const u = open.splice(bi, 1)[0];
      const uc = u % w.cols, ur = (u / w.cols) | 0;
      for (const [dc, dr, cost] of NB) {
        const vc = uc + dc, vr = ur + dr;
        if (!passable(w, vc, vr)) continue;
        if (dc && dr && (!passable(w, uc + dc, ur) || !passable(w, uc, ur + dr))) continue;
        const v = vr * w.cols + vc, nd = d[u] + cost;
        if (nd < d[v]) { if (d[v] === Infinity) open.push(v); d[v] = nd; }
      }
    }
    return d;
  }

  // Next waypoint (cell id) toward goal i from cell u.
  function nextCell(w, i, u) {
    const d = w.dist[i];
    const uc = u % w.cols, ur = (u / w.cols) | 0;
    let best = u, bd = d[u];
    for (const [dc, dr] of NB) {
      const vc = uc + dc, vr = ur + dr;
      if (!passable(w, vc, vr)) continue;
      if (dc && dr && (!passable(w, uc + dc, ur) || !passable(w, uc, ur + dr))) continue;
      const v = vr * w.cols + vc;
      if (d[v] < bd) { bd = d[v]; best = v; }
    }
    return best;
  }

  // ---------------------------------------------------------------- dynamics
  // Double integrator with linear drag, force limit and wall bounces.
  // Units: 1 cell = 1 length unit, seconds.
  const PHYS = {
    dt: 0.05,
    amax: 6.0,      // max |acceleration|
    drag: 0.8,      // linear drag coefficient (1/s)
    radius: 0.18,
    horizon: 8.0,   // seconds per episode
    goalTol: 0.32,  // success radius around goal center
    restitution: 0.35,
    Kmin: 0.5,      // gain used off-grid (never reached in practice)
    noise: 3.0,     // OU exploration noise scale (acceleration units)
  };

  function cellOf(w, x, y) {
    const c = Math.floor(x), r = Math.floor(y);
    if (c < 0 || r < 0 || c >= w.cols || r >= w.rows) return -1;
    return r * w.cols + c;
  }

  function overlapsWall(w, x, y, rad) {
    if (x - rad < 0 || y - rad < 0 || x + rad > w.cols || y + rad > w.rows) return true;
    const c0 = Math.floor(x - rad), c1 = Math.floor(x + rad);
    const r0 = Math.floor(y - rad), r1 = Math.floor(y + rad);
    for (let r = r0; r <= r1; r++) {
      for (let c = c0; c <= c1; c++) {
        if (!w.blocked[r * w.cols + c]) continue;
        const nx = Math.max(c, Math.min(x, c + 1)), ny = Math.max(r, Math.min(y, r + 1));
        if ((x - nx) ** 2 + (y - ny) ** 2 < rad * rad) return true;
      }
    }
    return false;
  }

  function integrate(w, s, ax, ay, P) {
    P = P || PHYS;
    const am = Math.hypot(ax, ay);
    if (am > P.amax) { ax *= P.amax / am; ay *= P.amax / am; }
    s.ax = ax; s.ay = ay;
    s.vx += (ax - P.drag * s.vx) * P.dt;
    s.vy += (ay - P.drag * s.vy) * P.dt;
    const nx = s.x + s.vx * P.dt;
    if (overlapsWall(w, nx, s.y, P.radius)) { s.vx *= -P.restitution; s.bumps++; } else s.x = nx;
    const ny = s.y + s.vy * P.dt;
    if (overlapsWall(w, s.x, ny, P.radius)) { s.vy *= -P.restitution; s.bumps++; } else s.y = ny;
  }

  // ---------------------------------------------------------------- policy
  // Policy = gain-scheduled PD controller + exploration noise:
  //   a = Kp (x_wp - x) - Kd v + sigma n,    Kd = 2 sqrt(Kp)  (critically damped)
  // x_wp is the next cell center on the shortest path to the goal (the goal
  // center once inside the goal cell). Kp is scheduled by region: K[c] is the
  // gain used while the robot is in cell c. n is an Ornstein-Uhlenbeck process
  // (smooth exploration noise) with fixed scale sigma. Low gain: weak, slow
  // tracking that the noise swamps, so far goals time out. High gain: stiff,
  // fast tracking (the force cap still applies). Training tunes K region by
  // region; difficulty emerges from path length, walls, and momentum.
  function policyAccel(w, K, goalIdx, s, rng, P) {
    P = P || PHYS;
    const u = cellOf(w, s.x, s.y);
    const g = w.goals[goalIdx];
    let tx, ty;
    if (u === g) { tx = (g % w.cols) + 0.5; ty = ((g / w.cols) | 0) + 0.5; }
    else {
      const v = nextCell(w, goalIdx, u);
      tx = (v % w.cols) + 0.5; ty = ((v / w.cols) | 0) + 0.5;
    }
    const Kp = u >= 0 ? K[u] : P.Kmin, Kd = 2 * Math.sqrt(Kp);
    // OU exploration noise
    const th = 1.2, sig = P.noise;
    s.nx += -th * s.nx * P.dt + sig * Math.sqrt(P.dt) * rng.normal();
    s.ny += -th * s.ny * P.dt + sig * Math.sqrt(P.dt) * rng.normal();
    return [Kp * (tx - s.x) - Kd * s.vx + s.nx, Kp * (ty - s.y) - Kd * s.vy + s.ny];
  }

  function newState(w, rng) {
    const h = w.home;
    return {
      x: (h % w.cols) + 0.5 + (rng() - 0.5) * 0.2,
      y: ((h / w.cols) | 0) + 0.5 + (rng() - 0.5) * 0.2,
      vx: 0, vy: 0, ax: 0, ay: 0, nx: 0, ny: 0, t: 0, bumps: 0,
    };
  }

  // ---------------------------------------------------------------- SGS
  const PRESETS = {
    paper: { target: 0.5, kappa: 1.0, T: 2.0, eps: 1e-8, H: 100, label: 'paper (§3.2)' },
    loco:  { target: 0.66, kappa: 5.0, T: 2.0, eps: 1e-8, H: 100, label: 'LOCO_POSITION' },
    manip: { target: 0.5, kappa: 1.0, T: 2.0, eps: 1e-4, H: 100, label: 'FACTORY_V2' },
  };

  function betaWeight(p, cfg) {
    const a = 1 + cfg.kappa * cfg.target, b = 1 + cfg.kappa * (1 - cfg.target);
    const w = Math.pow(p + cfg.eps, a - 1) * Math.pow(1 - p + cfg.eps, b - 1);
    return Math.max(w, cfg.eps);
  }

  function kernelProbs(rates, cfg, out) {
    const n = rates.length;
    out = out || new Float64Array(n);
    let mx = -Infinity;
    for (let i = 0; i < n; i++) {
      out[i] = Math.log(betaWeight(rates[i], cfg) + cfg.eps) / cfg.T;
      if (out[i] > mx) mx = out[i];
    }
    let z = 0;
    for (let i = 0; i < n; i++) { out[i] = Math.exp(out[i] - mx); z += out[i]; }
    for (let i = 0; i < n; i++) out[i] /= z;
    return out;
  }

  // SuccessMonitor: per-configuration ring buffer of the last H outcomes.
  // Loco semantics: buffer starts full of zeros (init_rate = 0), so an
  // unvisited configuration reads p = 0 until it is sampled.
  class Monitor {
    constructor(N, H) {
      this.N = N; this.H = H;
      this.buf = new Uint8Array(N * H);
      this.ptr = new Int32Array(N);
      this.count = new Int32Array(N);   // total outcomes ever recorded
      this.sum = new Int32Array(N);
      this.rate = new Float64Array(N);
    }
    update(i, o) {
      const j = i * this.H + this.ptr[i];
      this.sum[i] += o - this.buf[j];
      this.buf[j] = o;
      this.ptr[i] = (this.ptr[i] + 1) % this.H;
      this.count[i]++;
      this.rate[i] = this.sum[i] / this.H;
    }
  }

  function sampleIndex(probs, rng) {
    let u = rng(), acc = 0;
    for (let i = 0; i < probs.length; i++) { acc += probs[i]; if (u < acc) return i; }
    return probs.length - 1;
  }

  // ---------------------------------------------------------------- trainer
  const LEARN = {
    K0: 1.5,         // initial PD gain Kp in every region
    alpha: 0.001,    // step size of the advantage-weighted update
    spread: 0.35,    // fraction shared with 4-neighbours (generalization)
    Kmax: 25,        // gain ceiling the update approaches
    beta: 0.1,       // critic EMA rate for the per-configuration baseline V_i
  };

  class Trainer {
    constructor(opts) {
      opts = opts || {};
      this.world = opts.world || makeWorld();
      this.mode = opts.mode || 'sgs';
      this.cfg = Object.assign({}, PRESETS.paper, { H: 16 }, opts.cfg || {});
      this.learn = Object.assign({}, LEARN, opts.learn || {});
      this.P = Object.assign({}, PHYS, opts.phys || {});
      this.E = opts.envs || 64;
      this.rng = mulberry32(opts.seed || 1);
      const w = this.world;
      this.K = new Float64Array(w.rows * w.cols).fill(this.learn.K0);   // Kp per region
      for (let c = 0; c < this.K.length; c++) if (w.blocked[c]) this.K[c] = 0;
      this.monitor = new Monitor(w.N, this.cfg.H);
      this.V = new Float64Array(w.N);   // learner's critic: EMA of outcomes
      this.probs = new Float64Array(w.N);
      this.sampledCount = new Int32Array(w.N);
      this.refreshProbs();
      this.envs = [];
      for (let e = 0; e < this.E; e++) this.envs.push(this.resetEnv({}));
      this.episodes = 0; this.successes = 0; this.steps = 0;
      this.signal = 0;          // accumulated |advantage| actually learned from
      this.band = [0, 0, 0];    // episodes sampled at rate <.1, in band, >.9
      this.onEpisode = null;    // hook(env, outcome, goalIdx)
    }

    refreshProbs() {
      if (this.mode === 'uniform') this.probs.fill(1 / this.world.N);
      else kernelProbs(this.monitor.rate, this.cfg, this.probs);
    }

    resetEnv(env) {
      const g = sampleIndex(this.probs, this.rng);
      this.sampledCount[g]++;
      const r = this.monitor.rate[g];
      if (this.band) this.band[r < 0.1 ? 0 : r > 0.9 ? 2 : 1]++;
      env.goal = g;
      env.s = newState(this.world, this.rng);
      env.visited = new Set();
      env.trail = env.trail || [];
      env.trail.length = 0;
      return env;
    }

    stepEnv(env) {
      const w = this.world, P = this.P, s = env.s;
      const [ax, ay] = policyAccel(w, this.K, env.goal, s, this.rng, P);
      integrate(w, s, ax, ay, P);
      s.t += P.dt;
      const u = cellOf(w, s.x, s.y);
      if (u >= 0) env.visited.add(u);
      const g = w.goals[env.goal];
      const gx = (g % w.cols) + 0.5, gy = ((g / w.cols) | 0) + 0.5;
      if (Math.hypot(s.x - gx, s.y - gy) < P.goalTol) return 1;
      if (s.t >= P.horizon) return 0;
      return -1;
    }

    endEpisode(env, o) {
      const i = env.goal;
      const baseline = this.V[i];
      this.V[i] += this.learn.beta * (o - this.V[i]);
      this.monitor.update(i, o);
      this.episodes++; this.successes += o;
      // Advantage-weighted update: only successes raise the gains, scaled
      // by how surprising they were (1 - baseline).
      const adv = o - baseline;
      if (o === 1 && adv > 0) {
        this.signal += adv;
        const L = this.learn, w = this.world, K = this.K;
        for (const c of env.visited) {
          K[c] += L.alpha * adv * (L.Kmax - K[c]);
          const cc = c % w.cols, cr = (c / w.cols) | 0;
          for (const [dc, dr] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
            if (!passable(w, cc + dc, cr + dr)) continue;
            const n = (cr + dr) * w.cols + cc + dc;
            K[n] += L.spread * L.alpha * adv * (L.Kmax - K[n]);
          }
        }
      }
      if (this.onEpisode) this.onEpisode(env, o, i);
      this.refreshProbs();
      this.resetEnv(env);
    }

    // Advance every env by one physics step.
    tick(recordTrail) {
      for (const env of this.envs) {
        const o = this.stepEnv(env);
        if (recordTrail) {
          env.trail.push(env.s.x, env.s.y);
          if (env.trail.length > 120) env.trail.splice(0, 2);
        }
        if (o >= 0) this.endEpisode(env, o);
      }
      this.steps += this.E;
    }

    // Ground-truth success per configuration: M fresh rollouts each, no
    // learning, no SGS (mirrors "eval bypasses SGS").
    evaluate(M, seed) {
      M = M || 6;
      const w = this.world, rng = mulberry32(seed || 12345);
      const out = new Float64Array(w.N);
      for (let i = 0; i < w.N; i++) {
        let succ = 0;
        for (let m = 0; m < M; m++) {
          const s = newState(w, rng);
          const g = w.goals[i];
          const gx = (g % w.cols) + 0.5, gy = ((g / w.cols) | 0) + 0.5;
          while (s.t < this.P.horizon) {
            const [ax, ay] = policyAccel(w, this.K, i, s, rng, this.P);
            integrate(w, s, ax, ay, this.P);
            s.t += this.P.dt;
            if (Math.hypot(s.x - gx, s.y - gy) < this.P.goalTol) { succ++; break; }
          }
        }
        out[i] = succ / M;
      }
      return out;
    }
  }

  // One standalone rollout (used by the single-robot figure).
  function rollout(w, K, goalIdx, rng, P) {
    P = P || PHYS;
    const s = newState(w, rng);
    const g = w.goals[goalIdx];
    const gx = (g % w.cols) + 0.5, gy = ((g / w.cols) | 0) + 0.5;
    const pts = [s.x, s.y];
    let ok = 0;
    while (s.t < P.horizon) {
      const [ax, ay] = policyAccel(w, K, goalIdx, s, rng, P);
      integrate(w, s, ax, ay, P);
      s.t += P.dt;
      pts.push(s.x, s.y);
      if (Math.hypot(s.x - gx, s.y - gy) < P.goalTol) { ok = 1; break; }
    }
    return { pts, ok, t: s.t };
  }

  return {
    mulberry32, makeWorld, DEFAULT_MAP, PHYS, LEARN, PRESETS,
    betaWeight, kernelProbs, Monitor, sampleIndex, Trainer,
    policyAccel, integrate, newState, cellOf, nextCell, rollout,
  };
});
