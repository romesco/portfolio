---
title: Success Guided Sampling
description: SGS picks each episode's initial condition from the frontier of capability of the robot's policy, the edge of what it can already do, and follows that frontier outward as the policy improves.
authors:
  - Rosario Scalise
head: |
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" crossorigin="anonymous">
  <link rel="stylesheet" href="./garage-assets/success-guided-sampling/viz.css?v=2f325e1a">
scripts: |
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" crossorigin="anonymous"
    onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});"></script>
  <script src="./garage-assets/success-guided-sampling/sgs-engine.js?v=1b772d6e"></script>
  <script src="./garage-assets/success-guided-sampling/viz.js?v=20b7ef00"></script>
---

# Success Guided Sampling

<p class="lede">SGS picks each episode&#39;s initial condition from the <em>frontier of capability</em> of the robot&#39;s policy, the edge of what it can already do, and follows that frontier outward as the policy improves.</p>

```{=web}
<!-- shared arrowheads -->
<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <marker id="arrow-accent" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" style="fill: var(--accent)"/></marker>
    <marker id="arrow-prob" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" style="fill: var(--prob)"/></marker>
    <marker id="arrow-muted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0,1 L9,5 L0,9" style="fill: none; stroke: var(--fg-faint); stroke-width: 1.5"/></marker>
  </defs>
</svg>
<figure class="fig" id="fig-hero">
  <div class="fig-row hero">
    <div>
      <div class="panel-title"><span>Success Guided Sampling for Planar Point-Mass Control</span><span id="hero-ep">episode 0</span></div>
      <svg class="grid" id="hero-grid"></svg>
    </div>
    <div>
      <div class="panel-title"><span>goals by success rate · <span style="color:var(--prob)">sampler, κ = 10</span></span><span id="inlay-mass"></span></div>
      <svg class="plot" id="hero-inlay" viewBox="0 0 300 104"></svg>
      <div class="inlay-cap">Bars: how many goals sit at each $\hat p$ (hover a bar to find them on the map). Curve: the Beta sampler&#39;s relative probability for a goal at that $\hat p$.</div>
      <div class="panel-title"><span>key</span><span style="color:var(--fg-faint)">hover for details</span></div>
      <div class="key">
        <div class="key-row" tabindex="0" data-key="free">
          <svg viewBox="0 0 1 1"><rect width="1" height="1" class="cellbg" id="key-free"/></svg>
          <span class="term">free space $\mathcal{C}_\text{free}$</span>
          <div class="key-detail" role="tooltip">The robot can move anywhere in these squares. Each free square is also one goal $g_i$, so it stands for one task configuration $\tau_i = (s_0, g_i)$; there are $N=145$.</div>
        </div>
        <div class="key-row" tabindex="0" data-key="obs">
          <svg viewBox="0 0 1 1"><rect x=".03" y=".03" width=".94" height=".94" rx=".08" class="wall"/></svg>
          <span class="term">obstacles $\mathcal{C}_\text{obs}$</span>
          <div class="key-detail" role="tooltip">$\mathcal{C}_\text{obs} = \mathcal{C}\setminus\mathcal{C}_\text{free}$: walls. The robot bounces off them, and they are never goals.</div>
        </div>
        <div class="key-row" tabindex="0" data-key="start">
          <svg viewBox="0 0 1 1"><rect width="1" height="1" class="cellbg" id="key-home"/><rect x=".12" y=".12" width=".76" height=".76" rx=".12" class="home-mark"/><text x=".5" y=".53" class="home-text">s₀</text></svg>
          <span class="term">start state $s_0$</span>
          <div class="key-detail" role="tooltip">Every episode begins here, at rest. It is the same for all $N$ configurations; only the goal changes.</div>
        </div>
        <div class="key-row" tabindex="0" data-key="shade">
          <svg viewBox="0 0 1 1" id="key-ramp"></svg>
          <span class="term">shade: success rate $\hat p_i$</span>
          <div class="key-detail" role="tooltip">From pale (0, never reached) to deep blue (1, always reached). Estimated online from each goal&#39;s recent outcomes (§4).</div>
        </div>
        <div class="key-row" tabindex="0" data-key="dot">
          <svg viewBox="0 0 1 1"><rect width="1" height="1" class="cellbg" id="key-dot"/><circle cx=".5" cy=".5" r=".14" class="probdot"/></svg>
          <span class="term">dot area: sampling probability $P(i)$</span>
          <div class="key-detail" role="tooltip">How likely the next episode is to use goal $g_i$. This dot is the uniform size ($1/N$); a dot twice as wide is 4× as likely. Goals not yet reached sit below uniform, so their dots are smaller than this one.</div>
        </div>
        <div class="key-row" tabindex="0" data-key="robot">
          <svg viewBox="0 0 1 1"><polyline points=".08,.9 .25,.62 .45,.55 .6,.4" class="trail" style="opacity:.5;stroke-width:.06"/><circle cx=".62" cy=".38" r=".14" class="robot"/></svg>
          <span class="term">robot running policy $\pi$</span>
          <div class="key-detail" role="tooltip">48 parallel copies of the point mass (§1), all acting under the same policy $\pi$; only their sampled goals differ. The line behind each is its last ~3 s of motion.</div>
        </div>
      </div>
      <div class="controls">
        <button class="btn" id="hero-restart">reset</button>
        <button class="btn" data-hero-speed="1" aria-pressed="true">1×</button>
        <button class="btn" data-hero-speed="10" aria-pressed="false">10×</button>
        <button class="btn" data-hero-speed="100" aria-pressed="false">100×</button>
      </div>
    </div>
  </div>
  <figcaption class="wide"><strong>Figure 0.</strong> SGS training live: 48 parallel robots, all running the same policy $\pi$.
The blue basin around $s_0$ holds the goals the policy can already reach. Its edge is the
<strong>frontier of capability</strong>, where the sampling mass is focused. As the policy improves, the basin grows and the
frontier moves outward, with the sampling mass following it. The figure opens 2,500 episodes into training, after the cold start. Like every figure on this page, the sampler uses $\kappa = 10$, sharper than the paper&#39;s default of $1$ (§5).</figcaption>
</figure>
```

