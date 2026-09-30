"""LoadPilot executive briefing deck (single self-contained HTML).

Mirrors the ORMWO / Google Cloud "Aurora" deck system (mast, kicker bars, monumental
headlines, Gemini Enterprise cockpit, metric cards, blueprint cards) with a logistics
palette (amber -> teal route gradient) and a dim, animated route-map backdrop drawn from
the *real* demo dispatch plan. All demo numbers come from a live ``plan_dispatch`` run;
industry numbers come from cited public research (vendor figures are flagged).

Usage:  .venv/bin/python -m app.render.executive_presentation_html [out.html]
"""

from __future__ import annotations

import base64
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"

ROUTE_COLORS = ["#F29900", "#00A389", "#1A73E8", "#E8710A", "#12B5CB", "#9334E6",
                "#188038", "#D93025", "#F538A0", "#5F6368"]


def _b64(path: Path) -> str:
    if not path.exists():
        return ""
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _inr(v: float) -> str:
    """Indian digit grouping: 1864500 -> 18,64,500."""
    s = f"{abs(int(round(v)))}"
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("-" if v < 0 else "") + s


def _lakh(v: float) -> str:
    return f"{v / 1e5:,.1f}"


# ──────────────────────────────────────────────────────────────────────────────
# Live demo numbers
# ──────────────────────────────────────────────────────────────────────────────
def _demo_plan():
    from app.data.demo_mmr import HUBS, build_demo_stops
    from app.integration.tools import params_from_state
    from app.optim.dispatch import plan_dispatch

    params = params_from_state({})
    hub = HUBS[params.hub_id]
    stops = build_demo_stops(seed=42)
    return plan_dispatch(hub, stops, params), stops


def _map_svg(plan, stops) -> str:
    """Light, real-geography route-map backdrop (Web Mercator).

    Layers: OSM coastline / rail / primary / trunk / motorway polylines from
    app/data/basemap_*.json, locality labels from the demo gazetteer, today's routes (faint)
    and the LoadPilot routes following real roads (Google Routes / OSRM, straight fallback),
    with animated truck dots.
    """
    import math

    W, H = 1600, 900
    lats = [plan.hub.lat] + [s.lat for s in stops]
    lons = [plan.hub.lon] + [s.lon for s in stops]

    def mx(lon: float) -> float:
        return math.radians(lon)

    def my(lat: float) -> float:
        return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

    x0, x1 = mx(min(lons)), mx(max(lons))
    y0, y1 = my(min(lats)), my(max(lats))
    # fit the plan into the centre ~70% of the canvas; the slice viewBox fills any screen
    # map sits in the right ~45% of the canvas so slide text on the left stays readable
    MX = W * 0.74
    sc = min(W * 0.44 / max(x1 - x0, 1e-9), H * 0.80 / max(y1 - y0, 1e-9))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def xy(lat: float, lon: float) -> tuple[float, float]:
        return MX + (mx(lon) - cx) * sc, H / 2 - (my(lat) - cy) * sc

    # geographic box that covers the whole (sliced) canvas incl. ultra-wide screens
    def inv(px: float, py: float) -> tuple[float, float]:
        lon = math.degrees(cx + (px - MX) / sc)
        lat = math.degrees(2 * math.atan(math.exp(cy - (py - H / 2) / sc)) - math.pi / 2)
        return lat, lon

    s_, w_ = inv(-W * 0.45, H * 1.35)
    n_, e_ = inv(W * 1.45, -H * 0.35)

    def path_of(pts) -> str:
        return "M" + "L".join(f"{x:.0f},{y:.0f}" for x, y in pts)

    out = [f'<svg class="bg-map-svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMaxYMid slice" '
           'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">']

    # ── OSM basemap ────────────────────────────────────────────────────────
    bm = None
    for p in (ROOT / "app" / "data").glob("basemap_*.json"):
        try:
            d = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        bs, bw, bn, be = d["bbox"]
        if bs <= plan.hub.lat <= bn and bw <= plan.hub.lon <= be:
            bm = d
            break
    if bm:
        scale = bm.get("scale", 1e4)
        for cls in ("coast", "rail", "primary", "trunk", "motorway"):
            paths = []
            for flat in bm.get(cls, []):
                lon = lat = 0
                pts, hit, last = [], False, None
                for i in range(0, len(flat), 2):
                    lon += flat[i]
                    lat += flat[i + 1]
                    la, lo = lat / scale, lon / scale
                    if s_ <= la <= n_ and w_ <= lo <= e_:
                        hit = True
                    x, y = xy(la, lo)
                    if last is None or abs(x - last[0]) + abs(y - last[1]) >= 2.5:
                        pts.append((x, y))
                        last = (x, y)
                if hit and len(pts) > 1:
                    paths.append(path_of(pts))
            if paths:
                out.append(f'<path class="bgm-{cls}" d="{" ".join(paths)}"/>')

    # ── locality labels (demo gazetteer) ───────────────────────────────────
    try:
        from app.data.demo_extended import build_tables

        seen = []
        out.append('<g class="bgm-labels">')
        for g in build_tables()["gazetteer"]:
            x, y = xy(g["lat"], g["lon"])
            if any(abs(x - a) < 90 and abs(y - b) < 22 for a, b in seen):
                continue
            seen.append((x, y))
            out.append(f'<text x="{x:.0f}" y="{y - 9:.0f}">{html.escape(g["locality"])}</text>')
        out.append("</g>")
    except Exception:  # noqa: BLE001
        pass

    # ── routes: road-following where available ─────────────────────────────
    try:
        from app.geo.roads import plan_road_legs

        legs = plan_road_legs(plan)
    except Exception:  # noqa: BLE001
        legs = {"opt": {}, "base": {}}

    def route_pts(kind: str, r) -> list[tuple[float, float]]:
        lg = legs.get(kind, {}).get(r.truck_id)
        if lg:
            ll = [p for leg in lg for p in leg]
        else:
            ll = ([(plan.hub.lat, plan.hub.lon)] + [(rs.stop.lat, rs.stop.lon) for rs in r.stops]
                  + [(plan.hub.lat, plan.hub.lon)])
        pts, last = [], None
        for la, lo in ll:
            x, y = xy(la, lo)
            if last is None or abs(x - last[0]) + abs(y - last[1]) >= 2:
                pts.append((x, y))
                last = (x, y)
        return pts

    out.append('<g class="bgm-base">')
    for r in getattr(plan, "baseline_routes", []) or []:
        out.append(f'<path d="{path_of(route_pts("base", r))}"/>')
    out.append("</g>")
    out.append('<g class="bgm-routes">')
    for i, r in enumerate(plan.routes):
        d = path_of(route_pts("opt", r))
        c = ROUTE_COLORS[i % len(ROUTE_COLORS)]
        dur = 22 + 3 * i
        out.append(f'<path class="bgm-casing" d="{d}"/>')
        out.append(f'<path class="bgm-route" d="{d}" stroke="{c}" style="animation-delay:-{i * 1.7:.1f}s"/>')
        out.append(f'<circle r="6" fill="{c}" class="bgm-truck"><animateMotion dur="{dur}s" '
                   f'repeatCount="indefinite" path="{d}"/></circle>')
    out.append("</g>")
    out.append('<g class="bgm-stops">')
    for s in stops:
        x, y = xy(s.lat, s.lon)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6"/>')
    out.append("</g>")
    hx, hy = xy(plan.hub.lat, plan.hub.lon)
    out.append(f'<g class="bgm-hub"><circle cx="{hx:.1f}" cy="{hy:.1f}" r="10"/>'
               f'<circle class="bgm-pulse" cx="{hx:.1f}" cy="{hy:.1f}" r="10"/>'
               f'<text x="{hx + 16:.0f}" y="{hy + 5:.0f}">{html.escape(plan.hub.name)}</text></g>')
    out.append("</svg>")
    return "".join(out)


