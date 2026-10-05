"""LoadPilot ADK tools (simple, JSON-friendly signatures; compact JSON returns).

Heavy objects (order book, DispatchPlan, media links) live in a module-level cache keyed by a
session token held in `state`; only small JSON goes into session state. Visual surfaces are
queued in `state[PENDING_KEY]` and emitted deterministically by the agent's after_agent callback.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import logging
import re
import threading
import uuid
from typing import Any

from google.adk.tools import ToolContext

try:
    from app.contracts import Objective, PlanningParams, Stop
    from app.data.cities import ALL_HUBS, resolve_city_and_hub
    from app.data.demo_mmr import HUBS, build_demo_stops
    from app.data.master_data import (
        CORRIDOR_NAMES, DEFAULT_COST_PROFILE, DEFAULT_FLEET_AVAILABLE, TRUCK_CATALOGUE,
    )
    from app.optim.corridors import normalize_corridor
    from app.optim.dispatch import plan_dispatch as _plan_dispatch
except ImportError:  # pragma: no cover
    from contracts import Objective, PlanningParams, Stop
    from data.cities import ALL_HUBS, resolve_city_and_hub
    from data.demo_mmr import HUBS, build_demo_stops
    from data.master_data import (
        CORRIDOR_NAMES, DEFAULT_COST_PROFILE, DEFAULT_FLEET_AVAILABLE, TRUCK_CATALOGUE,
    )
    from optim.corridors import normalize_corridor
    from optim.dispatch import plan_dispatch as _plan_dispatch

logger = logging.getLogger(__name__)

TOKEN_KEY = "lp_token"
PARAMS_KEY = "lp_params"
PENDING_KEY = "lp_pending"

_CACHE: dict[str, dict[str, Any]] = {}
_DEMO_STOPS: dict[str, list[Stop]] = {}


# ==============================================================================
# Session helpers
# ==============================================================================
def demo_stops(hub_id: str = "") -> list[Stop]:
    city_cfg, _ = resolve_city_and_hub(query_hub=hub_id)
    return city_cfg.build_stops_fn(seed=42)


def session(state: Any) -> dict[str, Any]:
    """Return the cache entry for this ADK session (created on first use)."""
    tok = state.get(TOKEN_KEY) if state is not None else None
    if not tok:
        tok = uuid.uuid4().hex[:12]
        if state is not None:
            state[TOKEN_KEY] = tok
    return _CACHE.setdefault(tok, {"stops": None, "source": "demo", "plan": None, "links": {},
                                   "attachments": [], "scanned": [], "threads": []})


def params_to_state(p: PlanningParams) -> dict[str, Any]:
    d = dataclasses.asdict(p)
    d["objective"] = p.objective.value
    return d


def params_from_state(state: Any) -> PlanningParams:
    raw = (state.get(PARAMS_KEY) if state is not None else None) or {}
    p = PlanningParams()
    for k, v in raw.items():
        if hasattr(p, k) and v is not None:
            setattr(p, k, Objective(v) if k == "objective" else v)
    if not p.dispatch_date:
        p.dispatch_date = dt.date.today().isoformat()
    if not p.hub_id:
        p.hub_id = "BHW-DC"
    if not p.truck_counts:
        p.truck_counts = dict(DEFAULT_FLEET_AVAILABLE)
    return p


def save_params(state: Any, p: PlanningParams) -> None:
    state[PARAMS_KEY] = params_to_state(p)


def queue(state: Any, kind: str, **extra: Any) -> None:
    state[PENDING_KEY] = {"kind": kind, **extra}


def current_stops(sess: dict[str, Any], source: str, hub_id: str = "") -> list[Stop]:
    if source == "bigquery":
        try:
            from app.data.bq_source import load_stops_from_bigquery
            return load_stops_from_bigquery()
        except Exception as exc:  # noqa: BLE001 - fall back to the built-in demo book
            logging.warning("BigQuery order source failed, using demo data: %s", exc)
    base = sess["stops"] if (source == "chat" and sess["stops"]) else demo_stops(hub_id=hub_id)
    if source == "photos" and sess["scanned"]:
        by_stop: dict[str, list] = {}
        for b in sess["scanned"]:
            by_stop.setdefault(b.stop_id, []).append(b)
        out = []
        for s in base:
            extra = [b for b in by_stop.get(s.stop_id, []) if b.box_id not in {x.box_id for x in s.boxes}]
            out.append(dataclasses.replace(s, boxes=s.boxes + tuple(extra)) if extra else s)
        return out
    return base


# ==============================================================================
# Parsers for chat-style arguments
# ==============================================================================
def parse_truck_counts(text: str) -> dict[str, int]:
    """'T17=3, T14:2, ACE 1, 2 x T20' -> {'T17': 3, 'T14': 2, 'ACE': 1, 'T20': 2}."""
    out: dict[str, int] = {}
    codes = "|".join(TRUCK_CATALOGUE)
    for m in re.finditer(rf"\b({codes})\b\s*[:=x×]?\s*(\d+)", text or "", re.I):
        out[m.group(1).upper()] = int(m.group(2))
    for m in re.finditer(rf"(\d+)\s*[x×]?\s*\b({codes})\b", text or "", re.I):
        out.setdefault(m.group(2).upper(), int(m.group(1)))
    return out


def parse_claims(text: str) -> dict[str, str]:
    """'Ravi=West; Imran: North-East' -> {'Ravi': 'W', 'Imran': 'NE'}."""
    out: dict[str, str] = {}
    for chunk in re.split(r"[;,\n]+", text or ""):
        m = re.match(r"\s*([^=:]+?)\s*[=:]\s*(.+?)\s*$", chunk)
        if m:
            corr = normalize_corridor(m.group(2))
            if corr:
                out[m.group(1).strip().title()] = corr
    return out


def _objective(text: str) -> Objective | None:
    t = (text or "").lower().replace(" ", "_").replace("-", "_")
    for o in Objective:
        if o.value == t or o.value.split("_")[0] in t:
            return o
    if "truck" in t:
        return Objective.FEWEST_TRUCKS
    if "fast" in t or "time" in t:
        return Objective.FASTEST_FINISH
    if "balanc" in t:
        return Objective.BALANCED
    if "cost" in t or "cheap" in t:
        return Objective.LOWEST_COST
    return None


# ==============================================================================
# Plan runner shared by tools
# ==============================================================================
def run_plan(state: Any, focus_truck_id: str | None = None) -> dict[str, Any]:
    sess = session(state)
    p = params_from_state(state)
    stops = current_stops(sess, p.order_source, hub_id=p.hub_id)
    hub = ALL_HUBS.get(p.hub_id.upper()) if p.hub_id else None
    if hub is None:
        _, hub = resolve_city_and_hub(query_hub=p.hub_id, stops=stops)
    plan = _plan_dispatch(hub, stops, p)
    focus = focus_truck_id or (plan.routes[0].truck_id if plan.routes else None)
    plan.focus_truck_id = focus
    sess["plan"] = plan
    try:
        from app.integration.media import start_publishing
    except ImportError:  # pragma: no cover
        from integration.media import start_publishing
    sess["links"] = start_publishing(sess, plan, focus)
    queue(state, "dispatch", focus=focus)
    return plan_summary(plan)


def plan_summary(plan: Any) -> dict[str, Any]:
    b, o = plan.baseline, plan.optimized
    return {
        "plan_id": plan.plan_id, "hub": plan.hub.name, "date": plan.dispatch_date,
        "objective": plan.params.objective.value,
        "stops": sum(len(r.stops) for r in plan.routes), "unassigned_stops": len(plan.unassigned),
        "cartons": sum(len(lp.placed) for lp in plan.loads.values()),
        "today": {"trucks": b.trucks, "km": b.km, "cost_inr": b.cost_total},
        "fleetflow": {"trucks": o.trucks, "km": o.km, "cost_inr": o.cost_total,
                      "by_type": o.by_type},
        "loadpilot": {"trucks": o.trucks, "km": o.km, "cost_inr": o.cost_total,
                      "by_type": o.by_type},
        "saved_inr_per_day": round(plan.savings_inr), "saved_pct": round(
            100 * plan.savings_inr / b.cost_total, 1) if b.cost_total else 0,
        "diesel_saved_litres": plan.diesel_saved_litres,
        "co2_saved_kg": plan.co2_saved_kg,
        "annual_trees_offset": plan.annual_trees_offset_equiv,
        "cmvr_axle_compliance_all": all(lp.cmvr_axle_compliant for lp in plan.loads.values()),
        "lifo_verified_all": all(lp.lifo_ok for lp in plan.loads.values()),
        "trucks": [{"id": r.truck_id, "driver": r.driver, "corridor": r.corridor,
                    "branch": r.branch, "stops": len(r.stops), "truck": r.truck_type.name,
                    "cmvr_status": plan.loads[r.truck_id].cmvr_axle_status if r.truck_id in plan.loads else "Compliant",
                    "payload_fill_pct": plan.loads[r.truck_id].weight_fill_pct if r.truck_id in plan.loads else None,
                    "volume_fill_pct": plan.loads[r.truck_id].volume_fill_pct if r.truck_id in plan.loads else None}
                   for r in plan.routes],
        "why_drop_counts_differ": ("Each truck is filled to its payload / space / shift limit; small trucks "
                                   "(Tata Ace 0.75 t) fill after 3-4 heavy drops, 17 ft trucks take 13-15."),
        "notes": [n for n in plan.notes if "did not fit" not in n][:6],
        "ui": "Dispatch canvas and the full report are attached automatically; do not repeat tables.",
    }


# ==============================================================================
# Tools
# ==============================================================================
def show_planning_wizard(tool_context: ToolContext) -> dict[str, Any]:
    """Show the interactive planning form (date, hub, truck types & counts, objective, driver
    corridor claims, diesel and driver costs). Use when the user wants to start planning or asks
    what they need to enter."""
    p = params_from_state(tool_context.state)
    save_params(tool_context.state, p)
    queue(tool_context.state, "wizard")
    return {"status": "wizard_shown", "defaults": {
        "date": p.dispatch_date, "hub": p.hub_id, "trucks": p.truck_counts,
        "objective": p.objective.value}}


def plan_dispatch(tool_context: ToolContext, truck_counts: str = "", objective: str = "",
                  corridor_claims: str = "", fuel_price: float = 0.0, driver_day_cost: float = 0.0,
                  hub_id: str = "", city: str = "", dispatch_date: str = "", order_source: str = "",
                  driver: str = "") -> dict[str, Any]:
    """Optimise today's dispatch: corridors, truck assignment, stop order, LIFO truck loading and
    cost vs today's manual plan. Arguments are optional overrides; anything not given keeps the
    current values (from the planning form or earlier chat).

    Args:
        truck_counts: Trucks available, e.g. "T17=3, T14=2, ACE=1". Codes: ACE, PKP, T14, T17, T20.
        objective: lowest_cost | fewest_trucks | fastest_finish | balanced.
        corridor_claims: Driver or truck to corridor, e.g. "Ravi=West; T20-1=North-East".
        fuel_price: Diesel price per litre (INR). 0 keeps the current value.
        driver_day_cost: Driver cost per day (INR). 0 keeps the current value.
        hub_id: BHW-DC (Bhiwandi), TLJ-DC (Taloja), BLR-NLG (Nelamangala), BLR-EC (Electronic City).
        city: mumbai | bangalore | any city name or blank (auto-detected from hub or stops).
        dispatch_date: YYYY-MM-DD.
        driver: ONLY when the user asks for one driver or truck ("for Ravi", "only T17-1"): the fleet is
            still optimised, but the answer, map and 3D show just that driver's truck.
        order_source: demo | chat (orders pasted/uploaded) | photos (demo + scanned cartons) |
            bigquery (today's order book from BigQuery dataset loadpilot_demo).
    """
    st = tool_context.state
    p = params_from_state(st)
    if truck_counts:
        counts = parse_truck_counts(truck_counts)
        if counts:
            p.truck_counts = counts
    if objective and _objective(objective):
        p.objective = _objective(objective)  # type: ignore[assignment]
    if corridor_claims:
        p.corridor_claims = {**p.corridor_claims, **parse_claims(corridor_claims)}
    if fuel_price:
        p.fuel_price_per_litre = float(fuel_price)
    if driver_day_cost:
        p.driver_day_cost = float(driver_day_cost)
    if city:
        city_cfg, default_hub = resolve_city_and_hub(query_city=city)
        p.hub_id = default_hub.hub_id
    elif hub_id and hub_id.upper() in ALL_HUBS:
        p.hub_id = hub_id.upper()
    if dispatch_date:
        p.dispatch_date = dispatch_date[:10]
    if order_source in ("demo", "chat", "photos", "bigquery"):
        p.order_source = order_source
    save_params(st, p)
    who = (driver or "").strip().lower()
    if who in ("he", "him", "his", "this", "that", "it") and st.get("lp_last_driver"):
        who = st["lp_last_driver"].lower()

    # Fast-path for conversational follow-ups: if fleet was already planned and no parameters changed
    sess = session(st)
    if who and sess.get("plan") and not (truck_counts or objective or corridor_claims or fuel_price or driver_day_cost or city or hub_id or dispatch_date or order_source):
        plan = sess["plan"]
        r = next((x for x in plan.routes if who in (x.driver.lower(), x.truck_id.lower())), None)
        if r is not None:
            st["lp_last_driver"] = r.driver
            st["lp_last_truck"] = r.truck_id
            plan.focus_truck_id = r.truck_id
            sess["links"] = start_publishing_driver(sess, plan, r.truck_id)
            queue(st, "driver", focus=r.truck_id,
                  note=f"🗓️ {r.driver}'s part of today's fleet plan {plan.plan_id} "
                       f"({plan.optimized.trucks} trucks, ₹{plan.savings_inr:,.0f}/day saved fleet-wide).")
            return _driver_summary(plan, r.truck_id)

    try:
        out = run_plan(st)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
    if who:
        sess = session(st)
        plan = sess["plan"]
        r = next((x for x in plan.routes if who in (x.driver.lower(), x.truck_id.lower())), None)
        if r is None:
            out["note"] = f"'{driver}' is not driving today; showing the whole fleet."
            return out
        st["lp_last_driver"] = r.driver
        st["lp_last_truck"] = r.truck_id
        plan.focus_truck_id = r.truck_id
        sess["links"] = start_publishing_driver(sess, plan, r.truck_id)
        queue(st, "driver", focus=r.truck_id,
              note=f"🗓️ {r.driver}'s part of today's fleet plan {plan.plan_id} "
                   f"({plan.optimized.trucks} trucks, ₹{plan.savings_inr:,.0f}/day saved fleet-wide).")
        return _driver_summary(plan, r.truck_id)
    return out


def claim_corridor(tool_context: ToolContext, driver: str, corridor: str) -> dict[str, Any]:
    """A driver (or truck id) claims a corridor, e.g. "Ravi has the West route". The best stops in
    that corridor are pinned to his truck, other trucks branch around him, and the plan is
    re-optimised.

    Args:
        driver: Driver name or truck id (e.g. "Ravi" or "T17-2").
        corridor: Direction from the hub: N, NE, E, SE, S, SW, W, NW or words like "West".
    """
    corr = normalize_corridor(corridor)
    if not corr:
        return {"status": "error", "message": f"Unknown corridor '{corridor}'. Use N/NE/E/SE/S/SW/W/NW."}
    st = tool_context.state
    p = params_from_state(st)
    p.corridor_claims = {**p.corridor_claims, driver.strip().title(): corr}
    save_params(st, p)
    out = run_plan(st)
    out["claim"] = f"{driver.strip().title()} → {CORRIDOR_NAMES.get(corr, corr)}"
    return out


def get_truck_load_plan(tool_context: ToolContext, truck_id: str) -> dict[str, Any]:
    """Show the loading sheet, 3D loading animation and loader video for one truck (focus truck).

    Args:
        truck_id: Truck id from the plan, e.g. "T17-1", or a driver name.
    """
    st = tool_context.state
    sess = session(st)
    plan = sess.get("plan")
    if plan is None:
        run_plan(st)
        plan = sess["plan"]
    key = truck_id.strip().lower()
    if key in ("he", "him", "his", "this", "that", "it") and st.get("lp_last_driver"):
        key = st["lp_last_driver"].lower()
    elif key in ("he", "him", "his", "this", "that", "it") and st.get("lp_last_truck"):
        key = st["lp_last_truck"].lower()
    r = next((x for x in plan.routes if key in (x.truck_id.lower(), x.driver.lower())), None)
    if r is None:
        return {"status": "error", "message": f"No truck '{truck_id}' in plan.",
                "trucks": [x.truck_id for x in plan.routes]}
    st["lp_last_driver"] = r.driver
    st["lp_last_truck"] = r.truck_id
    plan.focus_truck_id = r.truck_id
    try:
        from app.integration.media import start_publishing
    except ImportError:  # pragma: no cover
        from integration.media import start_publishing
    sess["links"] = start_publishing(sess, plan, r.truck_id)
    queue(st, "truck", focus=r.truck_id)
    lp = plan.loads[r.truck_id]
    return {"truck": r.truck_id, "driver": r.driver, "type": r.truck_type.name,
            "corridor": r.corridor, "branch": r.branch, "stops": len(r.stops),
            "cartons": len(lp.placed), "volume_fill_pct": lp.volume_fill_pct,
            "payload_fill_pct": lp.weight_fill_pct, "lifo_ok": lp.lifo_ok,
            "load_first": f"stop {len(r.stops)} (last delivery) at the cab wall",
            "load_last": "stop 1 (first delivery) at the rear door",
            "ui": "Loading sheet, 3D animation and video are attached automatically."}


def ingest_delivery_orders(tool_context: ToolContext, text: str = "") -> dict[str, Any]:
    """Read a delivery/order list the user pasted (email, WhatsApp text) or attached (CSV, Excel,
    PDF), geocode the outlets, and make it the order book for planning.

    Args:
        text: The pasted order list. Leave empty to read attached files.
    """
    try:
        from app.ingest.orders import from_file_bytes, from_text
    except ImportError:  # pragma: no cover
        from ingest.orders import from_file_bytes, from_text
    st = tool_context.state
    sess = session(st)
    stops: list[Stop] = []
    issues: list[str] = []
    for data, mime, name in sess.get("attachments", []):
        if mime.startswith("image/"):
            continue
        s, i = from_file_bytes(data, mime, name)
        stops += s
        issues += i
    if text.strip():
        s, i = from_text(text)
        stops += s
        issues += i
    if not stops:
        return {"status": "error", "message": "No orders found. Paste the list or attach CSV/XLSX/PDF.",
                "issues": issues[:5]}
    stops = [dataclasses.replace(s, stop_id=f"C{k:03d}", boxes=tuple(
        dataclasses.replace(b, stop_id=f"C{k:03d}", box_id=f"C{k:03d}-B{j:02d}")
        for j, b in enumerate(s.boxes, start=1))) for k, s in enumerate(stops, start=1)]
    sess["stops"] = stops
    p = params_from_state(st)
    p.order_source = "chat"
    save_params(st, p)
    return {"status": "ok", "stops": len(stops), "cartons": sum(len(s.boxes) for s in stops),
            "volume_m3": round(sum(s.volume_m3 for s in stops), 1),
            "weight_kg": round(sum(s.weight_kg for s in stops)),
            "outlets": [f"{s.name} ({s.address.split(', ')[-1]})" for s in stops[:12]],
            "issues": issues[:6], "next": "Call plan_dispatch to optimise with these orders."}


def scan_box_manifest(tool_context: ToolContext) -> dict[str, Any]:
    """Scan attached carton photos (QR labels first, then Gemini vision reads printed labels) and
    add the cartons to the order book. The capture method is pluggable (photo, QR gun, Gemini Live)."""
    try:
        from app.capture.sources import PhotoSource
    except ImportError:  # pragma: no cover
        from capture.sources import PhotoSource
    st = tool_context.state
    sess = session(st)
    images = [(d, m) for d, m, _ in sess.get("attachments", []) if m.startswith("image/")]
    if not images:
        return {"status": "error", "message": "Attach one or more carton / pallet photos."}
    boxes, issues = PhotoSource().capture(images)
    known = {b.box_id for b in sess["scanned"]}
    sess["scanned"] += [b for b in boxes if b.box_id not in known]
    p = params_from_state(st)
    p.order_source = "photos"
    save_params(st, p)
    by_stop: dict[str, int] = {}
    for b in boxes:
        by_stop[b.stop_id] = by_stop.get(b.stop_id, 0) + 1
    return {"status": "ok", "photos": len(images), "cartons_read": len(boxes),
            "by_stop": by_stop, "fragile": sum(b.fragile for b in boxes),
            "sample": [f"{b.box_id} {b.sku} {b.l_cm:g}x{b.w_cm:g}x{b.h_cm:g}cm {b.weight_kg:g}kg"
                       for b in boxes[:6]],
            "issues": issues[:4], "next": "Call plan_dispatch to re-plan with the scanned cartons."}


def list_fleet_and_costs(tool_context: ToolContext) -> dict[str, Any]:
    """List truck types (inner size, payload, cost rates), today's availability and cost assumptions."""
    p = params_from_state(tool_context.state)
    cp = DEFAULT_COST_PROFILE
    return {
        "truck_types": [{"code": t.code, "name": t.name,
                         "inner_cm": f"{t.inner_l_cm:g}x{t.inner_w_cm:g}x{t.inner_h_cm:g}",
                         "volume_m3": round(t.volume_m3, 1), "payload_kg": t.payload_kg,
                         "day_rate_inr": t.fixed_daily_cost_inr, "per_km_inr": t.cost_per_km_inr,
                         "kmpl": t.km_per_litre}
                        for t in TRUCK_CATALOGUE.values()],
        "available_today": p.truck_counts,
        "costs": {"diesel_per_litre": p.fuel_price_per_litre or cp.fuel_price_per_litre,
                  "driver_per_day": p.driver_day_cost or cp.driver_day_cost,
                  "helper_per_day": cp.helper_day_cost, "overtime_per_hour": cp.overtime_per_hour,
                  "shift_hours": cp.shift_hours},
        "hubs": {h.hub_id: h.name for h in HUBS.values()},
    }


def reset_to_demo_data(tool_context: ToolContext) -> dict[str, Any]:
    """Reset to the demo order book (70 outlets across Mumbai MMR) and default fleet."""
    st = tool_context.state
    sess = session(st)
    sess.update({"stops": None, "scanned": [], "plan": None, "links": {}})
    save_params(st, PlanningParams(dispatch_date=dt.date.today().isoformat(), hub_id="BHW-DC",
                                   truck_counts=dict(DEFAULT_FLEET_AVAILABLE)))
    s = demo_stops()
    return {"status": "reset", "stops": len(s), "cartons": sum(len(x.boxes) for x in s),
            "fleet": DEFAULT_FLEET_AVAILABLE}


def _driver_runs() -> list[dict[str, Any]]:
    try:
        from app.data.demo_extended import DRIVER_RUNS
    except ImportError:  # pragma: no cover
        try:
            from data.demo_extended import DRIVER_RUNS
        except ImportError:
            return []
    return list(DRIVER_RUNS)


def _pick_truck(stops: list[Stop], wanted: str = "") -> list[str]:
    """Candidate truck codes, smallest first, that could carry these stops."""
    vol = sum(s.volume_m3 for s in stops)
    kg = sum(s.weight_kg for s in stops)
    codes = sorted(TRUCK_CATALOGUE, key=lambda c: TRUCK_CATALOGUE[c].volume_m3)
    if wanted and wanted.upper() in TRUCK_CATALOGUE:
        return [wanted.upper()] + [c for c in codes if TRUCK_CATALOGUE[c].volume_m3 > TRUCK_CATALOGUE[wanted.upper()].volume_m3]
    return [c for c in codes if TRUCK_CATALOGUE[c].volume_m3 * 0.8 >= vol and TRUCK_CATALOGUE[c].payload_kg >= kg] or codes[-1:]


def plan_my_route(tool_context: ToolContext, driver: str = "", truck_type: str = "",
                  stop_ids: str = "") -> dict[str, Any]:
    """DRIVER VIEW: one driver's route and how to load HIS truck ("I'm Suresh, here are my cartons,
    how do I load?"). Works from (1) attached carton photos (labels identify the stores), (2) stop
    ids or a pasted/attached order list, (3) the driver's preset run in the demo data, or (4) his
    truck in today's fleet plan.

    Args:
        driver: Driver name (e.g. "Suresh") or truck id.
        truck_type: ACE | PKP | T14 | T17 | T20. Empty = smallest truck that fits.
        stop_ids: Optional demo stop ids, e.g. "S045, S046, S050".
    """
    st = tool_context.state
    sess = session(st)
    name = (driver or "").strip().title() or "Driver"
    p = params_from_state(st)
    hub = HUBS.get(p.hub_id) or HUBS["BHW-DC"]
    by_id = {s.stop_id: s for s in demo_stops()}
    ids: list[str] = []
    source = ""
    images = [(d, m) for d, m, _ in sess.get("attachments", []) if m.startswith("image/")]
    if images:
        try:
            from app.capture.sources import PhotoSource
        except ImportError:  # pragma: no cover
            from capture.sources import PhotoSource
        boxes, _issues = PhotoSource().capture(images)
        known = {b.box_id for b in sess["scanned"]}
        sess["scanned"] += [b for b in boxes if b.box_id not in known]
        for b in boxes:
            if b.stop_id not in ids:
                ids.append(b.stop_id)
        source = (f"📷 Read {len(boxes)} carton labels from {len(images)} photo(s) → {len(ids)} stores; "
                  "each store's full consignment comes from the order book.")
    if not ids and stop_ids:
        ids = [m.upper() for m in re.findall(r"\bS\d{3}\b", stop_ids, re.I)]
        source = f"📝 {len(ids)} stores from your list."
    run = None
    if not ids:
        key = name.lower()
        run = next((r for r in _driver_runs() if key in (str(r.get("driver", "")).lower(), str(r.get("run_id", "")).lower())), None)
        if run:
            ids = list(run.get("stop_ids", []))
            truck_type = truck_type or run.get("truck_code", "")
            source = f"📋 {name}'s run from today's order book ({len(ids)} stores)."
    stops = [by_id[i] for i in ids if i in by_id]
    if not stops and sess["stops"] and not ids:
        stops = list(sess["stops"])
        source = f"📝 {len(stops)} stores from the order list you shared."
    if not stops:  # fall back to the driver's truck in today's fleet plan
        plan = sess.get("plan")
        if plan is None or not any(name.lower() in (r.driver.lower(), r.truck_id.lower()) for r in plan.routes):
            run_plan(st)
            plan = sess["plan"]
        r = next((x for x in plan.routes if name.lower() in (x.driver.lower(), x.truck_id.lower())), None)
        if r is None:
            return {"status": "error", "message": f"No stops for '{driver}'. Attach carton photos, give stop ids, "
                    "or use a demo driver.", "demo_drivers": [x.get("driver") for x in _driver_runs()],
                    "fleet_plan_drivers": [x.driver for x in plan.routes]}
        sess["links"] = start_publishing_driver(sess, plan, r.truck_id)
        queue(st, "driver", focus=r.truck_id, note=f"🗓️ Your part of today's fleet plan {plan.plan_id}.")
        return _driver_summary(plan, r.truck_id)
    missing = [i for i in ids if i not in by_id]
    plan = None
    for code in _pick_truck(stops, truck_type):
        dp = dataclasses.replace(p, truck_counts={code: 1}, corridor_claims={})
        plan = _plan_dispatch(hub, stops, dp)
        if plan.routes and not plan.unassigned:
            break
    if plan is None or not plan.routes:
        return {"status": "error", "message": "Could not build a route for these stops."}
    plan.routes = [dataclasses.replace(r, driver=name) for r in plan.routes]
    tid = plan.routes[0].truck_id
    plan.focus_truck_id = tid
    sess["plan"] = plan
    sess["links"] = start_publishing_driver(sess, plan, tid)
    note = source + (f" ⚠️ {len(plan.unassigned)} stores did not fit." if plan.unassigned else "") + (
        f" Unknown ids: {', '.join(missing)}." if missing else "")
    queue(st, "driver", focus=tid, note=note)
    out = _driver_summary(plan, tid)
    out["source"] = note
    return out


def start_publishing_driver(sess: dict[str, Any], plan: Any, truck_id: str) -> dict[str, str]:
    try:
        from app.integration.media import start_publishing
    except ImportError:  # pragma: no cover
        from integration.media import start_publishing
    return start_publishing(sess, plan, truck_id, only_truck=truck_id)


def _driver_summary(plan: Any, truck_id: str) -> dict[str, Any]:
    r = next(x for x in plan.routes if x.truck_id == truck_id)
    lp = plan.loads[truck_id]
    return {"driver": r.driver, "truck": r.truck_id, "type": r.truck_type.name, "stops": len(r.stops),
            "cartons": len(lp.placed), "km": r.km, "leave": f"{r.start_min // 60:02d}:{r.start_min % 60:02d}",
            "back": f"{r.end_min // 60:02d}:{r.end_min % 60:02d}", "first_drop": r.stops[0].stop.name if r.stops else "",
            "load_first": f"stop {len(r.stops)} at the cab wall", "volume_fill_pct": lp.volume_fill_pct,
            "lifo_ok": lp.lifo_ok,
            "ui": "Driver route table, loading steps and the tap-a-store map/3D view are attached automatically."}


def driver_briefings(tool_context: ToolContext, driver: str = "") -> dict[str, Any]:
    """FLEET MANAGER VIEW: ready-to-send instructions and shareable links for drivers in today's plan
    (report/leave/back times, route, first drop, cab-to-door load order, Google Maps navigation,
    WhatsApp dispatch link, and mobile driver portal link).

    Args:
        driver: Optional driver name (e.g. "Ravi") or truck id ("T17-1") to send instructions
            ONLY to that driver. When omitted, sends instructions to all drivers in the fleet.
    """
    st = tool_context.state
    sess = session(st)
    plan = sess.get("plan")
    if plan is None or len(plan.routes) < 2:
        run_plan(st)
        plan = sess["plan"]

    who = (driver or "").strip().lower()
    if who in ("he", "him", "his", "this", "that", "it") and st.get("lp_last_driver"):
        who = st["lp_last_driver"].lower()

    if who:
        r = next((x for x in plan.routes if who in (x.driver.lower(), x.truck_id.lower())), None)
        if r is not None:
            st["lp_last_driver"] = r.driver
            st["lp_last_truck"] = r.truck_id
            try:
                from app.integration.media import start_publishing
            except ImportError:  # pragma: no cover
                from integration.media import start_publishing
            sess["links"] = start_publishing(sess, plan, r.truck_id, only_truck=r.truck_id)
            if "brief_links" not in sess:
                sess["brief_links"] = {}
            if sess["links"].get("html"):
                sess["brief_links"][r.truck_id] = sess["links"]["html"]
            queue(st, "briefings", focus=r.truck_id, driver=r.driver)
            lp = plan.loads.get(r.truck_id)
            return {
                "plan_id": plan.plan_id,
                "driver": r.driver,
                "truck": r.truck_id,
                "stops": len(r.stops),
                "cartons": len(lp.placed) if lp else 0,
                "leave": f"{r.start_min // 60:02d}:{r.start_min % 60:02d}",
                "back": f"{r.end_min // 60:02d}:{r.end_min % 60:02d}",
                "first_drop": r.stops[0].stop.name if r.stops else "-",
                "ui": f"Instructions and personal links for {r.driver} ({r.truck_id}) are attached automatically."}
        return {"status": "error", "message": f"No driver or truck matching '{driver}' in today's plan ({', '.join(x.driver for x in plan.routes)})."}

    try:
        from app.integration.media import start_briefings
    except ImportError:  # pragma: no cover
        from integration.media import start_briefings
    sess["brief_links"] = start_briefings(sess, plan)
    queue(st, "briefings", focus=plan.routes[0].truck_id if plan.routes else None, driver=None)
    return {"plan_id": plan.plan_id, "drivers": [
        {"driver": r.driver, "truck": r.truck_id, "stops": len(r.stops),
         "leave": f"{r.start_min // 60:02d}:{r.start_min % 60:02d}"} for r in plan.routes],
        "ui": "One instruction block and personal link per driver is attached automatically."}


ALL_TOOLS = [show_planning_wizard, plan_dispatch, claim_corridor, get_truck_load_plan,
             plan_my_route, driver_briefings,
             ingest_delivery_orders, scan_box_manifest, list_fleet_and_costs, reset_to_demo_data]

_ = threading  # media publishing threads are tracked in the session entry