## 1 · Robot Dynamics and Task

Our robot is a point mass. It outputs a force, capped at a maximum. The force affects the velocity and energy dissapates due to environmental friction (modeled as drag). Forces are reflected when colliding with walls. It cannot teleport between cells and therefore has to
speed up, turn, and stop when dealing with corner geometry.

What we learn is its **policy** $\pi(a \mid s, g)$, which is a controller that maps the
current state $s$ and the goal $g$ to a force $a$. The robot's dynamics never change during training, but the policy
does. 

The task is to *reach the cell within 8 seconds*. The reward is sparse and the policy gets credit only when the
robot arrives.

In this toy, the policy is a **gain-scheduled PD controller** with exploration noise:

$$a = K_p\,(x_{\text{wp}} - x) - K_d\,v + \sigma n, \qquad K_d = 2\sqrt{K_p},$$

where $x_{\text{wp}}$ is the next waypoint on the shortest path to the goal and $K_d$ keeps the loop critically
damped. The proportional gain $K_p$ is scheduled by region: each grid cell has its own, and training tunes them.
The last term is exploration noise: $n$ is a smooth random signal (correlated over time) and $\sigma$ sets its
size. Read as an RL policy, this is a **Gaussian policy**: the PD law is the mean action and $\sigma$ controls how
stochastic it is.

Figure 1 lets you try both knobs; here one setting applies to every cell. The **gain** slider sets $K_p$: a low
gain tracks the path weakly and slowly, so the noise wins and far goals time out, while a high gain tracks it
stiffly and fast. The **noise** slider sets $\sigma$: at 0 the policy is deterministic, and larger values make
it wander more (training uses $\sigma = 3$). Switch to **8 rollouts** to run eight robots with the same gain
and noise level side by side and see how widely their outcomes spread. Click any cell to set a goal.

