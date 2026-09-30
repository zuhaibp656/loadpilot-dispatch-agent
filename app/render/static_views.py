"""Static Vega-Lite views for the Gemini Enterprise canvas.

GE did not render the large IFrameSrcdoc app reliably, so the canvas uses native VegaChart
components (which GE renders): a road-following route map with numbered drops and a
"where each store's cartons sit" load chart. The full interactive map + tap-a-store 3D app stays
available through the link in the chat answer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from app.contracts import DispatchPlan
    from app.render.anim_html import ROUTE_COLORS, _plan_box
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan
    from render.anim_html import ROUTE_COLORS, _plan_box

FONT = "Google Sans, Roboto, Arial"
STOP_COLORS = ["#f97316", "#06b6d4", "#facc15", "#d946ef", "#65a30d", "#e11d48", "#2563eb", "#14b8a6",
               "#f59e0b", "#be123c", "#84cc16", "#7c3aed", "#22d3ee", "#a3e635", "#ea580c", "#0ea5e9"]
_COAST: dict | None = None


def _hm(m: int) -> str:
    return f"{int(m) // 60:02d}:{int(m) % 60:02d}"


def _coast_lines(box: tuple[float, float, float, float]) -> list[dict]:
    """Coastline polylines (OSM) inside the plan box, as Vega line rows."""
    global _COAST
    if _COAST is None:
        _COAST = {}
        for p in (Path(__file__).resolve().parents[1] / "data").glob("basemap_*.json"):
            try:
                _COAST[p.stem] = json.loads(p.read_text())
            except Exception:  # noqa: BLE001
                continue
    s, w, n, e = box
    rows: list[dict] = []
    for bm in _COAST.values():
        scale = bm.get("scale", 1e4)
        for li, flat in enumerate(bm.get("coast", [])):
            lon = lat = 0
            pts = []
            for i in range(0, len(flat), 2):
                lon += flat[i]
                lat += flat[i + 1]
                la, lo = lat / scale, lon / scale
                if s <= la <= n and w <= lo <= e:
                    pts.append((round(la, 4), round(lo, 4)))
            pts = pts[::3] if len(pts) > 60 else pts
            for k, (la, lo) in enumerate(pts):
                rows.append({"g": f"c{li}", "k": k, "lat": la, "lon": lo})
    return rows


def route_view_spec(plan: DispatchPlan, only_truck: str | None = None, width: int = 640,
                    height: int = 520) -> dict[str, Any]:
    try:
        from app.geo.roads import _dp, plan_road_legs
    except ImportError:  # pragma: no cover
        from geo.roads import _dp, plan_road_legs
    try:
        road = plan_road_legs(plan)["opt"]
    except Exception:  # noqa: BLE001
        road = {}
    routes = [(i, r) for i, r in enumerate(plan.routes) if not only_truck or r.truck_id == only_truck]
    lines, pts = [], []
    domain, rng = [], []
    for i, r in routes:
        label = f"{r.truck_id} · {r.driver}"
        domain.append(label)
        rng.append(ROUTE_COLORS[i % len(ROUTE_COLORS)])
        legs = road.get(r.truck_id)
        if legs:
            seq = [p for lg in legs for p in _dp(list(lg), 0.0012)]
        else:
            seq = [(plan.hub.lat, plan.hub.lon)] + [(rs.stop.lat, rs.stop.lon) for rs in r.stops] + [
                (plan.hub.lat, plan.hub.lon)]
        for k, (la, lo) in enumerate(seq):
            lines.append({"truck": label, "k": k, "lat": round(la, 4), "lon": round(lo, 4)})
        for rs in r.stops:
            pts.append({"truck": label, "lat": rs.stop.lat, "lon": rs.stop.lon, "seq": rs.seq,
                        "name": rs.stop.name, "area": rs.stop.area, "eta": _hm(rs.arrive_min),
                        "cartons": len(rs.stop.boxes)})
    lats = [p["lat"] for p in pts] + [plan.hub.lat]
    lons = [p["lon"] for p in pts] + [plan.hub.lon]
    box = (min(lats) - 0.05, min(lons) - 0.05, max(lats) + 0.05, max(lons) + 0.05) if pts else _plan_box(plan)
    color = {"field": "truck", "type": "nominal", "title": None,
             "scale": {"domain": domain, "range": rng},
             "legend": None if only_truck else {"orient": "bottom", "columns": 4, "labelFont": FONT,
                                                "labelFontSize": 11, "symbolType": "stroke"}}
    geo = {"longitude": {"field": "lon", "type": "quantitative"},
           "latitude": {"field": "lat", "type": "quantitative"}}
    tip = [{"field": "truck", "title": "Truck"}, {"field": "seq", "title": "Drop #"},
           {"field": "name", "title": "Store"}, {"field": "area", "title": "Area"},
           {"field": "eta", "title": "ETA"}, {"field": "cartons", "title": "Cartons"}]
    if only_truck and routes:
        r = routes[0][1]
        title = f"{r.driver}'s route · {r.truck_id} · {len(r.stops)} drops · {r.km:.0f} km · {_hm(r.start_min)}–{_hm(r.end_min)}"
    else:
        title = f"Routes on real roads · {plan.optimized.trucks} trucks · {plan.optimized.km:,.0f} km"
    layers: list[dict] = [
        {"data": {"values": _coast_lines(box)},
         "mark": {"type": "line", "stroke": "#8ec3e6", "strokeWidth": 1.4, "opacity": 0.9},
         "encoding": {**geo, "detail": {"field": "g"}, "order": {"field": "k"}}},
        {"data": {"values": lines}, "mark": {"type": "line", "strokeWidth": 3.2 if only_truck else 2.4,
                                             "opacity": 0.9, "strokeJoin": "round"},
         "encoding": {**geo, "detail": {"field": "truck"}, "order": {"field": "k"}, "color": color}},
        {"data": {"values": pts},
         "mark": {"type": "circle", "size": 330 if only_truck else 150, "stroke": "white", "strokeWidth": 1.5,
                  "opacity": 1},
         "encoding": {**geo, "color": color, "tooltip": tip}},
        {"data": {"values": pts},
         "mark": {"type": "text", "font": FONT, "fontSize": 11 if only_truck else 8, "fontWeight": "bold",
                  "color": "white"},
         "encoding": {**geo, "text": {"field": "seq"}, "tooltip": tip}},
        {"data": {"values": [{"lat": plan.hub.lat, "lon": plan.hub.lon, "n": plan.hub.name}]},
         "mark": {"type": "point", "shape": "square", "size": 300, "filled": True, "color": "#f9ab00",
                  "stroke": "#202124", "strokeWidth": 1.5},
         "encoding": {**geo, "tooltip": [{"field": "n", "title": "Hub"}]}},
        {"data": {"values": [{"lat": plan.hub.lat, "lon": plan.hub.lon, "n": plan.hub.name}]},
         "mark": {"type": "text", "font": FONT, "fontSize": 11, "fontWeight": "bold", "dx": 14, "align": "left",
                  "color": "#b06000"},
         "encoding": {**geo, "text": {"field": "n"}}},
    ]
    if only_truck:  # store names next to the numbered drops
        layers.insert(4, {"data": {"values": pts},
                          "mark": {"type": "text", "font": FONT, "fontSize": 10, "dx": 12, "align": "left",
                                   "color": "#3c4043"},
                          "encoding": {**geo, "text": {"field": "name"}}})
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": {"text": title, "subtitle": "Numbers = drop order · hover a drop for store, ETA and cartons",
                  "font": FONT, "fontSize": 15, "anchor": "start", "color": "#202124",
                  "subtitleFont": FONT, "subtitleColor": "#5f6368"},
        "width": width, "height": height,
        "projection": {"type": "mercator"},
        "layer": layers,
        "config": {"view": {"stroke": "#dadce0", "fill": "#fbfaf7"}, "background": "white"},
    }


def load_view_spec(plan: DispatchPlan, only_truck: str | None = None, width: int = 620) -> dict[str, Any]:
    """Where each store's cartons sit, measured from the rear door (0 = door)."""
    rows = []
    routes = [r for r in plan.routes if not only_truck or r.truck_id == only_truck]
    for r in routes:
        lp = plan.loads.get(r.truck_id)
        if lp is None:
            continue
        L = lp.truck_type.inner_l_cm
        zones = {z.stop_seq: z for z in lp.zones}
        for rs in r.stops:
            z = zones.get(rs.seq)
            if z is None:
                continue
            a, b = max(0.0, L - z.x_end), L - z.x_start
            row = f"{rs.seq}. {rs.stop.name[:26]}" if only_truck else f"{r.truck_id} · {r.driver}"
            rows.append({"row": row, "truck": r.truck_id, "seq": rs.seq, "store": rs.stop.name,
                         "a": round(a), "b": round(b), "L": L, "cartons": len(rs.stop.boxes),
                         "kg": round(sum(x.weight_kg for x in rs.stop.boxes)),
                         "eta": _hm(rs.arrive_min), "lab": f"S{rs.seq}" if not only_truck else f"{len(rs.stop.boxes)} ctn",
                         "where": f"{round(a)}–{round(b)} cm from door"})
    Lmax = max((x["L"] for x in rows), default=500)
    seqs = sorted({x["seq"] for x in rows})
    color = {"field": "seq", "type": "ordinal", "title": "Drop #",
             "scale": {"domain": seqs, "range": [STOP_COLORS[(s - 1) % len(STOP_COLORS)] for s in seqs]},
             "legend": None}
    tip = [{"field": "truck", "title": "Truck"}, {"field": "seq", "title": "Drop #"},
           {"field": "store", "title": "Store"}, {"field": "cartons", "title": "Cartons"},
           {"field": "kg", "title": "kg"}, {"field": "where", "title": "Put them"}, {"field": "eta", "title": "ETA"}]
    order = [f"{rs.seq}. {rs.stop.name[:26]}" for r in routes for rs in r.stops] if only_truck else \
        [f"{r.truck_id} · {r.driver}" for r in routes]
    h = max(160, 30 * len(order))
    x = {"field": "a", "type": "quantitative", "title": "cm from the REAR DOOR  →  toward the CAB",
         "scale": {"domain": [0, Lmax]}, "axis": {"labelFont": FONT, "titleFont": FONT, "grid": True}}
    title = ("Where each store's cartons sit in the truck" if only_truck else
             "LIFO load plan · every truck: drop 1 at the door, last drop at the cab")
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": {"text": title, "subtitle": "Load from the cab end first (highest drop number) · "
                                             "hover a bar for store, cartons and position",
                  "font": FONT, "fontSize": 15, "anchor": "start", "color": "#202124",
                  "subtitleFont": FONT, "subtitleColor": "#5f6368"},
        "width": width, "height": h,
        "data": {"values": rows},
        "encoding": {"y": {"field": "row", "type": "nominal", "sort": order, "title": None,
                           "axis": {"labelFont": FONT, "labelFontSize": 11, "labelLimit": 220}}},
        "layer": [
            {"mark": {"type": "bar", "cornerRadius": 3, "height": {"band": 0.72}, "opacity": 0.9,
                      "stroke": "white", "strokeWidth": 1},
             "encoding": {"x": x, "x2": {"field": "b"}, "color": color, "tooltip": tip}},
            {"transform": [{"calculate": "(datum.a + datum.b) / 2", "as": "mid"}],
             "mark": {"type": "text", "font": FONT, "fontSize": 10, "fontWeight": "bold", "color": "#202124"},
             "encoding": {"x": {"field": "mid", "type": "quantitative"}, "text": {"field": "lab"},
                          "tooltip": tip}},
        ],
        "config": {"view": {"stroke": None}, "background": "white"},
    }
