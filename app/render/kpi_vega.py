"""Vega-Lite specs (deterministic): KPI comparison + corridor route map + cost stack."""

from __future__ import annotations

from typing import Any

try:
    from app.contracts import DispatchPlan
    from app.render.anim_html import BASE_COLORS, ROUTE_COLORS
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan
    from render.anim_html import BASE_COLORS, ROUTE_COLORS

FONT = "Google Sans, Roboto, Arial"


def _kpi_rows(plan: DispatchPlan) -> list[dict[str, Any]]:
    b, o = plan.baseline, plan.optimized
    metrics = [
        ("Trucks", b.trucks, o.trucks, ""), ("Road km", b.km, o.km, " km"),
        ("Crew hours", b.hours, o.hours, " h"), ("Fuel", b.litres, o.litres, " L"),
        ("CO₂", b.co2_kg, o.co2_kg, " kg"), ("Cost / day", b.cost_total, o.cost_total, ""),
    ]
    rows = []
    for name, bv, ov, unit in metrics:
        pct = 0 if not bv else round(100 * (bv - ov) / bv)
        fmt = (lambda v: f"₹{v:,.0f}") if name == "Cost / day" else (lambda v, u=unit: f"{v:,.0f}{u}")
        rows.append({"metric": name, "plan": "Today (manual)", "idx": 100, "label": fmt(bv), "pct": ""})
        rows.append({"metric": name, "plan": "FleetFlow", "idx": round(100 * ov / bv) if bv else 0,
                     "label": fmt(ov), "pct": f"−{pct}%" if pct > 0 else ""})
    return rows


def kpi_spec(plan: DispatchPlan, width: int = 620) -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": {"text": f"Today vs FleetFlow — saves ₹{plan.savings_inr:,.0f}/day, "
                          f"{plan.trucks_saved} truck(s) fewer", "font": FONT, "fontSize": 15,
                  "anchor": "start", "color": "#202124"},
        "width": width, "height": 230,
        "data": {"values": _kpi_rows(plan)},
        "encoding": {
            "y": {"field": "metric", "type": "nominal", "sort": None, "title": None,
                  "axis": {"labelFont": FONT, "labelFontSize": 12, "domain": False, "ticks": False}},
            "yOffset": {"field": "plan", "sort": ["Today (manual)", "FleetFlow"]},
        },
        "layer": [
            {"mark": {"type": "bar", "cornerRadiusEnd": 5, "height": {"band": 0.42}},
             "encoding": {
                 "x": {"field": "idx", "type": "quantitative", "title": "Index (today = 100)",
                       "scale": {"domain": [0, 125]}, "axis": {"grid": False, "labelFont": FONT}},
                 "color": {"field": "plan", "type": "nominal", "title": None,
                           "scale": {"domain": ["Today (manual)", "FleetFlow"],
                                     "range": ["#bdc1c6", "#1a73e8"]},
                           "legend": {"orient": "top", "labelFont": FONT}},
                 "tooltip": [{"field": "metric"}, {"field": "plan"}, {"field": "label"}]}},
            {"mark": {"type": "text", "align": "left", "dx": 4, "font": FONT, "fontSize": 11},
             "encoding": {"x": {"field": "idx", "type": "quantitative"},
                          "text": {"field": "label"}, "color": {"value": "#3c4043"}}},
            {"mark": {"type": "text", "align": "left", "dx": 70, "font": FONT, "fontSize": 11,
                      "fontWeight": "bold"},
             "encoding": {"x": {"field": "idx", "type": "quantitative"}, "text": {"field": "pct"},
                          "color": {"value": "#188038"}}},
        ],
        "config": {"view": {"stroke": None}, "background": "white"},
    }


def route_map_spec(plan: DispatchPlan, width: int = 620, height: int = 430,
                   baseline: bool = False) -> dict[str, Any]:
    routes = plan.baseline_routes if baseline else plan.routes
    colors = BASE_COLORS if baseline else ROUTE_COLORS
    lines, pts = [], []
    for i, r in enumerate(routes):
        label = r.driver if baseline else f"{r.truck_id} · {r.driver} ({r.corridor})"
        for k, (lat, lon) in enumerate(r.path):
            lines.append({"truck": label, "k": k, "lat": lat, "lon": lon})
        for rs in r.stops:
            pts.append({"truck": label, "lat": rs.stop.lat, "lon": rs.stop.lon, "seq": rs.seq,
                        "name": rs.stop.name, "eta": f"{rs.arrive_min // 60:02d}:{rs.arrive_min % 60:02d}"})
    domain = [(r.driver if baseline else f"{r.truck_id} · {r.driver} ({r.corridor})") for r in routes]
    color = {"field": "truck", "type": "nominal", "title": None,
             "scale": {"domain": domain, "range": [colors[i % len(colors)] for i in range(len(domain))]},
             "legend": {"orient": "right", "labelFont": FONT, "labelFontSize": 10, "symbolType": "circle"}}
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": {"text": ("Today: one truck per sales area" if baseline else
                           f"FleetFlow corridors — {plan.optimized.trucks} trucks, overlap {plan.overlap_km:.0f} km"),
                  "font": FONT, "fontSize": 15, "anchor": "start", "color": "#202124"},
        "width": width, "height": height,
        "projection": {"type": "mercator"},
        "layer": [
            {"data": {"values": lines}, "mark": {"type": "line", "strokeWidth": 2.2, "opacity": 0.85},
             "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                          "latitude": {"field": "lat", "type": "quantitative"},
                          "detail": {"field": "truck"}, "order": {"field": "k"}, "color": color}},
            {"data": {"values": pts}, "mark": {"type": "circle", "size": 46, "stroke": "white", "strokeWidth": 1},
             "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                          "latitude": {"field": "lat", "type": "quantitative"}, "color": color,
                          "tooltip": [{"field": "truck"}, {"field": "seq", "title": "Stop #"},
                                      {"field": "name"}, {"field": "eta", "title": "ETA"}]}},
            {"data": {"values": [{"lat": plan.hub.lat, "lon": plan.hub.lon, "n": plan.hub.name}]},
             "mark": {"type": "point", "shape": "diamond", "size": 260, "filled": True, "color": "#f9ab00",
                      "stroke": "#202124"},
             "encoding": {"longitude": {"field": "lon", "type": "quantitative"},
                          "latitude": {"field": "lat", "type": "quantitative"},
                          "tooltip": [{"field": "n", "title": "Hub"}]}},
        ],
        "config": {"view": {"stroke": "#dadce0"}, "background": "white"},
    }


def overview_spec(plan: DispatchPlan) -> dict[str, Any]:
    """Single composite spec used in the Overview tab / Card fallback."""
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "vconcat": [
            {k: v for k, v in route_map_spec(plan).items() if k != "$schema"},
            {k: v for k, v in kpi_spec(plan).items() if k != "$schema"},
        ],
        "spacing": 26,
        "config": {"view": {"stroke": None}, "background": "white", "font": FONT},
    }