```{=web}
<figure class="fig" id="fig-robot">
  <div class="fig-row two">
    <div>
      <div class="panel-title"><span>click a cell to set the goal</span><span id="robot-status">·</span></div>
      <svg class="grid" id="robot-grid"></svg>
    </div>
    <div>
      <div class="panel-title"><span>state</span></div>
      <svg class="plot" id="robot-speed" viewBox="0 0 300 120"></svg>
      <div class="stats">
        <div class="stat"><b id="robot-t">0.0 s</b>time / 8.0 s</div>
        <div class="stat"><b id="robot-v">0.00</b>speed (cells/s)</div>
        <div class="stat"><b id="robot-rec">0 / 0</b>reached / tried</div>
      </div>
      <div class="controls">
        <label><span>gain K<sub>p</sub></span> <input type="range" id="robot-k" min="0.5" max="25" step="0.5" value="6"><output id="robot-k-out">6.0</output></label><span id="robot-kd"></span>
      </div>
      <div class="controls">
        <label><span>noise σ</span> <input type="range" id="robot-sigma" min="0" max="8" step="0.5" value="3"><output id="robot-sigma-out" style="min-width:8em">3.0</output></label>
      </div>
      <div class="controls">
        <button class="btn" data-robot-n="1" aria-pressed="true">1 rollout</button>
        <button class="btn" data-robot-n="8" aria-pressed="false">8 rollouts</button>
      </div>
      <div class="legend">
        <span><i style="background:var(--prob)"></i>force (action)</span>
        <span><i style="background:var(--accent)"></i>velocity</span>
        <span><i style="background:var(--accent);opacity:.6"></i>shortest path</span>
      </div>
    </div>
  </div>
  <figcaption><strong>Figure 1.</strong> Double-integrator dynamics: $\dot v = a - c\,v$, with $\|a\| \le a_{\max}$ and inelastic bounces off walls.
The speed trace shows the robot accelerating, braking at corners, and settling near the goal; with 8 rollouts,
the first robot&#39;s trace is bold and the other samples are faint.</figcaption>
</figure>
```

## 2 · A fixed set of task configurations

Before training starts, SGS fixes a discrete set of $N$ task configurations $\tau_i = (s_0, g, e)_i$ and
draws every episode's initial condition from that set. Here every free cell is a goal and every episode starts at $s_0$,
so $N = $ <span id="n-configs">145</span> and the task space *is* the map.

Some configurations are easy and some are hard. For example: distance matters as well as walls, because the
robot has to brake, turn, and re-accelerate around them. Hover a cell to see its shortest path and a dozen
rollouts from the *untrained* policy.

```{=web}
<figure class="fig" id="fig-tasks">
  <div class="fig-row two">
    <div>
      <div class="panel-title"><span>shade: shortest-path length from s₀</span><span id="tasks-readout">hover a cell</span></div>
      <svg class="grid" id="tasks-grid"></svg>
    </div>
    <div>
      <div class="panel-title"><span>untrained success rate vs path length</span></div>
      <svg class="plot" id="tasks-scatter" viewBox="0 0 300 200"></svg>
      <figcaption>Each dot is one configuration: its success rate over 8 rollouts at initialization. Difficulty comes
out of the dynamics. We have no prior labels for how hard or easy a task is.</figcaption>
    </div>
  </div>
  <div class="legend"><span><i style="background:var(--ok)"></i>rollout reached goal</span><span><i style="background:var(--fail)"></i>timed out</span></div>
</figure>
```

## 3 · Where does learning occur?

With a sparse reward, an episode teaches in proportion to how *surprising* its outcome is. A configuration
the robot always solves has zero advantage: success was expected. One it never solves returns no reward to learn from.
For a configuration with success rate $p$, the expected signal per episode scales like $p(1-p)$.

Below is a policy partway through training. Most cells are either mastered or out of reach. Only the gold
band, the *frontier of capability*, is resulting in *useful rollout epsiodes*. Uniform sampling spends episodes in proportion to area, so
most of its budget goes to the other two groups.

In control terms, the mastered cells are the policy's *region of attraction*: the initial conditions
from which the closed loop reaches its goal. The frontier of capability is that region's edge. Classical regions of attraction
are deterministic and have a single fixed goal. Ours is probabilistic, time-limited, and goal-conditioned, so
think of the cell shade as a reach-probability field and the frontier as its middle contours.

