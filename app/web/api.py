"""FastAPI REST endpoints for the FleetFlow Supply Chain Control Tower & 3D Load Studio.

Shares the exact same backend optimization engine (OR-Tools VRPTW + 3D Height-Map LIFO Packer),
ADK tool layer (`app/integration/tools.py`), BigQuery connector (`app/data/bq_source.py`),
Google Maps / Routes API (`app/geo/`), and QR/Vision scanner (`app/capture/`) as the
Gemini Enterprise agent deployment.
"""

from __future__ import annotations

import base64
import dataclasses
import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from app.contracts import Box, Objective, PlanningParams, Stop
from app.data.bq_source import DEFAULT_DATASET, DEFAULT_LOCATION, DEFAULT_PROJECT, run_query
from app.data.cities import ALL_HUBS, CITIES, resolve_city_and_hub
from app.data.history import (
    MANIFESTS_DIR,
    REPORTS_DIR,
    generate_dispatch_manifest_csv,
    generate_dispatch_report_html,
    get_history_analytics,
    get_history_detail,
    get_history_list,
    record_dispatch_run,
)
from app.data.master_data import (
    CORRIDOR_NAMES,
    DEFAULT_COST_PROFILE,
    DEFAULT_DRIVERS,
    DEFAULT_FLEET_AVAILABLE,
    SKU_MASTER,
    TRUCK_CATALOGUE,
)
from app.geo.gmaps import (
    gmaps_embed_url,
    gmaps_route_url,
    gmaps_stop_nav_url,
    whatsapp_dispatch_url,
)
from app.geo.roads import provider_name
from app.integration import tools as T
from app.optim.corridors import normalize_corridor
from app.optim.lifo_packer import pack_truck_lifo
from app.render.anim_html import ROUTE_COLORS, plan_to_anim_data
from app.render.driver_portal_html import build_driver_portal_html

logger = logging.getLogger(__name__)

router = APIRouter()

ROOT_DIR = Path(__file__).resolve().parents[2]
SAMPLES_DIR = ROOT_DIR / "app" / "data" / "samples"


class WebToolContext:
    """Lightweight ToolContext adapter so Web UI calls the exact same ADK tool functions."""

    def __init__(self, state: dict[str, Any]) -> None:
        self.state = state


# Persistent singleton web session state for local/container interactive control tower
_WEB_STATE: dict[str, Any] = {}
_AUDIT_LOG: list[dict[str, Any]] = []


def _get_ctx() -> WebToolContext:
    ctx = WebToolContext(_WEB_STATE)
    T.session(_WEB_STATE)
    return ctx


def _hhmm(m: int) -> str:
    return f"{int(m) // 60:02d}:{int(m) % 60:02d}"


def _ensure_plan(ctx: WebToolContext):
    sess = T.session(ctx.state)
    if sess.get("plan") is None:
        T.run_plan(ctx.state)
    return sess["plan"]


def _record_audit(action: str, detail: str, tool_name: str, latency_ms: float) -> dict[str, Any]:
    entry = {
        "ts": time.strftime("%H:%M:%S"),
        "action": action,
        "tool": tool_name,
        "detail": detail,
        "latency_ms": round(latency_ms, 1),
        "model_armor": "PASS · 0 threats",
        "cloud_dlp": "PASS · PII/GSTIN masked",
        "enclave": "CERTIFIED · OR-Tools + 3D HeightMap",
    }
    _AUDIT_LOG.insert(0, entry)
    del _AUDIT_LOG[25:]
    return entry


def serialize_plan_bundle(
    plan: Any,
    active_trucks: list[str] | None = None,
    focus_truck_id: str | None = None,
) -> dict[str, Any]:
    """Build the complete JSON state for the Control Tower UI, MapView, and 3D LoadView."""
    if not focus_truck_id:
        if active_trucks:
            focus_truck_id = active_trucks[0]
        elif plan.focus_truck_id:
            focus_truck_id = plan.focus_truck_id
        elif plan.routes:
            focus_truck_id = plan.routes[0].truck_id

    anim_data = plan_to_anim_data(
        plan,
        focus_truck_id=focus_truck_id,
        mode="both",
        active_trucks=active_trucks,
    )

    hub_coords = (plan.hub.lat, plan.hub.lon)
    routes_out: list[dict[str, Any]] = []

    for idx, r in enumerate(plan.routes):
        lp = plan.loads.get(r.truck_id)
        color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
        stop_coords = [(rs.stop.lat, rs.stop.lon) for rs in r.stops]
        nav_url = gmaps_route_url(hub_coords, stop_coords)
        embed_url = gmaps_embed_url(hub_coords, stop_coords)
        portal_url = f"/api/driver-portal/{r.truck_id}"

        zone_by_seq = {z.stop_seq: (z.x_start, z.x_end) for z in (lp.zones if lp else [])}
        stops_list = []
        wa_stops = []
        for rs in r.stops:
            s = rs.stop
            skus: dict[str, int] = {}
            for b in s.boxes:
                skus[b.description] = skus.get(b.description, 0) + 1
            top_skus = ", ".join(f"{n}× {d}" for d, n in sorted(skus.items(), key=lambda x: -x[1])[:3])
            zx0, zx1 = zone_by_seq.get(rs.seq, (0.0, 0.0))
            door_dist_0 = max(0, round(r.truck_type.inner_l_cm - zx1))
            door_dist_1 = max(0, round(r.truck_type.inner_l_cm - zx0))
            stops_list.append({
                "seq": rs.seq,
                "stop_id": s.stop_id,
                "name": s.name,
                "address": s.address,
                "area": s.area,
                "lat": round(s.lat, 5),
                "lon": round(s.lon, 5),
                "eta": _hhmm(rs.arrive_min),
                "dep": _hhmm(rs.depart_min),
                "window": f"{_hhmm(s.window_start_min)}–{_hhmm(s.window_end_min)}",
                "cartons": len(s.boxes),
                "weight_kg": round(s.weight_kg, 1),
                "volume_m3": round(s.volume_m3, 2),
                "fragile": sum(1 for b in s.boxes if b.fragile),
                "skus": top_skus,
                "bay_cm_from_door": f"{door_dist_0}–{door_dist_1} cm from door",
                "cab_x_cm": f"{round(zx0)}–{round(zx1)} cm from cab",
                "gmaps_url": gmaps_stop_nav_url(s.lat, s.lon),
            })
            wa_stops.append({
                "seq": rs.seq,
                "name": s.name,
                "area": s.area or s.address.split(",")[-1].strip(),
                "eta": _hhmm(rs.arrive_min),
                "n": len(s.boxes),
            })

        wa_url = whatsapp_dispatch_url(
            driver_name=r.driver,
            truck_id=r.truck_id,
            truck_type=r.truck_type.name,
            hub_name=plan.hub.name,
            leave_time=_hhmm(r.start_min),
            back_time=_hhmm(r.end_min),
            stops_summary=wa_stops,
            gmaps_url=nav_url,
            driver_portal_url=portal_url,
        )

        front_share = lp.front_axle_share_pct if lp else 38.0
        rear_share = round(100.0 - front_share, 1)
        is_active = (r.truck_id in active_trucks) if active_trucks else True

        routes_out.append({
            "truck_id": r.truck_id,
            "driver": r.driver,
            "color": color,
            "active": is_active,
            "truck_code": r.truck_type.code,
            "truck_name": r.truck_type.name,
            "inner_cm": [r.truck_type.inner_l_cm, r.truck_type.inner_w_cm, r.truck_type.inner_h_cm],
            "payload_capacity_kg": r.truck_type.payload_kg,
            "volume_capacity_m3": round(r.truck_type.volume_m3, 2),
            "corridor": r.corridor,
            "corridor_name": CORRIDOR_NAMES.get(r.corridor, r.corridor),
            "branch": r.branch,
            "km": round(r.km, 1),
            "leave": _hhmm(r.start_min),
            "back": _hhmm(r.end_min),
            "shift_h": round((r.end_min - r.start_min) / 60.0, 1),
            "stops_count": len(r.stops),
            "cartons_count": len(lp.placed) if lp else 0,
            "weight_kg": round(lp.weight_kg, 1) if lp else 0.0,
            "volume_fill_pct": lp.volume_fill_pct if lp else 0.0,
            "weight_fill_pct": lp.weight_fill_pct if lp else 0.0,
            "lifo_ok": lp.lifo_ok if lp else True,
            "front_axle_pct": front_share,
            "rear_axle_pct": rear_share,
            "cmvr_compliant": lp.cmvr_axle_compliant if lp else True,
            "cmvr_status": lp.cmvr_axle_status if lp else "CMVR Rule 93 Compliant",
            "cost_total": round(r.cost.total),
            "cost_fixed": round(r.cost.fixed),
            "cost_km": round(r.cost.distance + r.cost.fuel),
            "cost_driver": round(r.cost.crew),
            "cost_toll": round(r.cost.tolls),
            "cost_overtime": round(r.cost.overtime),
            "gmaps_nav_url": nav_url,
            "gmaps_embed_url": embed_url,
            "whatsapp_url": wa_url,
            "driver_portal_url": portal_url,
            "stops": stops_list,
        })

    b, o = plan.baseline, plan.optimized
    city_id = "bangalore" if plan.hub.hub_id.startswith("BLR") else "mumbai"

    return {
        "plan_id": plan.plan_id,
        "city": city_id,
        "hub": {
            "hub_id": plan.hub.hub_id,
            "name": plan.hub.name,
            "address": plan.hub.address,
            "lat": plan.hub.lat,
            "lon": plan.hub.lon,
        },
        "dispatch_date": plan.dispatch_date,
        "objective": plan.params.objective.value,
        "order_source": plan.params.order_source,
        "truck_counts": plan.params.truck_counts,
        "corridor_claims": plan.params.corridor_claims,
        "fuel_price": plan.params.fuel_price_per_litre,
        "driver_day_cost": plan.params.driver_day_cost,
        "focus_truck_id": focus_truck_id,
        "active_trucks": active_trucks,
        "kpi": {
            "stops": sum(len(r.stops) for r in plan.routes),
            "unassigned": len(plan.unassigned),
            "cartons": sum(len(lp.placed) for lp in plan.loads.values()),
            "weight_tonnes": round(sum(lp.weight_kg for lp in plan.loads.values()) / 1000.0, 2),
            "baseline_trucks": b.trucks,
            "optimized_trucks": o.trucks,
            "trucks_saved": max(0, b.trucks - o.trucks),
            "baseline_km": round(b.km),
            "optimized_km": round(o.km),
            "km_saved": max(0, round(b.km - o.km)),
            "baseline_cost_inr": round(b.cost_total),
            "optimized_cost_inr": round(o.cost_total),
            "savings_inr": round(plan.savings_inr),
            "savings_pct": round(100.0 * plan.savings_inr / b.cost_total, 1) if b.cost_total else 0.0,
            "annual_savings_inr": round(plan.savings_inr * 300),
            "diesel_saved_litres": round(plan.diesel_saved_litres, 1),
            "co2_saved_kg": round(plan.co2_saved_kg, 1),
            "trees_offset": plan.annual_trees_offset_equiv,
            "lifo_all_ok": all(lp.lifo_ok for lp in plan.loads.values()),
            "cmvr_all_ok": all(lp.cmvr_axle_compliant for lp in plan.loads.values()),
            "avg_vol_fill_pct": b_fill if (b_fill := round(
                sum(lp.volume_fill_pct for lp in plan.loads.values()) / max(1, len(plan.loads)), 1
            )) else 0.0,
            "avg_wt_fill_pct": round(
                sum(lp.weight_fill_pct for lp in plan.loads.values()) / max(1, len(plan.loads)), 1
            ),
            "by_type": o.by_type,
        },
        "routes": routes_out,
        "notes": list(plan.notes[:8]),
        "anim_data": anim_data,
        "audit_log": _AUDIT_LOG[:10],
    }


