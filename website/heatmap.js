/* Element-level attention overlay ("poor-man's heatmap"), Path A.
 *
 * Loaded on demand by the ?heatmap toggle in _layout.html.j2. Tints each
 * instrumented element by its engagement count, read from heatmap-data.json
 * (falls back to heatmap-data.sample.json). This is NOT a coordinate density
 * plot: it colors the elements you already track (data-umami-event / data-section
 * / details.work) by aggregate counts. No coordinates, no PII. See
 * docs/ANALYTICS.md and scripts/umami-heatmap-export.py.
 *
 * Layers:
 *   regions  = [data-section] + details.work   (light fill, own scale)
 *   targets  = [data-umami-event]              (stronger tint + count badge)
 */
(function () {
  if (window.__heatmapOn) return;
  window.__heatmapOn = true;

  function num(v) { return typeof v === 'number' && isFinite(v) ? v : 0; }

  // green (low) -> red (high)
  function heat(t) { return 'hsl(' + Math.round((1 - t) * 115) + ', 90%, 48%)'; }

  function workTitle(d) {
    var wt = d.querySelector('.work-title');
    if (!wt) return '';
    var n = wt.childNodes[0];
    return ((n ? n.textContent : wt.textContent) || '').trim();
  }

  function eventCount(data, el) {
    var node = data.event && data.event[el.getAttribute('data-umami-event')];
    if (node == null) return 0;
    if (typeof node === 'number') return node;
    var title = el.getAttribute('data-umami-event-title');
    if (title != null && node[title] != null) return num(node[title]);
    var url = el.getAttribute('data-umami-event-url');
    if (url != null && node[url] != null) return num(node[url]);
    return 0;
  }

  function maxOf(list) {
    return Math.max(1, Math.max.apply(null, list.map(function (x) { return x.c; }).concat(0)));
  }

  function build(payload) {
    var data = payload.d;
    var regions = [], targets = [];

    document.querySelectorAll('[data-section]').forEach(function (el) {
      var name = el.getAttribute('data-section');
      regions.push({ el: el, c: num(data.section && data.section[name]), label: name });
    });
    document.querySelectorAll('details.work').forEach(function (el) {
      var t = workTitle(el), node = data.event && data.event['work-expand'];
      regions.push({ el: el, c: node && t ? num(node[t]) : 0, label: 'work' });
    });
    document.querySelectorAll('[data-umami-event]').forEach(function (el) {
      targets.push({ el: el, c: eventCount(data, el), label: el.getAttribute('data-umami-event') });
    });

    var rMax = maxOf(regions), tMax = maxOf(targets);

    var layer = document.createElement('div');
    layer.style.cssText = 'position:absolute;top:0;left:0;z-index:99998;pointer-events:none;';
    document.body.appendChild(layer);

    function drawBox(item, max, region) {
      var r = item.el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      var sx = window.pageXOffset, sy = window.pageYOffset, t = item.c / max;
      var pad = region ? 0 : 2;
      var b = document.createElement('div');
      b.style.cssText = 'position:absolute;box-sizing:border-box;left:' + (r.left + sx - pad)
        + 'px;top:' + (r.top + sy - pad) + 'px;width:' + (r.width + 2 * pad)
        + 'px;height:' + (r.height + 2 * pad) + 'px;border-radius:' + (region ? 8 : 5) + 'px;';
      if (item.c > 0) {
        b.style.background = heat(t);
        b.style.opacity = region ? (0.10 + 0.25 * t) : (0.30 + 0.45 * t);
        if (!region) b.style.outline = '1px solid ' + heat(t);
      } else {
        b.style.outline = '1px dashed rgba(128,128,128,.45)';
      }
      layer.appendChild(b);
      if (!region && item.c > 0) {
        var tag = document.createElement('div');
        tag.textContent = item.c;
        tag.style.cssText = 'position:absolute;left:' + (r.left + sx) + 'px;top:' + (r.top + sy - 15)
          + 'px;font:600 11px/13px ui-monospace,monospace;color:#fff;background:' + heat(t)
          + ';padding:0 4px;border-radius:3px;white-space:nowrap;';
        layer.appendChild(tag);
      }
    }

    function draw() {
      layer.innerHTML = '';
      layer.style.width = document.documentElement.scrollWidth + 'px';
      layer.style.height = document.documentElement.scrollHeight + 'px';
      regions.forEach(function (x) { drawBox(x, rMax, true); });
      targets.forEach(function (x) { drawBox(x, tMax, false); });
    }
    draw();

    var bar = document.createElement('div');
    bar.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:99999;pointer-events:auto;'
      + 'font:12px/1.45 ui-sans-serif,system-ui;background:#111;color:#eee;padding:10px 12px;'
      + 'border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,.4);max-width:300px;';
    var meta = data.meta || {};
    bar.innerHTML = '<b>Attention overlay</b>' + (payload.sample ? ' <span style="color:#f79ad3">SAMPLE</span>' : '')
      + '<br>' + [meta.range, meta.generated].filter(Boolean).join(' · ')
      + '<br>region max ' + rMax + ' · target max ' + tMax
      + '<br><span style="display:inline-block;width:130px;height:8px;border-radius:4px;vertical-align:middle;'
      + 'background:linear-gradient(90deg,hsl(115,90%,48%),hsl(58,90%,48%),hsl(0,90%,48%))"></span> low&rarr;high'
      + '<br><a href="#" id="hm-close" style="color:#9cf">close</a>';
    document.body.appendChild(bar);
    bar.querySelector('#hm-close').addEventListener('click', function (e) {
      e.preventDefault(); layer.remove(); bar.remove(); window.__heatmapOn = false;
    });

    var rt;
    function redraw() { clearTimeout(rt); rt = setTimeout(draw, 120); }
    window.addEventListener('resize', redraw);
    document.addEventListener('toggle', redraw, true);  // catch details expand/collapse
  }

  function get(url) {
    return fetch(url, { cache: 'no-store' }).then(function (r) {
      if (!r.ok) throw 0;
      return r.json();
    });
  }

  get('/heatmap-data.json').then(function (d) { return { d: d, sample: false }; })
    .catch(function () { return get('/heatmap-data.sample.json').then(function (d) { return { d: d, sample: true }; }); })
    .then(build)
    .catch(function () {
      var w = document.createElement('div');
      w.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:99999;background:#111;color:#eee;'
        + 'padding:10px 12px;border-radius:8px;font:12px ui-sans-serif,system-ui;';
      w.textContent = 'heatmap: no heatmap-data.json (or sample) found';
      document.body.appendChild(w);
    });
})();
