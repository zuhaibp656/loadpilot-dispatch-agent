/* LoadPilot animation engine — self-contained Canvas2D.
 * Views:
 *   map  : interactive road map. Pan/zoom; road-following routes; numbered delivery stops;
 *          click a stop for its card and a truck for its route; trucks drive the plan on a clock;
 *          toggle Today (manual) vs LoadPilot. Basemap: live CARTO/OSM tiles when the host
 *          allows them, otherwise the inlined OpenStreetMap vector basemap (no network needed).
 *   load : orbitable 3D truck; cartons slide in from the door in load order (last stop first);
 *          "Unload replay" plays deliveries stop by stop. Painter order uses separating-axis
 *          topological sorting so lower boxes never paint over the boxes above them.
 * Data: window.LP (see app/render/anim_html.py). Mode: window.LP_MODE = 'load'|'routes'|'both'.
 */
(function () {
  'use strict';
  var D = window.LP || {}, MODE = window.LP_MODE || 'both';
  var PAL = ['#ff6d00', '#00b8d4', '#ffd600', '#d500f9', '#64dd17', '#ff1744', '#2979ff', '#1de9b6',
             '#ffab00', '#f50057', '#76ff03', '#651fff', '#00e5ff', '#c6ff00', '#ff3d00', '#aa00ff'];
  function stopColor(seq) { return PAL[(seq - 1) % PAL.length]; }
  function $(tag, cls, parent, html) {
    var e = document.createElement(tag); if (cls) e.className = cls;
    if (html != null) e.innerHTML = html; if (parent) parent.appendChild(e); return e;
  }
  function fmtT(m) { m = Math.max(0, Math.round(m)); var h = Math.floor(m / 60), mm = m % 60;
    return (h < 10 ? '0' : '') + h + ':' + (mm < 10 ? '0' : '') + mm; }
  function shade(hex, f) {
    var n = parseInt(hex.slice(1), 16), r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    r = Math.min(255, Math.round(r * f)); g = Math.min(255, Math.round(g * f)); b = Math.min(255, Math.round(b * f));
    return 'rgb(' + r + ',' + g + ',' + b + ')';
  }
  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  /* keep a canvas sized to its wrapper, whatever the host does with display/visibility */
  function autoSize(wrap, cv, ctx, cb) {
    var st = { W: 0, H: 0 };
    function fit() {
      var r = wrap.getBoundingClientRect(); if (r.width < 20 || r.height < 20) return false;
      if (Math.abs(r.width - st.W) < 1 && Math.abs(r.height - st.H) < 1) return true;
      var dpr = window.devicePixelRatio || 1; st.W = r.width; st.H = r.height;
      cv.width = Math.round(st.W * dpr); cv.height = Math.round(st.H * dpr);
      cv.style.width = st.W + 'px'; cv.style.height = st.H + 'px'; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (cb) cb(st.W, st.H); return true;
    }
    if (window.ResizeObserver) new ResizeObserver(fit).observe(wrap);
    st.fit = fit; return st;
  }

  var root = document.getElementById('lp-app');
  var tabs = null, panes = {};
  if (MODE === 'both') {
    tabs = $('div', 'lp-tabs', root);
    [['routes', '🗺️ Route map'], ['load', '📦 3D truck loading']].forEach(function (k) {
      var b = $('button', 'lp-tab', tabs, k[1]); b.onclick = function () { show(k[0]); }; b.dataset.k = k[0];
    });
  }
  function show(k) {
    Object.keys(panes).forEach(function (p) { panes[p].el.style.display = p === k ? 'flex' : 'none'; });
    if (tabs) Array.prototype.forEach.call(tabs.children, function (b) { b.classList.toggle('on', b.dataset.k === k); });
  }

  /* ============================== 3D LOADING VIEW ============================== */
  function LoadView(host) {
    var el = $('div', 'lp-pane', host), self = this; this.el = el;
    var top = $('div', 'lp-top', el);
    var title = $('div', 'lp-title', top), stats = $('div', 'lp-stats', top);
    var body = $('div', 'lp-body', el);
    var cwrap = $('div', 'lp-cwrap', body), cv = $('canvas', 'lp-canvas', cwrap), ctx = cv.getContext('2d');
    var hud = $('div', 'lp-hud', cwrap), banner = $('div', 'lp-banner', cwrap);
    var legend = $('div', 'lp-legend', body);
    var ctr = $('div', 'lp-ctrl', el);
    var sel = $('div', 'lp-trucks', ctr);
    var play = $('button', 'lp-btn lp-play', ctr, '&#10074;&#10074;');
    var modeB = $('button', 'lp-btn', ctr, 'Unload replay');
    var spd = $('button', 'lp-btn', ctr, '4x');
    var scrub = $('input', 'lp-scrub', ctr); scrub.type = 'range'; scrub.min = 0; scrub.value = 0;
    var reset = $('button', 'lp-btn', ctr, 'Reset view');
    var S = autoSize(cwrap, cv, ctx);

    var trucks = D.trucks || [], T = null;
    var yaw = 0.62, pitch = 0.52, zoom = 1, speed = 4, playing = true, mode = 'load';
    var t = 0, last = null, scale = 1, ox = 0, oy = 0;
    var focusSeq = null, hoverIdx = -1, pinIdx = -1, polys = [], mouse = null;
    var card = $('div', 'lp-card', cwrap); card.style.display = 'none';
    var tip = $('div', 'lp-tip', cwrap); tip.style.display = 'none';
    var hint = $('div', 'lp-hint', cwrap, '👆 Click a store on the right (or any carton) to see exactly where its boxes go');

    trucks.forEach(function (tr, i) {
      var b = $('button', 'lp-chip', sel, esc(tr.id) + ' <small>' + esc(tr.driver) + '</small>');
      b.style.borderColor = tr.color; b.onclick = function () { pick(i); };
    });
    function stopInfo(seq) {  // derived from the placed cartons: zone, layers, load steps
      var bx = T.boxes, o = { n: 0, kg: 0, frag: 0, x0: 1e9, x1: -1e9, z1: 0, y0: 1e9, y1: -1e9, s0: 1e9, s1: -1, skus: {} };
      for (var i = 0; i < bx.length; i++) {
        var b = bx[i]; if (b[6] !== seq) continue;
        o.n++; o.kg += b[9] || 0; if (b[7]) o.frag++;
        o.x0 = Math.min(o.x0, b[0]); o.x1 = Math.max(o.x1, b[0] + b[3]); o.z1 = Math.max(o.z1, b[2] + b[5]);
        o.y0 = Math.min(o.y0, b[1]); o.y1 = Math.max(o.y1, b[1] + b[4]); o.s0 = Math.min(o.s0, i); o.s1 = Math.max(o.s1, i);
        var d = (T.desc && T.desc[b[8]]) || b[8]; o.skus[d] = (o.skus[d] || 0) + 1;
      }
      return o;
    }
    function where(b) {
      var fromDoor = Math.round(T.L - (b[0] + b[3])), side = (b[1] + b[4] / 2) < T.W / 3 ? 'left' : (b[1] + b[4] / 2) > 2 * T.W / 3 ? 'right' : 'middle';
      var layer = b[2] < 1 ? 'on the floor' : 'stacked at ' + Math.round(b[2]) + ' cm';
      return fromDoor + ' cm from the door · ' + side + ' · ' + layer;
    }
    function showCard(seq) {
      var s = T.stops.filter(function (x) { return x.seq === seq; })[0]; if (!s) { card.style.display = 'none'; return; }
      var o = stopInfo(seq), nS = T.stops.length, before = T.stops.filter(function (x) { return x.seq < seq; });
      var inFront = before.reduce(function (a, x) { return a + x.n; }, 0);
      var skus = Object.keys(o.skus).sort(function (a, b) { return o.skus[b] - o.skus[a]; }).map(function (k) { return o.skus[k] + '× ' + esc(k); }).join('<br>');
      var fromDoor0 = Math.max(0, Math.round(T.L - o.x1)), fromDoor1 = Math.round(T.L - o.x0);
      card.innerHTML = '<div class="lp-pop-h" style="border-color:' + stopColor(seq) + '"><span class="lp-num" style="background:' + stopColor(seq) + '">' + seq + '</span>' +
        '<div><b>' + esc(s.name) + '</b><br><span class="lp-muted">' + esc(s.addr || '') + '</span></div><button class="lp-x">&times;</button></div>' +
        '<div class="lp-pop-g">' +
        '<span>Delivery</span><b>' + seq + ' of ' + nS + ' · ETA ' + esc(s.eta) + (seq === 1 ? ' · first off' : seq === nS ? ' · last stop' : '') + '</b>' +
        '<span>Cartons</span><b>' + o.n + ' · ' + Math.round(o.kg) + ' kg' + (o.frag ? ' · <span class="bad">' + o.frag + ' fragile (on top)</span>' : '') + '</b>' +
        '<span>Put them</span><b>' + fromDoor0 + '–' + fromDoor1 + ' cm from the rear door' + (o.y1 - o.y0 > T.W * 0.8 ? ', full width' : '') + ', up to ' + Math.round(o.z1) + ' cm high</b>' +
        '<span>Load</span><b>steps ' + (o.s0 + 1) + '–' + (o.s1 + 1) + ' of ' + T.boxes.length + (seq < nS ? ' · after stop ' + (seq + 1) : ' · first, against the cab') + (seq > 1 ? ', before stop ' + (seq - 1) : ', last in (at the door)') + '</b>' +
        '<span>Unload</span><b>' + (inFront ? inFront + ' cartons of stops 1–' + (seq - 1) + ' are gone before you reach it' : 'nothing in front — straight out') + '</b>' +
        '<span>Goods</span><b>' + skus + '</b></div>';
      card.style.display = 'block';
      card.querySelector('.lp-x').onclick = function () { setFocus(null); };
    }
    function setFocus(seq) {
      focusSeq = seq; pinIdx = -1; tip.style.display = 'none';
      if (seq != null) { if (mode !== 'load') { mode = 'load'; modeB.textContent = 'Unload replay'; } t = T.boxes.length; playing = false; play.innerHTML = '&#9654;'; hint.style.display = 'none'; showCard(seq); }
      else card.style.display = 'none';
      Array.prototype.forEach.call(legend.querySelectorAll('.lp-li'), function (r) { r.classList.toggle('sel', +r.dataset.seq === seq); });
    }
    function pick(i) {
      T = trucks[i]; t = 0; mode = 'load'; modeB.textContent = 'Unload replay'; playing = true; focusSeq = null; pinIdx = -1;
      card.style.display = 'none'; tip.style.display = 'none';
      play.innerHTML = '&#10074;&#10074;';
      Array.prototype.forEach.call(sel.children, function (b, k) { b.classList.toggle('on', k === i); });
      scrub.max = T.boxes.length; title.innerHTML = '<b>' + esc(T.id) + '</b> &middot; ' + esc(T.name) +
        ' <span class="lp-muted">(' + T.L + '&times;' + T.W + '&times;' + T.H + ' cm)</span>';
      stats.innerHTML = kv('Driver', esc(T.driver)) + kv('Corridor', esc(T.corridor + ' · ' + T.branch)) +
        kv('Cartons', T.boxes.length) + kv('Volume fill', T.fill + '%') + kv('Payload', T.wfill + '%') +
        kv('LIFO check', T.lifo ? '<span class="ok">&#10003; pass</span>' : '<span class="bad">review</span>');
      legend.innerHTML = '<div class="lp-lh">Delivery order <span class="lp-muted">(1 = at the door) · click a store</span></div>';
      T.stops.forEach(function (s) {
        var r = $('div', 'lp-li lp-click', legend, '<i style="background:' + stopColor(s.seq) + '"></i><div><b>' + s.seq +
          '</b> ' + esc(s.name) + '<br><span class="lp-muted">' + s.n + ' ctn &middot; ETA ' + s.eta + '</span></div>');
        r.dataset.seq = s.seq; r.onclick = function () { setFocus(focusSeq === s.seq ? null : s.seq); };
      });
      var all = $('div', 'lp-li lp-click', legend, '<i style="background:#8ab4f8"></i><div><b>Show all stores</b></div>');
      all.onclick = function () { setFocus(null); };
    }
    this.focusTruckStop = function (id, seq) {
      for (var i = 0; i < trucks.length; i++) if (trucks[i].id === id) { pick(i); if (seq != null) setFocus(seq); return true; }
      return false;
    };
    function kv(k, v) { return '<div class="kv"><span>' + k + '</span><b>' + v + '</b></div>'; }

    play.onclick = function () { playing = !playing; play.innerHTML = playing ? '&#10074;&#10074;' : '&#9654;'; if (playing && focusSeq != null) setFocus(null); };
    spd.onclick = function () { speed = speed >= 16 ? 1 : speed * 2; spd.textContent = speed + 'x'; };
    modeB.onclick = function () {
      setFocus(null);
      mode = mode === 'load' ? 'unload' : 'load'; t = 0; playing = true; play.innerHTML = '&#10074;&#10074;';
      modeB.textContent = mode === 'load' ? 'Unload replay' : 'Loading replay';
    };
    scrub.oninput = function () { playing = false; play.innerHTML = '&#9654;'; mode = 'load'; t = +scrub.value; };
    reset.onclick = function () { yaw = 0.62; pitch = 0.52; zoom = 1; };
    function inPoly(px, py, pts) {
      var c = false;
      for (var i = 0, j = pts.length - 1; i < pts.length; j = i++) {
        if (((pts[i][1] > py) !== (pts[j][1] > py)) && (px < (pts[j][0] - pts[i][0]) * (py - pts[i][1]) / (pts[j][1] - pts[i][1]) + pts[i][0])) c = !c;
      }
      return c;
    }
    function hitBox(px, py) {
      for (var i = polys.length - 1; i >= 0; i--) if (inPoly(px, py, polys[i][1])) return polys[i][0];
      return -1;
    }
    function showTip(idx, px, py) {
      if (idx < 0) { tip.style.display = 'none'; return; }
      var b = T.boxes[idx], s = T.stops.filter(function (x) { return x.seq === b[6]; })[0] || {};
      tip.innerHTML = '<b style="color:' + stopColor(b[6]) + '">■</b> <b>' + esc(b[10] || b[8]) + '</b> · ' + esc((T.desc && T.desc[b[8]]) || b[8]) +
        '<br><span class="lp-muted">Stop ' + b[6] + ' · ' + esc(s.name || '') + '</span><br>' +
        Math.round(b[3]) + '×' + Math.round(b[4]) + '×' + Math.round(b[5]) + ' cm · ' + (b[9] || '?') + ' kg' + (b[7] ? ' · <span class="bad">FRAGILE</span>' : '') +
        '<br>Load step ' + (idx + 1) + ' · ' + where(b);
      tip.style.display = 'block';
      tip.style.left = Math.min(px + 14, S.W - tip.offsetWidth - 6) + 'px'; tip.style.top = Math.max(6, Math.min(py + 14, S.H - tip.offsetHeight - 6)) + 'px';
    }
    var drag = null;
    cv.addEventListener('pointerdown', function (e) { drag = [e.clientX, e.clientY, yaw, pitch, false]; try { cv.setPointerCapture(e.pointerId); } catch (x) { /* host */ } });
    cv.addEventListener('pointermove', function (e) {
      var r = cv.getBoundingClientRect(); mouse = [e.clientX - r.left, e.clientY - r.top];
      if (!drag) { hoverIdx = T ? hitBox(mouse[0], mouse[1]) : -1; cv.style.cursor = hoverIdx >= 0 ? 'pointer' : 'grab'; if (pinIdx < 0) showTip(hoverIdx, mouse[0], mouse[1]); return; }
      if (Math.abs(e.clientX - drag[0]) + Math.abs(e.clientY - drag[1]) > 4) drag[4] = true;
      if (!drag[4]) return;
      yaw = drag[2] - (e.clientX - drag[0]) * 0.008;
      pitch = Math.max(0.12, Math.min(1.3, drag[3] + (e.clientY - drag[1]) * 0.006));
    });
    cv.addEventListener('pointerup', function (e) {
      if (drag && !drag[4] && T) {
        var r = cv.getBoundingClientRect(), idx = hitBox(e.clientX - r.left, e.clientY - r.top);
        if (idx >= 0) { var sq = T.boxes[idx][6]; if (focusSeq !== sq) setFocus(sq); pinIdx = idx; showTip(idx, e.clientX - r.left, e.clientY - r.top); }
        else { setFocus(null); }
      }
      drag = null;
    });
    cv.addEventListener('pointerleave', function () { hoverIdx = -1; if (pinIdx < 0) tip.style.display = 'none'; });
    cv.addEventListener('wheel', function (e) { e.preventDefault(); zoom = Math.max(0.5, Math.min(2.5, zoom * (e.deltaY < 0 ? 1.1 : 0.9))); }, { passive: false });

    var B;
    function basis() {
      var cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
      return { v: [cp * cy, cp * sy, sp], r: [-sy, cy, 0], u: [-sp * cy, -sp * sy, cp] };
    }
    function P(x, y, z) {
      var px = x - T.L / 2, py = y - T.W / 2, pz = z - T.H / 2;
      return [ox + (px * B.r[0] + py * B.r[1]) * scale, oy - (px * B.u[0] + py * B.u[1] + pz * B.u[2]) * scale];
    }
    function depth(x, y, z) { return (x - T.L / 2) * B.v[0] + (y - T.W / 2) * B.v[1] + (z - T.H / 2) * B.v[2]; }
    function fitScale() {
      var diag = Math.sqrt(T.L * T.L + T.W * T.W + T.H * T.H);
      scale = Math.min(S.W, S.H * 1.6) / diag * 0.78 * zoom; ox = S.W / 2; oy = S.H / 2 + 10;
    }
    function quad(pts, fill, stroke, alpha) {
      ctx.globalAlpha = alpha == null ? 1 : alpha; ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]); for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.closePath(); if (fill) { ctx.fillStyle = fill; ctx.fill(); }
      if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 0.8; ctx.stroke(); } ctx.globalAlpha = 1;
    }
    function drawBox(x, y, z, l, w, h, col, alpha, glow, idx, outline) {
      var x2 = x + l, y2 = y + w, z2 = z + h, V = B.v, faces = [];
      if (V[0] > 0) faces.push([[x2, y, z], [x2, y2, z], [x2, y2, z2], [x2, y, z2], 0.82]);
      else faces.push([[x, y, z], [x, y2, z], [x, y2, z2], [x, y, z2], 0.82]);
      if (V[1] > 0) faces.push([[x, y2, z], [x2, y2, z], [x2, y2, z2], [x, y2, z2], 0.66]);
      else faces.push([[x, y, z], [x2, y, z], [x2, y, z2], [x, y, z2], 0.66]);
      faces.push([[x, y, z2], [x2, y, z2], [x2, y2, z2], [x, y2, z2], 1.0]);  // top last
      if (glow) { ctx.shadowColor = col; ctx.shadowBlur = 18; }
      for (var i = 0; i < faces.length; i++) {
        var f = faces[i], pts = [P.apply(null, f[0]), P.apply(null, f[1]), P.apply(null, f[2]), P.apply(null, f[3])];
        quad(pts, shade(col, f[4]), outline || 'rgba(0,0,0,0.35)', alpha);
        if (idx != null && idx >= 0) polys.push([idx, pts]);
      }
      ctx.shadowBlur = 0;
    }
    /* Painter order for axis-aligned boxes: build "a is behind b" edges from any separating axis
       (valid for orthographic views) between boxes whose screen footprints overlap, then Kahn-sort. */
    function orderItems(items) {
      var n = items.length, A = new Array(n), V = B.v, i, j;
      for (i = 0; i < n; i++) {
        var b = items[i][0], x0 = b[0] + items[i][2], z0 = b[2] + items[i][3];
        var o = { x0: x0, x1: x0 + b[3], y0: b[1], y1: b[1] + b[4], z0: z0, z1: z0 + b[5], i: i };
        var xs = [o.x0, o.x1], ys = [o.y0, o.y1], zs = [o.z0, o.z1], mnx = 1e9, mxx = -1e9, mny = 1e9, mxy = -1e9;
        for (var a = 0; a < 2; a++) for (var c = 0; c < 2; c++) for (var d = 0; d < 2; d++) {
          var p = P(xs[a], ys[c], zs[d]);
          if (p[0] < mnx) mnx = p[0]; if (p[0] > mxx) mxx = p[0]; if (p[1] < mny) mny = p[1]; if (p[1] > mxy) mxy = p[1];
        }
        o.sx0 = mnx; o.sx1 = mxx; o.sy0 = mny; o.sy1 = mxy;
        o.dep = depth((o.x0 + o.x1) / 2, (o.y0 + o.y1) / 2, (o.z0 + o.z1) / 2);
        A[i] = o;
      }
      var eps = 0.5, indeg = new Array(n).fill(0), adj = new Array(n);
      for (i = 0; i < n; i++) adj[i] = [];
      function behind(p, q) {  // true => p drawn before q
        if (p.x1 <= q.x0 + eps) return V[0] >= 0; if (q.x1 <= p.x0 + eps) return V[0] < 0;
        if (p.y1 <= q.y0 + eps) return V[1] >= 0; if (q.y1 <= p.y0 + eps) return V[1] < 0;
        if (p.z1 <= q.z0 + eps) return V[2] >= 0; if (q.z1 <= p.z0 + eps) return V[2] < 0;
        return p.dep < q.dep;
      }
      for (i = 0; i < n; i++) {
        var p1 = A[i];
        for (j = i + 1; j < n; j++) {
          var q1 = A[j];
          if (p1.sx1 <= q1.sx0 || q1.sx1 <= p1.sx0 || p1.sy1 <= q1.sy0 || q1.sy1 <= p1.sy0) continue;
          if (behind(p1, q1)) { adj[i].push(j); indeg[j]++; } else { adj[j].push(i); indeg[i]++; }
        }
      }
      var queue = [], out = [], used = new Array(n).fill(false);
      for (i = 0; i < n; i++) if (!indeg[i]) queue.push(i);
      queue.sort(function (a1, b1) { return A[a1].dep - A[b1].dep; });
      while (out.length < n) {
        if (!queue.length) {  // cycle (only possible with the moving carton) — break by depth
          var best = -1; for (i = 0; i < n; i++) if (!used[i] && (best < 0 || A[i].dep < A[best].dep)) best = i;
          indeg[best] = 0; queue.push(best);
        }
        var k = queue.shift(); if (used[k]) continue; used[k] = true; out.push(items[k]);
        for (j = 0; j < adj[k].length; j++) { var m = adj[k][j]; if (--indeg[m] === 0 && !used[m]) queue.push(m); }
      }
      return out;
    }
    var EDGES = function () {
      var L = T.L, Wd = T.W, Hh = T.H;
      return [[[0, 0, Hh], [L, 0, Hh]], [[0, Wd, Hh], [L, Wd, Hh]], [[L, 0, 0], [L, 0, Hh]], [[L, Wd, 0], [L, Wd, Hh]],
              [[L, 0, Hh], [L, Wd, Hh]], [[0, 0, Hh], [0, Wd, Hh]], [[0, 0, 0], [0, 0, Hh]], [[0, Wd, 0], [0, Wd, Hh]],
              [[0, 0, 0], [L, 0, 0]], [[0, Wd, 0], [L, Wd, 0]], [[L, 0, 0], [L, Wd, 0]], [[0, 0, 0], [0, Wd, 0]]];
    };
    function drawEdges(near) {
      var c = depth(T.L / 2, T.W / 2, T.H / 2);
      ctx.strokeStyle = near ? 'rgba(138,180,248,0.55)' : 'rgba(138,180,248,0.22)'; ctx.lineWidth = near ? 1.2 : 1;
      EDGES().forEach(function (s) {
        var m = depth((s[0][0] + s[1][0]) / 2, (s[0][1] + s[1][1]) / 2, (s[0][2] + s[1][2]) / 2);
        if ((m > c + 1) !== near) return;
        var a = P.apply(null, s[0]), b = P.apply(null, s[1]); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      });
    }
    function drawShell() {
      var L = T.L, Wd = T.W, Hh = T.H;
      quad([P(0, 0, 0), P(L, 0, 0), P(L, Wd, 0), P(0, Wd, 0)], '#1b2336', null, 1);
      (T.zones || []).forEach(function (zn) {
        quad([P(zn[1], 0, 0), P(zn[2], 0, 0), P(zn[2], Wd, 0), P(zn[1], Wd, 0)], stopColor(zn[0]), null, 0.12);
      });
      ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 1;
      for (var gx = 0; gx <= L; gx += 50) { var a = P(gx, 0, 0), b = P(gx, Wd, 0); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }
      // far walls only (translucent); near walls stay open so cartons remain visible
      var backY = B.v[1] > 0 ? 0 : Wd;
      quad([P(0, backY, 0), P(L, backY, 0), P(L, backY, Hh), P(0, backY, Hh)], '#2a3550', 'rgba(140,170,255,0.25)', 0.3);
      if (B.v[0] > 0) quad([P(0, 0, 0), P(0, Wd, 0), P(0, Wd, Hh), P(0, 0, Hh)], '#33415f', 'rgba(140,170,255,0.35)', 0.5);
      drawEdges(false);
    }
    function label(p, s, c) { ctx.font = '600 11px Inter,Roboto,Arial'; ctx.fillStyle = c; ctx.textAlign = 'center'; ctx.fillText(s, p[0], p[1]); }

    function frame(now) {
      if (!T || !S.fit()) return;
      var dt = last == null ? 0 : Math.min(0.05, (now - last) / 1000); last = now;
      var N = T.boxes.length, perBox = 0.22;
      if (playing) t += dt * speed / perBox;
      var hudTxt = '', cur = null;
      B = basis(); fitScale();
      ctx.clearRect(0, 0, S.W, S.H);
      var g = ctx.createRadialGradient(S.W / 2, S.H / 2, 20, S.W / 2, S.H / 2, Math.max(S.W, S.H) * 0.7);
      g.addColorStop(0, '#16203a'); g.addColorStop(1, '#070b16'); ctx.fillStyle = g; ctx.fillRect(0, 0, S.W, S.H);
      drawShell();
      var items = [];
      if (mode === 'load') {
        if (t > N + 6) { t = playing ? 0 : N; }
        var k = Math.min(N, Math.floor(t)), frac = t - Math.floor(t);
        for (var i = 0; i < k && i < N; i++) items.push([T.boxes[i], 1, 0, 0]);
        if (k < N) {
          var b = T.boxes[k], e = easeOut(Math.min(1, frac * 1.15));
          var dx = (T.L + 90 - b[0]) * (1 - e), dz = 60 * (1 - e) * (1 - e);
          items.push([b, 1, dx, dz, true]); cur = b;
          hudTxt = 'Loading carton <b>' + (k + 1) + '</b> / ' + N + ' &middot; stop <b>' + b[6] + '</b> &middot; ' + esc(b[8]);
        } else hudTxt = '<span class="ok">&#10003; Loaded</span> ' + N + ' cartons &middot; stop 1 sits at the door';
        scrub.value = Math.min(N, Math.floor(t));
        banner.style.opacity = 0;
      } else {
        var nS = T.stops.length, per = 3.2;
        var sT = t * perBox / per, sIdx = Math.floor(sT), sf = sT - sIdx;
        if (sIdx >= nS + 1) { t = 0; sIdx = 0; sf = 0; }
        for (var j = 0; j < N; j++) {
          var bx = T.boxes[j], sq = bx[6];
          if (sq <= sIdx) continue;
          if (sq === sIdx + 1) {
            var ee = easeOut(Math.min(1, Math.max(0, (sf - 0.25) / 0.6)));
            items.push([bx, 1 - ee, (T.L + 140 - bx[0]) * ee, 0, ee > 0 && ee < 1]);
          } else items.push([bx, 1, 0, 0]);
        }
        var st = T.stops[Math.min(sIdx, nS - 1)];
        if (sIdx < nS) {
          banner.innerHTML = '<i style="background:' + stopColor(st.seq) + '"></i> Stop ' + st.seq + ' &middot; ' + esc(st.name) +
            ' <span class="lp-muted">ETA ' + st.eta + ' &middot; ' + st.n + ' cartons out first, nothing to dig</span>';
          banner.style.opacity = 1; hudTxt = 'Unload replay &middot; stop <b>' + st.seq + '</b> of ' + nS; cur = [0, 0, 0, 0, 0, 0, st.seq];
        } else { banner.style.opacity = 0; hudTxt = '<span class="ok">&#10003; All ' + nS + ' deliveries done</span>'; }
      }
      items = orderItems(items.filter(function (it) { return it[1] > 0.02; }));
      polys = [];
      for (var m = 0; m < items.length; m++) {
        var it = items[m], bb = it[0], bi = T.boxes.indexOf(bb), a = it[1];
        var isF = focusSeq == null || bb[6] === focusSeq;
        if (!isF) a = Math.min(a, 0.1);
        var hl = bi >= 0 && (bi === pinIdx || bi === hoverIdx);
        drawBox(bb[0] + it[2], bb[1], bb[2] + it[3], bb[3], bb[4], bb[5], stopColor(bb[6]), a,
                it[4] || (focusSeq != null && isF && hl), isF && a > 0.5 && !it[4] ? bi : -1, hl ? '#ffffff' : null);
        if (bb[7] && a > 0.9) { var c = P(bb[0] + it[2] + bb[3] / 2, bb[1] + bb[4] / 2, bb[2] + it[3] + bb[5]); label(c, '!', '#fff'); }
      }
      if (focusSeq != null) {  // floor footprint of the focused store
        var fo = stopInfo(focusSeq);
        if (fo.n) {
          ctx.setLineDash([5, 4]); quad([P(fo.x0, fo.y0, 0.5), P(fo.x1, fo.y0, 0.5), P(fo.x1, fo.y1, 0.5), P(fo.x0, fo.y1, 0.5)], null, '#ffffff', 0.9); ctx.setLineDash([]);
          var lp = P((fo.x0 + fo.x1) / 2, (fo.y0 + fo.y1) / 2, fo.z1 + 18);
          label(lp, 'Stop ' + focusSeq + ' · ' + Math.max(0, Math.round(T.L - fo.x1)) + '–' + Math.round(T.L - fo.x0) + ' cm from door', '#ffffff');
        }
      }
      drawEdges(true);
      label(P(0, T.W / 2, T.H + 14), 'CAB', '#8ab4f8');
      label(P(T.L + 28, T.W / 2, 0), 'REAR DOOR', '#fdd663');
      hud.innerHTML = hudTxt;
      Array.prototype.forEach.call(legend.querySelectorAll('.lp-li'), function (r) {
        r.classList.toggle('on', !!cur && +r.dataset.seq === cur[6]);
      });
    }
    this.frame = frame;
    if (trucks.length) pick(0);
  }

  /* ============================== ROUTE MAP VIEW ============================== */
  function decode(arr, sc) {  // delta-int [a0,b0,da,db,...] -> [[a,b],...]
    var out = [], a = 0, b = 0;
    for (var i = 0; i + 1 < arr.length; i += 2) { a += arr[i]; b += arr[i + 1]; out.push([a / sc, b / sc]); }
    return out;
  }
  function mx(lon) { return (lon + 180) / 360; }
  function my(lat) { var s = Math.sin(lat * Math.PI / 180); return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI); }

  function MapView(host) {
    var el = $('div', 'lp-pane', host); this.el = el;
    var top = $('div', 'lp-top', el);
    $('div', 'lp-title', top, D.driver ? '<b>Your route today</b> &middot; ' + esc(D.driver.name) + ' · ' + esc(D.driver.id) +
      ' <span class="lp-muted">click a numbered stop, then “Where are these cartons?”</span>' :
      '<b>Delivery route map</b> &middot; ' + esc(D.hub ? D.hub.name : '') +
      ' <span class="lp-muted">click a numbered stop or a truck</span>');
    var kpis = $('div', 'lp-stats', top);
    var body = $('div', 'lp-body', el);
    var cwrap = $('div', 'lp-cwrap', body), cv = $('canvas', 'lp-canvas', cwrap), ctx = cv.getContext('2d');
    var clock = $('div', 'lp-clock', cwrap), hud = $('div', 'lp-hud', cwrap);
    var pop = $('div', 'lp-pop', cwrap); pop.style.display = 'none';
    var zbox = $('div', 'lp-zoom', cwrap);
    var zin = $('button', '', zbox, '+'), zout = $('button', '', zbox, '&minus;'), zfit = $('button', '', zbox, '&#9974;');
    zfit.title = 'Fit all';
    var attr = $('div', 'lp-attr', cwrap);
    var legend = $('div', 'lp-legend', body);
    var ctr = $('div', 'lp-ctrl', el);
    var tog = $('div', 'lp-seg', ctr);
    var bOpt = $('button', 'on', tog, 'LoadPilot plan'), bBase = $('button', '', tog, 'Today (manual)');
    var play = $('button', 'lp-btn lp-play', ctr, '&#10074;&#10074;');
    var spd = $('button', 'lp-btn', ctr, '2x');
    var scrub = $('input', 'lp-scrub', ctr); scrub.type = 'range';
    var S = autoSize(cwrap, cv, ctx, function () { if (!fitted) fitAll(); });

    var set = 'opt', playing = true, speed = 2, last = null, sel = -1, hover = null, popStop = null, fitted = false;
    var R = D.routes || { opt: [], base: [] };
    var t0 = D.clock ? D.clock[0] : 420, t1 = D.clock ? D.clock[1] : 1140, t = t0;
    scrub.min = t0; scrub.max = t1; scrub.value = t0;
    var hub = D.hub || { lat: 19, lon: 73, name: 'Hub' }, HX = mx(hub.lon), HY = my(hub.lat);

    /* ---- precompute mercator geometry ---- */
    ['opt', 'base'].forEach(function (k) {
      (R[k] || []).forEach(function (r) {
        r.L = (r.legs || []).map(function (enc) {
          var pts = decode(enc, 1e5).map(function (p) { return [mx(p[1]), my(p[0])]; });
          var cum = [0]; for (var i = 1; i < pts.length; i++) cum.push(cum[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
          return { p: pts, c: cum };
        });
        r.stops.forEach(function (s) { s.X = mx(s.lon); s.Y = my(s.lat); });
        // leg time windows: leg0 start->arr1, legi dep(i)->arr(i+1), last dep(n)->end
        var tw = [], prev = r.start;
        r.stops.forEach(function (s) { tw.push([prev, s.arr]); prev = s.dep; });
        tw.push([prev, r.end]); r.tw = tw;
      });
    });
    var BM = null;
    if (D.basemap) {
      BM = {};
      ['coast', 'motorway', 'trunk', 'primary', 'rail'].forEach(function (k) {
        BM[k] = (D.basemap[k] || []).map(function (a) {
          return decode(a, D.basemap.scale || 1e4).map(function (p) { return [mx(p[0]), my(p[1])]; });
        });
      });
    }
    var places = (D.places || []).map(function (p) { return [p[0], mx(p[2]), my(p[1])]; });

    /* ---- view state: centre (mercator 0..1) + zoom ---- */
    var cx = HX, cy = HY, z = 10;
    function wsz() { return 256 * Math.pow(2, z); }
    function sp(X, Y) { var s = wsz(); return [(X - cx) * s + S.W / 2, (Y - cy) * s + S.H / 2]; }
    function inv(px, py) { var s = wsz(); return [cx + (px - S.W / 2) / s, cy + (py - S.H / 2) / s]; }
    function fitBox(x0, y0, x1, y1) {
      if (!S.W) return; cx = (x0 + x1) / 2; cy = (y0 + y1) / 2;
      var dx = Math.max(1e-6, x1 - x0), dy = Math.max(1e-6, y1 - y0);
      z = Math.log2(Math.min((S.W - 70) / (dx * 256), (S.H - 70) / (dy * 256)));
      z = Math.max(4, Math.min(16, z)); fitted = true;
    }
    function boundsOf(routes) {
      var x0 = HX, x1 = HX, y0 = HY, y1 = HY;
      routes.forEach(function (r) { r.L.forEach(function (lg) { lg.p.forEach(function (p) {
        if (p[0] < x0) x0 = p[0]; if (p[0] > x1) x1 = p[0]; if (p[1] < y0) y0 = p[1]; if (p[1] > y1) y1 = p[1]; }); }); });
      return [x0, y0, x1, y1];
    }
    function fitAll() { var b = boundsOf(R[set] || []); fitBox(b[0], b[1], b[2], b[3]); }
    function zoomAt(f, px, py) {
      var a = inv(px, py); z = Math.max(4, Math.min(17, z + f)); var b = inv(px, py); cx += a[0] - b[0]; cy += a[1] - b[1];
    }
    zin.onclick = function () { zoomAt(0.7, S.W / 2, S.H / 2); };
    zout.onclick = function () { zoomAt(-0.7, S.W / 2, S.H / 2); };
    zfit.onclick = function () { sel = -1; closePop(); buildLegend(); fitAll(); };

    /* ---- tiles (full-screen page / permissive hosts); vector basemap otherwise ---- */
    var tileCache = {}, tileOk = 0, tileFail = 0, tilesOn = !!D.tiles;
    function tile(zi, x, y, url) {
      url = url || D.tiles;
      var n = Math.pow(2, zi), xx = ((x % n) + n) % n, key = url.length + ':' + zi + '/' + xx + '/' + y;
      var im = tileCache[key]; if (im) return im.ok ? im : null;
      if (!tilesOn) return null;
      im = new Image(); im.ok = false; tileCache[key] = im;
      im.onload = function () { im.ok = true; tileOk++; };
      im.onerror = function () { tileFail++; if (!tileOk && tileFail > 4) tilesOn = false; };
      im.src = url.replace('{s}', 'abcd'[(xx + y) % 4]).replace('{z}', zi).replace('{x}', xx).replace('{y}', y);
      return null;
    }
    function drawTiles(url) {
      var zi = Math.max(3, Math.min(18, Math.round(z))), ts = 256 * Math.pow(2, z - zi), n = Math.pow(2, zi);
      var tl = inv(0, 0), br = inv(S.W, S.H), drew = 0;
      for (var x = Math.floor(tl[0] * n); x <= Math.floor(br[0] * n); x++) {
        for (var y = Math.max(0, Math.floor(tl[1] * n)); y <= Math.min(n - 1, Math.floor(br[1] * n)); y++) {
          var im = tile(zi, x, y, url), p = sp(x / n, y / n);
          if (im) { ctx.drawImage(im, p[0], p[1], ts + 0.5, ts + 0.5); drew++; }
          else if (!url) {  // fall back to a parent tile while loading
            var pz = zi - 1, pim = pz >= 3 ? tile(pz, x >> 1, y >> 1) : null;
            if (pim) { var sx = (x & 1) * 128, sy = (y & 1) * 128; ctx.drawImage(pim, sx, sy, 128, 128, p[0], p[1], ts + 0.5, ts + 0.5); drew++; }
          }
        }
      }
      return drew;
    }
    var BMS = { coast: ['rgba(79,195,247,0.55)', 1.6], rail: ['rgba(176,190,197,0.25)', 1], primary: ['rgba(176,190,197,0.30)', 1],
                trunk: ['rgba(255,202,40,0.40)', 1.6], motorway: ['rgba(255,167,38,0.60)', 2.2] };
    function drawVectorBase() {
      if (!BM) return;
      ['rail', 'primary', 'trunk', 'motorway', 'coast'].forEach(function (k) {
        ctx.strokeStyle = BMS[k][0]; ctx.lineWidth = BMS[k][1] * (z > 11 ? 1.3 : 1); ctx.beginPath();
        BM[k].forEach(function (line) {
          for (var i = 0; i < line.length; i++) { var q = sp(line[i][0], line[i][1]); if (i) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); }
        });
        ctx.stroke();
      });
      ctx.font = '600 11px Inter,Roboto,Arial'; ctx.textAlign = 'left';
      places.forEach(function (pl) {
        var q = sp(pl[1], pl[2]); if (q[0] < -50 || q[1] < -20 || q[0] > S.W + 50 || q[1] > S.H + 20) return;
        ctx.fillStyle = 'rgba(0,0,0,0.55)'; ctx.fillText(pl[0], q[0] + 5, q[1] - 3);
        ctx.fillStyle = 'rgba(232,234,237,0.62)'; ctx.fillText(pl[0], q[0] + 4, q[1] - 4);
      });
    }

    /* ---- truck position along road geometry ---- */
    function posAt(r, tm) {
      if (!r.L.length) return { X: HX, Y: HY, leg: 0, f: 0, at: -1 };
      if (tm <= r.tw[0][0]) return { X: HX, Y: HY, leg: 0, f: 0, at: -1 };
      for (var i = 0; i < r.tw.length; i++) {
        var w = r.tw[i];
        if (tm < w[0]) { var s = r.stops[i - 1]; return { X: s.X, Y: s.Y, leg: i, f: 0, at: i - 1 }; }  // dwelling
        if (tm <= w[1]) {
          var lg = r.L[i], f = (tm - w[0]) / Math.max(1, w[1] - w[0]), target = f * lg.c[lg.c.length - 1];
          for (var k = 1; k < lg.p.length; k++) if (lg.c[k] >= target) {
            var u = (target - lg.c[k - 1]) / Math.max(1e-12, lg.c[k] - lg.c[k - 1]);
            return { X: lg.p[k - 1][0] + (lg.p[k][0] - lg.p[k - 1][0]) * u, Y: lg.p[k - 1][1] + (lg.p[k][1] - lg.p[k - 1][1]) * u, leg: i, f: f, k: k };
          }
          return { X: lg.p[lg.p.length - 1][0], Y: lg.p[lg.p.length - 1][1], leg: i, f: 1 };
        }
      }
      return { X: HX, Y: HY, leg: r.L.length, f: 1, at: -2 };
    }
    function pathLeg(lg, upto) {  // stroke leg points (optionally up to a partial position)
      for (var i = 0; i < lg.p.length; i++) {
        if (upto && i >= upto.k) { var q0 = sp(upto.X, upto.Y); ctx.lineTo(q0[0], q0[1]); return; }
        var q = sp(lg.p[i][0], lg.p[i][1]); if (i) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]);
      }
    }

    /* ---- legend / KPIs ---- */
    function kv(k, v) { return '<div class="kv"><span>' + k + '</span><b>' + v + '</b></div>'; }
    (function () {
      var K = D.kpi || {}, a = K.base || {}, b = K.opt || {};
      if (D.driver) {
        var dv = D.driver;
        kpis.innerHTML = kv('Drops', dv.stops) + kv('Cartons', dv.cartons) + kv('Road km', dv.km) + kv('Shift', dv.start + '–' + dv.end);
        sel = 0; tog.style.display = 'none';
        return;
      }
      kpis.innerHTML = kv('Trucks', a.trucks + ' &rarr; <span class="ok">' + b.trucks + '</span>') +
        kv('Road km', a.km + ' &rarr; <span class="ok">' + b.km + '</span>') +
        kv('Cost / day', a.cost + ' &rarr; <span class="ok">' + b.cost + '</span>') +
        kv('Saved', '<span class="ok">' + (K.saved || '') + '</span>');
    })();
    function buildLegend() {
      var routes = R[set] || [];
      legend.innerHTML = '';
      var h = $('div', 'lp-lh', legend, set === 'opt' ? 'LoadPilot trucks' : 'Today: one truck per sales area');
      var all = $('div', 'lp-li' + (sel < 0 ? ' on' : ''), legend, '<i style="background:#fdd663"></i><b>All trucks</b> <span class="lp-muted">' + routes.length + ' routes</span>');
      all.onclick = function () { sel = -1; closePop(); buildLegend(); fitAll(); };
      routes.forEach(function (r, i) {
        var row = $('div', 'lp-li lp-click' + (sel === i ? ' on' : ''), legend, '<i style="background:' + r.color + '"></i><div><b>' + esc(r.id) +
          '</b> ' + esc(r.driver) + '<br><span class="lp-muted">' + esc(r.cname || r.corridor) + (r.branch && r.branch !== 'solo' && r.branch !== 'area' ? ' · ' + esc(r.branch) : '') +
          ' · ' + r.stops.length + ' drops · ' + r.km + ' km · ' + fmtT(r.start) + '–' + fmtT(r.end) + '</span></div>');
        row.onclick = function () { focus(i); };
      });
      if (sel >= 0 && routes[sel]) {
        var r = routes[sel];
        $('div', 'lp-lh', legend, 'Drop sequence · ' + esc(r.id));
        $('div', 'lp-li', legend, '<span class="lp-num" style="background:#fdd663;color:#111">H</span><div>' + esc(hub.name) + ' <span class="lp-muted">depart ' + fmtT(r.start) + '</span></div>');
        r.stops.forEach(function (s) {
          var row = $('div', 'lp-li lp-click', legend, '<span class="lp-num" style="background:' + r.color + '">' + s.seq + '</span><div>' + esc(s.name) +
            '<br><span class="lp-muted">' + esc(s.area || '') + ' · ETA ' + fmtT(s.arr) + ' · ' + s.n + ' ctn</span></div>');
          row.onclick = function () { openPop(r, s, true); };
        });
        $('div', 'lp-li', legend, '<span class="lp-num" style="background:#fdd663;color:#111">H</span><div>Back at hub <span class="lp-muted">' + fmtT(r.end) + '</span></div>');
      }
      void h;
    }
    function focus(i) {
      sel = sel === i ? -1 : i; closePop(); buildLegend();
      if (sel >= 0) { var b = boundsOf([R[set][sel]]); fitBox(b[0], b[1], b[2], b[3]); } else fitAll();
    }
    function openPop(r, s, pan) {
      popStop = [r, s];
      if (pan) { cx = s.X; cy = s.Y; if (z < 12) z = 12.5; }
      var win = s.win ? fmtT(s.win[0]) + '–' + fmtT(s.win[1]) : '';
      pop.innerHTML = '<div class="lp-pop-h" style="border-color:' + r.color + '"><span class="lp-num" style="background:' + r.color + '">' + s.seq + '</span>' +
        '<div><b>' + esc(s.name) + '</b><br><span class="lp-muted">' + esc(s.addr || s.area || '') + '</span></div><button class="lp-x">&times;</button></div>' +
        '<div class="lp-pop-g">' +
        '<span>Truck</span><b>' + esc(r.id) + ' · ' + esc(r.driver) + '</b>' +
        '<span>Drop</span><b>' + s.seq + ' of ' + r.stops.length + (s.seq === 1 ? ' · first off, at the door' : s.seq === r.stops.length ? ' · last, behind the cab' : '') + '</b>' +
        '<span>ETA</span><b>' + fmtT(s.arr) + ' → leaves ' + fmtT(s.dep) + '</b>' +
        (win ? '<span>Window</span><b>' + win + '</b>' : '') +
        '<span>Cartons</span><b>' + s.n + (s.kg ? ' · ' + s.kg + ' kg' : '') + (s.frag ? ' · ' + s.frag + ' fragile' : '') + '</b>' +
        (s.skus ? '<span>Goods</span><b>' + esc(s.skus) + '</b>' : '') +
        '</div>' + (window.LPgoLoad && set === 'opt' ? '<button class="lp-go">📦 Where are these cartons in the truck?</button>' : '');
      pop.style.display = 'block';
      pop.querySelector('.lp-x').onclick = closePop;
      var go = pop.querySelector('.lp-go'); if (go) go.onclick = function () { window.LPgoLoad(r.id, s.seq); };
    }
    function closePop() { popStop = null; pop.style.display = 'none'; }
    function setMode(k) {
      set = k; bOpt.className = k === 'opt' ? 'on' : ''; bBase.className = k === 'base' ? 'on' : '';
      sel = -1; closePop(); t = t0; buildLegend(); fitAll();
    }
    bOpt.onclick = function () { setMode('opt'); };
    bBase.onclick = function () { setMode('base'); };
    play.onclick = function () { playing = !playing; play.innerHTML = playing ? '&#10074;&#10074;' : '&#9654;'; };
    spd.onclick = function () { speed = speed >= 16 ? 1 : speed * 2; spd.textContent = speed + 'x'; };
    scrub.oninput = function () { t = +scrub.value; };
    buildLegend();

    /* ---- interaction: drag to pan, wheel to zoom, click to pick ---- */
    var drag = null;
    function hit(px, py) {
      var routes = R[set] || [], best = null, bd = 13 * 13;
      routes.forEach(function (r, i) {
        if (sel >= 0 && sel !== i) return;
        r.stops.forEach(function (s) { var q = sp(s.X, s.Y), d = (q[0] - px) * (q[0] - px) + (q[1] - py) * (q[1] - py); if (d < bd) { bd = d; best = { r: r, s: s, i: i }; } });
      });
      if (best) return best;
      routes.forEach(function (r, i) {
        var p = posAt(r, t), q = sp(p.X, p.Y), d = (q[0] - px) * (q[0] - px) + (q[1] - py) * (q[1] - py);
        if (d < 14 * 14) { best = { r: r, i: i, truck: true }; }
      });
      return best;
    }
    cv.addEventListener('pointerdown', function (e) {
      var r = cv.getBoundingClientRect(); drag = { x: e.clientX, y: e.clientY, cx: cx, cy: cy, moved: false, ox: r.left, oy: r.top };
      try { cv.setPointerCapture(e.pointerId); } catch (x) { /* host */ }
    });
    cv.addEventListener('pointermove', function (e) {
      var r = cv.getBoundingClientRect();
      if (drag) {
        var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 4) drag.moved = true;
        if (drag.moved) { var s = wsz(); cx = drag.cx - dx / s; cy = drag.cy - dy / s; }
        return;
      }
      hover = hit(e.clientX - r.left, e.clientY - r.top); cv.style.cursor = hover ? 'pointer' : 'grab';
    });
    cv.addEventListener('pointerup', function (e) {
      if (drag && !drag.moved) {
        var h = hit(e.clientX - drag.ox, e.clientY - drag.oy);
        if (!h) closePop(); else if (h.truck) focus(h.i); else openPop(h.r, h.s, false);
      }
      drag = null;
    });
    cv.addEventListener('wheel', function (e) {
      e.preventDefault(); var r = cv.getBoundingClientRect(); zoomAt(e.deltaY < 0 ? 0.35 : -0.35, e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });
    cv.addEventListener('dblclick', function (e) { var r = cv.getBoundingClientRect(); zoomAt(1, e.clientX - r.left, e.clientY - r.top); });

    function frame(now) {
      if (!S.fit()) return;
      if (!fitted) fitAll();
      var dt = last == null ? 0 : Math.min(0.05, (now - last) / 1000); last = now;
      if (playing) { t += dt * 6 * speed; if (t > t1 + 20) t = t0; }
      scrub.value = t;
      ctx.fillStyle = '#0b1020'; ctx.fillRect(0, 0, S.W, S.H);
      var drewTiles = tilesOn || tileOk ? drawTiles() : 0;
      if (!drewTiles) drawVectorBase(); else if (D.labels) drawTiles(D.labels);
      attr.innerHTML = (drewTiles ? esc(D.tileAttr || '© OpenStreetMap') : '© OpenStreetMap contributors') + (D.router ? ' · roads: ' + esc(D.router) : '');
      var routes = R[set] || [], delivered = 0, total = 0;
      ctx.lineJoin = 'round'; ctx.lineCap = 'round';
      routes.forEach(function (r, i) {
        var dim = sel >= 0 && sel !== i, pos = posAt(r, t);
        // planned road path
        ctx.globalAlpha = dim ? 0.12 : 0.5; ctx.strokeStyle = r.color; ctx.lineWidth = sel === i ? 4 : 2.2; ctx.setLineDash(sel === i ? [] : [6, 5]);
        ctx.beginPath(); r.L.forEach(function (lg) { pathLeg(lg); }); ctx.stroke(); ctx.setLineDash([]);
        // driven trail
        if (!dim) {
          ctx.globalAlpha = 1; ctx.shadowColor = r.color; ctx.shadowBlur = 8; ctx.lineWidth = sel === i ? 5 : 3.2; ctx.beginPath();
          for (var li = 0; li < r.L.length && li <= pos.leg; li++) pathLeg(r.L[li], li === pos.leg && pos.k ? pos : null);
          ctx.stroke(); ctx.shadowBlur = 0;
        }
        // stops
        var big = z >= 10.5 || sel === i;
        r.stops.forEach(function (s) {
          var q = sp(s.X, s.Y), done = t >= s.arr; total++; if (done) delivered++;
          if (q[0] < -20 || q[1] < -20 || q[0] > S.W + 20 || q[1] > S.H + 20) return;
          ctx.globalAlpha = dim ? 0.18 : 1;
          var rad = big ? 8.5 : 4.5, isPop = popStop && popStop[1] === s;
          ctx.beginPath(); ctx.arc(q[0], q[1], isPop ? rad + 3 : rad, 0, Math.PI * 2);
          ctx.fillStyle = done ? r.color : '#0b1020'; ctx.fill(); ctx.strokeStyle = isPop ? '#fff' : r.color; ctx.lineWidth = isPop ? 2.5 : 1.8; ctx.stroke();
          if (big) { ctx.fillStyle = done ? '#0b1020' : '#fff'; ctx.font = '700 10px Inter,Roboto,Arial'; ctx.textAlign = 'center'; ctx.fillText(s.seq, q[0], q[1] + 3.5); }
          if (done && t - s.arr < 12 && !dim) { ctx.globalAlpha = (1 - (t - s.arr) / 12) * 0.9; ctx.beginPath(); ctx.arc(q[0], q[1], rad + (t - s.arr) * 1.5, 0, Math.PI * 2); ctx.stroke(); }
        });
        // truck marker
        var cp = sp(pos.X, pos.Y);
        ctx.globalAlpha = dim ? 0.25 : 1;
        ctx.beginPath(); ctx.arc(cp[0], cp[1], 9, 0, Math.PI * 2); ctx.fillStyle = r.color; ctx.fill(); ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke();
        ctx.font = '12px Arial'; ctx.textAlign = 'center'; ctx.fillStyle = '#fff'; ctx.fillText('🚚', cp[0], cp[1] + 4);
        if (!dim) {
          ctx.font = '700 11px Inter,Roboto,Arial'; ctx.textAlign = 'left'; var lbl = r.id;
          var w = ctx.measureText(lbl).width; ctx.fillStyle = 'rgba(8,12,24,0.85)'; ctx.fillRect(cp[0] + 11, cp[1] - 8, w + 8, 16);
          ctx.fillStyle = r.color; ctx.fillText(lbl, cp[0] + 15, cp[1] + 4);
        }
        ctx.globalAlpha = 1;
      });
      // hub
      var hp = sp(HX, HY), pulse = (now / 1000) % 1.6 / 1.6;
      ctx.beginPath(); ctx.arc(hp[0], hp[1], 10 + pulse * 20, 0, Math.PI * 2); ctx.strokeStyle = 'rgba(253,214,99,' + (1 - pulse) + ')'; ctx.lineWidth = 2; ctx.stroke();
      ctx.beginPath(); ctx.arc(hp[0], hp[1], 10, 0, Math.PI * 2); ctx.fillStyle = '#fdd663'; ctx.fill();
      ctx.fillStyle = '#111'; ctx.font = '700 11px Inter,Roboto,Arial'; ctx.textAlign = 'center'; ctx.fillText('H', hp[0], hp[1] + 4);
      ctx.font = '700 12px Inter,Roboto,Arial'; ctx.textAlign = 'left'; ctx.fillStyle = 'rgba(8,12,24,0.8)';
      var hn = hub.name || 'Hub', hw = ctx.measureText(hn).width; ctx.fillRect(hp[0] + 13, hp[1] - 9, hw + 8, 18);
      ctx.fillStyle = '#fdd663'; ctx.fillText(hn, hp[0] + 17, hp[1] + 4);
      // popup follows its stop
      if (popStop) {
        var q = sp(popStop[1].X, popStop[1].Y), pw = pop.offsetWidth, ph = pop.offsetHeight;
        var left = Math.min(Math.max(8, q[0] + 16), S.W - pw - 8), topp = Math.min(Math.max(8, q[1] - ph / 2), S.H - ph - 8);
        pop.style.left = left + 'px'; pop.style.top = topp + 'px';
      }
      clock.innerHTML = fmtT(t);
      hud.innerHTML = (set === 'opt' ? 'LoadPilot plan' : 'Today\'s manual plan') + ' &middot; delivered <b>' + delivered + '</b> / ' + total;
    }
    this.frame = frame;
  }

  if (MODE === 'both') window.LPgoLoad = function (id, seq) { show('load'); if (panes.load) panes.load.focusTruckStop(id, seq); };
  if (MODE === 'both' || MODE === 'routes') panes.routes = new MapView(root);
  if (MODE === 'both' || MODE === 'load') panes.load = new LoadView(root);
  show(MODE === 'load' || D.start === 'load' ? 'load' : 'routes');
  function loop(now) {
    Object.keys(panes).forEach(function (k) {
      if (panes[k].el.style.display !== 'none') { try { panes[k].frame(now); } catch (e) { if (window.console) console.error(e); } }
    });
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
})();