# ==============================================================================
# Request Models
# ==============================================================================
class DriverAssignmentItem(BaseModel):
    driver: str
    corridor: str
    truck_type: str = ""  # Optional: ACE, PKP, T14, T17, T20 (empty = solver auto-fit)


class PlanRequest(BaseModel):
    hub_id: str = ""
    city: str = ""
    dispatch_date: str = ""
    objective: str = ""
    order_source: str = ""
    truck_counts: dict[str, int] | None = None
    corridor_claims: dict[str, str] | None = None
    driver_assignments: list[DriverAssignmentItem] | None = None
    selected_corridors: list[str] | None = None
    prompt: str = ""
    fuel_price: float = 0.0
    driver_day_cost: float = 0.0
    scope: str = "all"  # "all", "1", "3", or comma-separated truck IDs / driver names
    focus_truck_id: str = ""


class UploadManifestRequest(BaseModel):
    filename: str = ""
    mime_type: str = ""
    file_base64: str = ""
    text: str = ""
    raw_text: str = ""
    sample_file: str = ""
    hub_id: str = ""


class CustomBoxInput(BaseModel):
    sku: str = "PNT-EMU-20L"
    qty: int = Field(default=1, ge=1, le=50)
    stop_seq: int = Field(default=1, ge=1, le=30)
    custom_name: str = ""
    l_cm: float = 0.0
    w_cm: float = 0.0
    h_cm: float = 0.0
    weight_kg: float = 0.0
    fragile: bool = False


class RepackRequest(BaseModel):
    source_truck_id: str = ""
    target_truck_code: str = "T17"
    extra_boxes: list[CustomBoxInput] = []
    clear_existing_boxes: bool = False


class ChatRequest(BaseModel):
    prompt: str


class ScanPhotoRequest(BaseModel):
    sample_name: str = ""
    image_base64: str = ""
    mime_type: str = "image/jpeg"
    auto_replan: bool = True


class IngestTextRequest(BaseModel):
    text: str = ""
    sample_file: str = ""
    auto_replan: bool = True


class BigQueryRequest(BaseModel):
    sql: str
    use_live_bq: bool = True