def _lifo_svg(plan) -> str:
    """Side cross-section of the focus truck: deepest = last stop, door = first stop."""
    route = max(plan.routes, key=lambda r: len(r.stops))
    n = len(route.stops)
    W, H = 760, 250
    x0, x1, top, bot = 120, 690, 48, 196
    zone = (x1 - x0) / max(n, 1)
    g = [f'<svg viewBox="0 0 {W} {H}" class="lifo-svg" xmlns="http://www.w3.org/2000/svg">',
         f'<rect x="20" y="{top + 38}" width="96" height="{bot - top - 38}" rx="14" class="lifo-cab"/>',
         f'<rect x="38" y="{top + 52}" width="52" height="40" rx="6" class="lifo-window"/>',
         f'<rect x="{x0}" y="{top}" width="{x1 - x0}" height="{bot - top}" rx="6" class="lifo-body"/>']
    for k in range(n):
        seq = n - k  # left (cab) = last stop
        c = ROUTE_COLORS[(seq - 1) % len(ROUTE_COLORS)]
        x = x0 + k * zone
        rows = 3
        for rr in range(rows):
            h = (bot - top - 16) / rows
            g.append(f'<rect class="lifo-box" x="{x + 4:.1f}" y="{top + 8 + rr * h:.1f}" '
                     f'width="{zone - 8:.1f}" height="{h - 5:.1f}" rx="3" fill="{c}" '
                     f'style="animation-delay:{(n - seq) * 0.18 + rr * 0.05:.2f}s"/>')
        g.append(f'<text x="{x + zone / 2:.1f}" y="{top + (bot - top) / 2 + 5:.1f}" class="lifo-num">{seq}</text>')
    g.append(f'<rect x="{x1}" y="{top}" width="10" height="{bot - top}" class="lifo-door"/>')
    for cx in (70, 250, 610):
        g.append(f'<circle cx="{cx}" cy="{bot + 14}" r="17" class="lifo-wheel"/>'
                 f'<circle cx="{cx}" cy="{bot + 14}" r="6" class="lifo-hub"/>')
    g.append(f'<text x="{x0}" y="{top - 14}" class="lifo-cap">CAB END · LAST DROP</text>')
    g.append(f'<text x="{x1}" y="{top - 14}" class="lifo-cap" text-anchor="end">REAR DOOR · FIRST DROP →</text>')
    g.append("</svg>")
    return "".join(g), route


