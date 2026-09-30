"""A2UI v0.9 surfaces for LoadPilot (deterministic builders — the model never authors UI).

1. Planning Wizard  : Card form (DateTimeInput, ChoicePicker chips, TextFields, primary Button
                      emitting the `optimiseDispatch` action event with all form values).
2. Dispatch Canvas  : Canvas side panel -> Stepper + Tabs:
                      Overview (VegaChart map + KPIs) · Route animation (IFrameSrcdoc)
                      · 3D truck loading (IFrameSrcdoc) · Loader video (Video).
   Fallback (LOADPILOT_UI_MODE=card): a Card with the Overview VegaChart only.
"""

from __future__ import annotations

import os
from typing import Any

from google.genai import types

try:
    from app.contracts import DispatchPlan, PlanningParams
    from app.data.demo_mmr import HUBS
    from app.data.master_data import DEFAULT_FLEET_AVAILABLE, TRUCK_CATALOGUE
    from app.render.a2ui_envelope import wrap_a2ui_part
    from app.render.a2ui_lifecycle import (
        build_create_surface, build_update_components, build_update_data_model,
    )
    from app.render.anim_html import build_anim_html
    from app.render.kpi_vega import kpi_spec, route_map_spec
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan, PlanningParams
    from data.demo_mmr import HUBS
    from data.master_data import DEFAULT_FLEET_AVAILABLE, TRUCK_CATALOGUE
    from render.a2ui_envelope import wrap_a2ui_part
    from render.a2ui_lifecycle import (
        build_create_surface, build_update_components, build_update_data_model,
    )
    from render.anim_html import build_anim_html
    from render.kpi_vega import kpi_spec, route_map_spec

WIZARD_EVENT = "optimiseDispatch"


def _t(cid: str, text: str, variant: str = "body") -> dict[str, Any]:
    return {"id": cid, "component": "Text", "text": text, "variant": variant}


def _emit(surface_id: str, components: list[dict[str, Any]], data: dict[str, Any] | None) -> list[types.Part]:
    parts = [wrap_a2ui_part(build_create_surface(surface_id))]
    if data is not None:
        parts.append(wrap_a2ui_part(build_update_data_model(surface_id, data)))
    parts.append(wrap_a2ui_part(build_update_components(surface_id, components)))
    return parts