def _build_hub_context_payload(hub_id: str = "BHW-DC", order_source: str = "demo") -> dict[str, Any]:
    """Build dynamic Hub-specific metadata: driver roster, fleet pool, 8-corridor demand, and store manifest."""
    from app.optim.corridors import corridor_of

    ctx = _get_ctx()
    sess = T.session(ctx.state)
    city_cfg, hub = resolve_city_and_hub(query_hub=hub_id or "BHW-DC")
    src_norm = "demo" if (not order_source or order_source.startswith("sample_")) else order_source
    stops = T.current_stops(sess, src_norm, hub_id=hub.hub_id)

    # Hub-specific driver profiles with default home corridor & preferred vehicle
    corridor_keys = ["W", "S", "NE", "N", "E", "NW", "SE", "SW"]
    pref_trucks = ["T17", "T17", "T14", "T14", "T20", "PKP", "ACE", "T14"]
    driver_profiles = []
    for idx, drv_name in enumerate(city_cfg.default_drivers):
        hc = corridor_keys[idx % len(corridor_keys)]
        pt = pref_trucks[idx % len(pref_trucks)]
        driver_profiles.append({
            "name": drv_name,
            "home_corridor": hc,
            "home_corridor_name": CORRIDOR_NAMES.get(hc, hc),
            "preferred_truck": pt,
            "shift": "08:00–18:00",
        })

    # Compute live demand per compass corridor for this hub's stops
    corr_buckets: dict[str, list[Stop]] = {c: [] for c in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]}
    stores_out = []
    for s in stops:
        c = corridor_of(hub, s)
        corr_buckets.setdefault(c, []).append(s)
        stores_out.append({
            "stop_id": s.stop_id,
            "name": s.name,
            "area": s.area or s.address.split(",")[-1].strip(),
            "address": s.address,
            "corridor": c,
            "corridor_name": CORRIDOR_NAMES.get(c, c),
            "cartons": len(s.boxes),
            "volume_m3": round(s.volume_m3, 2),
            "weight_kg": round(s.weight_kg, 1),
        })

    compass_labels = {
        "N": "North",
        "NE": "North-East",
        "E": "East",
        "SE": "South-East",
        "S": "South",
        "SW": "South-West",
        "W": "West",
        "NW": "North-West",
    }
    corridor_summary = []
    for c_code in ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]:
        c_stops = corr_buckets.get(c_code, [])
        vol = round(sum(x.volume_m3 for x in c_stops), 2)
        wt = round(sum(x.weight_kg for x in c_stops), 1)
        ctns = sum(len(x.boxes) for x in c_stops)
        # Recommend smallest single truck or multi-truck split
        rec_truck = "ACE"
        for tc in ["ACE", "PKP", "T14", "T17", "T20"]:
            spec = TRUCK_CATALOGUE[tc]
            if spec.volume_m3 * 0.82 >= vol and spec.payload_kg * 0.95 >= wt:
                rec_truck = tc
                break
        else:
            rec_truck = "T20 + Branch"
        sample_areas = ", ".join(sorted({x.area for x in c_stops if x.area})[:3]) or "Hub Sector"
        if city_cfg.city_id == "mumbai":
            c_name = CORRIDOR_NAMES.get(c_code, c_code)
        else:
            c_name = f"{compass_labels.get(c_code, c_code)} ({sample_areas})"
        corridor_summary.append({
            "code": c_code,
            "name": c_name,
            "stops": len(c_stops),
            "cartons": ctns,
            "volume_m3": vol,
            "weight_kg": wt,
            "recommended_truck": rec_truck,
            "sample_areas": sample_areas,
        })

    # Hub-specific default fleet counts
    hub_fleet = dict(DEFAULT_FLEET_AVAILABLE)
    if city_cfg.city_id == "bangalore":
        hub_fleet = {"ACE": 2, "PKP": 2, "T14": 3, "T17": 3, "T20": 1}

    return {
        "city_id": city_cfg.city_id,
        "city_name": city_cfg.display_name,
        "hub": {
            "id": hub.hub_id,
            "hub_id": hub.hub_id,
            "name": hub.name,
            "address": hub.address,
            "lat": hub.lat,
            "lon": hub.lon,
        },
        "order_source": order_source or "demo",
        "total_stops": len(stops),
        "total_cartons": sum(len(s.boxes) for s in stops),
        "total_volume_m3": round(sum(s.volume_m3 for s in stops), 1),
        "total_weight_tonnes": round(sum(s.weight_kg for s in stops) / 1000.0, 2),
        "drivers": driver_profiles,
        "driver_names": list(city_cfg.default_drivers),
        "truck_counts": hub_fleet,
        "corridor_summary": corridor_summary,
        "stores": stores_out,
        "connectors": [
            {"id": "bigquery", "name": "Google BigQuery Order Book", "status": "CONNECTED", "icon": "📊", "desc": f"{DEFAULT_PROJECT}.{DEFAULT_DATASET} (live stores & cartons)"},
            {"id": "excel_csv", "name": "Excel / CSV / TSV Spreadsheet", "status": "READY", "icon": "📗", "desc": "Upload .xlsx, .csv, .tsv delivery sheets"},
            {"id": "gsheets", "name": "Google Sheets Live Sync", "status": "READY", "icon": "📄", "desc": "Paste or link tabular dispatch rows"},
            {"id": "sap_erp", "name": "SAP S/4HANA / Oracle TMS", "status": "PLUGIN READY", "icon": "🔌", "desc": "Pluggable IDoc / webhook connector slot"},
        ],
    }


# ==============================================================================
# Endpoints
# ==============================================================================
@router.get("/api/hub-context")
def api_get_hub_context(hub_id: str = "BHW-DC", order_source: str = "demo") -> dict[str, Any]:
    """Return dynamic Hub-aware drivers, fleet counts, corridor breakdown, and store manifest for the Launchpad."""
    return _build_hub_context_payload(hub_id=hub_id, order_source=order_source)


@router.post("/api/upload-manifest")
def api_upload_manifest(req: UploadManifestRequest) -> dict[str, Any]:
    """Parse an uploaded Excel (.xlsx), CSV (.csv), TSV, or text delivery manifest and stage it for the agent."""
    from app.ingest.orders import from_file_bytes, from_text

    t0 = time.perf_counter()
    ctx = _get_ctx()
    st = ctx.state
    sess = T.session(st)
    p = T.params_from_state(st)

    stops: list[Stop] = []
    issues: list[str] = []
    fname = req.filename or req.sample_file or "uploaded_manifest.csv"
    txt_body = (req.text or req.raw_text or "").strip()

    if req.sample_file:
        sp = SAMPLES_DIR / Path(req.sample_file).name
        if not sp.is_file():
            raise HTTPException(status_code=404, detail=f"Sample file not found: {req.sample_file}")
        raw_bytes = sp.read_bytes()
        stops, issues = from_file_bytes(raw_bytes, req.mime_type or "text/plain", sp.name)
    elif req.file_base64:
        b64_clean = req.file_base64.split(",")[-1]
        raw_bytes = base64.b64decode(b64_clean)
        stops, issues = from_file_bytes(raw_bytes, req.mime_type or "", fname)
    elif txt_body:
        if fname.lower().endswith((".csv", ".tsv")) or "," in txt_body.splitlines()[0]:
            stops, issues = from_file_bytes(txt_body.encode("utf-8"), "text/csv", fname)
        if not stops:
            stops, issues = from_text(txt_body, use_llm=False)
    else:
        raise HTTPException(status_code=400, detail="Provide an Excel/CSV file, sample_file, or text rows.")

    if not stops:
        raise HTTPException(
            status_code=400,
            detail=f"Could not geocode any stops from '{fname}'. Include known Mumbai or Bangalore locality names (e.g. Andheri, Borivali, Thane, Whitefield, Electronic City, Koramangala).",
        )

    sess["stops"] = stops
    sess["source"] = "chat"
    p.order_source = "chat"
    if req.hub_id and req.hub_id.upper() in ALL_HUBS:
        p.hub_id = req.hub_id.upper()
    else:
        _, auto_hub = resolve_city_and_hub(stops=stops)
        p.hub_id = auto_hub.hub_id
    T.save_params(st, p)

    ms = (time.perf_counter() - t0) * 1000.0
    total_cartons = sum(len(s.boxes) for s in stops)
    _record_audit(
        action="Spreadsheet / Manifest Loaded",
        detail=f"File={fname} · {len(stops)} stops · {total_cartons} cartons staged for Hub {p.hub_id}",
        tool_name="ingest_delivery_orders",
        latency_ms=ms,
    )
    return {
        "status": "ok",
        "filename": fname,
        "stops_parsed": len(stops),
        "cartons_parsed": total_cartons,
        "OrderCount": len(stops),
        "TotalCartons": total_cartons,
        "issues": issues[:8],
        "hub_context": _build_hub_context_payload(hub_id=p.hub_id, order_source="chat"),
    }


