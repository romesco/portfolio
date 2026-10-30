---
title: Nine Ways a Matrix Can Flow
description: Every 2×2 matrix turns the plane into a flow, and every such flow is one of nine kinds. An interactive reproduction of matharium's phase-portrait figure, with a trace–determinant explorer.
authors:
  - Rosario Scalise
head: |
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" crossorigin="anonymous">
  <link rel="stylesheet" href="./garage-assets/phase-portraits/viz.css?v=2be8a371">
scripts: |
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" crossorigin="anonymous"
    onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});"></script>
  <script src="./garage-assets/phase-portraits/viz.js?v=ccb392c9"></script>
---

# Nine Ways a Matrix Can Flow

<p class="lede">A 2×2 matrix $A$ makes the plane flow by $\dot{x} = Ax$. Every such flow is one of nine kinds: points sink, escape, spiral, circle, or settle on a line. Which kind you get is decided entirely by two numbers, the trace and the determinant of $A$.</p>

```{=web}
<figure class="pp" id="fig-gallery">
  <div class="pp-gallery">
    <div class="pp-tile" data-kind="snode"><button class="pp-name" type="button" title="Open the stable node in the explorer">Stable node</button><div class="pp-view" role="img" aria-label="Animated phase portrait of a stable node" title="Click to drop a trajectory"></div><div class="pp-cond">$\lambda_1 < \lambda_2 < 0$</div></div>
    <div class="pp-tile" data-kind="unode"><button class="pp-name" type="button" title="Open the unstable node in the explorer">Unstable node</button><div class="pp-view" role="img" aria-label="Animated phase portrait of an unstable node" title="Click to drop a trajectory"></div><div class="pp-cond">$0 < \lambda_1 < \lambda_2$</div></div>
    <div class="pp-tile" data-kind="saddle"><button class="pp-name" type="button" title="Open the saddle in the explorer">Saddle</button><div class="pp-view" role="img" aria-label="Animated phase portrait of a saddle" title="Click to drop a trajectory"></div><div class="pp-cond">$\lambda_1 < 0 < \lambda_2$</div></div>
    <div class="pp-tile" data-kind="sspiral"><button class="pp-name" type="button" title="Open the stable spiral in the explorer">Stable spiral</button><div class="pp-view" role="img" aria-label="Animated phase portrait of a stable spiral" title="Click to drop a trajectory"></div><div class="pp-cond">$\lambda = \alpha \pm i\beta,\ \alpha < 0$</div></div>
    <div class="pp-tile" data-kind="uspiral"><button class="pp-name" type="button" title="Open the unstable spiral in the explorer">Unstable spiral</button><div class="pp-view" role="img" aria-label="Animated phase portrait of an unstable spiral" title="Click to drop a trajectory"></div><div class="pp-cond">$\lambda = \alpha \pm i\beta,\ \alpha > 0$</div></div>
    <div class="pp-tile" data-kind="center"><button class="pp-name" type="button" title="Open the center in the explorer">Center</button><div class="pp-view" role="img" aria-label="Animated phase portrait of a center" title="Click to drop a trajectory"></div><div class="pp-cond">$\lambda = \pm i\beta$</div></div>
    <div class="pp-tile" data-kind="star"><button class="pp-name" type="button" title="Open the star in the explorer">Star</button><div class="pp-view" role="img" aria-label="Animated phase portrait of a star node" title="Click to drop a trajectory"></div><div class="pp-cond">$A = \lambda I,\ \lambda < 0$</div></div>
    <div class="pp-tile" data-kind="degen"><button class="pp-name" type="button" title="Open the degenerate node in the explorer">Degenerate node</button><div class="pp-view" role="img" aria-label="Animated phase portrait of a degenerate node" title="Click to drop a trajectory"></div><div class="pp-cond">$\lambda_1 = \lambda_2,\ A \neq \lambda I$</div></div>
    <div class="pp-tile" data-kind="line"><button class="pp-name" type="button" title="Open the line of fixed points in the explorer">Line of fixed points</button><div class="pp-view" role="img" aria-label="Animated phase portrait of a line of fixed points" title="Click to drop a trajectory"></div><div class="pp-cond">$\lambda_1 = 0,\ \lambda_2 < 0$</div></div>
    <div class="pp-bar">
      <span class="pp-credit">after <a href="https://x.com/matharium/status/2115846057263542668">@matharium</a></span>
      <button class="pp-btn" id="gal-pause" type="button" aria-pressed="false">pause</button>
    </div>
  </div>
  <figcaption><strong>Figure 1.</strong> The nine phase portraits of $\dot{x} = Ax$. Each colored streak is a point
being carried by the flow; the white curve is one trajectory traced from start to finish. Grey lines are the real
eigendirections, along which points move in a straight line. <b>Click inside any panel</b> to start the white trajectory
from there, or <b>click a title</b> to open that matrix in the explorer below. Reproduced, and made interactive,
from a figure by matharium (see <a href="#source">Source</a>).</figcaption>
</figure>
```

