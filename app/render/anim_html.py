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
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#090d1a;color:#e2e8f0;
font:13.5px/1.45 Inter,-apple-system,BlinkMacSystemFont,'Google Sans',Roboto,sans-serif;overflow:hidden;-webkit-font-smoothing:antialiased}
#lp-app{height:100%;display:flex;flex-direction:column}
.lp-tabs{display:flex;gap:4px;padding:8px 14px 0;background:rgba(9,13,26,0.95)}
.lp-tab{background:rgba(18,26,48,0.7);color:#94a3b8;border:1px solid rgba(255,255,255,0.07);
border-bottom:none;border-radius:10px 10px 0 0;padding:8px 18px;cursor:pointer;font-weight:700;font-size:13px;
transition:all .18s ease;display:inline-flex;align-items:center;gap:6px}
.lp-tab:hover{color:#e2e8f0;background:rgba(30,41,69,0.8)}
.lp-tab.on{background:rgba(26,38,68,0.95);color:#38bdf8;border-color:rgba(56,189,248,0.35);box-shadow:0 -2px 10px rgba(56,189,248,0.08)}
.lp-pane{flex:1;display:flex;flex-direction:column;min-height:0;border-top:1px solid rgba(255,255,255,0.08)}
.lp-top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:10px 16px;
background:linear-gradient(90deg,rgba(15,23,42,0.92),rgba(20,30,55,0.88));backdrop-filter:blur(14px);flex-wrap:wrap;border-bottom:1px solid rgba(255,255,255,0.06)}
.lp-title{font-size:15px;font-weight:700;color:#f8fafc;display:flex;align-items:center;gap:6px}.lp-muted{color:#94a3b8;font-weight:400;font-size:12.5px}
.lp-stats{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.kv{background:rgba(22,32,58,0.65);border:1px solid rgba(255,255,255,0.07);border-radius:10px;
padding:5px 12px;display:flex;flex-direction:column;min-width:76px;transition:border-color .15s}
.kv:hover{border-color:rgba(56,189,248,0.3)}
.kv span{font-size:10.5px;color:#94a3b8;text-transform:uppercase;letter-spacing:.06em;font-weight:600}
.kv b{font-size:13.5px;font-weight:700;color:#f1f5f9}
.ok{color:#4ade80}.bad{color:#f87171}
.lp-body{flex:1;display:flex;min-height:0}.lp-cwrap{flex:1;position:relative;min-width:0;overflow:hidden}
.lp-canvas{display:block;width:100%;height:100%;cursor:grab}
.lp-legend{width:310px;overflow-y:auto;padding:12px 14px;background:rgba(11,17,33,0.95);border-left:1px solid rgba(255,255,255,0.07);backdrop-filter:blur(12px)}
.lp-lh{font-size:11.5px;color:#38bdf8;text-transform:uppercase;letter-spacing:.07em;margin:4px 0 10px;font-weight:800;display:flex;align-items:center;justify-content:space-between}
.lp-li{display:flex;gap:9px;align-items:baseline;padding:8px 10px;border-radius:10px;font-size:13px;cursor:default;line-height:1.4;transition:all .15s ease;margin-bottom:3px}
.lp-li i{width:11px;height:11px;border-radius:3px;flex:none;transform:translateY(1px)}
.lp-li.on{background:rgba(30,45,77,0.85);outline:1px solid rgba(56,189,248,0.45);box-shadow:0 2px 8px rgba(0,0,0,0.3)}
.lp-li:hover{background:rgba(24,36,64,0.75)}
.lp-li.dim{opacity:0.42}
.lp-li.dim:hover{opacity:0.85}
.lp-hud{position:absolute;left:16px;bottom:14px;background:rgba(15,23,42,0.88);backdrop-filter:blur(10px);
border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:8px 14px;font-size:12.5px;box-shadow:0 8px 24px rgba(0,0,0,0.4)}
.lp-banner{position:absolute;left:50%;top:14px;transform:translateX(-50%);background:rgba(15,23,42,0.92);backdrop-filter:blur(12px);
border:1px solid rgba(56,189,248,0.4);border-radius:14px;padding:9px 18px;font-size:13.5px;transition:opacity .3s,transform .3s;opacity:0;
white-space:nowrap;font-weight:600;box-shadow:0 10px 30px rgba(0,0,0,0.5)}
.lp-banner i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:8px}
.lp-clock{position:absolute;right:18px;top:14px;font:700 24px 'Roboto Mono',monospace;color:#facc15;
background:rgba(15,23,42,0.82);backdrop-filter:blur(8px);padding:4px 12px;border-radius:10px;border:1px solid rgba(250,204,21,0.25);
text-shadow:0 0 12px rgba(250,204,21,0.35);letter-spacing:1px}
.lp-ctrl{display:flex;align-items:center;gap:10px;padding:10px 16px;background:rgba(11,17,33,0.96);border-top:1px solid rgba(255,255,255,0.07);
backdrop-filter:blur(12px);flex-wrap:wrap}
.lp-btn{background:rgba(26,38,68,0.8);color:#e2e8f0;border:1px solid rgba(255,255,255,0.12);border-radius:20px;
padding:6px 15px;cursor:pointer;font-weight:700;font-size:12.5px;transition:all .18s ease;display:inline-flex;align-items:center;gap:6px}
.lp-btn:hover{background:rgba(40,58,98,0.95);border-color:rgba(56,189,248,0.4);color:#fff}
.lp-play{min-width:44px;justify-content:center}
.lp-scrub{flex:1;min-width:140px;height:6px;accent-color:#38bdf8;cursor:pointer;border-radius:3px}
.lp-truck-bar{display:flex;gap:7px;padding:8px 16px;background:rgba(13,20,38,0.9);border-bottom:1px solid rgba(255,255,255,0.06);overflow-x:auto;align-items:center}
.lp-truck-bar-lbl{font-size:11px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-right:4px;flex:none}
.lp-chip{background:rgba(22,32,58,0.7);color:#cbd5e1;border:1px solid rgba(255,255,255,0.1);
border-left-width:4px;border-radius:18px;padding:5px 13px;cursor:pointer;font-weight:700;font-size:12.5px;transition:all .18s;white-space:nowrap}
.lp-chip small{color:#94a3b8;font-weight:400;margin-left:4px}
.lp-chip:hover{background:rgba(34,48,82,0.9);color:#fff}
.lp-chip.on{background:rgba(30,50,90,0.95);color:#fff;border-color:rgba(56,189,248,0.6);box-shadow:0 0 12px rgba(56,189,248,0.25)}
.lp-chip.dim{opacity:0.55}
.lp-seg{display:flex;border:1px solid rgba(255,255,255,0.12);border-radius:20px;overflow:hidden;background:rgba(18,26,48,0.6)}
.lp-seg button{background:transparent;color:#94a3b8;border:none;padding:6px 14px;cursor:pointer;font-weight:700;font-size:12px;transition:all .15s}
.lp-seg button.on{background:#38bdf8;color:#090d1a}
@media (max-width:640px){.lp-legend{display:none}}
.lp-li.lp-click{cursor:pointer}.lp-li div{min-width:0}
.lp-num{display:inline-flex;align-items:center;justify-content:center;min-width:22px;height:22px;border-radius:11px;
font:700 11.5px Inter,-apple-system,sans-serif;color:#090d1a;flex:none;padding:0 5px}
.lp-pop{position:absolute;z-index:10;width:340px;background:rgba(15,23,42,0.96);backdrop-filter:blur(16px);
border:1px solid rgba(56,189,248,0.3);border-radius:16px;box-shadow:0 20px 45px rgba(0,0,0,0.65);font-size:13px;overflow:hidden}
.lp-pop-h{display:flex;gap:10px;align-items:flex-start;padding:13px 15px;border-left:5px solid;background:rgba(20,30,55,0.85)}
.lp-pop-h b{font-size:14.5px}.lp-x{margin-left:auto;background:none;border:none;color:#94a3b8;font-size:20px;cursor:pointer;line-height:1}
.lp-x:hover{color:#fff}
.lp-pop-g{display:grid;grid-template-columns:76px 1fr;gap:7px 12px;padding:13px 15px}
.lp-pop-g span{color:#94a3b8;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;padding-top:1px;font-weight:600}
.lp-zoom{position:absolute;right:16px;top:60px;display:flex;flex-direction:column;gap:6px;z-index:4}
.lp-zoom button{width:36px;height:36px;border-radius:10px;border:1px solid rgba(255,255,255,0.12);background:rgba(15,23,42,0.9);
backdrop-filter:blur(8px);color:#e2e8f0;font:700 17px Inter,sans-serif;cursor:pointer;transition:all .15s}
.lp-zoom button:hover{background:rgba(30,45,77,0.95);border-color:rgba(56,189,248,0.4);color:#fff}
.lp-attr{position:absolute;right:12px;bottom:8px;font-size:10.5px;color:#94a3b8;background:rgba(9,13,26,0.85);backdrop-filter:blur(4px);padding:3px 8px;border-radius:6px}
.lp-card{position:absolute;left:16px;top:16px;z-index:10;width:320px;max-height:calc(100% - 80px);overflow-y:auto;
background:rgba(15,23,42,0.96);backdrop-filter:blur(16px);border:1px solid rgba(56,189,248,0.3);border-radius:16px;
box-shadow:0 20px 45px rgba(0,0,0,0.65);font-size:13px}
.lp-card .lp-pop-g{grid-template-columns:72px 1fr}
.lp-tip{position:absolute;z-index:12;pointer-events:none;max-width:340px;background:rgba(15,23,42,0.96);backdrop-filter:blur(12px);
border:1px solid rgba(56,189,248,0.4);border-radius:12px;padding:8px 13px;font-size:12.5px;line-height:1.5;box-shadow:0 12px 28px rgba(0,0,0,0.6)}
.lp-li.sel{background:rgba(34,54,92,0.9);outline:2px solid #38bdf8}
.lp-go{display:block;width:calc(100% - 26px);margin:0 13px 14px;background:#38bdf8;color:#090d1a;border:none;border-radius:20px;
padding:9px 14px;font-weight:800;font-size:12.5px;cursor:pointer;transition:all .18s;box-shadow:0 4px 14px rgba(56,189,248,0.3)}
.lp-go:hover{background:#7dd3fc;box-shadow:0 6px 18px rgba(56,189,248,0.45)}
.lp-btn-sm{padding:3px 10px;font-size:11px;border-radius:14px;font-weight:700}
.lp-step-tag{display:inline-block;background:rgba(56,189,248,0.14);color:#38bdf8;border:1px solid rgba(56,189,248,0.3);
font-size:10.5px;font-weight:800;padding:2px 7px;border-radius:6px;margin-right:6px}
.lp-active-pill{display:inline-block;background:rgba(74,222,128,0.15);color:#4ade80;border:1px solid rgba(74,222,128,0.35);
font-size:10px;font-weight:800;padding:1px 6px;border-radius:4px;margin-left:6px;text-transform:uppercase}
.lp-vmodes{display:flex;gap:6px;padding:8px 14px;background:rgba(20,30,55,0.7);border-bottom:1px solid rgba(255,255,255,0.07);flex-wrap:wrap;align-items:center}
.lp-vbtn{background:rgba(26,38,68,0.7);color:#94a3b8;border:1px solid rgba(255,255,255,0.1);border-radius:14px;padding:5px 11px;font-size:11.5px;cursor:pointer;font-weight:700;transition:all .15s}
.lp-vbtn:hover{background:rgba(40,58,98,0.9);color:#fff}
.lp-vbtn.on{background:#38bdf8;color:#090d1a;border-color:#38bdf8}
.lp-vbtn.lp-rep{margin-left:auto;background:rgba(40,58,98,0.8);color:#facc15;border-color:rgba(250,204,21,0.35)}
.lp-vbtn.lp-rep:hover{background:rgba(55,80,135,0.95)}
.lp-btn.lp-active{background:rgba(56,189,248,0.2);color:#38bdf8;border-color:#38bdf8}
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
                 only_truck: str | None = None, active_trucks: list[str] | None = None) -> list[dict]:
    trucks = []
    routes = [r for r in plan.routes if not only_truck or r.truck_id == only_truck]
    if active_trucks:
        # Sort active trucks to the front, with focus_truck_id first if specified
        routes = sorted(routes, key=lambda r: (
            r.truck_id not in active_trucks,
            r.truck_id != focus_truck_id if focus_truck_id else False,
        ))
    elif focus_truck_id:
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
            "active": (r.truck_id in active_trucks) if active_trucks else True,
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
                      only_truck: str | None = None, start: str | None = None,
                      active_trucks: list[str] | None = None) -> dict:
    """only_truck: driver view (one truck's route + load). active_trucks: list of highlighted trucks (others dimmed)."""
    if only_truck and not active_trucks:
        active_trucks = [only_truck]
    data: dict = {"hub": {"name": plan.hub.name, "lat": plan.hub.lat, "lon": plan.hub.lon}}
    if start:
        data["start"] = start
    if active_trucks:
        data["active_trucks"] = list(active_trucks)
    if mode in ("both", "load"):
        data["trucks"] = _load_trucks(plan, focus_truck_id, max_trucks, only_truck=only_truck, active_trucks=active_trucks)
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
                    start: str | None = None, active_trucks: list[str] | None = None) -> str:
    data = plan_to_anim_data(plan, focus_truck_id=focus_truck_id, max_trucks=max_trucks, mode=mode,
                             only_truck=only_truck, start=start, active_trucks=active_trucks)
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    engine_js = (Path(__file__).parent / "anim" / "engine.js").read_text(encoding="utf-8")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>FleetFlow · {plan.plan_id}</title><style>{_CSS}</style></head>"
        "<body><div id='lp-app'></div>"
        f"<script>window.LP={payload};window.LP_MODE={json.dumps(mode)};</script>"
        f"<script>{engine_js}</script></body></html>"
    )