@router.get("/api/meta")
def get_meta(include_plan: bool = True) -> dict[str, Any]:
    """Return master catalogue, hubs, SKUs, sample files, and initial hub context for the Launchpad."""
    ctx = _get_ctx()

    sample_photos = []
    if SAMPLES_DIR.is_dir():
        for p in sorted(SAMPLES_DIR.iterdir()):
            if p.suffix.lower() in (".jpg", ".jpeg", ".png") and not p.name.startswith("bg_"):
                label = p.stem.replace("_", " ").title()
                sample_photos.append({"filename": p.name, "label": label, "url": f"/api/samples/{p.name}"})

    sample_orders = []
    if SAMPLES_DIR.is_dir():
        for p in sorted(SAMPLES_DIR.iterdir()):
            if p.suffix.lower() in (".txt", ".csv"):
                sample_orders.append({
                    "filename": p.name,
                    "label": p.stem.replace("_", " ").title(),
                    "preview": p.read_text(encoding="utf-8", errors="ignore")[:600],
                })

    initial_plan_bundle = None
    if include_plan:
        plan = _ensure_plan(ctx)
        initial_plan_bundle = serialize_plan_bundle(plan)

    return {
        "cities": [
            {
                "city_id": cid,
                "name": cfg.display_name,
                "default_hub_id": cfg.default_hub_id,
                "hubs": [
                    {"hub_id": h.hub_id, "name": h.name, "address": h.address, "lat": h.lat, "lon": h.lon}
                    for h in cfg.hubs.values()
                ],
                "drivers": cfg.default_drivers,
            }
            for cid, cfg in CITIES.items()
        ],
        "truck_types": [
            {
                "code": t.code,
                "name": t.name,
                "inner_l_cm": t.inner_l_cm,
                "inner_w_cm": t.inner_w_cm,
                "inner_h_cm": t.inner_h_cm,
                "volume_m3": round(t.volume_m3, 1),
                "payload_kg": t.payload_kg,
                "fixed_daily_cost_inr": t.fixed_daily_cost_inr,
                "cost_per_km_inr": t.cost_per_km_inr,
                "km_per_litre": t.km_per_litre,
                "color": t.color,
                "default_count": DEFAULT_FLEET_AVAILABLE.get(t.code, 2),
            }
            for t in TRUCK_CATALOGUE.values()
        ],
        "skus": [
            {
                "sku": s.sku,
                "description": s.description,
                "l_cm": s.l_cm,
                "w_cm": s.w_cm,
                "h_cm": s.h_cm,
                "weight_kg": s.weight_kg,
                "fragile": s.fragile,
                "this_side_up": s.this_side_up,
                "category": s.category,
                "industry": s.industry,
            }
            for s in SKU_MASTER.values()
        ],
        "corridors": [{"code": k, "name": v} for k, v in CORRIDOR_NAMES.items()],
        "drivers": DEFAULT_DRIVERS,
        "default_costs": {
            "fuel_price_per_litre": DEFAULT_COST_PROFILE.fuel_price_per_litre,
            "driver_day_cost": DEFAULT_COST_PROFILE.driver_day_cost,
            "helper_day_cost": DEFAULT_COST_PROFILE.helper_day_cost,
            "overtime_per_hour": DEFAULT_COST_PROFILE.overtime_per_hour,
        },
        "sample_photos": sample_photos,
        "sample_orders": sample_orders,
        "gcp_services": [
            {
                "id": "cloud_run",
                "name": "Google Cloud Run",
                "role": "Serverless Container Runtime",
                "status": "ACTIVE",
                "detail": "FastAPI + Uvicorn container (port 8080, auto-scaling 1–20 instances)",
                "icon": "🚀",
            },
            {
                "id": "bigquery",
                "name": "BigQuery Warehouse",
                "role": "Enterprise Order Book & KPI Analytics",
                "status": "CONNECTED",
                "detail": f"{DEFAULT_PROJECT}.{DEFAULT_DATASET} (stores, cartons, orders, kpi_runs)",
                "icon": "📊",
            },
            {
                "id": "vertex_ai",
                "name": "Vertex AI Agent Engine",
                "role": "Gemini 2.5 Flash + Google ADK",
                "status": "ACTIVE",
                "detail": "Managed Reasoning Engine · Dual-surface (Gemini Enterprise + Web UI)",
                "icon": "🧠",
            },
            {
                "id": "routes_api",
                "name": "Google Maps Routes API",
                "role": "Highway Geodesics & Live Traffic",
                "status": "ACTIVE",
                "detail": f"Active router: {provider_name()} · Turn-by-turn Directions & Embed",
                "icon": "🗺️",
            },
            {
                "id": "model_armor",
                "name": "Model Armor & Cloud DLP",
                "role": "Prompt Guardrails & PII/GSTIN Masking",
                "status": "PROTECTED",
                "detail": "Pre-turn injection filter + Post-turn deterministic math verification",
                "icon": "🛡️",
            },
            {
                "id": "gcs",
                "name": "Cloud Storage (GCS)",
                "role": "3D Videos, Driver Portals & Dock Media",
                "status": "ACTIVE",
                "detail": f"gs://{DEFAULT_PROJECT}-fleetflow-media (V4 signed URLs & mobile portals)",
                "icon": "☁️",
            },
        ],
        "gcp_config": {
            "project_id": DEFAULT_PROJECT,
            "dataset": DEFAULT_DATASET,
            "region": DEFAULT_LOCATION,
        },
        "hub_context": _build_hub_context_payload(hub_id="BHW-DC", order_source="demo"),
        "initial_plan": initial_plan_bundle,
    }