## 1 · A matrix is a flow

Put an arrow at every point $x$ of the plane, and let the arrow be $Ax$. Now drop a grain of sand anywhere and let it
follow the arrows. Its path is the solution of

$$\dot{x} = Ax, \qquad x(t) = e^{At}x(0).$$

Two facts make the linear case special. The origin never moves, because $A0 = 0$. And the picture has no
characteristic size: if $x(t)$ is a trajectory then so is $c\,x(t)$ for any $c$, so the flow looks the same at
every zoom level. All of the interesting structure is in *directions* and *rates*, which is exactly what
eigenvalues measure.

## 2 · Eigenvalues decide

If $v$ is an eigenvector, $Av = \lambda v$, then a point on the line through $v$ stays on that line forever and
moves along it as $e^{\lambda t}$: it shrinks toward the origin when $\lambda < 0$ and runs away when $\lambda > 0$.
The eigenvalues are the roots of the characteristic polynomial

$$\lambda^2 - \tau\lambda + \Delta = 0, \qquad \tau = \operatorname{tr} A,\quad \Delta = \det A,$$

so

$$\lambda_{1,2} = \frac{\tau \pm \sqrt{\tau^2 - 4\Delta}}{2}.$$

Everything about the flow's *kind* depends on $A$ only through $\tau$ and $\Delta$. That turns the whole
classification into a map of the $(\tau, \Delta)$ plane:

- $\Delta < 0$: the eigenvalues are real with opposite signs. **Saddle.**
- $0 < \Delta < \tau^2/4$: real with the same sign. **Node**, stable if $\tau < 0$ and unstable if $\tau > 0$.
- $\Delta > \tau^2/4$: a complex pair $\alpha \pm i\beta$ with $\alpha = \tau/2$ and $\beta = \sqrt{\Delta - \tau^2/4}$.
  **Spiral**, stable if $\tau < 0$, unstable if $\tau > 0$, and a **center** if $\tau = 0$.
- $\Delta = \tau^2/4$: a repeated eigenvalue. A **star** if $A = \lambda I$, otherwise a **degenerate node** with a
  single eigendirection.
- $\Delta = 0$: one eigenvalue is zero. A **line of fixed points.**

The explorer below puts that map next to the flow it describes. Drag the dot in the trace–determinant plane and
watch the portrait change kind as you cross each boundary. The eigenvalue plane shows *why*: two real eigenvalues
slide toward each other along the real axis, collide exactly on the parabola $\Delta = \tau^2/4$, and split off
into a complex-conjugate pair. Press **tour** to orbit the origin of the $(\tau, \Delta)$ plane and pass through
every region in turn.

```{=web}
<figure class="pp" id="fig-explorer">
  <div class="pp-explorer">
    <div>
      <div class="pp-view" id="ex-view" role="img" aria-label="Interactive phase portrait of x dot equals A x for the matrix set on the right" title="Click to drop a trajectory"></div>
      <div class="pp-hint"><span id="ex-hover">hover: the arrow is Ax, the velocity at that point</span><span>click: drop a trajectory</span></div>
      <div class="pp-controls">
        <button class="pp-btn" id="ex-tour" type="button" aria-pressed="false" title="Sweep A around the trace–determinant plane">tour</button>
        <button class="pp-btn" id="ex-clear" type="button" title="Remove the white trajectories">clear trajectories</button>
        <button class="pp-btn" id="ex-pause" type="button" aria-pressed="false">pause</button>
      </div>
      <div class="pp-chips" id="ex-chips" role="group" aria-label="Load one of the nine kinds"></div>
    </div>
    <div>
      <div class="pp-kind" id="ex-kind" aria-live="polite"></div>
      <div class="pp-blurb" id="ex-blurb"></div>
      <dl class="pp-read" id="ex-read"></dl>
      <div class="pp-panel-title"><span>trace–determinant plane</span><span>drag the dot</span></div>
      <svg class="pp-plane" id="ex-td"></svg>
      <div class="pp-panel-title"><span>eigenvalues in the complex plane</span></div>
      <svg class="pp-plane" id="ex-ev"></svg>
      <div class="pp-panel-title"><span>the matrix A</span><span>or set entries directly</span></div>
      <div class="pp-matrix">
        <label>a <input type="range" min="-3" max="3" step="0.05" aria-label="entry a, row 1 column 1"><output>0</output></label>
        <label>b <input type="range" min="-3" max="3" step="0.05" aria-label="entry b, row 1 column 2"><output>0</output></label>
        <label>c <input type="range" min="-3" max="3" step="0.05" aria-label="entry c, row 2 column 1"><output>0</output></label>
        <label>d <input type="range" min="-3" max="3" step="0.05" aria-label="entry d, row 2 column 2"><output>0</output></label>
      </div>
    </div>
  </div>
  <figcaption><strong>Figure 2.</strong> The flow of $\dot{x} = Ax$ (left) and where $A$ sits on the
trace–determinant map (right). Dragging the dot picks a representative matrix with that trace and determinant and a
fixed eigen-geometry; the dot snaps onto the boundary curves when you get close, because those are the only places
the rarer kinds live. The parabola is drawn as a degenerate node; the <b>Star</b> chip gives the one matrix on it,
$A = \lambda I$, that is a star instead. The sliders set the entries of $A$ directly. Arrow keys move the dot
(Shift for bigger steps).</figcaption>
</figure>
```

