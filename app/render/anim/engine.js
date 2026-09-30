/* LoadPilot animation engine — self-contained Canvas2D (no network, CSP-safe).
 * Views:
 *   load   : orbitable 3D truck; cartons slide in from the door in load order (last stop first),
 *            "Unload" replays deliveries stop by stop (door-side cartons leave first).
 *   routes : animated corridor map; trucks drive their routes on a clock, stops light up on
 *            delivery; toggle Today (manual) vs LoadPilot (optimised).
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

  var root = document.getElementById('lp-app');
  var tabs = null, panes = {};
  if (MODE === 'both') {
    tabs = $('div', 'lp-tabs', root);
    ['routes', 'load'].forEach(function (k) {
      var b = $('button', 'lp-tab', tabs, k === 'load' ? '3D Truck Loading' : 'Route Animation');
      b.onclick = function () { show(k); };
      b.dataset.k = k;
    });
  }
  function show(k) {
    Object.keys(panes).forEach(function (p) { panes[p].el.style.display = p === k ? 'flex' : 'none'; });
    if (tabs) Array.prototype.forEach.call(tabs.children, function (b) { b.classList.toggle('on', b.dataset.k === k); });
    if (panes[k]) panes[k].resize();
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

    var trucks = D.trucks || [], ti = 0, T = null;
    var yaw = 0.62, pitch = 0.52, zoom = 1, speed = 4, playing = true, mode = 'load';
    var t = 0, last = null, W = 0, H = 0, scale = 1, ox = 0, oy = 0;

    trucks.forEach(function (tr, i) {
      var b = $('button', 'lp-chip', sel, tr.id + ' <small>' + tr.driver + '</small>');
      b.style.borderColor = tr.color; b.onclick = function () { pick(i); };
    });
    function pick(i) {
      ti = i; T = trucks[i]; t = 0; mode = 'load'; modeB.textContent = 'Unload replay'; playing = true;
      play.innerHTML = '&#10074;&#10074;';
      Array.prototype.forEach.call(sel.children, function (b, k) { b.classList.toggle('on', k === i); });
      scrub.max = T.boxes.length; title.innerHTML = '<b>' + T.id + '</b> &middot; ' + T.name +
        ' <span class="lp-muted">(' + T.L + '&times;' + T.W + '&times;' + T.H + ' cm)</span>';
      stats.innerHTML = kv('Driver', T.driver) + kv('Corridor', T.corridor + ' &middot; ' + T.branch) +
        kv('Cartons', T.boxes.length) + kv('Volume fill', T.fill + '%') + kv('Payload', T.wfill + '%') +
        kv('LIFO check', T.lifo ? '<span class="ok">&#10003; pass</span>' : '<span class="bad">review</span>');
      legend.innerHTML = '<div class="lp-lh">Delivery order <span class="lp-muted">(1 = at the door)</span></div>';
      T.stops.forEach(function (s) {
        var r = $('div', 'lp-li', legend, '<i style="background:' + stopColor(s.seq) + '"></i><b>' + s.seq +
          '</b> ' + s.name + ' <span class="lp-muted">' + s.n + ' ctn &middot; ' + s.eta + '</span>');
        r.dataset.seq = s.seq;
      });
      self.resize();
    }
    function kv(k, v) { return '<div class="kv"><span>' + k + '</span><b>' + v + '</b></div>'; }

    play.onclick = function () { playing = !playing; play.innerHTML = playing ? '&#10074;&#10074;' : '&#9654;'; };
    spd.onclick = function () { speed = speed >= 16 ? 1 : speed * 2; spd.textContent = speed + 'x'; };
    modeB.onclick = function () {
      mode = mode === 'load' ? 'unload' : 'load'; t = 0; playing = true; play.innerHTML = '&#10074;&#10074;';
      modeB.textContent = mode === 'load' ? 'Unload replay' : 'Loading replay';
    };
    scrub.oninput = function () { playing = false; play.innerHTML = '&#9654;'; mode = 'load'; t = +scrub.value; };
    reset.onclick = function () { yaw = 0.62; pitch = 0.52; zoom = 1; self.resize(); };
    var drag = null;
    cv.addEventListener('pointerdown', function (e) { drag = [e.clientX, e.clientY, yaw, pitch]; cv.setPointerCapture(e.pointerId); });
    cv.addEventListener('pointermove', function (e) {
      if (!drag) return; yaw = drag[2] - (e.clientX - drag[0]) * 0.008;
      pitch = Math.max(0.12, Math.min(1.3, drag[3] + (e.clientY - drag[1]) * 0.006));
    });
    cv.addEventListener('pointerup', function () { drag = null; });
    cv.addEventListener('wheel', function (e) { e.preventDefault(); zoom = Math.max(0.5, Math.min(2.5, zoom * (e.deltaY < 0 ? 1.1 : 0.9))); }, { passive: false });

    function basis() {
      var cy = Math.cos(yaw), sy = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
      return { v: [cp * cy, cp * sy, sp], r: [-sy, cy, 0], u: [-sp * cy, -sp * sy, cp] };
    }
    var B = basis();
    function P(x, y, z) {
      var px = x - T.L / 2, py = y - T.W / 2, pz = z - T.H / 2;
      return [ox + (px * B.r[0] + py * B.r[1]) * scale, oy - (px * B.u[0] + py * B.u[1] + pz * B.u[2]) * scale];
    }
    function depth(x, y, z) { return (x - T.L / 2) * B.v[0] + (y - T.W / 2) * B.v[1] + (z - T.H / 2) * B.v[2]; }
    this.resize = function () {
      var r = cwrap.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
      W = Math.max(200, r.width); H = Math.max(200, r.height);
      cv.width = W * dpr; cv.height = H * dpr; cv.style.width = W + 'px'; cv.style.height = H + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    function fitScale() {
      if (!T) return; var diag = Math.sqrt(T.L * T.L + T.W * T.W + T.H * T.H);
      scale = Math.min(W, H * 1.6) / diag * 0.95 * zoom; ox = W / 2; oy = H / 2 + 10;
    }
    function quad(pts, fill, stroke, alpha) {
      ctx.globalAlpha = alpha == null ? 1 : alpha; ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]); for (var i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
      ctx.closePath(); if (fill) { ctx.fillStyle = fill; ctx.fill(); }
      if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 0.8; ctx.stroke(); } ctx.globalAlpha = 1;
    }
    function drawBox(x, y, z, l, w, h, col, alpha, glow) {
      var x2 = x + l, y2 = y + w, z2 = z + h, V = B.v;
      var faces = [];
      faces.push([[x, y, z2], [x2, y, z2], [x2, y2, z2], [x, y2, z2], 1.0]);  // top
      if (V[0] > 0) faces.push([[x2, y, z], [x2, y2, z], [x2, y2, z2], [x2, y, z2], 0.82]);
      else faces.push([[x, y, z], [x, y2, z], [x, y2, z2], [x, y, z2], 0.82]);
      if (V[1] > 0) faces.push([[x, y2, z], [x2, y2, z], [x2, y2, z2], [x, y2, z2], 0.66]);
      else faces.push([[x, y, z], [x2, y, z], [x2, y, z2], [x, y, z2], 0.66]);
      if (glow) { ctx.shadowColor = col; ctx.shadowBlur = 18; }
      for (var i = 0; i < faces.length; i++) {
        var f = faces[i];
        quad([P.apply(null, f[0]), P.apply(null, f[1]), P.apply(null, f[2]), P.apply(null, f[3])],
             shade(col, f[4]), 'rgba(0,0,0,0.35)', alpha);
      }
      ctx.shadowBlur = 0;
    }
    function drawBody(front) {
      var L = T.L, Wd = T.W, Hh = T.H;
      // floor with stop-zone tint + grid
      quad([P(0, 0, 0), P(L, 0, 0), P(L, Wd, 0), P(0, Wd, 0)], '#1b2336', null, 1);
      (T.zones || []).forEach(function (zn) {
        quad([P(zn[1], 0, 0), P(zn[2], 0, 0), P(zn[2], Wd, 0), P(zn[1], Wd, 0)], stopColor(zn[0]), null, 0.10);
      });
      ctx.strokeStyle = 'rgba(255,255,255,0.06)'; ctx.lineWidth = 1;
      for (var gx = 0; gx <= L; gx += 50) { var a = P(gx, 0, 0), b = P(gx, Wd, 0); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); }
      if (!front) {
        var backY = B.v[1] > 0 ? 0 : Wd;
        quad([P(0, backY, 0), P(L, backY, 0), P(L, backY, Hh), P(0, backY, Hh)], '#2a3550', 'rgba(140,170,255,0.25)', 0.35);
        quad([P(0, 0, 0), P(0, Wd, 0), P(0, Wd, Hh), P(0, 0, Hh)], '#33415f', 'rgba(140,170,255,0.35)', 0.55);
        label(P(0, Wd / 2, Hh + 12), 'CAB', '#8ab4f8');
      } else {
        ctx.strokeStyle = 'rgba(138,180,248,0.55)'; ctx.lineWidth = 1.2;
        var e = [[[0, 0, Hh], [L, 0, Hh]], [[0, Wd, Hh], [L, Wd, Hh]], [[L, 0, 0], [L, 0, Hh]], [[L, Wd, 0], [L, Wd, Hh]],
                 [[L, 0, Hh], [L, Wd, Hh]], [[0, 0, Hh], [0, Wd, Hh]], [[0, 0, 0], [0, 0, Hh]], [[0, Wd, 0], [0, Wd, Hh]]];
        e.forEach(function (s) { var a = P.apply(null, s[0]), b = P.apply(null, s[1]); ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke(); });
        label(P(L + 25, Wd / 2, 0), 'REAR DOOR', '#fdd663');
      }
    }
    function label(p, s, c) { ctx.font = '600 11px Inter,Roboto,Arial'; ctx.fillStyle = c; ctx.textAlign = 'center'; ctx.fillText(s, p[0], p[1]); }

    function frame(now) {
      if (!T) return;
      var dt = last == null ? 0 : Math.min(0.05, (now - last) / 1000); last = now;
      var N = T.boxes.length, perBox = 0.22;
      if (playing) t += dt * speed / perBox;
      var hudTxt = '', cur = null;
      B = basis(); fitScale();
      ctx.clearRect(0, 0, W, H);
      var g = ctx.createRadialGradient(W / 2, H / 2, 20, W / 2, H / 2, Math.max(W, H) * 0.7);
      g.addColorStop(0, '#16203a'); g.addColorStop(1, '#070b16'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      drawBody(false);
      var items = [];
      if (mode === 'load') {
        if (t > N + 6) { t = playing ? 0 : N; }
        var k = Math.min(N, Math.floor(t)), frac = t - Math.floor(t);
        for (var i = 0; i < k && i < N; i++) items.push([T.boxes[i], 1, 0, 0]);
        if (k < N) {
          var b = T.boxes[k], e = easeOut(Math.min(1, frac * 1.15));
          var dx = (T.L + 90 - b[0]) * (1 - e), dz = 60 * (1 - e) * (1 - e);
          items.push([b, 1, dx, dz, true]); cur = b;
          hudTxt = 'Loading carton <b>' + (k + 1) + '</b> / ' + N + ' &middot; stop <b>' + b[6] + '</b> &middot; ' + b[8];
        } else hudTxt = '<span class="ok">&#10003; Loaded</span> ' + N + ' cartons &middot; stop 1 sits at the door';
        scrub.value = Math.min(N, Math.floor(t));
        banner.style.opacity = 0;
      } else {
        var nS = T.stops.length, per = 3.2, phase = t * perBox / (per * speed / speed) / 1.0;
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
          banner.innerHTML = '<i style="background:' + stopColor(st.seq) + '"></i> Stop ' + st.seq + ' &middot; ' + st.name +
            ' <span class="lp-muted">ETA ' + st.eta + ' &middot; ' + st.n + ' cartons out first, nothing to dig</span>';
          banner.style.opacity = 1; hudTxt = 'Unload replay &middot; stop <b>' + st.seq + '</b> of ' + nS; cur = [0, 0, 0, 0, 0, 0, st.seq];
        } else { banner.style.opacity = 0; hudTxt = '<span class="ok">&#10003; All ' + nS + ' deliveries done</span>'; }
      }
      items.sort(function (a, b) {
        var A = a[0], Bb = b[0];
        return depth(A[0] + a[2] + A[3] / 2, A[1] + A[4] / 2, A[2] + a[3] + A[5] / 2) -
               depth(Bb[0] + b[2] + Bb[3] / 2, Bb[1] + Bb[4] / 2, Bb[2] + b[3] + Bb[5] / 2);
      });
      for (var m = 0; m < items.length; m++) {
        var it = items[m], bb = it[0];
        if (it[1] <= 0.02) continue;
        drawBox(bb[0] + it[2], bb[1], bb[2] + it[3], bb[3], bb[4], bb[5], stopColor(bb[6]), it[1], it[4]);
        if (bb[7] && it[1] > 0.9) { var c = P(bb[0] + it[2] + bb[3] / 2, bb[1] + bb[4] / 2, bb[2] + it[3] + bb[5]); label(c, '!', '#fff'); }
      }
      drawBody(true);
      hud.innerHTML = hudTxt;
      Array.prototype.forEach.call(legend.querySelectorAll('.lp-li'), function (r) {
        r.classList.toggle('on', cur && +r.dataset.seq === cur[6]);
      });
    }
    this.frame = frame;
    if (trucks.length) pick(0);
  }

  /* ============================== ROUTE VIEW ============================== */
  function RouteView(host) {
    var el = $('div', 'lp-pane', host), self = this; this.el = el;
    var top = $('div', 'lp-top', el);
    var title = $('div', 'lp-title', top, '<b>Corridor dispatch</b> &middot; ' + (D.hub ? D.hub.name : ''));
    var kpis = $('div', 'lp-stats', top);
    var body = $('div', 'lp-body', el);
    var cwrap = $('div', 'lp-cwrap', body), cv = $('canvas', 'lp-canvas', cwrap), ctx = cv.getContext('2d');
    var clock = $('div', 'lp-clock', cwrap), hud = $('div', 'lp-hud', cwrap);
    var legend = $('div', 'lp-legend', body);
    var ctr = $('div', 'lp-ctrl', el);
    var tog = $('div', 'lp-seg', ctr);
    var bOpt = $('button', 'on', tog, 'LoadPilot (optimised)'), bBase = $('button', '', tog, 'Today (manual)');
    var play = $('button', 'lp-btn lp-play', ctr, '&#10074;&#10074;');
    var spd = $('button', 'lp-btn', ctr, '1x');
    var scrub = $('input', 'lp-scrub', ctr); scrub.type = 'range';
    var set = 'opt', playing = true, speed = 1, hi = -1, W = 0, H = 0, last = null;
    var R = D.routes || { opt: [], base: [] };
    var t0 = D.clock ? D.clock[0] : 420, t1 = D.clock ? D.clock[1] : 1140, t = t0;
    scrub.min = t0; scrub.max = t1; scrub.value = t0;
    function kv(k, v) { return '<div class="kv"><span>' + k + '</span><b>' + v + '</b></div>'; }
    function setKpi() {
      var K = D.kpi || {}, a = K.base || {}, b = K.opt || {};
      kpis.innerHTML = kv('Trucks', a.trucks + ' &rarr; <span class="ok">' + b.trucks + '</span>') +
        kv('Road km', a.km + ' &rarr; <span class="ok">' + b.km + '</span>') +
        kv('Cost / day', a.cost + ' &rarr; <span class="ok">' + b.cost + '</span>') +
        kv('CO&#8322; kg', a.co2 + ' &rarr; <span class="ok">' + b.co2 + '</span>') +
        kv('Saved', '<span class="ok">' + (K.saved || '') + '</span>');
    }
    setKpi();
    function buildLegend() {
      legend.innerHTML = '<div class="lp-lh">' + (set === 'opt' ? 'Trucks by corridor' : 'Today: one truck per sales area') + '</div>';
      R[set].forEach(function (r, i) {
        var row = $('div', 'lp-li', legend, '<i style="background:' + r.color + '"></i><b>' + r.id + '</b> ' + r.driver +
          ' <span class="lp-muted">' + r.corridor + (r.branch && r.branch !== 'solo' && r.branch !== 'area' ? ' &middot; ' + r.branch : '') +
          ' &middot; ' + r.stops.length + ' stops &middot; ' + r.km + ' km</span>');
        row.onmouseenter = function () { hi = i; }; row.onmouseleave = function () { hi = -1; };
      });
    }
    buildLegend();
    bOpt.onclick = function () { set = 'opt'; bOpt.className = 'on'; bBase.className = ''; t = t0; buildLegend(); };
    bBase.onclick = function () { set = 'base'; bBase.className = 'on'; bOpt.className = ''; t = t0; buildLegend(); };
    play.onclick = function () { playing = !playing; play.innerHTML = playing ? '&#10074;&#10074;' : '&#9654;'; };
    spd.onclick = function () { speed = speed >= 8 ? 1 : speed * 2; spd.textContent = speed + 'x'; };
    scrub.oninput = function () { t = +scrub.value; };

    var bb = (function () {
      var la = [], lo = [];
      ['opt', 'base'].forEach(function (k) { (R[k] || []).forEach(function (r) { r.path.forEach(function (p) { la.push(p[0]); lo.push(p[1]); }); }); });
      if (D.hub) { la.push(D.hub.lat); lo.push(D.hub.lon); }
      return [Math.min.apply(null, la), Math.max.apply(null, la), Math.min.apply(null, lo), Math.max.apply(null, lo)];
    })();
    var kx = Math.cos((bb[0] + bb[1]) / 2 * Math.PI / 180);
    function proj(lat, lon) {
      var pad = 30, sw = (bb[3] - bb[2]) * kx, sh = bb[1] - bb[0];
      var s = Math.min((W - 2 * pad) / sw, (H - 2 * pad) / sh);
      var cx = (W - sw * s) / 2, cy = (H - sh * s) / 2;
      return [cx + (lon - bb[2]) * kx * s, cy + (bb[1] - lat) * s];
    }
    this.resize = function () {
      var r = cwrap.getBoundingClientRect(), dpr = window.devicePixelRatio || 1;
      W = Math.max(200, r.width); H = Math.max(200, r.height);
      cv.width = W * dpr; cv.height = H * dpr; cv.style.width = W + 'px'; cv.style.height = H + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    function posAt(r, tm) {
      var tl = r.times, p = r.path;
      if (tm <= tl[0]) return [p[0], 0];
      for (var i = 0; i < tl.length - 1; i++) {
        if (tm <= tl[i + 1]) {
          var f = (tm - tl[i]) / Math.max(1, tl[i + 1] - tl[i]);
          return [[p[i][0] + (p[i + 1][0] - p[i][0]) * f, p[i][1] + (p[i + 1][1] - p[i][1]) * f], i + f];
        }
      }
      return [p[p.length - 1], p.length - 1];
    }
    function frame(now) {
      var dt = last == null ? 0 : Math.min(0.05, (now - last) / 1000); last = now;
      if (playing) { t += dt * 28 * speed; if (t > t1 + 30) t = t0; }
      scrub.value = t;
      ctx.clearRect(0, 0, W, H);
      var g = ctx.createRadialGradient(W / 2, H / 2, 10, W / 2, H / 2, Math.max(W, H) * 0.75);
      g.addColorStop(0, '#111a30'); g.addColorStop(1, '#060912'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
      var hub = D.hub ? proj(D.hub.lat, D.hub.lon) : [W / 2, H / 2];
      // corridor wedges
      var rad = Math.max(W, H);
      for (var c = 0; c < 8; c++) {
        var a0 = (c * 45 - 22.5 - 90) * Math.PI / 180, a1 = (c * 45 + 22.5 - 90) * Math.PI / 180;
        ctx.beginPath(); ctx.moveTo(hub[0], hub[1]); ctx.arc(hub[0], hub[1], rad, a0, a1); ctx.closePath();
        ctx.fillStyle = c % 2 ? 'rgba(138,180,248,0.035)' : 'rgba(138,180,248,0.015)'; ctx.fill();
        var am = (c * 45 - 90) * Math.PI / 180, lr = Math.min(W, H) * 0.44;
        ctx.font = '600 12px Inter,Roboto,Arial'; ctx.fillStyle = 'rgba(138,180,248,0.45)'; ctx.textAlign = 'center';
        ctx.fillText(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'][c], hub[0] + Math.cos(am) * lr, hub[1] + Math.sin(am) * lr);
      }
      // place labels
      ctx.font = '10px Inter,Roboto,Arial'; ctx.fillStyle = 'rgba(255,255,255,0.28)'; ctx.textAlign = 'left';
      (D.places || []).forEach(function (pl) { var p = proj(pl[1], pl[2]); ctx.fillText(pl[0], p[0] + 4, p[1] - 4); });
      var routes = R[set] || [];
      var delivered = 0, total = 0;
      routes.forEach(function (r, i) {
        var dim = hi >= 0 && hi !== i, pos = posAt(r, t), segs = pos[1];
        ctx.lineJoin = 'round'; ctx.lineCap = 'round';
        // planned path (faint)
        ctx.globalAlpha = dim ? 0.08 : 0.28; ctx.strokeStyle = r.color; ctx.lineWidth = 1.5; ctx.setLineDash([4, 5]);
        ctx.beginPath(); r.path.forEach(function (p, k) { var q = proj(p[0], p[1]); if (k) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); });
        ctx.stroke(); ctx.setLineDash([]);
        // driven trail (glow)
        ctx.globalAlpha = dim ? 0.15 : 1; ctx.shadowColor = r.color; ctx.shadowBlur = dim ? 0 : 10; ctx.lineWidth = 3;
        ctx.beginPath();
        var fi = Math.floor(segs);
        for (var k = 0; k <= fi && k < r.path.length; k++) { var q = proj(r.path[k][0], r.path[k][1]); if (k) ctx.lineTo(q[0], q[1]); else ctx.moveTo(q[0], q[1]); }
        var cp = proj(pos[0][0], pos[0][1]); ctx.lineTo(cp[0], cp[1]); ctx.stroke(); ctx.shadowBlur = 0;
        // stops
        r.stops.forEach(function (s) {
          var q = proj(s.lat, s.lon), done = t >= s.arr; total++; if (done) delivered++;
          ctx.globalAlpha = dim ? 0.2 : 1; ctx.beginPath(); ctx.arc(q[0], q[1], done ? 4.2 : 3.4, 0, Math.PI * 2);
          ctx.fillStyle = done ? r.color : '#0b1020'; ctx.fill(); ctx.strokeStyle = r.color; ctx.lineWidth = 1.4; ctx.stroke();
          if (done && t - s.arr < 25) { ctx.globalAlpha = (1 - (t - s.arr) / 25) * (dim ? 0.2 : 0.9); ctx.beginPath(); ctx.arc(q[0], q[1], 4 + (t - s.arr) * 0.6, 0, Math.PI * 2); ctx.stroke(); }
        });
        // truck marker
        ctx.globalAlpha = dim ? 0.3 : 1; ctx.beginPath(); ctx.arc(cp[0], cp[1], 6.5, 0, Math.PI * 2); ctx.fillStyle = r.color; ctx.fill();
        ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke();
        ctx.font = '700 10px Inter,Roboto,Arial'; ctx.fillStyle = '#fff'; ctx.textAlign = 'left';
        if (!dim) ctx.fillText(r.id, cp[0] + 9, cp[1] + 3);
        ctx.globalAlpha = 1;
      });
      // hub
      var pulse = (now / 1000) % 1.6 / 1.6;
      ctx.beginPath(); ctx.arc(hub[0], hub[1], 8 + pulse * 18, 0, Math.PI * 2); ctx.strokeStyle = 'rgba(253,214,99,' + (1 - pulse) + ')'; ctx.lineWidth = 2; ctx.stroke();
      ctx.beginPath(); ctx.arc(hub[0], hub[1], 8, 0, Math.PI * 2); ctx.fillStyle = '#fdd663'; ctx.fill();
      ctx.font = '700 11px Inter,Roboto,Arial'; ctx.fillStyle = '#fdd663'; ctx.textAlign = 'left'; ctx.fillText('HUB', hub[0] + 12, hub[1] + 4);
      clock.innerHTML = fmtT(t);
      hud.innerHTML = (set === 'opt' ? 'LoadPilot plan' : 'Today\'s manual plan') + ' &middot; delivered <b>' + delivered + '</b> / ' + total;
    }
    this.frame = frame;
  }

  if (MODE === 'both' || MODE === 'routes') panes.routes = new RouteView(root);
  if (MODE === 'both' || MODE === 'load') panes.load = new LoadView(root);
  show(MODE === 'load' ? 'load' : 'routes');
  window.addEventListener('resize', function () { Object.keys(panes).forEach(function (k) { panes[k].resize(); }); });
  function loop(now) {
    Object.keys(panes).forEach(function (k) { if (panes[k].el.style.display !== 'none') panes[k].frame(now); });
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
})();
