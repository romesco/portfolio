---
title: "[WIP] Compression via Continuous Optimization is Intelligence"
description: "A position paper, drafted in the open: why lossless compression found by gradient descent is a workable operational definition of intelligence."
authors:
  - Rosario Scalise
abstract: |
  We argue that *intelligence* is well modeled as **lossless compression**, and
  that **continuous optimization** is the mechanism by which learning systems
  discover short codes for their observations. This page is both an interactive
  essay and the source of an arXiv position paper: the prose you read here is the
  prose that compiles to the PDF. This is a work in progress, drafted in the open.
arxiv: true
# Per-post assets injected into the standalone page (page.html.j2 forwards
# `head` -> <head> and `scripts` -> end of <body>). KaTeX is loaded from a CDN
# for now; self-hosting is on the planned list below.
head: |
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" crossorigin="anonymous">
  <style>
    .garage-widget{border:1px solid color-mix(in srgb, currentColor 16%, transparent);
      border-radius:10px;padding:1rem 1.1rem;margin:1.6rem 0;}
    .garage-widget canvas{width:100%;height:auto;display:block;border-radius:6px;}
    .garage-controls{display:flex;gap:.9rem;align-items:center;flex-wrap:wrap;
      margin-top:.7rem;font-size:.9rem;}
    .garage-controls button{padding:.25rem .7rem;border-radius:6px;cursor:pointer;
      border:1px solid color-mix(in srgb, currentColor 30%, transparent);
      background:color-mix(in srgb, currentColor 8%, transparent);color:inherit;}
    .garage-caption{font-size:.82rem;opacity:.68;margin:.55rem 0 0;}
    .marginnote{font-size:.8rem;opacity:.7;border-left:2px solid
      color-mix(in srgb, currentColor 30%, transparent);padding-left:.6rem;margin:.9rem 0;}
    .ai-draft{background:color-mix(in srgb, gold 22%, transparent);border-radius:3px;
      padding:0 .15em;}
  </style>
scripts: |
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" crossorigin="anonymous"></script>
  <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" crossorigin="anonymous"
    onload="renderMathInElement(document.body,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],throwOnError:false});"></script>
---

> **This is a test post.** It exists to exercise every feature the garage
> authoring pipeline supports: dual-target prose, math, interactive widgets with
> print fallbacks, provenance markers, and the one-file-to-two-outputs build. The
> argument itself is a sketch, not a finished claim.

## How this post is authored

This whole page is **one Markdown file**, `website/pages/garage-compression-is-intelligence.md`.
That single file produces two things:

1. the interactive web page you are reading, and
2. an arXiv-ready `main.tex` (run `make paper`), compiled from the *same* prose.

The loop is: Claude drafts a section, I rewrite it in my voice and strip the
`AI-DRAFT` marker, `make site` rebuilds in under a second, and a lint pass warns
about em-dashes, unreviewed drafts, and unchecked citations before anything ships.

Interactive widgets live in ` ```{=web} ` fenced blocks (raw HTML/JS/SVG, passed
through untouched) and each is paired with a ` ```{=paper} ` LaTeX fallback so the
PDF stays whole. Math is written once in `$...$` and renders with KaTeX on the web
and native LaTeX in the PDF.

## Test formatting