### The example from the original post

The stable spiral in Figure 1 is the one from matharium's post:

$$A = \begin{pmatrix} -0.5 & -1.55 \\ 1.55 & -0.5 \end{pmatrix}, \qquad \tau = -1,\quad \Delta = 0.25 + 1.55^2 \approx 2.65.$$

Since $\Delta > \tau^2/4 = 0.25$, the eigenvalues are complex: $\lambda = -0.5 \pm i\sqrt{2.65 - 0.25} \approx -0.5 \pm 1.55i$.
The imaginary part sets the turning rate, one lap every $2\pi/1.55 \approx 4.05$ time units, and the real part sets
the decay. Each lap the orbit shrinks by a factor $e^{-0.5 \cdot 4.05} \approx 0.13$, which is why the white
trajectory in that panel only manages about two visible turns before it disappears into the origin.

## 3 · Five kinds are robust, four are knife-edges

The table sorts the nine by where they live on the map.

| kind | condition | lives on |
|---|---|---|
| saddle | $\Delta < 0$ | open region |
| stable / unstable node | $0 < \Delta < \tau^2/4$ | open region |
| stable / unstable spiral | $\Delta > \tau^2/4,\ \tau \neq 0$ | open region |
| center | $\tau = 0,\ \Delta > 0$ | half-line |
| star, degenerate node | $\Delta = \tau^2/4$ | parabola |
| line of fixed points | $\Delta = 0$ | line |

The five kinds in open regions are **structurally stable**: nudge the entries of $A$ a little and the flow stays the
same kind. The other four sit on curves, so almost any nudge knocks them into a neighbor. Try it in the explorer:
load the center and move the $a$ slider by a single step. The closed ellipses open into a spiral, inward or
outward depending on the sign of the step.

This matters well beyond linear systems. Near a fixed point of a nonlinear system $\dot{x} = f(x)$, the flow
looks like that of its Jacobian $A = Df(x^*)$, and for saddles, nodes, and spirals the linear picture tells the
truth (this is the Hartman–Grobman theorem, which needs no eigenvalue on the imaginary axis). The knife-edge cases
are exactly where it can lie. A linearized center can be a stable or unstable spiral once the nonlinear terms are
included, and a star or degenerate node can turn into a node or a spiral, although it keeps its stability.

## How the figures are drawn

Nothing here is a numerical ODE solver. For a 2×2 matrix the exponential has a closed form. Write
$s = \tau/2$ and $M = A - sI$. Since $M$ has zero trace, Cayley–Hamilton gives $M^2 = (\tau^2/4 - \Delta)\,I$, so

$$e^{At} = e^{st}\left(\cosh(rt)\,I + \frac{\sinh(rt)}{r}\,M\right), \qquad r = \sqrt{\tau^2/4 - \Delta},$$

with $\cosh, \sinh$ becoming $\cos, \sin$ when $\tau^2/4 < \Delta$ and the bracket becoming $I + tM$ on the parabola.
Each frame computes $E = e^{A\,\delta t}$ once and moves every particle by $x \leftarrow Ex$, so the
motion is exact at any frame rate. Particles respawn at random after a short life, and each keeps a short history
that is drawn as its fading streak.

## Source

This post reproduces, and makes interactive, a figure and thread by
[matharium (@matharium)](https://x.com/matharium), posted on X on 29 October 2026:
[*"A 2×2 matrix A makes the plane flow by x′ = Ax, and each flow is one of nine kinds…"*](https://x.com/matharium/status/2115846057263542668).
The nine-panel layout, the color-per-kind palette, the $(\tau, \Delta)$ framing, and the stable-spiral example
($\tau = -1$, $\Delta \approx 2.65$, $\lambda = -0.5 \pm 1.55i$) all come from that post. The code and the explorer
are new.

For the full treatment, see S. H. Strogatz, *Nonlinear Dynamics and Chaos*, 2nd ed. (Westview, 2015):
§5.2 *Classification of Linear Systems* for the trace–determinant map, and §6.3 *Fixed Points and Linearization*
for when the linear picture survives the nonlinear terms.