# ==============================================================================
# 1) Planning wizard
# ==============================================================================
def wizard_components(counts: dict[str, int]) -> list[dict[str, Any]]:
    codes = list(TRUCK_CATALOGUE)
    comps: list[dict[str, Any]] = [
        {"id": "root", "component": "Card", "child": "wz-col"},
        {"id": "wz-col", "component": "Column", "children": [
            "wz-title", "wz-sub", "wz-row1", "wz-source", "wz-types", "wz-counts-lbl", "wz-counts",
            "wz-objective", "wz-claims", "wz-costs", "wz-div", "wz-go"]},
        _t("wz-title", "🚚 LoadPilot · Plan today's dispatch", "h3"),
        _t("wz-sub", "Pick the fleet and goal. LoadPilot plans corridors, routes, LIFO truck loading "
                     "and costs in seconds. You can also type all of this in chat.", "caption"),
        {"id": "wz-row1", "component": "Row", "children": ["wz-date", "wz-hub"]},
        {"id": "wz-date", "component": "DateTimeInput", "value": {"path": "/form/date"},
         "enableDate": True, "enableTime": True, "weight": 1},
        {"id": "wz-hub", "component": "ChoicePicker", "label": "Dispatch hub", "variant": "mutuallyExclusive",
         "displayStyle": "chips", "weight": 1,
         "options": [{"label": h.name, "value": h.hub_id} for h in HUBS.values()],
         "value": {"path": "/form/hub"}},
        {"id": "wz-source", "component": "ChoicePicker", "label": "Orders & cartons from",
         "variant": "mutuallyExclusive", "displayStyle": "chips",
         "options": [{"label": "Demo order book (70 outlets)", "value": "demo"},
                     {"label": "Orders I pasted / uploaded in chat", "value": "chat"},
                     {"label": "Demo + my box photos", "value": "photos"}],
         "value": {"path": "/form/source"}},
        {"id": "wz-types", "component": "ChoicePicker", "label": "Truck types available today",
         "variant": "multipleSelection", "displayStyle": "chips",
         "options": [{"label": f"{t.code} · {t.name.split('(')[0].strip()} · "
                               f"{t.volume_m3:.1f} m³ / {t.payload_kg / 1000:g} t", "value": t.code}
                     for t in TRUCK_CATALOGUE.values()],
         "value": {"path": "/form/types"}},
        _t("wz-counts-lbl", "How many of each type are available?", "caption"),
        {"id": "wz-counts", "component": "Row", "children": [f"wz-n-{c}" for c in codes]},
        *[{"id": f"wz-n-{c}", "component": "TextField", "label": c, "variant": "number",
           "value": {"path": f"/form/n_{c}"}, "weight": 1} for c in codes],
        {"id": "wz-objective", "component": "ChoicePicker", "label": "Optimise for",
         "variant": "mutuallyExclusive", "displayStyle": "chips",
         "options": [{"label": "Lowest total cost", "value": "lowest_cost"},
                     {"label": "Fewest trucks", "value": "fewest_trucks"},
                     {"label": "Fastest finish", "value": "fastest_finish"},
                     {"label": "Balanced workload", "value": "balanced"}],
         "value": {"path": "/form/objective"}},
        {"id": "wz-claims", "component": "TextField", "variant": "longText",
         "label": "Driver corridor claims (optional), e.g. Ravi=West, Imran=North-East",
         "value": {"path": "/form/claims"}},
        {"id": "wz-costs", "component": "Row", "children": ["wz-fuel", "wz-driver"]},
        {"id": "wz-fuel", "component": "TextField", "label": "Diesel ₹/litre", "variant": "number",
         "value": {"path": "/form/fuel"}, "weight": 1},
        {"id": "wz-driver", "component": "TextField", "label": "Driver ₹/day", "variant": "number",
         "value": {"path": "/form/driver"}, "weight": 1},
        {"id": "wz-div", "component": "Divider"},
        _t("wz-go-lbl", "⚡ Optimise dispatch"),
        {"id": "wz-go", "component": "Button", "child": "wz-go-lbl", "variant": "primary",
         "action": {"event": {"name": WIZARD_EVENT, "context": {
             "date": {"path": "/form/date"}, "hub": {"path": "/form/hub"},
             "source": {"path": "/form/source"}, "types": {"path": "/form/types"},
             **{f"n_{c}": {"path": f"/form/n_{c}"} for c in codes},
             "objective": {"path": "/form/objective"}, "claims": {"path": "/form/claims"},
             "fuel": {"path": "/form/fuel"}, "driver": {"path": "/form/driver"}}}}},
    ]
    _ = counts
    return comps


def wizard_data(params: PlanningParams, fuel: float, driver: float) -> dict[str, Any]:
    counts = params.truck_counts or DEFAULT_FLEET_AVAILABLE
    return {"form": {
        "date": f"{params.dispatch_date}T{params.shift_start_min // 60:02d}:{params.shift_start_min % 60:02d}:00",
        "hub": [params.hub_id or "BHW-DC"], "source": [params.order_source or "demo"],
        "types": [c for c in TRUCK_CATALOGUE if counts.get(c, 0) > 0],
        **{f"n_{c}": str(counts.get(c, 0)) for c in TRUCK_CATALOGUE},
        "objective": [params.objective.value], "claims": ", ".join(f"{k}={v}" for k, v in params.corridor_claims.items()),
        "fuel": f"{fuel:g}", "driver": f"{driver:g}",
    }}


def build_wizard_surface(surface_id: str, params: PlanningParams, fuel: float, driver: float) -> list[types.Part]:
    return _emit(surface_id, wizard_components(params.truck_counts), wizard_data(params, fuel, driver))