Prose supports the usual Markdown: **bold**, *italic*, ~~struck~~, `inline code`,
and [external links](https://en.wikipedia.org/wiki/Kolmogorov_complexity). A short
list of the load-bearing ideas:

- **Compression** is finding the shortest program that reproduces the data.
- **Prediction** is compression: a good next-token model *is* a good code.
- **Optimization** is how a bounded agent searches the space of codes.

And an ordered list, because order sometimes matters:

1. Observe data.
2. Fit a model by continuous optimization.
3. Ship the model plus the residuals: that total length is your score.

A table, rendered to a real `<table>` on the web and a `tabular` in the PDF:

| Representation | Description length | Lossless? |
|:---------------|-------------------:|:---------:|
| Raw pixels     |            1.00 MB |    yes    |
| PNG            |            0.32 MB |    yes    |
| Learned model  |            0.05 MB |    yes*   |

A fenced code block passes through verbatim to both targets:

```python
def mdl_score(model, data):
    # Minimum Description Length: model bits + residual bits
    return bits(model) + bits(data | model)
```

<p class="marginnote">Margin-style asides are just styled HTML in the source.
They degrade to ordinary paragraphs in print, so no figure fallback is needed.</p>

## Test math

Inline first: the description length of data $x$ under model $\theta$ is
$\ell(x) = -\log_2 p_\theta(x)$, and learning minimizes the expected code length
$L(\theta) = \mathbb{E}_{x}\left[-\log_2 p_\theta(x)\right]$ by gradient flow:

$$\dot{\theta} = -\nabla_\theta L(\theta), \qquad L(\theta) = \tfrac{1}{N}\sum_{i=1}^{N} -\log_2 p_\theta(x_i).$$

The claim of the paper is that the fixed point of this flow is the shortest code
this model class can express, and that *shortness is what we mean by understanding*.

## Test widgets

Four widgets follow, each interactive on the web with a captioned print
fallback in the PDF.

### Gradient descent on a 1-D loss

The first widget: a ball rolling downhill on a 1-D loss, stepped by gradient
descent. Drag the learning rate and press **step** or **run**. In the PDF this
becomes a captioned figure that links back to the live version.

```{=web}
<figure class="garage-widget" id="gd-widget">
  <canvas id="gd-canvas" width="640" height="260" aria-label="Gradient descent on a 1-D loss curve"></canvas>
  <div class="garage-controls">
    <button type="button" id="gd-step">step</button>
    <button type="button" id="gd-run">run</button>
    <button type="button" id="gd-reset">reset</button>
    <label>learning rate <input type="range" id="gd-lr" min="0.01" max="0.9" step="0.01" value="0.18"></label>
    <span id="gd-lr-val">0.18</span>
  </div>
  <p class="garage-caption">Figure 1. Gradient descent on $L(x)=(x-2)^2$. Interactive on the web; static in the PDF.</p>
  <script>
  (function () {
    var cv = document.getElementById('gd-canvas'), ctx = cv.getContext('2d');
    var lr = document.getElementById('gd-lr'), lrv = document.getElementById('gd-lr-val');
    var x = -4.5, timer = null;
    function L(t){ return (t-2)*(t-2); }
    function dL(t){ return 2*(t-2); }
    function draw(){
      var W = cv.width, H = cv.height, pad = 24;
      ctx.clearRect(0,0,W,H);
      var xmin=-6, xmax=6, ymin=0, ymax=64;
      function px(t){ return pad + (t-xmin)/(xmax-xmin)*(W-2*pad); }
      function py(v){ return H-pad - (v-ymin)/(ymax-ymin)*(H-2*pad); }
      ctx.strokeStyle = 'rgba(128,128,128,.5)'; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(px(0),pad); ctx.lineTo(px(0),H-pad); ctx.stroke();
      ctx.strokeStyle = '#4f7cff'; ctx.lineWidth = 2; ctx.beginPath();
      for (var t=xmin; t<=xmax; t+=0.05){ var X=px(t),Y=py(L(t)); t===xmin?ctx.moveTo(X,Y):ctx.lineTo(X,Y); }
      ctx.stroke();
      ctx.fillStyle = '#e0479a';
      ctx.beginPath(); ctx.arc(px(x), py(L(x)), 6, 0, 2*Math.PI); ctx.fill();
    }
    function step(){ x = x - parseFloat(lr.value)*dL(x); if (Math.abs(x-2)<1e-3) stop(); draw(); }
    function run(){ if (timer) return stop(); timer = setInterval(step, 60); }
    function stop(){ clearInterval(timer); timer = null; }
    document.getElementById('gd-step').onclick = step;
    document.getElementById('gd-run').onclick = run;
    document.getElementById('gd-reset').onclick = function(){ stop(); x=-4.5; draw(); };
    lr.oninput = function(){ lrv.textContent = parseFloat(lr.value).toFixed(2); };
    draw();
  })();
  </script>
</figure>
```
```{=paper}
\begin{figure}[h]
  \centering
  \fbox{\parbox{0.8\linewidth}{\centering\vspace{2em}
    \textit{Interactive figure:} gradient descent on $L(x)=(x-2)^2$.\\
    Live version: \url{https://rosarioscalise.com/garage-compression-is-intelligence}
    \vspace{2em}}}
  \caption{Gradient descent on a 1-D loss. Interactive on the web; a captioned
  still here. Replace this \texttt{fbox} with \texttt{\textbackslash includegraphics}
  of a committed PNG in \texttt{website/img/garage/<slug>/} for a real screenshot.}
\end{figure}
```

### Code length of a message

Type into the box and watch the code length shrink as the letters get more predictable, which is exactly what compression exploits.

```{=web}
<figure class="garage-widget" id="ent-widget">
  <div class="garage-controls">
    <label>message <input type="text" id="ent-input" value="the quick brown fox" size="28" spellcheck="false" aria-label="message to encode"></label>
  </div>
  <p style="margin:.5rem 0 .3rem;font-size:.9rem;">
    total code length <strong id="ent-total">0</strong> bits  · 
    <strong id="ent-bpc">0</strong> bits per character
  </p>
  <canvas id="ent-canvas" width="640" height="260" aria-label="Bits contributed by each distinct character"></canvas>
  <p class="garage-caption">Figure 2. A simple code assigns each character $-\log_2 p$ bits, where $p$ is its frequency in this exact string. Bars show total bits per distinct character. Skewed frequencies (better prediction) mean fewer bits per character: that is compression. Type "aaaa" for $0$ bits, or a string of all-distinct letters for the $\log_2(\text{alphabet size})$ ceiling.</p>
  <script>
  (function () {
    var fig = document.getElementById('ent-widget');
    if (!fig) return;
    var inp = document.getElementById('ent-input');
    var cv = document.getElementById('ent-canvas');
    var tot = document.getElementById('ent-total');
    var bpc = document.getElementById('ent-bpc');
    if (!inp || !cv || !tot || !bpc) return;
    var ctx = cv.getContext('2d');
    function update() {
      var s = inp.value, n = s.length, W = cv.width, H = cv.height;
      ctx.clearRect(0, 0, W, H);
      if (n === 0) { tot.textContent = '0'; bpc.textContent = '0'; return; }
      var counts = {};
      for (var i = 0; i < n; i++) counts[s[i]] = (counts[s[i]] || 0) + 1;
      var rows = Object.keys(counts).map(function (c) {
        var p = counts[c] / n;
        return { c: c, count: counts[c], total: (-Math.log(p) / Math.log(2)) * counts[c] };
      });
      rows.sort(function (a, b) { return b.total - a.total; });
      var totalBits = rows.reduce(function (a, r) { return a + r.total; }, 0);
      tot.textContent = totalBits.toFixed(1);
      bpc.textContent = (totalBits / n).toFixed(2);
      var pad = 8, rowH = 22, gap = 6, maxTot = rows[0].total || 1;
      var visible = Math.min(rows.length, Math.floor((H - 2 * pad + gap) / (rowH + gap)));
      ctx.font = '13px system-ui,sans-serif'; ctx.textBaseline = 'middle';
      for (var k = 0; k < visible; k++) {
        var r = rows[k], y = pad + k * (rowH + gap);
        var barMax = W - 110, w = Math.max(2, r.total / maxTot * barMax);
        var glyph = r.c === ' ' ? '␣' : r.c;
        ctx.fillStyle = 'rgba(128,128,128,.85)';
        ctx.fillText(glyph + '  ×' + r.count, pad, y + rowH / 2);
        var grad = ctx.createLinearGradient(52, 0, 52 + w, 0);
        grad.addColorStop(0, '#4f7cff'); grad.addColorStop(1, '#e0479a');
        ctx.fillStyle = grad;
        ctx.fillRect(52, y + 3, w, rowH - 6);
        ctx.fillStyle = 'rgba(128,128,128,.9)';
        ctx.fillText(r.total.toFixed(1) + ' b', 52 + w + 6, y + rowH / 2);
      }
    }
    inp.addEventListener('input', update);
    update();
  })();
  </script>
</figure>
```
```{=paper}
\begin{figure}[h]
  \centering
  \fbox{\parbox{0.8\linewidth}{\centering\vspace{1.5em}
    \textit{Interactive figure:} type a message and watch its code length, where each character costs $-\log_2 p$ bits for its frequency $p$ in the string.\\
    Live: \url{https://rosarioscalise.com/garage-compression-is-intelligence}
    \vspace{1.5em}}}
  \caption{The per-character code length of a typed message: skewed letter frequencies (better prediction) yield fewer bits per character, illustrating compression. Interactive on the web; a captioned still here.}
\end{figure}
```

### Overfitting is bad compression

Drag the degree slider to fit a polynomial to ten fixed noisy points and watch the total description length trace a U whose minimum sits well short of the wiggliest curve.

```{=web}
<figure class="garage-widget" id="mdl-widget">
  <canvas id="mdl-canvas" width="640" height="260" aria-label="Polynomial of adjustable degree fit to ten noisy points"></canvas>
  <div class="garage-controls">
    <label>degree <input type="range" id="mdl-deg" min="1" max="12" step="1" value="3"></label>
    <span id="mdl-deg-val">3</span>
    <span>model bits <strong id="mdl-model">0</strong></span>
    <span>residual bits <strong id="mdl-resid">0</strong></span>
    <span>total bits <strong id="mdl-total">0</strong></span>
  </div>
  <p class="garage-caption">Figure 3. Least-squares fit of degree $d$ to a fixed noisy set. Description length $= \underbrace{\tfrac{d+1}{2}\log_2 n}_{\text{model}} + \underbrace{\tfrac{n}{2}\log_2\!\big(1+\tfrac{\mathrm{RSS}/n}{\sigma_0^2}\big)}_{\text{residual}}$. The minimum is at $d=3$, the degree that truly generated the data, not the highest degree that drives training error to zero.</p>
  <script>
  (function () {
    var cv = document.getElementById('mdl-canvas'); if (!cv) return;
    var ctx = cv.getContext('2d');
    var deg = document.getElementById('mdl-deg');
    var degv = document.getElementById('mdl-deg-val');
    var mB = document.getElementById('mdl-model'), rB = document.getElementById('mdl-resid'), tB = document.getElementById('mdl-total');
    var XS = [-1,-0.78,-0.56,-0.33,-0.11,0.11,0.33,0.56,0.78,1];       // fixed noisy set
    var YS = [0.4,-0.091,-0.098,-0.206,0.045,0.005,0.196,0.088,0.091,-0.42];
    var N = XS.length, S0 = 0.008;                                     // noise-variance floor sigma0^2
    function fit(d){                                                   // exact least squares: normal equations
      var k=d+1,i,j,r,c,M=[],b=[];
      for(i=0;i<k;i++){b[i]=0;M[i]=[];for(j=0;j<k;j++)M[i][j]=0;}
      for(r=0;r<N;r++){var pw=[1];for(j=1;j<k;j++)pw[j]=pw[j-1]*XS[r];  // Vandermonde row
        for(i=0;i<k;i++){b[i]+=pw[i]*YS[r];for(j=0;j<k;j++)M[i][j]+=pw[i]*pw[j];}}
      for(i=0;i<k;i++)M[i][i]+=1e-9;                                   // tiny ridge for numerical stability
      for(c=0;c<k;c++){var p=c;for(r=c+1;r<k;r++)if(Math.abs(M[r][c])>Math.abs(M[p][c]))p=r;
        var t=M[c];M[c]=M[p];M[p]=t;var tb=b[c];b[c]=b[p];b[p]=tb;     // partial pivot
        var dd=M[c][c];if(Math.abs(dd)<1e-12)continue;
        for(r=0;r<k;r++){if(r===c)continue;var f=M[r][c]/dd;
          for(j=c;j<k;j++)M[r][j]-=f*M[c][j];b[r]-=f*b[c];}}
      var co=[];for(i=0;i<k;i++)co[i]=Math.abs(M[i][i])>1e-12?b[i]/M[i][i]:0;return co;
    }
    function ev(co,x){var v=0,p=1,i;for(i=0;i<co.length;i++){v+=co[i]*p;p*=x;}return v;}
    function draw(){
      var d=parseInt(deg.value,10), co=fit(d), W=cv.width, H=cv.height, pad=26;
      var xm=-1.12,xM=1.12,ym=-0.75,yM=0.75;
      function px(x){return pad+(x-xm)/(xM-xm)*(W-2*pad);}
      function py(y){return H-pad-(y-ym)/(yM-ym)*(H-2*pad);}
      ctx.clearRect(0,0,W,H);
      ctx.strokeStyle='rgba(128,128,128,.35)';ctx.lineWidth=1;                      // y=0 axis
      ctx.beginPath();ctx.moveTo(px(xm),py(0));ctx.lineTo(px(xM),py(0));ctx.stroke();
      ctx.strokeStyle='#4f7cff';ctx.lineWidth=2;ctx.beginPath();                     // fitted curve
      for(var x=xm;x<=xM;x+=0.01){var Y=ev(co,x);if(Y<ym)Y=ym;if(Y>yM)Y=yM;
        var X=px(x),Yy=py(Y);x===xm?ctx.moveTo(X,Yy):ctx.lineTo(X,Yy);}
      ctx.stroke();
      ctx.fillStyle='#e0479a';                                                       // data points
      for(var r=0;r<N;r++){ctx.beginPath();ctx.arc(px(XS[r]),py(YS[r]),4,0,2*Math.PI);ctx.fill();}
      var rss=0;for(r=0;r<N;r++){var e=YS[r]-ev(co,XS[r]);rss+=e*e;}
      var resid=(N/2)*Math.log2(1+(rss/N)/S0), model=((d+1)/2)*Math.log2(N);
      if(degv)degv.textContent=d;
      if(mB)mB.textContent=model.toFixed(1);
      if(rB)rB.textContent=resid.toFixed(1);
      if(tB)tB.textContent=(model+resid).toFixed(1);
    }
    if(deg)deg.oninput=draw;
    draw();
  })();
  </script>
</figure>
```
```{=paper}
\begin{figure}[h]
  \centering
  \fbox{\parbox{0.8\linewidth}{\centering\vspace{1.5em}
    \textit{Interactive figure:} a polynomial of adjustable degree fit to ten fixed noisy points, with live model bits, residual bits, and total description length.\\
    Live: \url{https://rosarioscalise.com/garage-compression-is-intelligence}
    \vspace{1.5em}}}
  \caption{Sliding the polynomial degree traces the total description length as a U-shape whose minimum lands at the true generating degree, showing that the best model minimizes total code length rather than training error.}
\end{figure}
```

### The bit budget: how many bits to describe the data

This widget animates the description length in bits of the same data under four codes, showing that a learned model finds the shortest code.

```{=web}
<figure class="garage-widget" id="bits-widget">
  <canvas id="bits-canvas" width="640" height="240" aria-label="Bar chart of description length in bits under four codes"></canvas>
  <div class="garage-controls">
    <button type="button" id="bits-rerun">re-run</button>
  </div>
  <p class="garage-caption">Figure 4. Description length of one fixed datum under four codes. Shorter is better: the learned model reaches $\approx 640$ bits, about $12.8\times$ shorter than the $8192$-bit raw encoding. Learning is finding a shorter code.</p>
  <script>
  (function () {
    var cv = document.getElementById('bits-canvas'); if (!cv) return;
    var ctx = cv.getContext('2d');
    var rerun = document.getElementById('bits-rerun');
    var data = [
      { name: 'Raw',           bits: 8192, color: 'rgba(150,150,150,.8)' },
      { name: 'gzip',          bits: 3120, color: '#7a8bd4' },
      { name: 'PNG',           bits: 2360, color: '#4f7cff' },
      { name: 'Learned model', bits: 640,  color: '#e0479a' }
    ];
    var maxBits = 8192, t0 = null, dur = 900, timer = null;
    function ease(u){ return 1 - Math.pow(1 - u, 3); }
    function draw(p){
      var W = cv.width, H = cv.height, padL = 108, padR = 78, padT = 16, padB = 16;
      ctx.clearRect(0, 0, W, H);
      var n = data.length, gap = 14;
      var bh = (H - padT - padB - gap * (n - 1)) / n;
      ctx.font = '13px system-ui, sans-serif'; ctx.textBaseline = 'middle';
      for (var i = 0; i < n; i++) {
        var y = padT + i * (bh + gap);
        var full = (data[i].bits / maxBits) * (W - padL - padR);
        var w = full * p;
        ctx.fillStyle = 'rgba(128,128,128,.14)';
        ctx.fillRect(padL, y, W - padL - padR, bh);
        ctx.fillStyle = data[i].color;
        ctx.fillRect(padL, y, w, bh);
        ctx.fillStyle = 'rgba(128,128,128,.95)'; ctx.textAlign = 'right';
        ctx.fillText(data[i].name, padL - 12, y + bh / 2);
        ctx.textAlign = 'left';
        ctx.fillText(Math.round(data[i].bits * p) + ' b', padL + w + 8, y + bh / 2);
      }
    }
    function frame(ts){
      if (t0 === null) t0 = ts;
      var p = Math.min(1, (ts - t0) / dur);
      draw(ease(p));
      if (p < 1) timer = requestAnimationFrame(frame); else timer = null;
    }
    function run(){ if (timer) cancelAnimationFrame(timer); t0 = null; timer = requestAnimationFrame(frame); }
    if (rerun) rerun.onclick = run;
    run();
  })();
  </script>
</figure>
```
```{=paper}
\begin{figure}[h]
  \centering
  \fbox{\parbox{0.8\linewidth}{\centering\vspace{1.5em}
    \textit{Interactive figure:} animated bar chart of description length in bits for the same datum under Raw, gzip, PNG, and a learned model.\\
    Live: \url{https://rosarioscalise.com/garage-compression-is-intelligence}
    \vspace{1.5em}}}
  \caption{Description length of one fixed datum under four codes; the learned model yields the shortest encoding ($\approx 640$ bits vs. $8192$ raw), illustrating that learning finds a shorter code.}
\end{figure}
```

## Provenance

Spans still awaiting a human editing pass are marked inline, so the lint pass can
count them and flag the post as unfinished:

<!-- AI-DRAFT --><span class="ai-draft">This sentence is a stand-in for
machine-drafted text that has not yet been rewritten in the author's voice; the
build reports one unreviewed AI-DRAFT span for this post.</span>

## Planned, not yet wired

- **Citations with a bibliography**: `[@key]` resolving to a references list on the
  web and `\cite{key}` plus a flattened `main.bbl` for arXiv. The lint already
  refuses a `[@key]` whose `sources:` entry is missing or not `checked: true`.
- **Self-hosted KaTeX** (drop the CDN dependency; matches the analytics self-host plan).
- **Auto-captured widget stills** so `{=paper}` fallbacks show a real screenshot
  without a manual export step.
