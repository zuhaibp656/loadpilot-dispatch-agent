"""Build self-contained animation HTML (engine.js + plan JSON inlined, no network access).

Used for:
  * A2UI `IFrameSrcdoc` (sandboxed, CSP connect-src 'none') inside the Gemini Enterprise canvas.
  * A full-screen standalone page uploaded to GCS (both views with tabs).
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    from app.contracts import DispatchPlan, TruckRoute
    from app.data.demo_mmr import GAZETTEER
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan, TruckRoute
    from data.demo_mmr import GAZETTEER

_ENGINE_JS = (Path(__file__).parent / "anim" / "engine.js").read_text(encoding="utf-8")

ROUTE_COLORS = ["#00e5ff", "#ff6d00", "#76ff03", "#ff4081", "#ffd600", "#b388ff", "#18ffff",
                "#ff9e80", "#69f0ae", "#ea80fc", "#ffff00", "#82b1ff"]
BASE_COLORS = ["#90a4ae", "#b0bec5", "#78909c", "#cfd8dc", "#a1887f", "#bcaaa4", "#9e9e9e",
               "#b39ddb", "#80cbc4", "#ef9a9a"]

_CSS = """
*{box-sizing:border-box}html,body{margin:0;height:100%;background:#070b16;color:#e8eaed;
font:13px/1.35 Inter,Roboto,'Google Sans',Arial,sans-serif;overflow:hidden}
#lp-app{height:100%;display:flex;flex-direction:column}
.lp-tabs{display:flex;gap:6px;padding:8px 10px 0}.lp-tab{background:#121a2e;color:#9aa0a6;border:1px solid #243049;
border-bottom:none;border-radius:10px 10px 0 0;padding:7px 14px;cursor:pointer;font-weight:600}
.lp-tab.on{background:#1a2440;color:#fff;border-color:#3b4b72}
.lp-pane{flex:1;display:flex;flex-direction:column;min-height:0;border-top:1px solid #1f2a44}
.lp-top{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 12px;
background:linear-gradient(90deg,#0f1730,#111b36);flex-wrap:wrap}
.lp-title{font-size:14px}.lp-muted{color:#8a94a6;font-weight:400}
.lp-stats{display:flex;gap:6px;flex-wrap:wrap}.kv{background:#16203a;border:1px solid #243049;border-radius:10px;
padding:4px 9px;display:flex;flex-direction:column;min-width:74px}.kv span{font-size:10px;color:#8a94a6;
text-transform:uppercase;letter-spacing:.04em}.kv b{font-size:13px}
.ok{color:#5bf59a}.bad{color:#ff8a80}
.lp-body{flex:1;display:flex;min-height:0}.lp-cwrap{flex:1;position:relative;min-width:0}
.lp-canvas{display:block;width:100%;height:100%;cursor:grab}
.lp-legend{width:240px;overflow:auto;padding:8px 10px;background:#0b1224;border-left:1px solid #1f2a44}
.lp-lh{font-size:11px;color:#8ab4f8;text-transform:uppercase;letter-spacing:.05em;margin:2px 0 8px;font-weight:700}
.lp-li{display:flex;gap:6px;align-items:baseline;padding:4px 6px;border-radius:8px;font-size:12px;cursor:default}
.lp-li i{width:10px;height:10px;border-radius:3px;flex:none;transform:translateY(1px)}
.lp-li.on{background:#1d2a4a;outline:1px solid #3b4b72}.lp-li:hover{background:#15203a}
.lp-hud{position:absolute;left:12px;bottom:10px;background:rgba(10,16,32,.8);border:1px solid #243049;
border-radius:10px;padding:6px 10px;font-size:12px}
.lp-banner{position:absolute;left:50%;top:12px;transform:translateX(-50%);background:rgba(16,24,48,.92);
border:1px solid #3b4b72;border-radius:12px;padding:8px 14px;font-size:13px;transition:opacity .3s;opacity:0;
white-space:nowrap}.lp-banner i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px}
.lp-clock{position:absolute;right:14px;top:10px;font:700 26px 'Roboto Mono',monospace;color:#fdd663;
text-shadow:0 0 12px rgba(253,214,99,.45)}
.lp-ctrl{display:flex;align-items:center;gap:8px;padding:8px 10px;background:#0b1224;border-top:1px solid #1f2a44;
flex-wrap:wrap}.lp-btn{background:#1a2440;color:#e8eaed;border:1px solid #3b4b72;border-radius:18px;
padding:5px 12px;cursor:pointer;font-weight:600}.lp-btn:hover{background:#22305a}.lp-play{min-width:44px}
.lp-scrub{flex:1;min-width:120px;accent-color:#8ab4f8}
.lp-trucks{display:flex;gap:5px;flex-wrap:wrap}.lp-chip{background:#121a2e;color:#e8eaed;border:1px solid #3b4b72;
border-left-width:4px;border-radius:14px;padding:4px 9px;cursor:pointer;font-weight:600;font-size:12px}
.lp-chip small{color:#8a94a6;font-weight:400}.lp-chip.on{background:#22305a}
.lp-seg{display:flex;border:1px solid #3b4b72;border-radius:18px;overflow:hidden}
.lp-seg button{background:#121a2e;color:#9aa0a6;border:none;padding:5px 12px;cursor:pointer;font-weight:600}
.lp-seg button.on{background:#8ab4f8;color:#0b1020}
@media (max-width:640px){.lp-legend{display:none}}
"""


def _hhmm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _route_json(r: TruckRoute, color: str) -> dict:
    times = [r.start_min]
    for rs in r.stops:
        times.append(rs.arrive_min)
    times.append(r.end_min)
    # add dwell: duplicate each stop point at depart time so the marker pauses while unloading
    path: list[list[float]] = [[round(r.path[0][0], 5), round(r.path[0][1], 5)]]
    tl: list[int] = [r.start_min]
    for rs in r.stops:
        p = [round(rs.stop.lat, 5), round(rs.stop.lon, 5)]
        path += [p, p]
        tl += [rs.arrive_min, rs.depart_min]
    path.append([round(r.path[-1][0], 5), round(r.path[-1][1], 5)])
    tl.append(r.end_min)
    return {
        "id": r.truck_id if not r.truck_id.startswith("BASE") else r.driver,
        "color": color, "driver": r.driver if not r.truck_id.startswith("BASE") else r.truck_type.code,
        "corridor": r.corridor, "branch": r.branch, "km": round(r.km),
        "path": path, "times": tl,
        "stops": [{"seq": rs.seq, "name": rs.stop.name, "lat": rs.stop.lat, "lon": rs.stop.lon,
                   "arr": rs.arrive_min} for rs in r.stops],
    }


def plan_to_anim_data(plan: DispatchPlan, focus_truck_id: str | None = None,
                      max_trucks: int | None = None) -> dict:
    trucks = []
    routes = plan.routes
    if focus_truck_id:
        routes = sorted(routes, key=lambda r: r.truck_id != focus_truck_id)
    for i, r in enumerate(routes[: max_trucks or len(routes)]):
        lp = plan.loads.get(r.truck_id)
        if lp is None:
            continue
        seq_to_stop = {rs.seq: rs for rs in r.stops}
        trucks.append({
            "id": r.truck_id, "name": r.truck_type.name, "L": lp.truck_type.inner_l_cm,
            "W": lp.truck_type.inner_w_cm, "H": lp.truck_type.inner_h_cm,
            "color": ROUTE_COLORS[plan.routes.index(r) % len(ROUTE_COLORS)], "driver": r.driver,
            "corridor": r.corridor, "branch": r.branch, "fill": lp.volume_fill_pct,
            "wfill": lp.weight_fill_pct, "lifo": lp.lifo_ok,
            "zones": [[z.stop_seq, z.x_start, z.x_end] for z in lp.zones],
            "stops": [{"seq": rs.seq, "name": rs.stop.name[:28], "n": len(rs.stop.boxes),
                       "eta": _hhmm(rs.arrive_min)} for rs in r.stops],
            "boxes": [[p.x, p.y, p.z, p.l, p.w, p.h, p.stop_seq, 1 if p.box.fragile else 0,
                       p.box.sku] for p in sorted(lp.placed, key=lambda q: q.load_step)],
        })
        _ = seq_to_stop
    k = plan.baseline, plan.optimized
    all_routes = plan.routes + plan.baseline_routes
    t0 = min((r.start_min for r in all_routes), default=420) - 10
    t1 = max((r.end_min for r in all_routes), default=1140) + 10
    return {
        "hub": {"name": plan.hub.name, "lat": plan.hub.lat, "lon": plan.hub.lon},
        "clock": [t0, t1],
        "trucks": trucks,
        "routes": {
            "opt": [_route_json(r, ROUTE_COLORS[i % len(ROUTE_COLORS)]) for i, r in enumerate(plan.routes)],
            "base": [_route_json(r, BASE_COLORS[i % len(BASE_COLORS)]) for i, r in enumerate(plan.baseline_routes)],
        },
        "kpi": {
            "base": {"trucks": k[0].trucks, "km": round(k[0].km), "cost": f"₹{k[0].cost_total:,.0f}",
                     "co2": round(k[0].co2_kg)},
            "opt": {"trucks": k[1].trucks, "km": round(k[1].km), "cost": f"₹{k[1].cost_total:,.0f}",
                    "co2": round(k[1].co2_kg)},
            "saved": f"₹{plan.savings_inr:,.0f}/day",
        },
        "places": [[n, v[0], v[1]] for n, v in GAZETTEER.items()],
    }


def build_anim_html(plan: DispatchPlan, mode: str = "both", focus_truck_id: str | None = None,
                    max_trucks: int | None = None) -> str:
    data = plan_to_anim_data(plan, focus_truck_id=focus_truck_id, max_trucks=max_trucks)
    payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>LoadPilot · {plan.plan_id}</title><style>{_CSS}</style></head>"
        "<body><div id='lp-app'></div>"
        f"<script>window.LP={payload};window.LP_MODE={json.dumps(mode)};</script>"
        f"<script>{_ENGINE_JS}</script></body></html>"
    )