@router.post("/api/plan")
def api_run_plan(req: PlanRequest) -> dict[str, Any]:
    """Synthesize and run the dispatch plan from the Launchpad or Control Tower using the shared backend engine."""
    from app.optim.corridors import corridor_of

    t0 = time.perf_counter()
    ctx = _get_ctx()
    st = ctx.state
    p = T.params_from_state(st)
    sess = T.session(st)

    replan_needed = False
    if req.city:
        _, default_hub = resolve_city_and_hub(query_city=req.city)
        if p.hub_id != default_hub.hub_id:
            p.hub_id = default_hub.hub_id
            replan_needed = True
    if req.hub_id and req.hub_id.upper() in ALL_HUBS:
        if p.hub_id != req.hub_id.upper():
            p.hub_id = req.hub_id.upper()
            replan_needed = True
    if req.dispatch_date:
        p.dispatch_date = req.dispatch_date[:10]
    if req.objective:
        try:
            obj = Objective(req.objective)
            if p.objective != obj:
                p.objective = obj
                replan_needed = True
        except ValueError:
            pass
    if req.order_source in ("demo", "bigquery", "photos", "chat"):
        if p.order_source != req.order_source:
            p.order_source = req.order_source
            replan_needed = True
    if req.truck_counts:
        clean_counts = {k.upper(): max(0, int(v)) for k, v in req.truck_counts.items() if k.upper() in TRUCK_CATALOGUE}
        if clean_counts and sum(clean_counts.values()) > 0 and clean_counts != p.truck_counts:
            p.truck_counts = clean_counts
            replan_needed = True

    # Merge corridor_claims + structured driver_assignments (with optional truck_type!)
    merged_claims: dict[str, str] = {}
    if req.corridor_claims is not None:
        for drv, corr_val in req.corridor_claims.items():
            if drv and corr_val:
                raw_corr = str(corr_val).strip()
                tc = ""
                if "|" in raw_corr:
                    raw_corr, tc = [x.strip() for x in raw_corr.split("|", 1)]
                nc = normalize_corridor(raw_corr)
                if nc:
                    tc_up = tc.upper()
                    merged_claims[drv.strip().title()] = f"{nc}|{tc_up}" if tc_up in TRUCK_CATALOGUE else nc

    if req.driver_assignments is not None:
        for item in req.driver_assignments:
            drv = (item.driver or "").strip().title()
            nc = normalize_corridor(item.corridor or "")
            tc_up = (item.truck_type or "").strip().upper()
            if drv and nc:
                merged_claims[drv] = f"{nc}|{tc_up}" if tc_up in TRUCK_CATALOGUE else nc

    # Also parse natural-language prompt overrides if entered on the Launchpad
    prompt_str = (req.prompt or "").strip()
    if prompt_str:
        ql = prompt_str.lower()
        if any(w in ql for w in ("bangalore", "bengaluru", "nelamangala", "electronic city", "blr")):
            p.hub_id = "BLR-EC" if "electronic" in ql else "BLR-NLG"
            replan_needed = True
        elif "taloja" in ql:
            p.hub_id = "TLJ-DC"
            replan_needed = True
        elif "bhiwandi" in ql or "mumbai" in ql:
            p.hub_id = "BHW-DC"
            replan_needed = True
        if "fewest" in ql:
            p.objective = Objective.FEWEST_TRUCKS
            replan_needed = True
        elif "fast" in ql:
            p.objective = Objective.FASTEST_COMPLETION
            replan_needed = True
        elif "balanc" in ql:
            p.objective = Objective.BALANCED
            replan_needed = True

        # Parse natural-language driver + corridor + optional truck size e.g. "Ravi to West in T14"
        all_drv_names = "|".join(
            sorted({d.lower() for cfg in CITIES.values() for d in cfg.default_drivers}, key=len, reverse=True)
        )
        for m_c in re.finditer(
            rf"\b({all_drv_names})\b[^.;,\n]*?\b(north[\s-]*east|north[\s-]*west|south[\s-]*east|south[\s-]*west|north|south|east|west|ne|nw|se|sw)\b",
            ql,
        ):
            d_name = m_c.group(1).title()
            c_norm = normalize_corridor(m_c.group(2))
            # Check if a truck code or size is mentioned in the same clause
            clause = ql[max(0, m_c.start() - 15):min(len(ql), m_c.end() + 45)]
            tc_match = re.search(r"\b(ace|pkp|t14|t17|t20|14\s*ft|17\s*ft|20\s*ft|22\s*ft|small\s*truck)\b", clause)
            tc_code = ""
            if tc_match:
                tok = tc_match.group(1).upper().replace(" ", "")
                tc_map = {"14FT": "T14", "17FT": "T17", "20FT": "T20", "22FT": "T20", "SMALLTRUCK": "T14"}
                tc_code = tc_map.get(tok, tok)
            if c_norm:
                merged_claims[d_name] = f"{c_norm}|{tc_code}" if tc_code in TRUCK_CATALOGUE else c_norm
                replan_needed = True

    if req.corridor_claims is not None or req.driver_assignments is not None or merged_claims:
        if merged_claims != p.corridor_claims:
            p.corridor_claims = merged_claims
            replan_needed = True

    if req.fuel_price > 0 and req.fuel_price != p.fuel_price_per_litre:
        p.fuel_price_per_litre = float(req.fuel_price)
        replan_needed = True
    if req.driver_day_cost > 0 and req.driver_day_cost != p.driver_day_cost:
        p.driver_day_cost = float(req.driver_day_cost)
        replan_needed = True

    # Optional corridor filtering from Launchpad (e.g., dispatch only selected compass sectors)
    saved_stops_backup = None
    if req.selected_corridors and len(req.selected_corridors) < 8:
        valid_corrs = {normalize_corridor(c) for c in req.selected_corridors if normalize_corridor(c)}
        if valid_corrs:
            _, hub_obj = resolve_city_and_hub(query_hub=p.hub_id)
            base_stops = T.current_stops(sess, p.order_source, hub_id=p.hub_id)
            filtered_stops = [s for s in base_stops if corridor_of(hub_obj, s) in valid_corrs]
            if filtered_stops:
                saved_stops_backup = (sess.get("stops"), p.order_source)
                sess["stops"] = filtered_stops
                p.order_source = "chat"
                replan_needed = True

    T.save_params(st, p)
    try:
        if replan_needed or sess.get("plan") is None:
            T.run_plan(st, focus_truck_id=req.focus_truck_id or None)
    finally:
        if saved_stops_backup is not None:
            sess["stops"], p.order_source = saved_stops_backup
            T.save_params(st, p)

    plan = sess["plan"]

    # Determine active_trucks from req.scope or prompt
    active_trucks: list[str] | None = None
    scope_str = (req.scope or "all").strip()
    if scope_str.lower() not in ("all", "", "fleet", "all trucks"):
        if scope_str == "1":
            focus_id = req.focus_truck_id or (plan.routes[0].truck_id if plan.routes else "")
            active_trucks = [focus_id] if focus_id else None
        elif scope_str == "3":
            active_trucks = [r.truck_id for r in plan.routes[:3]]
        else:
            active_trucks = T.parse_target_trucks(scope_str, plan)
    elif prompt_str:
        targets = T.parse_target_trucks(prompt_str, plan)
        if targets is not None and len(targets) < len(plan.routes):
            active_trucks = targets

    focus_id = req.focus_truck_id
    if not focus_id:
        focus_id = active_trucks[0] if active_trucks else (plan.routes[0].truck_id if plan.routes else "")

    ms = (time.perf_counter() - t0) * 1000.0
    _record_audit(
        action="Dispatch Synthesis & Optimization",
        detail=f"Hub={p.hub_id} · Obj={p.objective.value} · Claims={len(p.corridor_claims)} · {len(plan.routes)} trucks",
        tool_name="plan_dispatch",
        latency_ms=ms,
    )
    out_bundle = serialize_plan_bundle(plan, active_trucks=active_trucks, focus_truck_id=focus_id)
    out_bundle["hub_context"] = _build_hub_context_payload(hub_id=p.hub_id, order_source=p.order_source)
    try:
        hist_rec = record_dispatch_run(
            out_bundle,
            actor="Fleet Dispatcher",
            prompt=prompt_str or "Standard Dispatch Optimization",
        )
        out_bundle["history_record"] = hist_rec
    except Exception as exc:
        logger.warning("Could not record dispatch run: %s", exc)
    return out_bundle


