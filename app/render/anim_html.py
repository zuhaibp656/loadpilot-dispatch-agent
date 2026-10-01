"""Build self-contained animation HTML (engine.js + plan JSON inlined, no network access).

Used for:
  * A2UI `IFrameSrcdoc` (sandboxed, CSP connect-src 'none') inside the Gemini Enterprise canvas.
  * A full-screen standalone page uploaded to GCS (both views with tabs).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

try:
    from app.contracts import DispatchPlan, TruckRoute
    from app.data.demo_mmr import GAZETTEER
    from app.data.master_data import CORRIDOR_NAMES
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan, TruckRoute
    from data.demo_mmr import GAZETTEER
    from data.master_data import CORRIDOR_NAMES

_ENGINE_JS = (Path(__file__).parent / "anim" / "engine.js").read_text(encoding="utf-8")

ROUTE_COLORS = ["#00e5ff", "#ff6d00", "#76ff03", "#ff4081", "#ffd600", "#b388ff", "#18ffff",
                "#ff9e80", "#69f0ae", "#ea80fc", "#ffff00", "#82b1ff"]
BASE_COLORS = ["#90a4ae", "#b0bec5", "#78909c", "#cfd8dc", "#a1887f", "#bcaaa4", "#9e9e9e",
               "#b39ddb", "#80cbc4", "#ef9a9a"]

_CSS = """
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#070b16;color:#e8eaed;
font:14px/1.4 Inter,Roboto,'Google Sans',Arial,sans-serif;overflow:hidden}
#lp-app{height:100%;display:flex;flex-direction:column}
.lp-tabs{display:flex;gap:6px;padding:8px 10px 0}.lp-tab{background:#121a2e;color:#9aa0a6;border:1px solid #243049;
border-bottom:none;border-radius:10px 10px 0 0;padding:8px 16px;cursor:pointer;font-weight:700;font-size:13.5px}
.lp-tab.on{background:#1a2440;color:#fff;border-color:#3b4b72}
.lp-pane{flex:1;display:flex;flex-direction:column;min-height:0;border-top:1px solid #1f2a44}
.lp-top{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:9px 14px;
background:linear-gradient(90deg,#0f1730,#111b36);flex-wrap:wrap}
.lp-title{font-size:16px;font-weight:700}.lp-muted{color:#8a94a6;font-weight:400}
.lp-stats{display:flex;gap:7px;flex-wrap:wrap}.kv{background:#16203a;border:1px solid #243049;border-radius:10px;
padding:5px 10px;display:flex;flex-direction:column;min-width:82px}.kv span{font-size:11px;color:#8a94a6;
text-transform:uppercase;letter-spacing:.05em;font-weight:600}.kv b{font-size:14.5px;font-weight:700}
.ok{color:#5bf59a}.bad{color:#ff8a80}
.lp-body{flex:1;display:flex;min-height:0}.lp-cwrap{flex:1;position:relative;min-width:0}
.lp-canvas{display:block;width:100%;height:100%;cursor:grab}
.lp-legend{width:290px;overflow:auto;padding:10px 12px;background:#0b1224;border-left:1px solid #1f2a44}
.lp-lh{font-size:12px;color:#8ab4f8;text-transform:uppercase;letter-spacing:.06em;margin:3px 0 9px;font-weight:800}
.lp-li{display:flex;gap:8px;align-items:baseline;padding:6px 8px;border-radius:8px;font-size:13.5px;cursor:default;line-height:1.35}
.lp-li i{width:12px;height:12px;border-radius:3px;flex:none;transform:translateY(1px)}
.lp-li.on{background:#1d2a4a;outline:1px solid #3b4b72}.lp-li:hover{background:#15203a}
.lp-hud{position:absolute;left:14px;bottom:12px;background:rgba(10,16,32,.88);border:1px solid #243049;
border-radius:10px;padding:7px 12px;font-size:13px}
.lp-banner{position:absolute;left:50%;top:12px;transform:translateX(-50%);background:rgba(16,24,48,.95);
border:1px solid #3b4b72;border-radius:12px;padding:9px 16px;font-size:14px;transition:opacity .3s;opacity:0;
white-space:nowrap;font-weight:600}.lp-banner i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:8px}
.lp-clock{position:absolute;right:16px;top:10px;font:700 28px 'Roboto Mono',monospace;color:#fdd663;
text-shadow:0 0 14px rgba(253,214,99,.5)}
.lp-ctrl{display:flex;align-items:center;gap:9px;padding:9px 12px;background:#0b1224;border-top:1px solid #1f2a44;
flex-wrap:wrap}.lp-btn{background:#1a2440;color:#e8eaed;border:1px solid #3b4b72;border-radius:18px;
padding:6px 14px;cursor:pointer;font-weight:700;font-size:13px}.lp-btn:hover{background:#22305a}.lp-play{min-width:48px}
.lp-scrub{flex:1;min-width:130px;accent-color:#8ab4f8}
.lp-trucks{display:flex;gap:6px;flex-wrap:wrap}.lp-chip{background:#121a2e;color:#e8eaed;border:1px solid #3b4b72;
border-left-width:4px;border-radius:14px;padding:5px 11px;cursor:pointer;font-weight:700;font-size:13px}
.lp-chip small{color:#8a94a6;font-weight:400}.lp-chip.on{background:#22305a}
.lp-seg{display:flex;border:1px solid #3b4b72;border-radius:18px;overflow:hidden}
.lp-seg button{background:#121a2e;color:#9aa0a6;border:none;padding:6px 14px;cursor:pointer;font-weight:700;font-size:12.5px}
.lp-seg button.on{background:#8ab4f8;color:#0b1020}
@media (max-width:640px){.lp-legend{display:none}}
.lp-li.lp-click{cursor:pointer}.lp-li div{min-width:0}
.lp-num{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;border-radius:11px;
font:700 12px Inter,Roboto,Arial;color:#0b1020;flex:none;padding:0 6px}
.lp-pop{position:absolute;z-index:5;width:330px;background:rgba(12,18,36,.98);border:1px solid #3b4b72;border-radius:14px;
box-shadow:0 14px 35px rgba(0,0,0,.6);font-size:13.5px;overflow:hidden}
.lp-pop-h{display:flex;gap:10px;align-items:flex-start;padding:12px 14px;border-left:5px solid;background:#111a33}
.lp-pop-h b{font-size:15px}.lp-x{margin-left:auto;background:none;border:none;color:#9aa0a6;font-size:20px;cursor:pointer;line-height:1}
.lp-pop-g{display:grid;grid-template-columns:76px 1fr;gap:6px 12px;padding:12px 14px}
.lp-pop-g span{color:#8a94a6;font-size:12px;text-transform:uppercase;letter-spacing:.05em;padding-top:1px;font-weight:600}
.lp-zoom{position:absolute;right:14px;top:54px;display:flex;flex-direction:column;gap:5px;z-index:4}
.lp-zoom button{width:36px;height:36px;border-radius:10px;border:1px solid #3b4b72;background:rgba(16,24,48,.94);color:#e8eaed;
font:700 18px Inter,Roboto,Arial;cursor:pointer}.lp-zoom button:hover{background:#22305a}
.lp-attr{position:absolute;right:10px;bottom:8px;font-size:11px;color:#9aa0a6;background:rgba(8,12,24,.8);padding:3px 7px;border-radius:6px}
.lp-card{position:absolute;left:14px;top:14px;z-index:5;width:350px;max-height:calc(100% - 75px);overflow:auto;
background:rgba(12,18,36,.98);border:1px solid #3b4b72;border-radius:14px;box-shadow:0 14px 35px rgba(0,0,0,.6);font-size:13.5px}
.lp-card .lp-pop-g{grid-template-columns:70px 1fr}
.lp-tip{position:absolute;z-index:6;pointer-events:none;max-width:340px;background:rgba(8,12,24,.97);border:1px solid #5b6b92;
border-radius:11px;padding:8px 12px;font-size:13px;line-height:1.5;box-shadow:0 10px 24px rgba(0,0,0,.6)}
.lp-li.sel{background:#2a3a66;outline:2px solid #fdd663}
.lp-go{display:block;width:calc(100% - 24px);margin:0 12px 14px;background:#fdd663;color:#111;border:none;border-radius:18px;
padding:8px 12px;font-weight:800;font-size:13px;cursor:pointer}.lp-go:hover{background:#ffe38a}
.lp-btn-sm{padding:3px 9px;font-size:11px;border-radius:12px;font-weight:700}
.lp-step-tag{display:inline-block;background:#243049;color:#8ab4f8;font-size:11px;font-weight:800;padding:2px 6px;border-radius:4px;margin-right:5px}
.lp-vmodes{display:flex;gap:5px;padding:7px 12px;background:#141d36;border-bottom:1px solid #243049;flex-wrap:wrap;align-items:center}
.lp-vbtn{background:#1b243d;color:#9aa0a6;border:1px solid #3b4b72;border-radius:13px;padding:4px 10px;font-size:12px;cursor:pointer;font-weight:700}
.lp-vbtn:hover{background:#28365a;color:#fff}
.lp-vbtn.on{background:#8ab4f8;color:#0b1020;border-color:#8ab4f8}
.lp-vbtn.lp-rep{margin-left:auto;background:#2a3a66;color:#fdd663;border-color:#fdd663}
.lp-vbtn.lp-rep:hover{background:#3b4f88}
.lp-btn.lp-active{background:#8ab4f8;color:#0b1020;border-color:#8ab4f8}
"""


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


_ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/"
TILE_URL = os.environ.get("LOADPILOT_TILE_URL", _ESRI + "World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}")
LABEL_URL = os.environ.get("LOADPILOT_LABEL_URL", _ESRI + "World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}")
TILE_ATTR = os.environ.get("LOADPILOT_TILE_ATTR", "Tiles © Esri — Esri, HERE, Garmin, © OpenStreetMap contributors")
_BASEMAPS: dict[str, dict] = {}


BASEMAP_CLASSES = tuple(os.environ.get("LOADPILOT_BASEMAP_CLASSES", "coast,motorway").split(","))


def _crop(lines: list, scale: float, box: tuple[float, float, float, float]) -> list:
    """Keep only delta-encoded lon,lat polylines that touch box (s, w, n, e)."""
    s, w, n, e = box
    out = []
    for flat in lines:
        lon = lat = 0
        hit = False
        for i in range(0, len(flat), 2):
            lon += flat[i]
            lat += flat[i + 1]
            if s <= lat / scale <= n and w <= lon / scale <= e:
                hit = True
                break
        if hit:
            out.append(flat)
    return out


def _basemap_for(lat: float, lon: float, box: tuple[float, float, float, float] | None = None) -> dict | None:
    """Inlined OSM vector basemap covering the hub (app/data/basemap_*.json), if any."""
    if not _BASEMAPS:
        for p in (Path(__file__).resolve().parents[1] / "data").glob("basemap_*.json"):
            try:
                _BASEMAPS[p.stem] = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
    for bm in _BASEMAPS.values():
        s, w, n, e = bm["bbox"]
        if s <= lat <= n and w <= lon <= e:
            scale = bm.get("scale", 1e4)
            res: dict = {"scale": scale}
            for k in BASEMAP_CLASSES:
                if k in bm:
                    res[k] = _crop(bm[k], scale, box) if box else bm[k]
            return res
    return None


def _plan_box(plan: DispatchPlan, pad: float = 0.08) -> tuple[float, float, float, float]:
    lats = [plan.hub.lat] + [rs.stop.lat for r in plan.routes + plan.baseline_routes for rs in r.stops]
    lons = [plan.hub.lon] + [rs.stop.lon for r in plan.routes + plan.baseline_routes for rs in r.stops]
    return min(lats) - pad, min(lons) - pad, max(lats) + pad, max(lons) + pad


def _enc(pts: list) -> list[int]:
    out, pa, pb = [], 0, 0
    for a, b in pts:
        ia, ib = round(a * 1e5), round(b * 1e5)
        out += [ia - pa, ib - pb]
        pa, pb = ia, ib
    return out


def _stop_json(rs) -> dict:
    s = rs.stop
    skus: dict[str, int] = {}
    for bx in s.boxes:
        skus[bx.description] = skus.get(bx.description, 0) + 1
    top = sorted(skus.items(), key=lambda kv: -kv[1])[:3]
    return {"seq": rs.seq, "name": s.name[:40], "addr": s.address[:60], "area": s.area,
            "lat": round(s.lat, 5), "lon": round(s.lon, 5), "arr": rs.arrive_min, "dep": rs.depart_min,
            "win": [s.window_start_min, s.window_end_min], "n": len(s.boxes),
            "kg": round(sum(b.weight_kg for b in s.boxes)), "frag": sum(1 for b in s.boxes if b.fragile),
            "skus": " · ".join(f"{n}× {d}" for d, n in top)}


def _route_json(r: TruckRoute, color: str, legs: list | None, eps: float = 0.0007) -> dict:
    hub = (r.path[0][0], r.path[0][1])
    if legs and eps:
        try:
            from app.geo.roads import _dp
        except ImportError:  # pragma: no cover
            from geo.roads import _dp
        legs = [_dp(list(lg), eps) for lg in legs]
    if not legs:
        wps = [hub] + [(rs.stop.lat, rs.stop.lon) for rs in r.stops] + [hub]
        legs = [[wps[i], wps[i + 1]] for i in range(len(wps) - 1)]
    base = r.truck_id.startswith("BASE")
    return {
        "id": r.driver if base else r.truck_id, "color": color,
        "driver": r.truck_type.code if base else r.driver,
        "corridor": r.corridor, "cname": CORRIDOR_NAMES.get(r.corridor, r.corridor), "branch": r.branch,
        "km": round(r.km), "start": r.start_min, "end": r.end_min,
        "legs": [_enc(lg) for lg in legs],
        "stops": [_stop_json(rs) for rs in r.stops],
    }


def _load_trucks(plan: DispatchPlan, focus_truck_id: str | None, max_trucks: int | None,
                 only_truck: str | None = None) -> list[dict]:
    trucks = []
    routes = [r for r in plan.routes if not only_truck or r.truck_id == only_truck]
    if focus_truck_id:
        routes = sorted(routes, key=lambda r: r.truck_id != focus_truck_id)
    for r in routes[: max_trucks or len(routes)]:
        lp = plan.loads.get(r.truck_id)
        if lp is None:
            continue
        placed = sorted(lp.placed, key=lambda q: q.load_step)
        trucks.append({
            "id": r.truck_id, "name": r.truck_type.name, "L": lp.truck_type.inner_l_cm,
            "W": lp.truck_type.inner_w_cm, "H": lp.truck_type.inner_h_cm,
            "color": ROUTE_COLORS[plan.routes.index(r) % len(ROUTE_COLORS)], "driver": r.driver,
            "corridor": r.corridor, "branch": r.branch, "fill": lp.volume_fill_pct,
            "wfill": lp.weight_fill_pct, "lifo": lp.lifo_ok,
            "zones": [[z.stop_seq, z.x_start, z.x_end] for z in lp.zones],
            "stops": [{"seq": rs.seq, "name": rs.stop.name[:32], "n": len(rs.stop.boxes),
                       "eta": _hhmm(rs.arrive_min),
                       "addr": rs.stop.address.split(", ")[-1] + (f" · {rs.stop.area}" if rs.stop.area else "")}
                      for rs in r.stops],
            "desc": {p.box.sku: p.box.description[:40] for p in placed},
            "boxes": [[round(p.x), round(p.y), round(p.z), p.l, p.w, p.h, p.stop_seq,
                       1 if p.box.fragile else 0, p.box.sku, round(p.box.weight_kg, 1), p.box.box_id]
                      for p in placed],
        })
    return trucks


def plan_to_anim_data(plan: DispatchPlan, focus_truck_id: str | None = None,
                      max_trucks: int | None = None, mode: str = "both",
                      only_truck: str | None = None, start: str | None = None) -> dict:
    """only_truck: driver view (one truck's route + load). start: 'load' opens the 3D tab first."""
    data: dict = {"hub": {"name": plan.hub.name, "lat": plan.hub.lat, "lon": plan.hub.lon}}
    if start:
        data["start"] = start
    if mode in ("both", "load"):
        data["trucks"] = _load_trucks(plan, focus_truck_id, max_trucks, only_truck)
    if mode in ("both", "routes"):
        try:
            from app.geo.roads import plan_road_legs, provider_name
        except ImportError:  # pragma: no cover
            from geo.roads import plan_road_legs, provider_name
        road = plan_road_legs(plan)
        k = plan.baseline, plan.optimized
        opt_routes = [(i, r) for i, r in enumerate(plan.routes) if not only_truck or r.truck_id == only_truck]
        base_routes = [] if only_truck else list(enumerate(plan.baseline_routes))
        all_routes = [r for _, r in opt_routes] + [r for _, r in base_routes]
        data.update({
            "clock": [min((r.start_min for r in all_routes), default=420) - 10,
                      max((r.end_min for r in all_routes), default=1140) + 10],
            "routes": {
                "opt": [_route_json(r, ROUTE_COLORS[i % len(ROUTE_COLORS)], road["opt"].get(r.truck_id))
                        for i, r in opt_routes],
                # today's manual routes: straight legs (they are only a faint dashed comparison)
                "base": [_route_json(r, BASE_COLORS[i % len(BASE_COLORS)], None)
                         for i, r in base_routes],
            },
            "kpi": {
                "base": {"trucks": k[0].trucks, "km": round(k[0].km), "cost": f"₹{k[0].cost_total:,.0f}"},
                "opt": {"trucks": k[1].trucks, "km": round(k[1].km), "cost": f"₹{k[1].cost_total:,.0f}"},
                "saved": f"₹{plan.savings_inr:,.0f}/day",
            },
            "places": [[n, v[0], v[1]] for n, v in GAZETTEER.items()],
            "basemap": _basemap_for(plan.hub.lat, plan.hub.lon, _plan_box(plan)),
            "tiles": TILE_URL, "labels": LABEL_URL, "tileAttr": TILE_ATTR,
            "router": provider_name(),
        })
        if only_truck and opt_routes:
            r = opt_routes[0][1]
            data["driver"] = {"id": r.truck_id, "name": r.driver, "stops": len(r.stops), "km": round(r.km),
                              "start": _hhmm(r.start_min), "end": _hhmm(r.end_min),
                              "cartons": sum(len(rs.stop.boxes) for rs in r.stops)}
    return data


def build_anim_html(plan: DispatchPlan, mode: str = "both", focus_truck_id: str | None = None,
                    max_trucks: int | None = None, only_truck: str | None = None,
                    start: str | None = None) -> str:
    data = plan_to_anim_data(plan, focus_truck_id=focus_truck_id, max_trucks=max_trucks, mode=mode,
                             only_truck=only_truck, start=start)
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    engine_js = (Path(__file__).parent / "anim" / "engine.js").read_text(encoding="utf-8")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>LoadPilot · {plan.plan_id}</title><style>{_CSS}</style></head>"
        "<body><div id='lp-app'></div>"
        f"<script>window.LP={payload};window.LP_MODE={json.dumps(mode)};</script>"
        f"<script>{engine_js}</script></body></html>"
    )