# ==============================================================================
# 2) Dispatch canvas
# ==============================================================================
def dispatch_components(plan: DispatchPlan, video_url: str | None, focus_truck_id: str | None,
                        mode: str | None = None) -> list[dict[str, Any]]:
    mode = (mode or os.environ.get("LOADPILOT_UI_MODE", "canvas")).lower()
    b, o = plan.baseline, plan.optimized
    headline = (f"{o.trucks} trucks instead of {b.trucks} · ₹{plan.savings_inr:,.0f} saved today · "
                f"{b.km - o.km:,.0f} km and {b.co2_kg - o.co2_kg:,.0f} kg CO₂ less · LIFO verified on every truck")
    if mode == "card":
        return [
            {"id": "root", "component": "Card", "child": "dc-col"},
            {"id": "dc-col", "component": "Column", "children": ["dc-title", "dc-sub", "dc-map", "dc-kpi"]},
            _t("dc-title", f"LoadPilot dispatch plan · {plan.plan_id}", "h4"),
            _t("dc-sub", headline, "caption"),
            {"id": "dc-map", "component": "VegaChart", "spec": route_map_spec(plan), "height": 500},
            {"id": "dc-kpi", "component": "VegaChart", "spec": kpi_spec(plan), "height": 300},
        ]

    load_html = build_anim_html(plan, mode="load", focus_truck_id=focus_truck_id)
    route_html = build_anim_html(plan, mode="routes", focus_truck_id=focus_truck_id)
    tabs = [{"title": "📊 Overview", "child": "tab-overview"},
            {"title": "🗺️ Route animation", "child": "tab-routes"},
            {"title": "📦 3D truck loading", "child": "tab-load"}]
    comps: list[dict[str, Any]] = [
        {"id": "root", "component": "Canvas", "children": ["dc-title", "dc-sub", "dc-steps", "dc-tabs"],
         "autoOpen": True, "autoFullscreen": False,
         "cardTitle": f"LoadPilot · {o.trucks} trucks · ₹{plan.savings_inr:,.0f} saved",
         "cardDescription": "Corridor routes, animated LIFO truck loading and loader video",
         "cardIcon": "local_shipping"},
        _t("dc-title", f"🚚 LoadPilot dispatch plan · {plan.plan_id} · {plan.hub.name}", "h3"),
        _t("dc-sub", headline, "caption"),
        {"id": "dc-steps", "component": "Stepper", "activeStep": 4, "steps": [
            {"title": "Orders & cartons", "helpText": f"{sum(len(r.stops) for r in plan.routes)} stops · "
                                                       f"{sum(len(lp.placed) for lp in plan.loads.values())} cartons",
             "status": "completed"},
            {"title": "Corridors", "helpText": f"{len(plan.corridors)} directions from the hub", "status": "completed"},
            {"title": "Routes", "helpText": f"{o.trucks} trucks · {o.km:,.0f} km", "status": "completed"},
            {"title": "LIFO loading", "helpText": "stop 1 at the door on every truck", "status": "completed"},
            {"title": "Costed", "helpText": f"₹{o.cost_total:,.0f} vs ₹{b.cost_total:,.0f} today",
             "status": "completed"}]},
        {"id": "dc-tabs", "component": "Tabs", "tabs": tabs},
        {"id": "tab-overview", "component": "Column", "children": ["ov-map", "ov-kpi"]},
        {"id": "ov-map", "component": "VegaChart", "spec": route_map_spec(plan), "height": 500},
        {"id": "ov-kpi", "component": "VegaChart", "spec": kpi_spec(plan), "height": 300},
        {"id": "tab-routes", "component": "IFrameSrcdoc", "htmlContent": route_html, "height": 640,
         "title": "Animated corridor route plan"},
        {"id": "tab-load", "component": "IFrameSrcdoc", "htmlContent": load_html, "height": 640,
         "title": "Animated 3D LIFO truck loading"},
    ]
    if video_url:
        tabs.append({"title": "🎬 Loader video", "child": "tab-video"})
        comps += [
            {"id": "tab-video", "component": "Column", "children": ["vid-cap", "vid"]},
            _t("vid-cap", "Share with the dock team: loading sequence for the focus truck (last stop first).",
               "caption"),
            {"id": "vid", "component": "Video", "url": video_url},
        ]
    return comps


def build_dispatch_surface(surface_id: str, plan: DispatchPlan, video_url: str | None = None,
                           focus_truck_id: str | None = None, mode: str | None = None) -> list[types.Part]:
    return _emit(surface_id, dispatch_components(plan, video_url, focus_truck_id, mode), None)