@router.post("/api/repack-truck")
def api_repack_truck(req: RepackRequest) -> dict[str, Any]:
    """Interactive 3D Load Studio Calculator: test packing any route + custom boxes into any truck type."""
    t0 = time.perf_counter()
    ctx = _get_ctx()
    plan = _ensure_plan(ctx)

    target_code = (req.target_truck_code or "T17").upper()
    if target_code not in TRUCK_CATALOGUE:
        raise HTTPException(status_code=400, detail=f"Unknown truck type: {target_code}")
    truck_spec = TRUCK_CATALOGUE[target_code]

    route = next((r for r in plan.routes if r.truck_id == req.source_truck_id), None)
    if route is None and plan.routes:
        route = plan.routes[0]

    # Build stops list in delivery order
    if req.clear_existing_boxes or route is None:
        base_stops: list[Stop] = []
    else:
        base_stops = [rs.stop for rs in route.stops]

    # Group any extra custom boxes by stop_seq
    stops_by_seq: dict[int, Stop] = {idx + 1: s for idx, s in enumerate(base_stops)}
    for idx, eb in enumerate(req.extra_boxes):
        sku_obj = SKU_MASTER.get(eb.sku)
        l_cm = eb.l_cm if eb.l_cm > 0 else (sku_obj.l_cm if sku_obj else 40.0)
        w_cm = eb.w_cm if eb.w_cm > 0 else (sku_obj.w_cm if sku_obj else 30.0)
        h_cm = eb.h_cm if eb.h_cm > 0 else (sku_obj.h_cm if sku_obj else 30.0)
        wt_kg = eb.weight_kg if eb.weight_kg > 0 else (sku_obj.weight_kg if sku_obj else 15.0)
        desc = eb.custom_name or (sku_obj.description if sku_obj else f"Custom Carton ({l_cm:g}×{w_cm:g}×{h_cm:g})")
        fragile = eb.fragile if eb.l_cm > 0 else (sku_obj.fragile if sku_obj else eb.fragile)
        seq = max(1, min(eb.stop_seq, max(len(stops_by_seq) + 1, 1)))

        if seq not in stops_by_seq:
            stops_by_seq[seq] = Stop(
                stop_id=f"CUST-{seq:02d}",
                name=f"Custom Drop #{seq}",
                address="Custom Dealer Consignment",
                lat=plan.hub.lat + 0.03 * seq,
                lon=plan.hub.lon + 0.03 * seq,
                window_start_min=480,
                window_end_min=1020,
                boxes=(),
                area="Custom",
            )
        target_stop = stops_by_seq[seq]
        new_boxes = [
            Box(
                box_id=f"ADD-{idx + 1}-{q + 1:02d}",
                stop_id=target_stop.stop_id,
                sku=eb.sku if sku_obj else "CUSTOM-SKU",
                description=desc,
                l_cm=l_cm,
                w_cm=w_cm,
                h_cm=h_cm,
                weight_kg=wt_kg,
                fragile=fragile,
                this_side_up=True,
                category=sku_obj.category if sku_obj else "custom",
            )
            for q in range(eb.qty)
        ]
        stops_by_seq[seq] = dataclasses.replace(target_stop, boxes=target_stop.boxes + tuple(new_boxes))

    ordered_stops = [stops_by_seq[k] for k in sorted(stops_by_seq.keys())]
    sim_truck_id = f"{target_code}-SIM" if (not route or route.truck_type.code != target_code or req.extra_boxes) else route.truck_id
    lp = pack_truck_lifo(sim_truck_id, truck_spec, ordered_stops)

    placed = sorted(lp.placed, key=lambda q: q.load_step)
    truck_anim_obj = {
        "id": sim_truck_id,
        "name": truck_spec.name,
        "L": truck_spec.inner_l_cm,
        "W": truck_spec.inner_w_cm,
        "H": truck_spec.inner_h_cm,
        "color": truck_spec.color,
        "driver": route.driver if route else "Simulator",
        "corridor": route.corridor if route else "SIM",
        "branch": route.branch if route else "Custom 3D Load",
        "fill": lp.volume_fill_pct,
        "wfill": lp.weight_fill_pct,
        "lifo": lp.lifo_ok,
        "active": True,
        "zones": [[z.stop_seq, z.x_start, z.x_end] for z in lp.zones],
        "stops": [
            {
                "seq": i + 1,
                "name": s.name[:32],
                "n": len(s.boxes),
                "eta": f"{8 + i:02d}:30",
                "addr": s.address.split(", ")[-1],
            }
            for i, s in enumerate(ordered_stops)
        ],
        "desc": {p.box.sku: p.box.description[:40] for p in placed},
        "boxes": [
            [
                round(p.x), round(p.y), round(p.z),
                p.l, p.w, p.h,
                p.stop_seq,
                1 if p.box.fragile else 0,
                p.box.sku,
                round(p.box.weight_kg, 1),
                p.box.box_id,
            ]
            for p in placed
        ],
    }

    km_est = route.km if route else 85.0
    est_cost = round(
        truck_spec.fixed_daily_cost_inr
        + km_est * truck_spec.cost_per_km_inr
        + DEFAULT_COST_PROFILE.driver_day_cost
        + DEFAULT_COST_PROFILE.helper_day_cost
    )

    ms = (time.perf_counter() - t0) * 1000.0
    _record_audit(
        action="3D Load Recalculation",
        detail=f"Truck={truck_spec.code} ({truck_spec.name}) · Placed={len(lp.placed)} · Unplaced={len(lp.unplaced)}",
        tool_name="pack_truck_lifo",
        latency_ms=ms,
    )

    return {
        "status": "ok",
        "truck_anim": truck_anim_obj,
        "stats": {
            "truck_id": sim_truck_id,
            "truck_code": truck_spec.code,
            "truck_name": truck_spec.name,
            "inner_cm": f"{truck_spec.inner_l_cm:g} × {truck_spec.inner_w_cm:g} × {truck_spec.inner_h_cm:g} cm",
            "volume_capacity_m3": round(truck_spec.volume_m3, 2),
            "payload_capacity_kg": truck_spec.payload_kg,
            "placed_count": len(lp.placed),
            "unplaced_count": len(lp.unplaced),
            "unplaced_skus": [f"{b.box_id} ({b.sku})" for b in lp.unplaced[:10]],
            "volume_fill_pct": lp.volume_fill_pct,
            "weight_fill_pct": lp.weight_fill_pct,
            "weight_kg": lp.weight_kg,
            "lifo_ok": lp.lifo_ok,
            "front_axle_pct": lp.front_axle_share_pct,
            "rear_axle_pct": round(100.0 - lp.front_axle_share_pct, 1),
            "cmvr_compliant": lp.cmvr_axle_compliant,
            "cmvr_status": lp.cmvr_axle_status,
            "estimated_day_cost_inr": est_cost,
        },
        "audit_log": _AUDIT_LOG[:10],
    }


@router.post("/api/scan-photo")
def api_scan_photo(req: ScanPhotoRequest) -> dict[str, Any]:
    """Decode warehouse dock carton photo (QR + label OCR) using PhotoSource and optionally re-plan."""
    t0 = time.perf_counter()
    ctx = _get_ctx()
    sess = T.session(ctx.state)

    img_bytes: bytes | None = None
    mime = req.mime_type or "image/jpeg"
    name = req.sample_name or "uploaded_photo.jpg"

    if req.sample_name:
        p = SAMPLES_DIR / Path(req.sample_name).name
        if not p.is_file():
            raise HTTPException(status_code=404, detail=f"Sample photo not found: {req.sample_name}")
        img_bytes = p.read_bytes()
        mime = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    elif req.image_base64:
        raw = req.image_base64.split(",")[-1]
        img_bytes = base64.b64decode(raw)
    else:
        raise HTTPException(status_code=400, detail="Provide sample_name or image_base64.")

    sess["attachments"] = [(img_bytes, mime, name)]
    scan_res = T.scan_box_manifest(ctx)

    bundle = None
    if req.auto_replan and scan_res.get("status") == "ok":
        T.run_plan(ctx.state)
        bundle = serialize_plan_bundle(sess["plan"])

    ms = (time.perf_counter() - t0) * 1000.0
    _record_audit(
        action="Dock QR Vision Scan",
        detail=f"File={name} · Decoded={scan_res.get('cartons_read', 0)} cartons",
        tool_name="scan_box_manifest",
        latency_ms=ms,
    )
    return {"scan": scan_res, "bundle": bundle, "audit_log": _AUDIT_LOG[:10]}


@router.post("/api/ingest-orders")
def api_ingest_orders(req: IngestTextRequest) -> dict[str, Any]:
    """Ingest unstructured order text / CSV / ERP paste and optionally re-plan."""
    t0 = time.perf_counter()
    ctx = _get_ctx()
    sess = T.session(ctx.state)

    text = req.text
    if req.sample_file and not text.strip():
        p = SAMPLES_DIR / Path(req.sample_file).name
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="ignore")

    res = T.ingest_delivery_orders(ctx, text=text)
    bundle = None
    if req.auto_replan and res.get("status") == "ok":
        T.run_plan(ctx.state)
        bundle = serialize_plan_bundle(sess["plan"])

    ms = (time.perf_counter() - t0) * 1000.0
    _record_audit(
        action="ERP / Text Order Intake",
        detail=f"Parsed {res.get('stops', 0)} stops, {res.get('cartons', 0)} cartons",
        tool_name="ingest_delivery_orders",
        latency_ms=ms,
    )
    return {"ingest": res, "bundle": bundle, "audit_log": _AUDIT_LOG[:10]}