def build_executive_presentation_html() -> str:
    plan, stops = _demo_plan()
    b, o = plan.baseline, plan.optimized
    days = 300
    cartons = sum(len(s.boxes) for s in stops)
    save_day = plan.savings_inr
    pct = 100 * save_day / b.cost_total if b.cost_total else 0
    lifo_svg, lifo_route = _lifo_svg(plan)

    rows = [
        ("Trucks dispatched", b.trucks, o.trucks, "", 0),
        ("Fleet km", b.km, o.km, "km", 0),
        ("Diesel", b.litres, o.litres, "L", 0),
        ("CO₂", b.co2_kg, o.co2_kg, "kg", 0),
        ("Crew hours on road", b.hours, o.hours, "h", 1),
        ("Carton-digging hours", b.unload_search_hours, o.unload_search_hours, "h", 1),
        ("Cost of the day", b.cost_total, o.cost_total, "₹", 0),
    ]
    bars = []
    for label, bv, ov, unit, dp in rows:
        mx = max(bv, ov, 1e-9)
        fmt = (lambda v: "₹" + _inr(v)) if unit == "₹" else (lambda v, dp=dp, unit=unit: f"{v:,.{dp}f} {unit}".strip())
        delta = (bv - ov) / bv * 100 if bv else 0
        bars.append(
            f'<div class="cmp-row"><div class="cmp-label">{label}<span class="cmp-delta">−{delta:.0f}%</span></div>'
            f'<div class="cmp-bars"><div class="cmp-bar base" style="--w:{bv / mx * 80:.1f}%"><span>{fmt(bv)}</span></div>'
            f'<div class="cmp-bar opt" style="--w:{max(ov / mx * 80, 1.5):.1f}%"><span>{fmt(ov)}</span></div></div></div>')

    trucks_rows = "".join(
        f'<tr><td><span class="dot" style="background:{ROUTE_COLORS[i % len(ROUTE_COLORS)]}"></span>{html.escape(r.truck_id)}</td>'
        f'<td>{html.escape(r.driver or "—")}</td><td>{html.escape(r.corridor)}{("·" + r.branch) if r.branch else ""}</td>'
        f'<td>{len(r.stops)}</td><td>{r.km:,.0f}</td></tr>'
        for i, r in enumerate(plan.routes))

    demo = {
        "base_cost_per_truck": round(b.cost_total / b.trucks),
        "pct": round(pct, 1),
        "litres_per_truck_saved": round((b.litres - o.litres) / b.trucks, 1),
        "co2_per_truck_saved": round((b.co2_kg - o.co2_kg) / b.trucks, 1),
        "trucks_freed_ratio": round((b.trucks - o.trucks) / b.trucks, 3),
        "search_h_per_truck": round(b.unload_search_hours / b.trucks, 2),
    }
    subs = {
        "__MAP_SVG__": _map_svg(plan, stops),
        "__LIFO_SVG__": lifo_svg,
        "__LIFO_TRUCK__": html.escape(f"{lifo_route.truck_id} · {len(lifo_route.stops)} drops · "
                                      f"{lifo_route.corridor} corridor"),
        "__LOGO__": _b64(ASSETS / "gcloud_logo.png"),
        "__SHOT_LOAD__": _b64(ASSETS / "shot_load3d.png"),
        "__SHOT_ROUTES__": _b64(ASSETS / "shot_routes.png"),
        "__STOPS__": str(len(stops)),
        "__CARTONS__": _inr(cartons),
        "__B_TRUCKS__": str(b.trucks),
        "__O_TRUCKS__": str(o.trucks),
        "__B_COST__": _inr(b.cost_total),
        "__O_COST__": _inr(o.cost_total),
        "__SAVE_DAY__": _inr(save_day),
        "__SAVE_PCT__": f"{pct:.0f}",
        "__SAVE_YEAR_L__": _lakh(save_day * days),
        "__KM_SAVED__": f"{b.km - o.km:,.0f}",
        "__L_SAVED__": f"{b.litres - o.litres:,.0f}",
        "__L_SAVED_YEAR__": _inr((b.litres - o.litres) * days),
        "__CO2_SAVED__": f"{b.co2_kg - o.co2_kg:,.0f}",
        "__CO2_YEAR_T__": f"{(b.co2_kg - o.co2_kg) * days / 1000:,.0f}",
        "__SEARCH_H__": f"{b.unload_search_hours:,.1f}",
        "__CREW_H_SAVED__": f"{b.hours - o.hours:,.1f}",
        "__CMP_BARS__": "".join(bars),
        "__TRUCK_ROWS__": trucks_rows,
        "__DEMO_JSON__": json.dumps(demo),
        "__HUB__": html.escape(plan.hub.name),
    }
    out = HTML_TEMPLATE
    for k, v in subs.items():
        out = out.replace(k, v)
    return out


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" class="theme-light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LoadPilot — Truck Load &amp; Route Optimizer | Google Cloud Executive Briefing</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700;800&family=Google+Sans+Text:wght@400;500;700&family=Roboto+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --g-blue:#1A73E8; --g-green:#00AF57; --g-yellow:#FEC700; --g-red:#FC413D;
    --amber:#F29900; --amber-deep:#E37400; --teal:#00A389; --route-green:#188038;
    --font-display:'Google Sans',-apple-system,BlinkMacSystemFont,sans-serif;
    --font-body:'Google Sans Text',-apple-system,BlinkMacSystemFont,sans-serif;
    --font-mono:'Roboto Mono',monospace;
    --grad-route:linear-gradient(90deg,#E37400 0%,#F29900 38%,#00A389 100%);
    --grad-road:linear-gradient(135deg,#F29900 0%,#00A389 100%);
    --gemini-spark:linear-gradient(135deg,#1A73E8 0%,#4B31E3 100%);
  }
  html.theme-light {
    --canvas:#FBFAF7; --surface:#FFFFFF; --surface-card:rgba(255,255,255,.97); --surface-sunk:#F4F1EA;
    --border-hairline:#ECE6DA; --border-subtle:#DCD3C2; --border-strong:#A8A08F;
    --text:#1B1A17; --text-muted:#4E4A42; --text-dim:#7A7468;
    --amber-ink:#B35C00; --teal-ink:#00796B; --green-ink:#137333; --red-ink:#C5221F; --blue-ink:#1A73E8;
    --map-alpha:.36; --map-water:#8EC3E6; --map-rail:#C9C2B4; --map-road:#E2DBCD; --map-trunk:#F3D08A; --map-motorway:#F1B26B; --map-label:#8A8374;
    --card-shadow:0 4px 20px rgba(60,40,0,.06),0 1px 3px rgba(0,0,0,.03);
    --cockpit-shadow:0 8px 30px rgba(60,40,0,.08),0 1px 3px rgba(0,0,0,.04);
  }
  html.theme-dark {
    --canvas:#0A0D12; --surface:#141820; --surface-card:rgba(20,24,32,.86); --surface-sunk:#0E1117;
    --border-hairline:rgba(255,255,255,.08); --border-subtle:rgba(255,255,255,.13); --border-strong:rgba(255,255,255,.24);
    --text:#F6F4EF; --text-muted:#A9A396; --text-dim:#6F6A60;
    --amber-ink:#FDB750; --teal-ink:#4FD1B8; --green-ink:#5BB974; --red-ink:#F28B82; --blue-ink:#8AB4F8;
    --map-alpha:.38; --map-water:#2F5E80; --map-rail:#3A3F48; --map-road:#2A2F38; --map-trunk:#6B5A35; --map-motorway:#8A6630; --map-label:#8C8778;
    --card-shadow:0 16px 40px rgba(0,0,0,.4); --cockpit-shadow:0 16px 40px rgba(0,0,0,.4);
  }
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--canvas);color:var(--text);font-family:var(--font-body);-webkit-font-smoothing:antialiased;overflow-x:hidden;min-height:100vh}

  /* ── Light real-map backdrop ────────────────────────────────────── */
  .bg-map{position:fixed;inset:0;z-index:0;pointer-events:none;overflow:hidden;opacity:var(--map-alpha)}
  .bg-map-svg{width:100%;height:100%}
  .bg-map{-webkit-mask-image:linear-gradient(90deg,transparent 0%,transparent 52%,rgba(0,0,0,.45) 72%,#000 92%);mask-image:linear-gradient(90deg,transparent 0%,transparent 52%,rgba(0,0,0,.45) 72%,#000 92%)}
  .bgm-coast{fill:none;stroke:var(--map-water);stroke-width:3.2;stroke-linejoin:round;stroke-linecap:round}
  .bgm-rail{fill:none;stroke:var(--map-rail);stroke-width:1;stroke-dasharray:5 4}
  .bgm-primary{fill:none;stroke:var(--map-road);stroke-width:1.1;stroke-linejoin:round}
  .bgm-trunk{fill:none;stroke:var(--map-trunk);stroke-width:2.2;stroke-linejoin:round;stroke-linecap:round}
  .bgm-motorway{fill:none;stroke:var(--map-motorway);stroke-width:3.2;stroke-linejoin:round;stroke-linecap:round}
  .bgm-labels text{font-family:var(--font-body);font-size:13px;font-weight:500;fill:var(--map-label);text-anchor:middle;paint-order:stroke;stroke:var(--canvas);stroke-width:3px}
  .bgm-base path{fill:none;stroke:var(--map-label);stroke-width:1.4;stroke-dasharray:3 5;opacity:.35}
  .bgm-casing{fill:none;stroke:var(--canvas);stroke-width:6.5;stroke-linejoin:round;stroke-linecap:round;opacity:.9}
  .bgm-route{fill:none;stroke-width:3.4;stroke-linejoin:round;stroke-linecap:round;stroke-dasharray:14 9;opacity:.85;animation:roadflow 9s linear infinite}
  .bgm-truck{stroke:#fff;stroke-width:2}
  .bgm-stops circle{fill:var(--surface);stroke:var(--map-label);stroke-width:1.4}
  .bgm-hub circle{fill:var(--amber);stroke:#fff;stroke-width:2}
  .bgm-hub text{font-family:var(--font-display);font-size:14px;font-weight:700;fill:var(--amber-ink);paint-order:stroke;stroke:var(--canvas);stroke-width:3px}
  .bgm-pulse{fill:none!important;stroke:var(--amber);stroke-width:2;transform-box:fill-box;transform-origin:center;animation:pulse 2.6s ease-out infinite}
  @keyframes roadflow{to{stroke-dashoffset:-230}}
  @keyframes pulse{0%{transform:scale(1);opacity:.7}100%{transform:scale(4.5);opacity:0}}

  /* ── Mast ───────────────────────────────────────────────────────── */
  .mast{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;align-items:center;justify-content:space-between;padding:12px max(24px,4vw);background:color-mix(in srgb,var(--surface) 86%,transparent);backdrop-filter:blur(16px);border-bottom:1px solid var(--border-hairline);gap:16px}
  .mast-brand{display:flex;align-items:center;gap:12px}
  .mast-logo{height:26px}
  .mast-rule{width:1px;height:18px;background:var(--border-subtle)}
  .mast-stage-tag{font-family:var(--font-mono);font-size:11.5px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:var(--amber-ink)}
  .mast-nav-group{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  .mast-pills{display:flex;gap:4px;background:var(--surface-sunk);border:1px solid var(--border-hairline);border-radius:999px;padding:3px 5px}
  .slide-tab{font-family:var(--font-mono);font-size:11px;font-weight:700;padding:5px 12px;border-radius:999px;border:none;background:transparent;color:var(--text-muted);cursor:pointer;transition:all .18s}
  .slide-tab:hover{color:var(--text)}
  .slide-tab.active{background:var(--amber-deep);color:#fff;box-shadow:0 2px 8px rgba(227,116,0,.35)}
  .nav-btn{font-family:var(--font-display);font-size:12px;font-weight:700;cursor:pointer;padding:6px 12px;border-radius:20px;border:1px solid var(--border-hairline);background:var(--surface);color:var(--text)}
  .nav-btn:hover:not(:disabled){border-color:var(--amber-ink);color:var(--amber-ink)}
  .nav-btn:disabled{opacity:.35;cursor:not-allowed}
  .slide-counter{font-family:var(--font-mono);font-size:12px;font-weight:700;color:var(--amber-ink);min-width:48px;text-align:center}
  .mast-cta{font-family:var(--font-display);font-size:12px;font-weight:700;text-decoration:none;padding:6px 14px;border-radius:20px;background:var(--grad-road);color:#fff}

  /* ── Slides ─────────────────────────────────────────────────────── */
  .deck-container{padding-top:60px;min-height:100vh;position:relative;z-index:1}
  .slide-section{display:none;min-height:calc(100vh - 60px);padding:clamp(16px,2.5vh,36px) max(20px,2.5vw) 28px;position:relative}
  .slide-section.active{display:flex;flex-direction:column;justify-content:center;animation:fadeIn .3s cubic-bezier(.16,1,.3,1)}
  @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
  .wrap-max{max-width:1400px;margin:0 auto;width:100%;transform-origin:top center}
  .title-kicker{display:flex;align-items:center;gap:10px;margin-bottom:18px;flex-wrap:wrap}
  .kicker-bar{width:24px;height:3px;border-radius:2px;background:var(--grad-route)}
  .kicker-primary{font-family:var(--font-display);font-size:13.5px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:var(--amber-ink)}
  .kicker-sep{color:var(--border-strong)}
  .kicker-sub{font-family:var(--font-mono);font-size:13px;color:var(--text-dim);letter-spacing:.5px}
  .monumental-headline{font-family:var(--font-display);font-size:clamp(32px,3.8vw,54px);font-weight:800;line-height:1.12;letter-spacing:-1.3px;margin-bottom:16px}
  .gradient-span{background:var(--grad-route);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
  .tagline-lead{font-size:clamp(16px,1.25vw,19.5px);line-height:1.55;color:var(--text-muted);max-width:1240px;margin-bottom:28px}
  .tagline-lead b{color:var(--text)}

  .monumental-headline,.tagline-lead,.title-kicker,.hero-stats{text-shadow:0 0 10px var(--canvas),0 0 4px var(--canvas)}
  .gradient-span,.gradient-span *{text-shadow:none}
  /* ── Gemini cockpit ─────────────────────────────────────────────── */
  .gemini-cockpit{background:var(--surface);border:1px solid var(--border-subtle);border-radius:24px;padding:14px 20px;display:flex;align-items:center;gap:16px;box-shadow:var(--cockpit-shadow);max-width:1400px;margin-bottom:16px}
  .gemini-brand-badge{display:flex;align-items:center;gap:8px;flex-shrink:0}
  .gemini-spark-svg{width:26px;height:26px;filter:drop-shadow(0 0 8px rgba(26,115,232,.45))}
  .gemini-brand-text{font-family:var(--font-display);font-size:17px;font-weight:700}
  .gemini-cockpit-divider{width:1px;height:30px;background:var(--border-subtle)}
  .gemini-prompt-box{flex:1;min-width:0;font-size:15.5px;color:var(--text);line-height:1.45}
  .gemini-prompt-box .caret{display:inline-block;width:2px;height:1.05em;background:var(--amber-deep);vertical-align:-2px;margin-left:2px;animation:blink 1s steps(1) infinite}
  @keyframes blink{50%{opacity:0}}
  .gemini-exec-btn{font-family:var(--font-display);font-weight:700;font-size:13px;border:none;border-radius:16px;padding:9px 16px;background:var(--gemini-spark);color:#fff;cursor:pointer;flex-shrink:0}
  .cockpit-pills{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
  .query-chip{font-family:var(--font-mono);font-size:11.5px;font-weight:700;padding:7px 13px;border-radius:999px;border:1px solid var(--border-subtle);background:var(--surface-card);color:var(--text-muted);cursor:pointer;transition:all .18s}
  .query-chip.active,.query-chip:hover{border-color:var(--amber-deep);color:var(--amber-ink);background:color-mix(in srgb,var(--amber) 10%,var(--surface))}
  .agent-response-drawer{max-width:1400px;background:var(--surface-card);border:1px solid var(--border-hairline);border-left:3px solid var(--teal);border-radius:14px;padding:14px 18px;box-shadow:var(--card-shadow);font-size:14.5px;line-height:1.6;color:var(--text-muted);min-height:92px}
  .agent-response-drawer b{color:var(--text)}
  .tool-trace{font-family:var(--font-mono);font-size:11.5px;color:var(--teal-ink);margin-bottom:6px}

  /* ── Cards & metrics ────────────────────────────────────────────── */
  .metrics-4col-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:16px}
  .metric-box{background:var(--surface-card);border:1px solid var(--border-hairline);border-radius:18px;padding:18px 18px 14px;box-shadow:var(--card-shadow);position:relative;overflow:hidden;backdrop-filter:blur(6px)}
  .metric-box::before{content:"";position:absolute;left:0;top:0;right:0;height:3px;background:var(--grad-route)}
  .metric-value{font-family:var(--font-display);font-size:clamp(28px,2.6vw,40px);font-weight:800;letter-spacing:-1px;line-height:1.05}
  .metric-value.amber{color:var(--amber-ink)} .metric-value.teal{color:var(--teal-ink)} .metric-value.red{color:var(--red-ink)} .metric-value.green{color:var(--green-ink)}
  .metric-label{font-family:var(--font-display);font-size:14px;font-weight:700;margin:6px 0 4px}
  .metric-desc{font-size:12.5px;color:var(--text-muted);line-height:1.45}
  .metric-src{font-family:var(--font-mono);font-size:10px;color:var(--text-dim);margin-top:8px;letter-spacing:.3px}
  .metric-src a{color:inherit}
  .tag-vendor{font-family:var(--font-mono);font-size:9.5px;font-weight:700;color:var(--amber-ink);border:1px solid currentColor;border-radius:6px;padding:0 5px;margin-left:4px}
  .hero-stats{display:flex;gap:28px;flex-wrap:wrap;margin-top:22px}
  .hero-stat .v{font-family:var(--font-display);font-size:30px;font-weight:800;letter-spacing:-.8px}
  .hero-stat .l{font-family:var(--font-mono);font-size:11px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px}

  .split{display:grid;grid-template-columns:1.05fr .95fr;gap:22px;align-items:stretch}
  .blueprint-card{background:var(--surface-card);border:1px solid var(--border-hairline);border-radius:20px;padding:18px;box-shadow:var(--card-shadow);backdrop-filter:blur(6px)}
  .card-title{font-family:var(--font-display);font-weight:800;font-size:16px;margin-bottom:4px}
  .card-sub{font-family:var(--font-mono);font-size:11px;color:var(--text-dim);margin-bottom:12px;letter-spacing:.3px}
  .shot{width:100%;border-radius:12px;border:1px solid var(--border-hairline);display:block;background:#0B132B}

  .steps{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:18px}
  .step{background:var(--surface-card);border:1px solid var(--border-hairline);border-radius:16px;padding:14px;box-shadow:var(--card-shadow);position:relative}
  .step .n{font-family:var(--font-mono);font-size:11px;font-weight:700;color:#fff;background:var(--grad-road);border-radius:999px;width:24px;height:24px;display:grid;place-items:center;margin-bottom:8px}
  .step h4{font-family:var(--font-display);font-size:15px;margin-bottom:4px}
  .step p{font-size:12.5px;color:var(--text-muted);line-height:1.45}
  .step:not(:last-child)::after{content:"→";position:absolute;right:-11px;top:40%;color:var(--amber-ink);font-weight:800}

  .lifo-svg{width:100%;height:auto}
  .lifo-cab{fill:var(--surface-sunk);stroke:var(--border-strong);stroke-width:1.5}
  .lifo-window{fill:color-mix(in srgb,var(--teal) 25%,transparent)}
  .lifo-body{fill:none;stroke:var(--border-strong);stroke-width:2}
  .lifo-door{fill:var(--amber)}
  .lifo-box{opacity:0;animation:boxIn .5s ease forwards;stroke:rgba(0,0,0,.18)}
  @keyframes boxIn{from{opacity:0;transform:translateY(-18px)}to{opacity:.9;transform:none}}
  .lifo-num{font-family:var(--font-display);font-weight:800;font-size:18px;fill:#fff;text-anchor:middle;paint-order:stroke;stroke:rgba(0,0,0,.35);stroke-width:3}
  .lifo-wheel{fill:var(--text);opacity:.85} .lifo-hub{fill:var(--surface)}
  .lifo-cap{font-family:var(--font-mono);font-size:11px;font-weight:700;fill:var(--text-dim);letter-spacing:1px}
  .replay{font-family:var(--font-mono);font-size:11px;border:1px solid var(--border-subtle);background:var(--surface);color:var(--text-muted);border-radius:999px;padding:4px 10px;cursor:pointer;float:right}

  /* ── Comparison bars ────────────────────────────────────────────── */
  .cmp-legend{display:flex;gap:16px;font-family:var(--font-mono);font-size:11px;color:var(--text-dim);margin-bottom:10px}
  .cmp-legend i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
  .cmp-row{display:grid;grid-template-columns:190px 1fr;gap:12px;align-items:center;padding:6px 0;border-bottom:1px dashed var(--border-hairline)}
  .cmp-label{font-family:var(--font-display);font-weight:700;font-size:13.5px;display:flex;justify-content:space-between;gap:8px}
  .cmp-delta{font-family:var(--font-mono);font-size:11.5px;color:var(--green-ink)}
  .cmp-bars{display:flex;flex-direction:column;gap:4px}
  .cmp-bar{height:17px;border-radius:5px;width:0;position:relative;transition:width 1.1s cubic-bezier(.16,1,.3,1)}
  .slide-section.active .cmp-bar{width:var(--w)}
  .cmp-bar span{position:absolute;left:calc(100% + 8px);top:0;font-family:var(--font-mono);font-size:11px;white-space:nowrap;line-height:17px;color:var(--text-muted)}
  .cmp-bar.base{background:color-mix(in srgb,var(--text-dim) 45%,transparent)}
  .cmp-bar.opt{background:var(--grad-route)}
  table.tt{width:100%;border-collapse:collapse;font-size:12.5px}
  table.tt th{font-family:var(--font-mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.8px;color:var(--text-dim);text-align:left;padding:6px 8px;border-bottom:1px solid var(--border-subtle)}
  table.tt td{padding:6px 8px;border-bottom:1px solid var(--border-hairline)}
  .dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}

  /* ── ROI calculator ─────────────────────────────────────────────── */
  .roi-grid{display:grid;grid-template-columns:.9fr 1.1fr;gap:22px}
  .slider-row{margin-bottom:16px}
  .slider-row label{display:flex;justify-content:space-between;font-family:var(--font-display);font-weight:700;font-size:14px;margin-bottom:6px}
  .slider-row label output{font-family:var(--font-mono);color:var(--amber-ink)}
  .slider-row small{display:block;color:var(--text-dim);font-size:11.5px;margin-top:3px}
  input[type=range]{width:100%;accent-color:var(--amber-deep)}
  .roi-big{font-family:var(--font-display);font-size:clamp(40px,4.4vw,64px);font-weight:800;letter-spacing:-1.5px;line-height:1}
  .roi-out{display:grid;grid-template-columns:repeat(2,1fr);gap:12px;margin-top:16px}

  /* ── Architecture ───────────────────────────────────────────────── */
  .arch{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;align-items:stretch;margin-bottom:16px}
  .arch-node{background:var(--surface-card);border:1px solid var(--border-hairline);border-radius:16px;padding:14px;box-shadow:var(--card-shadow)}
  .arch-node .ic{font-size:22px;margin-bottom:6px}
  .arch-node h4{font-family:var(--font-display);font-size:14.5px;margin-bottom:4px}
  .arch-node p{font-size:12px;color:var(--text-muted);line-height:1.45}
  .arch-node.hl{border-color:color-mix(in srgb,var(--amber) 55%,transparent)}
  .roadmap{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:14px}
  .rm{border-radius:14px;padding:12px 14px;border:1px dashed var(--border-subtle);background:var(--surface-card)}
  .rm b{font-family:var(--font-display)} .rm p{font-size:12px;color:var(--text-muted);margin-top:4px;line-height:1.45}
  .sources{font-size:11px;color:var(--text-dim);line-height:1.6;columns:2;column-gap:28px}
  .sources a{color:var(--text-muted)}
  .note{font-family:var(--font-mono);font-size:10.5px;color:var(--text-dim);margin-top:10px}

  @media (max-width:1100px){.metrics-4col-grid,.steps,.arch{grid-template-columns:repeat(2,1fr)}.split,.roi-grid{grid-template-columns:1fr}.mast-pills{display:none}.sources{columns:1}}
</style>
</head>
<body>
<div class="bg-map">__MAP_SVG__</div>

<header class="mast">
  <div class="mast-brand">
    <img class="mast-logo" src="__LOGO__" alt="Google Cloud">
    <span class="mast-rule"></span>
    <span class="mast-stage-tag">LoadPilot · Executive Briefing</span>
  </div>
  <div class="mast-nav-group">
    <div class="mast-pills" id="slideTabs"></div>
    <button class="nav-btn" id="prevBtn" onclick="prev()">‹ Prev</button>
    <span class="slide-counter" id="slideCounter">1 / 6</span>
    <button class="nav-btn" id="nextBtn" onclick="next()">Next ›</button>
    <button class="nav-btn" onclick="toggleTheme()" title="Toggle theme">◐</button>
    <a class="mast-cta" href="https://github.com/zuhaibp656/loadpilot-dispatch-agent" target="_blank">Repo ↗</a>
  </div>
</header>

<main class="deck-container">

<!-- ═════════════ 00 OVERVIEW ═════════════ -->
<section class="slide-section" data-title="00 Overview">
 <div class="wrap-max">
  <div class="title-kicker"><span class="kicker-bar"></span><span class="kicker-primary">Retail &amp; CPG Supply Chain</span><span class="kicker-sep">/</span><span class="kicker-sub">Gemini Enterprise · ADK · Vertex AI Agent Engine</span></div>
  <h1 class="monumental-headline">Load it in reverse.<br><span class="gradient-span">Drive it in order.</span> Deliver it all.</h1>
  <p class="tagline-lead"><b>LoadPilot</b> is a dispatch co-pilot for primary and secondary distribution. Each morning it decides <b>which trucks</b> roll out and <b>which corridor</b> each driver takes. It then works out <b>the drop order</b> and <b>where every carton sits</b>, so drop 1 is at the door and the last drop sits behind the cab. Crews stop digging for cartons, and the fleet runs fewer kilometres.</p>

  <div class="gemini-cockpit">
    <div class="gemini-brand-badge">
      <svg class="gemini-spark-svg" viewBox="0 0 24 24" fill="none"><defs><linearGradient id="sg" x1="0%" y1="100%" x2="100%" y2="0%"><stop offset="0%" stop-color="#217BFE"/><stop offset="50%" stop-color="#078EFB"/><stop offset="100%" stop-color="#AC87EB"/></linearGradient></defs><path d="M21.365 10.712C19.519 9.917 17.904 8.827 16.519 7.442C15.135 6.058 14.045 4.442 13.25 2.596C12.945 1.889 12.7 1.161 12.512 0.416C12.451 0.172 12.232 0 11.981 0C11.729 0 11.511 0.172 11.45 0.416C11.262 1.161 11.016 1.888 10.711 2.596C9.917 4.442 8.826 6.058 7.442 7.442C6.058 8.827 4.442 9.917 2.596 10.712C1.888 11.017 1.161 11.262 0.415 11.45C0.172 11.511 0 11.73 0 11.981C0 12.232 0.172 12.451 0.415 12.512C1.161 12.7 1.888 12.945 2.596 13.25C4.442 14.045 6.057 15.135 7.442 16.52C8.827 17.904 9.917 19.52 10.711 21.366C11.016 22.073 11.262 22.801 11.45 23.546C11.511 23.79 11.729 23.962 11.981 23.962C12.232 23.962 12.451 23.79 12.512 23.546C12.7 22.801 12.945 22.074 13.25 21.366C14.045 19.52 15.135 17.905 16.519 16.52C17.904 15.135 19.519 14.045 21.365 13.25C22.073 12.945 22.8 12.7 23.546 12.512C23.79 12.451 23.961 12.232 23.961 11.981C23.961 11.73 23.79 11.511 23.546 11.45C22.801 11.262 22.074 11.017 21.365 10.712Z" fill="url(#sg)"/></svg>
      <span class="gemini-brand-text">Gemini Enterprise</span>
    </div>
    <div class="gemini-cockpit-divider"></div>
    <div class="gemini-prompt-box"><span id="cockpitText"></span><span class="caret"></span></div>
    <button class="gemini-exec-btn" onclick="cycleQuery()">Run ↵</button>
  </div>
  <div class="cockpit-pills" id="cockpitPills"></div>
  <div class="agent-response-drawer" id="cockpitDrawer"></div>

  <div class="hero-stats">
    <div class="hero-stat"><div class="v">__STOPS__ drops · __CARTONS__ cartons</div><div class="l">Demo day · __HUB__</div></div>
    <div class="hero-stat"><div class="v" style="color:var(--amber-ink)">__B_TRUCKS__ → __O_TRUCKS__ trucks</div><div class="l">Fleet right-sized</div></div>
    <div class="hero-stat"><div class="v" style="color:var(--teal-ink)">₹__SAVE_DAY__ / day</div><div class="l">−__SAVE_PCT__% cost of the day</div></div>
    <div class="hero-stat"><div class="v" style="color:var(--green-ink)">__SEARCH_H__ h → 0</div><div class="l">Carton-digging per day</div></div>
  </div>
 </div>
</section>

<!-- ═════════════ 01 COST REALITY ═════════════ -->
<section class="slide-section" data-title="01 The Problem">
 <div class="wrap-max">
  <div class="title-kicker"><span class="kicker-bar"></span><span class="kicker-primary">The Cost Reality</span><span class="kicker-sep">/</span><span class="kicker-sub">Public research · India &amp; global</span></div>
  <h2 class="monumental-headline">The last mile is where <span class="gradient-span">margin leaks out.</span></h2>
  <p class="tagline-lead">Today, most depots plan dispatch by area and by habit. Trucks leave half-empty and stops get resequenced on the road. At every drop the crew unloads cartons that belong to later stops to reach the right one. The published numbers look like this.</p>
  <div class="metrics-4col-grid">
    <div class="metric-box"><div class="metric-value amber">7.97%</div><div class="metric-label">of India's GDP is logistics</div><div class="metric-desc">≈ ₹24 lakh crore a year (FY24). The National Logistics Policy targets a global-benchmark cost and a top-25 LPI rank by 2030.</div><div class="metric-src"><a href="https://www.ncaer.org/" target="_blank">NCAER / DPIIT, 2025</a> · <a href="https://pib.gov.in/" target="_blank">PIB</a></div></div>
    <div class="metric-box"><div class="metric-value red">41%</div><div class="metric-label">of supply-chain cost is the last mile</div><div class="metric-desc">It is the single largest cost block. Left unaddressed, it can erode retailer profit by up to 26% over 3 years.</div><div class="metric-src"><a href="https://www.capgemini.com/insights/research-library/the-last-mile-delivery-challenge/" target="_blank">Capgemini Research Institute, 2019</a></div></div>
    <div class="metric-box"><div class="metric-value amber">~40%</div><div class="metric-label">empty running on Indian trucks</div><div class="metric-desc">Indian trucks average 300–325 km/day, against 500–800 km/day for global peers. Poor utilisation is the root cause.</div><div class="metric-src"><a href="https://rmi.org/insight/fast-tracking-freight-in-india/" target="_blank">NITI Aayog &amp; RMI, 2021</a></div></div>
    <div class="metric-box"><div class="metric-value red">40–55%</div><div class="metric-label">of truck operating cost is diesel</div><div class="metric-desc">Every kilometre cut goes straight to the P&amp;L and to Scope-3 emissions.</div><div class="metric-src">Industry estimates · range varies by source</div></div>
  </div>
  <div class="metrics-4col-grid">
    <div class="metric-box"><div class="metric-value teal">100M mi</div><div class="metric-label">saved per year by route optimisation</div><div class="metric-desc">UPS ORION: ~10M gallons of fuel and ~100k t CO₂ a year, from 6–8 fewer miles per driver per day.</div><div class="metric-src"><a href="https://www.informs.org/Impact/O.R.-Analytics-Success-Stories/UPS-On-Road-Integrated-Optimization-and-Navigation-ORION-Project" target="_blank">INFORMS Edelman, 2016</a></div></div>
    <div class="metric-box"><div class="metric-value teal">+36%</div><div class="metric-label">more delivery vehicles by 2030</div><div class="metric-desc">Emissions are projected to rise +32% in the top 100 cities. Routing and consolidation can cut that by up to ~30%.</div><div class="metric-src"><a href="https://www.weforum.org/publications/the-future-of-the-last-mile-ecosystem/" target="_blank">World Economic Forum, 2020</a></div></div>
    <div class="metric-box"><div class="metric-value green">3–4 h → min</div><div class="metric-label">daily dispatch planning</div><div class="metric-desc">Route-planning software users report 75–84% less planning time.<span class="tag-vendor">VENDOR</span></div><div class="metric-src">Descartes · Locus case studies</div></div>
    <div class="metric-box"><div class="metric-value green">10–25%</div><div class="metric-label">routing cost reduction</div><div class="metric-desc">Typical range for optimised VRP over manual planning. Descartes/ArrowXL reports −13% mileage.<span class="tag-vendor">VENDOR</span></div><div class="metric-src">McKinsey via Locus · Descartes</div></div>
  </div>
  <p class="note">Carton-search time and damage have no credible public benchmark. LoadPilot measures them per pilot; the demo assumes 9 min of digging per stop that is out of sequence.</p>
 </div>
</section>

<!-- ═════════════ 02 HOW IT WORKS ═════════════ -->
<section class="slide-section" data-title="02 How It Works">
 <div class="wrap-max">
  <div class="title-kicker"><span class="kicker-bar"></span><span class="kicker-primary">How LoadPilot Works</span><span class="kicker-sep">/</span><span class="kicker-sub">One conversation · four optimisers</span></div>
  <h2 class="monumental-headline">From order list to <span class="gradient-span">loaded, routed trucks</span> in under a minute.</h2>
  <div class="steps">
    <div class="step"><div class="n">1</div><h4>Ingest</h4><p>Orders arrive as a list, a CSV/XLSX, a PDF or an email body. Cartons are captured from photos: QR codes and labels are read with Gemini vision.</p></div>
    <div class="step"><div class="n">2</div><h4>Corridors &amp; claims</h4><p>Drivers claim a direction, e.g. “I've got West”. If several trucks share a corridor, LoadPilot splits it into branches.</p></div>
    <div class="step"><div class="n">3</div><h4>Fleet &amp; routes</h4><p>An OR-Tools VRP handles a mixed fleet of 5 truck types, time windows and capacity. It can minimise cost, trucks or finish time.</p></div>
    <div class="step"><div class="n">4</div><h4>LIFO loading</h4><p>A 3D packer loads in reverse drop order, keeping fragile cartons on top and this-side-up cartons upright. It checks the door rule for every stop.</p></div>
  </div>
  <div class="split">
   <div class="blueprint-card">
     <button class="replay" onclick="replayLifo()">↻ replay</button>
     <div class="card-title">The door rule, visualised</div>
     <div class="card-sub">__LIFO_TRUCK__ · number = drop sequence</div>
     <div id="lifoWrap">__LIFO_SVG__</div>
     <p class="metric-desc" style="margin-top:8px">Loading follows the reverse of the route. At every stop, that stop's cartons are the first ones the crew reaches, with no re-handling. The same plan is shown in the agent as an animated 3D loading sequence (MP4 plus an interactive canvas).</p>
   </div>
   <div class="blueprint-card">
     <div class="card-title">Inside Gemini Enterprise: 3D load view</div>
     <div class="card-sub">A2UI canvas · rendered by the agent · colour = stop</div>
     <img class="shot" src="__SHOT_LOAD__" alt="3D load plan">
   </div>
  </div>
 </div>
</section>

<!-- ═════════════ 03 DEMO RESULTS ═════════════ -->
<section class="slide-section" data-title="03 Demo Results">
 <div class="wrap-max">
  <div class="title-kicker"><span class="kicker-bar"></span><span class="kicker-primary">Demo Results</span><span class="kicker-sep">/</span><span class="kicker-sub">__HUB__ · __STOPS__ dealers · live engine output</span></div>
  <h2 class="monumental-headline">Same orders. <span class="gradient-span">__B_TRUCKS__ → __O_TRUCKS__ trucks, −__SAVE_PCT__% cost.</span></h2>
  <div class="split">
   <div class="blueprint-card">
     <div class="card-title">Today (manual, area-based) vs LoadPilot</div>
     <div class="cmp-legend"><span><i style="background:color-mix(in srgb,var(--text-dim) 45%,transparent)"></i>Today</span><span><i style="background:var(--grad-route)"></i>LoadPilot</span></div>
     __CMP_BARS__
   </div>
   <div class="blueprint-card">
     <div class="card-title">Optimised routes</div>
     <div class="card-sub">Corridors, branches and drop sequence per truck</div>
     <img class="shot" src="__SHOT_ROUTES__" alt="Route map">
     <table class="tt" style="margin-top:10px"><thead><tr><th>Truck</th><th>Driver</th><th>Corridor</th><th>Drops</th><th>km</th></tr></thead><tbody>__TRUCK_ROWS__</tbody></table>
   </div>
  </div>
  <div class="metrics-4col-grid" style="margin-top:16px">
    <div class="metric-box"><div class="metric-value amber">₹__SAVE_YEAR_L__ L</div><div class="metric-label">per DC per year</div><div class="metric-desc">₹__SAVE_DAY__/day × 300 operating days</div></div>
    <div class="metric-box"><div class="metric-value teal">__L_SAVED_YEAR__ L</div><div class="metric-label">diesel avoided per year</div><div class="metric-desc">__L_SAVED__ L/day · __KM_SAVED__ fewer km/day</div></div>
    <div class="metric-box"><div class="metric-value green">__CO2_YEAR_T__ t</div><div class="metric-label">CO₂ avoided per year</div><div class="metric-desc">__CO2_SAVED__ kg/day, Scope-3 reportable</div></div>
    <div class="metric-box"><div class="metric-value red">__CREW_H_SAVED__ h</div><div class="metric-label">crew hours freed daily</div><div class="metric-desc">Includes __SEARCH_H__ h/day of carton digging, now zero</div></div>
  </div>
 </div>
</section>

<!-- ═════════════ 04 VALUE AT SCALE ═════════════ -->
<section class="slide-section" data-title="04 Value at Scale">
 <div class="wrap-max">
  <div class="title-kicker"><span class="kicker-bar"></span><span class="kicker-primary">Value at Scale</span><span class="kicker-sep">/</span><span class="kicker-sub">Interactive ROI model · defaults from the demo day</span></div>
  <h2 class="monumental-headline">Scale one depot's win <span class="gradient-span">across the network.</span></h2>
  <p class="tagline-lead">Large paints, FMCG and building-materials networks run 100–150+ depots. Some serve 50k–160k+ dealers and replenish several times a day. Move the sliders to model your fleet.</p>
  <div class="roi-grid">
   <div class="blueprint-card">
     <div class="slider-row"><label>Trucks dispatched per day <output id="oFleet"></output></label><input type="range" id="sFleet" min="10" max="3000" step="10" value="500"><small>All depots combined</small></div>
     <div class="slider-row"><label>Cost per truck-day (₹) <output id="oCost"></output></label><input type="range" id="sCost" min="2000" max="15000" step="100"><small>Fixed + driver + diesel. Demo baseline shown.</small></div>
     <div class="slider-row"><label>Saving on cost of the day <output id="oPct"></output></label><input type="range" id="sPct" min="5" max="35" step="0.5"><small>Demo: __SAVE_PCT__% · public range 10–25%</small></div>
     <div class="slider-row"><label>Operating days / year <output id="oDays"></output></label><input type="range" id="sDays" min="250" max="365" step="5" value="300"></div>
   </div>
   <div class="blueprint-card">
     <div class="card-sub">Annual value</div>
     <div class="roi-big gradient-span" id="rTotal">—</div>
     <div class="roi-out">
       <div class="metric-box"><div class="metric-value amber" id="rTrucks">—</div><div class="metric-label">trucks freed daily</div></div>
       <div class="metric-box"><div class="metric-value teal" id="rDiesel">—</div><div class="metric-label">litres diesel / year</div></div>
       <div class="metric-box"><div class="metric-value green" id="rCo2">—</div><div class="metric-label">t CO₂ / year</div></div>
       <div class="metric-box"><div class="metric-value red" id="rHours">—</div><div class="metric-label">crew hours of digging / year</div></div>
     </div>
     <p class="note">Truck, diesel, CO₂ and digging figures scale linearly from the demo day's per-truck ratios. This is illustrative; validate it with a 2-week shadow pilot.</p>
   </div>
  </div>
 </div>
</section>

<!-- ═════════════ 05 ARCHITECTURE ═════════════ -->
<section class="slide-section" data-title="05 Architecture">
 <div class="wrap-max">
  <div class="title-kicker"><span class="kicker-bar"></span><span class="kicker-primary">Architecture &amp; Roadmap</span><span class="kicker-sep">/</span><span class="kicker-sub">Built on Google Cloud · deployable in one script</span></div>
  <h2 class="monumental-headline">Enterprise-grade, <span class="gradient-span">industry-agnostic.</span></h2>
  <div class="arch">
    <div class="arch-node hl"><div class="ic">💬</div><h4>Gemini Enterprise</h4><p>The chat surface on web and mobile, with A2UI planning forms, dropdowns, and interactive route and load canvases.</p></div>
    <div class="arch-node hl"><div class="ic">🧠</div><h4>ADK agent · Gemini</h4><p>8 tools: plan, claim a corridor, load plan, ingest orders, scan cartons, fleet &amp; costs. Callbacks guard against fabricated numbers.</p></div>
    <div class="arch-node"><div class="ic">⚙️</div><h4>Vertex AI Agent Engine</h4><p>Managed runtime with a dedicated service account, min-instance warm start, and the same engine updated in place.</p></div>
    <div class="arch-node"><div class="ic">🧮</div><h4>Optimisation core</h4><p>An OR-Tools VRP with time windows, a height-map LIFO 3D packer, a corridor clusterer and a cost model.</p></div>
    <div class="arch-node"><div class="ic">🎬</div><h4>Media &amp; storage</h4><p>A poster PNG, a full-screen HTML animation and an MP4 loading video, delivered from Cloud Storage through signed links.</p></div>
  </div>
  <div class="roadmap">
    <div class="rm"><b>Now · POC</b><p>Demo data for any geography. Photos, QR codes and labels for carton capture. Orders from a list, sheet, PDF or email. 5 truck types.</p></div>
    <div class="rm"><b>Next · Pilot</b><p>Live orders from ERP/DMS (SAP, Salesforce). Google Maps Route Optimization API for road-true ETAs. BigQuery KPI history.</p></div>
    <div class="rm"><b>Later · Scale</b><p>Gemini Live on the dock phone: point the camera at the pallet and have it confirm each carton. Re-planning on the road. Driver app hand-off.</p></div>
  </div>
  <div class="blueprint-card">
    <div class="card-title">Sources</div>
    <div class="sources">
      <div>NCAER for DPIIT, <i>Assessment of Logistics Cost in India</i> (2025): 7.97% of GDP, FY2023-24 · <a href="https://www.ncaer.org/" target="_blank">ncaer.org</a></div>
      <div>Government of India, National Logistics Policy (2022) · <a href="https://pib.gov.in/" target="_blank">pib.gov.in</a></div>
      <div>Capgemini Research Institute, <i>The Last-Mile Delivery Challenge</i> (2019) · <a href="https://www.capgemini.com/insights/research-library/the-last-mile-delivery-challenge/" target="_blank">capgemini.com</a></div>
      <div>NITI Aayog &amp; RMI, <i>Fast Tracking Freight in India</i> (2021) · <a href="https://rmi.org/insight/fast-tracking-freight-in-india/" target="_blank">rmi.org</a></div>
      <div>INFORMS, UPS ORION, Franz Edelman Award (2016) · <a href="https://www.informs.org/" target="_blank">informs.org</a></div>
      <div>World Economic Forum, <i>The Future of the Last-Mile Ecosystem</i> (2020) · <a href="https://www.weforum.org/" target="_blank">weforum.org</a></div>
      <div>Vendor-reported (flagged): Descartes, Locus, and McKinsey figures cited by Locus</div>
      <div>Demo numbers: LoadPilot engine run on synthetic data for __STOPS__ Mumbai MMR dealers (seed 42)</div>
    </div>
  </div>
 </div>
</section>

</main>

<script>
const DEMO = __DEMO_JSON__;
const slides = [...document.querySelectorAll('.slide-section')];
let cur = 0;
const tabs = document.getElementById('slideTabs');
slides.forEach((s,i)=>{const b=document.createElement('button');b.className='slide-tab';b.textContent=s.dataset.title.split(' ')[0];b.title=s.dataset.title;b.onclick=()=>goToSlide(i);tabs.appendChild(b);});
function goToSlide(i){
  cur=Math.max(0,Math.min(slides.length-1,i));
  slides.forEach((s,k)=>s.classList.toggle('active',k===cur));
  [...tabs.children].forEach((t,k)=>t.classList.toggle('active',k===cur));
  document.getElementById('slideCounter').textContent=(cur+1)+' / '+slides.length;
  document.getElementById('prevBtn').disabled=cur===0;
  document.getElementById('nextBtn').disabled=cur===slides.length-1;
  history.replaceState(null,'','#'+cur);
  if(cur===2) replayLifo();
  window.scrollTo(0,0);
}

/* Fit-to-screen: zoom the active slide so its content uses the full viewport. */
function fitSlide(){
  const sec=document.querySelector('.slide-section.active'); if(!sec) return;
  const w=sec.querySelector('.wrap-max'); if(!w) return;
  w.style.zoom=1;
  if(window.innerWidth<1100){return;}
  const cs=getComputedStyle(sec);
  const availW=sec.clientWidth-parseFloat(cs.paddingLeft)-parseFloat(cs.paddingRight);
  const availH=window.innerHeight-60-parseFloat(cs.paddingTop)-parseFloat(cs.paddingBottom);
  const z=Math.max(.7,Math.min(availW/w.offsetWidth,availH/w.scrollHeight,1.15));
  w.style.zoom=z.toFixed(3);
}
window.addEventListener('resize',fitSlide);
window.addEventListener('load',fitSlide);
if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fitSlide);
const _goRaw=goToSlide;goToSlide=function(i){_goRaw(i);requestAnimationFrame(fitSlide);};
function next(){goToSlide(cur+1)} function prev(){goToSlide(cur-1)}
document.addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key)){e.preventDefault();next()}if(['ArrowLeft','PageUp'].includes(e.key)){e.preventDefault();prev()}});
let tx=null;document.addEventListener('touchstart',e=>tx=e.touches[0].clientX);document.addEventListener('touchend',e=>{if(tx===null)return;const d=e.changedTouches[0].clientX-tx;if(Math.abs(d)>60)(d<0?next:prev)();tx=null;});
function toggleTheme(){const h=document.documentElement;const d=h.classList.contains('theme-dark');h.classList.toggle('theme-dark',!d);h.classList.toggle('theme-light',d);localStorage.setItem('lp-theme',d?'light':'dark');}
if(localStorage.getItem('lp-theme')==='dark'){document.documentElement.classList.replace('theme-light','theme-dark');}
function replayLifo(){document.querySelectorAll('.lifo-box').forEach(b=>{b.style.animation='none';b.offsetHeight;b.style.animation='';});}

/* ── Cockpit ── */
const Q=[
 {chip:'Plan today',p:'Plan today\u2019s dispatch from Bhiwandi DC for all __STOPS__ dealer orders. Minimise cost.',t:'plan_dispatch(objective="lowest_cost") \u2192 17 s',r:'<b>__B_TRUCKS__ \u2192 __O_TRUCKS__ trucks, \u20b9__B_COST__ \u2192 \u20b9__O_COST__ (\u2212__SAVE_PCT__%).</b> All loads pass the LIFO door rule, and __SEARCH_H__ h of carton digging is gone. The dispatch canvas has routes, 3D loads and the loading video, with the full report below.'},
 {chip:'Driver claims West',p:'Ravi says he has been given the West route. Re-plan around that.',t:'claim_corridor(driver="Ravi", corridor="W") \u2192 24 s',r:'<b>Ravi is pinned to the West corridor.</b> West is now split into two branches so the second West truck never overlaps with him. The fleet is re-optimised and the savings hold.'},
 {chip:'Load plan T17',p:'Show me how to load the 17-ft truck: what goes in first?',t:'get_truck_load_plan(truck_id=...) \u2192 5 s',r:'<b>Load the last drop first, behind the cab.</b> Each stop\u2019s cartons form a contiguous block, with fragile tinters on top and pails upright. An animated 3D loading sequence and a printable dock sheet are attached.'},
 {chip:'Scan cartons (photo)',p:'Here is a photo of the staging floor. Add these cartons to today\u2019s plan.',t:'scan_box_manifest(image) \u2192 QR 8/8 decoded',r:'<b>8 cartons recognised</b> across 3 stops from their QR codes and labels. Dimensions and weights were matched to the SKU master, the plan was refreshed, and one T14 now carries 2 more drops.'},
 {chip:'Orders from email',p:'Take the orders from this email and the attached Excel and plan it.',t:'ingest_delivery_orders(...) \u2192 plan_dispatch',r:'<b>Orders parsed:</b> dealers geocoded, SKUs mapped to carton dimensions and time windows applied. Any issues are listed before planning so nothing is dropped silently.'}
];
let qi=0,typer=null;
const pills=document.getElementById('cockpitPills');
Q.forEach((q,i)=>{const b=document.createElement('button');b.className='query-chip';b.textContent=q.chip;b.onclick=()=>setQuery(i);pills.appendChild(b);});
function setQuery(i){
  qi=i;[...pills.children].forEach((c,k)=>c.classList.toggle('active',k===i));
  const el=document.getElementById('cockpitText'),dr=document.getElementById('cockpitDrawer');
  clearInterval(typer);el.textContent='';dr.innerHTML='<div class="tool-trace">thinking\u2026</div>';
  let k=0;const s=Q[i].p;
  typer=setInterval(()=>{el.textContent=s.slice(0,++k);if(k>=s.length){clearInterval(typer);setTimeout(()=>{dr.innerHTML='<div class="tool-trace">\u25b8 '+Q[i].t+'</div>'+Q[i].r;},350);}},18);
}
function cycleQuery(){setQuery((qi+1)%Q.length)}
setQuery(0);
setInterval(()=>{if(cur===0&&!document.hidden)cycleQuery()},9000);

/* ── ROI ── */
const $=id=>document.getElementById(id);
$('sCost').value=DEMO.base_cost_per_truck;$('sPct').value=DEMO.pct;
const fmtIN=v=>Math.round(v).toLocaleString('en-IN');
function crore(v){return v>=1e7?'\u20b9'+(v/1e7).toFixed(2)+' Cr':'\u20b9'+(v/1e5).toFixed(1)+' L'}
function roi(){
  const f=+$('sFleet').value,c=+$('sCost').value,p=+$('sPct').value,d=+$('sDays').value;
  $('oFleet').textContent=fmtIN(f);$('oCost').textContent='\u20b9'+fmtIN(c);$('oPct').textContent=p+'%';$('oDays').textContent=d;
  $('rTotal').textContent=crore(f*c*p/100*d)+' / yr';
  $('rTrucks').textContent=fmtIN(f*DEMO.trucks_freed_ratio);
  $('rDiesel').textContent=fmtIN(f*DEMO.litres_per_truck_saved*d);
  $('rCo2').textContent=fmtIN(f*DEMO.co2_per_truck_saved*d/1000);
  $('rHours').textContent=fmtIN(f*DEMO.search_h_per_truck*d);
}
['sFleet','sCost','sPct','sDays'].forEach(id=>$(id).addEventListener('input',roi));roi();

goToSlide(parseInt((location.hash||'#0').slice(1))||0);
</script>
</body>
</html>
"""


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "loadpilot_executive_presentation.html"
    out.write_text(build_executive_presentation_html(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