```{=web}
<figure class="fig" id="fig-signal">
  <div class="fig-row two">
    <div>
      <div class="panel-title"><span>a policy after <span id="signal-eps">6000</span> uniform episodes</span></div>
      <svg class="grid" id="signal-grid"></svg>
      <div class="legend"><span><i style="background:var(--fg-faint);opacity:.35"></i>too hard (p &lt; 0.1)</span><span><i style="background:var(--band)"></i>frontier (edge of the region of attraction)</span><span><i style="background:var(--accent);opacity:.35"></i>mastered (p &gt; 0.9)</span></div>
    </div>
    <div>
      <div class="panel-title"><span>signal per episode ∝ p(1−p)</span></div>
      <svg class="plot" id="signal-curve" viewBox="0 0 300 170"></svg>
      <div class="panel-title" style="margin-top:.9rem"><span>where each sampler spends its episodes</span></div>
      <svg class="plot" id="signal-bars" viewBox="0 0 300 74"></svg>
    </div>
  </div>
  <figcaption><strong>Figure 3.</strong> Success rates here are ground truth: 8 fresh rollouts per cell, no learning. The bars
show where each sampler actually spends its next 3,000 episodes if it takes over from this snapshot: same policy
(learning paused, so these success rates stay true), same starting estimates, each episode binned by its cell&#39;s
true success rate. SGS chooses using its own lagging estimates $\hat p$, so a cell that has just been mastered
still draws some episodes until its window catches up.</figcaption>
</figure>
```

## 4 · Tracking success with a sliding window

SGS does not know the true success rates. It estimates them online, almost for free: each configuration keeps a
circular buffer of its last $H$ Boolean outcomes, and $\hat p_i$ is the buffer's mean. Unvisited configurations
read $\hat p_i = 0$ (the locomotion convention). The strips follow three cells live: one mastered, one on the
frontier, and one the policy cannot solve yet. Click the map to swap in a cell of your own.

```{=web}
<figure class="fig" id="fig-monitor">
  <div class="fig-row two">
    <div>
      <div class="panel-title"><span>live · 24 robots · SGS · click a cell</span><span id="mon-ep">episode 0</span></div>
      <svg class="grid" id="mon-grid"></svg>
    </div>
    <div>
      <div class="panel-title"><span>last $H = 16$ outcomes per cell</span></div>
      <svg class="plot" id="mon-strips" viewBox="0 0 360 214"></svg>
      <div class="panel-title" style="margin-top:.4rem"><span>p̂ over time for the three cells</span></div>
      <svg class="plot" id="mon-spark" viewBox="0 0 300 70"></svg>
      <div class="controls">
        <button class="btn" id="mon-play" aria-pressed="true">playing</button>
        <label>speed <input type="range" id="mon-speed" min="1" max="12" step="1" value="2"><output id="mon-speed-out">2×</output></label>
      </div>
    </div>
  </div>
  <figcaption><strong>Figure 4.</strong> Each strip is one cell&#39;s window of its last $H$ outcomes, oldest on the left. When an episode
for that cell ends, the new outcome slides in on the right and the oldest drops off; $\hat p$ is the filled
fraction. A filled dot is a success, a hollow dot a failure, and a dashed dot one of the initial zeros of a cell
that has not been tried $H$ times yet. Notice how often each strip moves: SGS tries the frontier cell far more
often than the other two. Production stores the window as a ring buffer, overwriting the oldest slot in place;
the strip shows what that computes. $H = 16$ here so windows fill in seconds; the paper uses $H = 100$.</figcaption>
</figure>
```

## 5 · Score each configuration with a Beta kernel

Each configuration's estimated success rate goes through a Beta-shaped kernel in mode–concentration form,
$\mathrm{Beta}(1+\kappa t,\ 1+\kappa(1-t))$. The target $t$ is the success rate SGS aims for, and the
concentration $\kappa$ sets how sharply it prefers configurations near $t$:

$$w_i = (\hat p_i + \epsilon)^{\kappa t}\,(1-\hat p_i+\epsilon)^{\kappa(1-t)},\qquad \ell_i=\log(w_i+\epsilon),$$