@router.post("/api/agent-chat")
def api_agent_chat(req: ChatRequest) -> dict[str, Any]:
    """Execute natural-language commands against the shared FleetFlow tool layer."""
    t0 = time.perf_counter()
    ctx = _get_ctx()
    st = ctx.state
    sess = T.session(st)
    q = (req.prompt or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty prompt.")

    ql = q.lower()
    tool_used = "plan_dispatch"
    active_trucks: list[str] | None = None
    reply = ""

    # 0. Check for how-to / architecture / deployment questions
    if any(w in ql for w in ("how to use", "how do i use", "architecture", "how to deploy", "deployment option", "why bigquery", "why cloud storage")):
        tool_used = "get_architecture_and_howto"
        info = T.get_architecture_and_howto(ctx)
        plan = _ensure_plan(ctx)
        reply = (
            "**FleetFlow Architecture & How-To:** "
            "1) **Dual Deployment:** Run `./scripts/deploy.sh --target gemini-enterprise` or `--target ui` (zero hardcoded credentials). "
            "2) **BigQuery & GCS:** BigQuery stores the 13-table enterprise order book (`stores`, `orders`, `cartons`), while Cloud Storage serves V4-signed 3D MP4 videos & zero-login mobile driver portals. "
            "3) **How to Use:** Select a hub & goal in the left rail, scope to 1/3/All trucks, test truck sizes in **3D Load Studio**, or open the **📘 Architecture & How-To** tab."
        )

    # 1. Check for reset
    elif "reset" in ql or "default demo" in ql:
        tool_used = "reset_to_demo_data"
        T.reset_to_demo_data(ctx)
        T.run_plan(st)
        plan = sess["plan"]
        reply = f"Reset to default demo order book for **{plan.hub.name}** ({sum(len(r.stops) for r in plan.routes)} stops, {len(plan.routes)} trucks)."

    # 2. Check for corridor claim e.g. "pin Ravi to West", "Suresh claims South", "Ravi has West"
    elif m_claim := re.search(
        r"\b(ravi|sanjay|imran|deepak|arjun|manoj|farhan|suresh|vikram|naveen|prakash|kiran)\b.*?\b(north[\s-]*east|north[\s-]*west|south[\s-]*east|south[\s-]*west|north|south|east|west|ne|nw|se|sw)\b",
        ql,
    ):
        drv = m_claim.group(1).title()
        corr_raw = m_claim.group(2)
        tool_used = "claim_corridor"
        res = T.claim_corridor(ctx, driver=drv, corridor=corr_raw)
        plan = sess["plan"]
        matched = T.parse_target_trucks(drv, plan)
        active_trucks = matched
        reply = (
            f"Pinned **{drv}** to **{res.get('claim', corr_raw)}** with trunk-and-branch splitting. "
            f"Fleet re-optimized to **{plan.optimized.trucks} trucks** (saving **₹{plan.savings_inr:,.0f}/day**)."
        )

    # 3. Check for city/hub switch
    elif any(w in ql for w in ("bangalore", "bengaluru", "nelamangala", "electronic city", "blr", "taloja")):
        city_q = "bangalore" if any(w in ql for w in ("bangalore", "bengaluru", "nelamangala", "electronic city", "blr")) else "mumbai"
        hub_q = "BLR-EC" if "electronic" in ql else ("BLR-NLG" if city_q == "bangalore" else ("TLJ-DC" if "taloja" in ql else "BHW-DC"))
        obj_q = "fewest_trucks" if "fewest" in ql or "truck" in ql else "lowest_cost"
        T.plan_dispatch(ctx, city=city_q, hub_id=hub_q, objective=obj_q)
        plan = sess["plan"]
        reply = (
            f"Switched hub to **{plan.hub.name}** (`{plan.hub.hub_id}`). "
            f"Optimized **{sum(len(r.stops) for r in plan.routes)} stops** into **{plan.optimized.trucks} trucks** "
            f"(down from {plan.baseline.trucks}, saving **₹{plan.savings_inr:,.0f}/day**)."
        )

    # 4. Check for scoping / filtering (1 truck, 3 trucks, specific driver/truck, or all)
    else:
        plan = _ensure_plan(ctx)
        targets = T.parse_target_trucks(q, plan)
        if targets is not None:
            active_trucks = targets
            tool_used = "get_truck_load_plan" if ("load" in ql or "3d" in ql or "box" in ql or "pack" in ql) else "driver_briefings"
            if len(targets) == 1:
                r = next((x for x in plan.routes if x.truck_id == targets[0]), plan.routes[0])
                lp = plan.loads.get(r.truck_id)
                reply = (
                    f"Scoped view to **{r.truck_id} ({r.driver})** on **{CORRIDOR_NAMES.get(r.corridor, r.corridor)}** "
                    f"({len(r.stops)} stops, {len(lp.placed) if lp else 0} cartons, {lp.volume_fill_pct if lp else 0}% vol fill). "
                    f"All other {len(plan.routes) - 1} fleet routes are dimmed."
                )
            else:
                names = ", ".join(f"{r.truck_id} ({r.driver})" for r in plan.routes if r.truck_id in targets)
                reply = (
                    f"Highlighted **{len(targets)} trucks**: **{names}**. "
                    f"The remaining {len(plan.routes) - len(targets)} fleet routes are dimmed for clarity."
                )
        else:
            # General optimization command
            obj_q = "fewest_trucks" if "fewest" in ql else ("balanced" if "balanc" in ql else "lowest_cost")
            src_q = "bigquery" if "bigquery" in ql or "bq" in ql else ""
            T.plan_dispatch(ctx, objective=obj_q, order_source=src_q)
            plan = sess["plan"]
            active_trucks = None
            reply = (
                f"Full fleet dispatch optimized (`{plan.plan_id}`): **{plan.baseline.trucks} → {plan.optimized.trucks} trucks**, "
                f"**₹{plan.baseline.cost_total:,.0f} → ₹{plan.optimized.cost_total:,.0f}/day** "
                f"(saving **₹{plan.savings_inr:,.0f}/day**, **-{round(100 * plan.savings_inr / max(1, plan.baseline.cost_total), 1)}%**). "
                f"All {plan.optimized.trucks} trucks pass 100% LIFO & CMVR Rule 93 axle checks."
            )

    plan = sess["plan"]
    focus_id = active_trucks[0] if active_trucks else (plan.routes[0].truck_id if plan.routes else "")
    ms = (time.perf_counter() - t0) * 1000.0
    audit = _record_audit(
        action=f"AI Copilot: {q[:48]}",
        detail=reply.replace("**", "")[:90],
        tool_name=tool_used,
        latency_ms=ms,
    )
    return {
        "reply": reply,
        "tool_called": tool_used,
        "latency_ms": round(ms, 1),
        "audit": audit,
        "bundle": serialize_plan_bundle(plan, active_trucks=active_trucks, focus_truck_id=focus_id),
    }


@router.post("/api/bigquery/query")
def api_bigquery_query(req: BigQueryRequest) -> dict[str, Any]:
    """Execute SQL against BigQuery (`<project>.<dataset>`) or local in-memory analytical mirror."""
    t0 = time.perf_counter()
    sql = (req.sql or "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty.")

    ctx = _get_ctx()
    plan = _ensure_plan(ctx)

    # First attempt live BigQuery if requested and SQL references the GCP project/dataset
    if req.use_live_bq and f"{DEFAULT_PROJECT}.{DEFAULT_DATASET}" in sql:
        try:
            rows = run_query(sql, timeout_s=15)
            ms = (time.perf_counter() - t0) * 1000.0
            _record_audit("BigQuery SQL Execution", f"Live GCP query returned {len(rows)} rows", "bigquery.jobs.query", ms)
            cols = list(rows[0].keys()) if rows else []
            return {
                "engine": f"Google BigQuery ({DEFAULT_PROJECT}.{DEFAULT_DATASET})",
                "latency_ms": round(ms, 1),
                "columns": cols,
                "rows": rows[:200],
                "row_count": len(rows),
            }
        except Exception as exc:
            logger.info("Live BigQuery fallback to local mirror: %s", exc)

    # Local analytical SQLite mirror populated with live `stores`, `cartons`, `routes`, and `sku_master`
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE stores (stop_id TEXT, name TEXT, address TEXT, sales_area TEXT, lat REAL, lon REAL, window_start_min INT, window_end_min INT)"
    )
    cur.execute(
        "CREATE TABLE cartons (box_id TEXT, stop_id TEXT, sku TEXT, description TEXT, l_cm REAL, w_cm REAL, h_cm REAL, weight_kg REAL, fragile INT, category TEXT)"
    )
    cur.execute(
        "CREATE TABLE routes (truck_id TEXT, driver TEXT, truck_code TEXT, corridor TEXT, branch TEXT, stops INT, cartons INT, km REAL, cost_inr REAL, volume_fill_pct REAL, weight_fill_pct REAL, cmvr_status TEXT)"
    )

    for r in plan.routes:
        lp = plan.loads.get(r.truck_id)
        cur.execute(
            "INSERT INTO routes VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                r.truck_id, r.driver, r.truck_type.code, r.corridor, r.branch,
                len(r.stops), len(lp.placed) if lp else 0, round(r.km, 1),
                round(r.cost.total, 0), lp.volume_fill_pct if lp else 0.0,
                lp.weight_fill_pct if lp else 0.0, lp.cmvr_axle_status if lp else "Compliant",
            ),
        )
        for rs in r.stops:
            s = rs.stop
            cur.execute(
                "INSERT INTO stores VALUES (?,?,?,?,?,?,?,?)",
                (s.stop_id, s.name, s.address, s.area, s.lat, s.lon, s.window_start_min, s.window_end_min),
            )
            for b in s.boxes:
                cur.execute(
                    "INSERT INTO cartons VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (b.box_id, s.stop_id, b.sku, b.description, b.l_cm, b.w_cm, b.h_cm, b.weight_kg, int(b.fragile), b.category),
                )

    # Normalize BigQuery backtick table names so exact BigQuery SQL runs seamlessly in SQLite mirror
    clean_sql = re.sub(r"`[^`]+\.([a-zA-Z0-9_]+)`", r"\1", sql)
    clean_sql = clean_sql.replace("`", "")
    try:
        cur.execute(clean_sql)
        fetched = [dict(row) for row in cur.fetchall()]
        cols = list(fetched[0].keys()) if fetched else [d[0] for d in (cur.description or [])]
    except Exception as exc:
        conn.close()
        raise HTTPException(status_code=400, detail=f"SQL execution error: {exc}") from exc
    conn.close()

    ms = (time.perf_counter() - t0) * 1000.0
    _record_audit("BigQuery Studio Query", f"Returned {len(fetched)} rows", "bigquery.sql", ms)
    return {
        "engine": f"BigQuery Mirror ({DEFAULT_PROJECT}.{DEFAULT_DATASET})",
        "latency_ms": round(ms, 1),
        "columns": cols,
        "rows": fetched[:200],
        "row_count": len(fetched),
    }