$$P(i)=\frac{\exp(\ell_i/T)}{\sum_{j=1}^{N} \exp(\ell_j/T)}.$$

The floor $\epsilon$ keeps every configuration reachable. Unsolved cells are still sampled now and then, so
their estimates can change the moment the robot gets lucky. The temperature $T$ flattens the whole thing further.
Every figure on this page uses $t = 0.5$, $\kappa = 10$, $T = 2$. The paper uses a gentler $\kappa = 1$ at
$N = 32{,}768$ configurations; on this 145-cell toy, the sharper kernel is both easier to see and slightly
better (mean success 0.94 vs 0.92 after 40,000 episodes). Sharper still backfires: at $T = 1$ the sampler
revisits too few cells to keep their estimates fresh.
The dots on the curve are the live $\hat p_i$ from Figure 4.

```{=web}
<figure class="fig" id="fig-kernel">
  <div class="fig-row two">
    <div>
      <div class="panel-title"><span>kernel over p̂ · live cells as dots</span><span id="k-readout"></span></div>
      <svg class="plot" id="k-plot" viewBox="0 0 420 250"></svg>
      <div class="controls">
        <label>target t <input type="range" id="k-t" min="0.05" max="0.95" step="0.01" value="0.5"><output id="k-t-out"></output></label>
        <label>κ <input type="range" id="k-kappa" min="0" max="30" step="0.5" value="10"><output id="k-kappa-out"></output></label>
        <label>T <input type="range" id="k-T" min="0.25" max="6" step="0.05" value="2"><output id="k-T-out"></output></label>
        <label>log₁₀ ε <input type="range" id="k-eps" min="-10" max="-1" step="0.5" value="-8"><output id="k-eps-out"></output></label>
      </div>
      <div class="controls">
        <span>presets</span>
        <button class="btn" data-preset="page">this page (κ=10)</button>
        <button class="btn" data-preset="paper">paper (κ=1)</button>
        <button class="btn" data-preset="loco">loco (κ=5, t=.66)</button>
        <button class="btn" data-preset="manip">manip (ε=1e-4)</button>
        <button class="btn" data-preset="sharp">sharp (κ=20)</button>
      </div>
    </div>
    <div>
      <div class="panel-title"><span>resulting initial-condition distribution P(i)</span></div>
      <svg class="grid" id="k-grid"></svg>
      <div class="stats">
        <div class="stat"><b id="k-ess">·</b>effective # configs</div>
        <div class="stat"><b id="k-band">·</b>mass on frontier</div>
        <div class="stat"><b id="k-floor">·</b>least likely / most likely</div>
      </div>
    </div>
  </div>
  <figcaption><strong>Figure 5.</strong> Solid: kernel weight $w(p)$ rescaled to its peak. Vermilion: the relative
sampling probability after the log, softmax, and temperature, which is proportional to $(w+\epsilon)^{1/T}$.
At this page&#39;s settings ($t{=}0.5,\ \kappa{=}10,\ T{=}2$) a frontier cell is about 220× likelier to be sampled
than an unsolved one, not infinitely likelier; at the paper&#39;s gentler $\kappa{=}1$ it is about 70×. The effective number of configs is
$\exp(\text{entropy})$. These sliders only change this figure; they do not affect the live training in Figure 4.</figcaption>
</figure>
```

## 6 · The loop

Whenever any parallel environment finishes an episode, SGS records the outcome against
the configuration it had sampled, rescores every configuration, draws a new one, and hands it to the environment.
There is no curriculum schedule, no difficulty labels, and no task-specific tuning. The diagram below walks through
one pass of the loop every 20 seconds; during training, a pass runs every time any environment finishes an episode.

```{=web}
<figure class="fig" id="fig-loop">
  <svg class="plot" id="loop-svg" viewBox="0 0 760 150"></svg>
  <figcaption><strong>Figure 6.</strong> In code, initial-condition sampling lives in the environment&#39;s reset hook:
<code>SGS.on_reset(env_ids)</code> in <code>uwrl/sgs/core.py</code>.
Evaluation bypasses SGS entirely: success is always measured on the fixed set, uniformly.</figcaption>
</figure>
```