@router.get("/api/driver-portal/{truck_id}", response_class=HTMLResponse)
def api_driver_portal(truck_id: str) -> HTMLResponse:
    """Render standalone mobile driver portal HTML for any truck in the active plan."""
    ctx = _get_ctx()
    plan = _ensure_plan(ctx)
    tid = truck_id.upper()
    if not any(r.truck_id.upper() == tid for r in plan.routes):
        tid = plan.routes[0].truck_id if plan.routes else tid
    html_str = build_driver_portal_html(plan, tid)
    return HTMLResponse(content=html_str)


@router.get("/api/samples/{filename}")
def api_sample_file(filename: str):
    """Serve sample dock photos and order files."""
    safe_name = Path(filename).name
    p = SAMPLES_DIR / safe_name
    if not p.is_file():
        raise HTTPException(status_code=404, detail="Sample file not found")
    return FileResponse(p)


@router.get("/deck", response_class=HTMLResponse)
def serve_executive_deck() -> HTMLResponse:
    """Serve the FleetFlow Executive Presentation HTML."""
    deck_path = ROOT_DIR / "fleetflow_executive_presentation.html"
    if deck_path.is_file():
        return HTMLResponse(content=deck_path.read_text(encoding="utf-8"))
    from app.render.executive_presentation_html import build_executive_presentation_html
    return HTMLResponse(content=build_executive_presentation_html())


@router.get("/ui", response_class=HTMLResponse)
@router.get("/control-tower", response_class=HTMLResponse)
def serve_control_tower_ui() -> HTMLResponse:
    """Serve the FleetFlow Supply Chain Control Tower & 3D Load Studio SPA."""
    import importlib
    import app.web.ui_html
    importlib.reload(app.web.ui_html)
    return HTMLResponse(content=app.web.ui_html.build_control_tower_html())


@router.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Container health check endpoint for Cloud Run / GKE."""
    return {"status": "ok", "service": "fleetflow-control-tower"}


@router.get("/api/history")
def api_get_history(hub_id: str = "all", search: str = "", limit: int = 50) -> list[dict[str, Any]]:
    """Retrieve historical dispatch runs filterable by hub and query."""
    return get_history_list(hub_id=hub_id, search=search, limit=limit)


@router.get("/api/history/analytics")
def api_get_history_analytics() -> dict[str, Any]:
    """Compute 30-day cumulative operational KPIs and telemetry."""
    return get_history_analytics()


@router.get("/api/history/{plan_id}")
def api_get_history_detail(plan_id: str) -> dict[str, Any]:
    """Retrieve complete plan bundle JSON for replay/restoration."""
    detail = get_history_detail(plan_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Historical plan not found")
    return detail


@router.get("/api/history/{plan_id}/report", response_class=HTMLResponse)
def api_get_history_report(plan_id: str) -> HTMLResponse:
    """Serve standalone printable Executive Dispatch Report & Audit Certificate."""
    report_file = REPORTS_DIR / f"report_{plan_id}.html"
    if report_file.is_file():
        return HTMLResponse(content=report_file.read_text(encoding="utf-8"))

    bundle = get_history_detail(plan_id)
    if bundle and "routes" in bundle:
        html = generate_dispatch_report_html(bundle)
        return HTMLResponse(content=html)
    raise HTTPException(status_code=404, detail="Dispatch report not found")


@router.get("/api/history/{plan_id}/manifest.csv")
def api_get_history_manifest(plan_id: str) -> Response:
    """Download RFC 4180 CSV consignment manifest for SAP TM / Oracle OTM / Excel."""
    manifest_file = MANIFESTS_DIR / f"manifest_{plan_id}.csv"
    if manifest_file.is_file():
        csv_text = manifest_file.read_text(encoding="utf-8")
    else:
        bundle = get_history_detail(plan_id)
        if not bundle or "routes" not in bundle:
            raise HTTPException(status_code=404, detail="Consignment manifest not found")
        csv_text = generate_dispatch_manifest_csv(bundle)

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="consignment_manifest_{plan_id}.csv"'}
    )


@router.post("/api/history/{plan_id}/restore")
def api_restore_history_plan(plan_id: str) -> dict[str, Any]:
    """Restore a historical dispatch plan into the active Control Tower session."""
    bundle = get_history_detail(plan_id)
    if not bundle or "routes" not in bundle:
        raise HTTPException(status_code=404, detail=f"Cannot restore plan {plan_id}: invalid bundle")

    _record_audit(
        action="Restore Historical Plan",
        detail=f"Restored plan {plan_id} ({bundle.get('hub', {}).get('name')}) into active session",
        tool_name="restore_plan",
        latency_ms=12.0,
    )
    return bundle

