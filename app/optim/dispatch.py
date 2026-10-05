"""Dispatch orchestrator: corridors -> claims -> VRP -> LIFO packing (feedback loop) -> costs.

Returns a complete DispatchPlan (routes, per-truck load plans, baseline vs optimised).
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import replace

try:
    from app.contracts import (
        CostProfile, DispatchPlan, FleetSummary, Hub, Objective, PlanningParams, RouteStop, Stop,
        TruckRoute, TruckType,
    )
    from app.data.master_data import (
        DEFAULT_COST_PROFILE, DEFAULT_DRIVERS, DEFAULT_FLEET_AVAILABLE, TRUCK_CATALOGUE,
    )
    from app.optim.corridors import (
        build_corridors, claim_stops, corridor_of, dominant_corridor, label_trunk_and_branches,
        normalize_corridor, overlap_km,
    )
    from app.optim.cost import LOADING_MIN, route_cost, service_minutes
    from app.optim.distance import road_km_matrix
    from app.optim.lifo_packer import pack_truck_lifo
    from app.optim.vrp import Vehicle, solve_vrp
except ImportError:  # pragma: no cover
    from contracts import (
        CostProfile, DispatchPlan, FleetSummary, Hub, Objective, PlanningParams, RouteStop, Stop,
        TruckRoute, TruckType,
    )
    from data.master_data import (
        DEFAULT_COST_PROFILE, DEFAULT_DRIVERS, DEFAULT_FLEET_AVAILABLE, TRUCK_CATALOGUE,
    )
    from optim.corridors import (
        build_corridors, claim_stops, corridor_of, dominant_corridor, label_trunk_and_branches,
        normalize_corridor, overlap_km,
    )
    from optim.cost import LOADING_MIN, route_cost, service_minutes
    from optim.distance import road_km_matrix
    from optim.lifo_packer import pack_truck_lifo
    from optim.vrp import Vehicle, solve_vrp

logger = logging.getLogger(__name__)


def effective_profile(params: PlanningParams, base: CostProfile = DEFAULT_COST_PROFILE) -> CostProfile:
    kw = {}
    if params.fuel_price_per_litre:
        kw["fuel_price_per_litre"] = float(params.fuel_price_per_litre)
    if params.driver_day_cost:
        kw["driver_day_cost"] = float(params.driver_day_cost)
    return replace(base, **kw) if kw else base


def _build_vehicles(hub: Hub, stops: list[Stop], params: PlanningParams,
                    catalogue: dict[str, TruckType]) -> tuple[list[Vehicle], dict[str, str], list[str]]:
    counts = params.truck_counts or DEFAULT_FLEET_AVAILABLE
    vehicles: list[Vehicle] = []
    for code in sorted(counts, key=lambda c: -catalogue[c].volume_m3 if c in catalogue else 0):
        if code not in catalogue:
            continue
        for k in range(int(counts[code])):
            vehicles.append(Vehicle(f"{code}-{k + 1}", catalogue[code]))

    drivers: dict[str, str] = {}
    notes: list[str] = []
    taken: set[str] = set()
    for label, corr_text in (params.corridor_claims or {}).items():
        corr = normalize_corridor(corr_text)
        if corr is None:
            notes.append(f"Could not understand corridor '{corr_text}' for {label}; ignored.")
            continue
        corr_stops = [s for s in stops if corridor_of(hub, s) == corr]
        demand = sum(s.volume_m3 for s in corr_stops)
        # a truck id claim (e.g. "T17-2") or a driver name claim
        veh = next((v for v in vehicles if v.truck_id.lower() == label.lower()), None)
        if veh is None:
            free = [v for v in vehicles if v.truck_id not in taken]
            fitting = [v for v in free if v.truck.volume_m3 * v.fill_factor >= demand]
            veh = min(fitting, key=lambda v: v.truck.volume_m3) if fitting else (
                max(free, key=lambda v: v.truck.volume_m3) if free else None)
            if veh is None:
                notes.append(f"No free truck for {label}'s claim on {corr}.")
                continue
            drivers[veh.truck_id] = label.strip().title()
        taken.add(veh.truck_id)
        veh.pinned_stop_ids = tuple(claim_stops(
            hub, stops, corr, veh.truck.volume_m3 * veh.fill_factor, veh.truck.payload_kg * 0.97,
            max_stops=12))
        notes.append(f"{drivers.get(veh.truck_id, veh.truck_id)} claimed {corr}: "
                     f"{len(veh.pinned_stop_ids)} of {len(corr_stops)} corridor stops pinned to {veh.truck_id}.")
    return vehicles, drivers, notes


def _nearest_neighbour(hub: Hub, members: list[Stop]) -> list[Stop]:
    from app.optim.distance import haversine_km  # local import keeps module graph simple

    left = list(members)
    cur = (hub.lat, hub.lon)
    order: list[Stop] = []
    while left:
        nxt = min(left, key=lambda s: haversine_km(cur[0], cur[1], s.lat, s.lon))
        order.append(nxt)
        left.remove(nxt)
        cur = (nxt.lat, nxt.lon)
    return order


def _simulate(hub: Hub, truck: TruckType, ordered: list[Stop], depart_min: int,
              profile: CostProfile, lifo: bool, arrivals: list[int] | None = None):
    pts = [(hub.lat, hub.lon)] + [(s.lat, s.lon) for s in ordered] + [(hub.lat, hub.lon)]
    km = road_km_matrix(pts)
    t = depart_min
    rs: list[RouteStop] = []
    total_km = 0.0
    for i, s in enumerate(ordered):
        leg = km[i][i + 1]
        total_km += leg
        t = t + leg / truck.avg_speed_kmph * 60
        if arrivals is not None:
            t = max(t, arrivals[i])
        t = max(t, s.window_start_min)
        dep = t + service_minutes(s, profile, lifo)
        rs.append(RouteStop(stop=s, seq=i + 1, arrive_min=int(round(t)), depart_min=int(round(dep)),
                            km_from_prev=round(leg, 2)))
        t = dep
    last = km[len(ordered)][len(ordered) + 1]
    total_km += last
    end = t + last / truck.avg_speed_kmph * 60
    return rs, round(total_km, 1), int(round(end)), tuple(pts)


def _summary(label: str, routes: list[TruckRoute], profile: CostProfile, lifo: bool) -> FleetSummary:
    by_type: dict[str, int] = {}
    for r in routes:
        by_type[r.truck_type.code] = by_type.get(r.truck_type.code, 0) + 1
    search_h = 0.0 if lifo else sum(len(r.stops) for r in routes) * profile.unsorted_search_min_per_stop / 60
    return FleetSummary(
        label=label, trucks=len(routes), km=round(sum(r.km for r in routes), 1),
        hours=round(sum((r.end_min - r.start_min + LOADING_MIN) for r in routes) / 60, 1),
        litres=round(sum(r.cost.litres for r in routes), 1),
        co2_kg=round(sum(r.cost.co2_kg for r in routes), 1),
        cost_total=round(sum(r.cost.total for r in routes), 0),
        unload_search_hours=round(search_h, 1), by_type=by_type,
    )


def build_baseline(hub: Hub, stops: list[Stop], profile: CostProfile, depart_min: int,
                   catalogue: dict[str, TruckType] = TRUCK_CATALOGUE) -> list[TruckRoute]:
    """Today's plan: area-based assignment, nearest-neighbour order, unsorted loading."""
    try:
        from app.data.cities import resolve_city_and_hub
        city_cfg, _ = resolve_city_and_hub(query_hub=hub.hub_id, stops=stops)
        baseline_fn = city_cfg.baseline_fn
    except Exception:  # pragma: no cover
        try:
            from app.data.demo_mmr import baseline_assignment as baseline_fn
        except ImportError:
            from data.demo_mmr import baseline_assignment as baseline_fn
    if all(s.area for s in stops):
        groups = baseline_fn(stops)
    else:
        groups = {}
        for s in stops:
            groups.setdefault(f"{corridor_of(hub, s)}|T17", []).append(s)
    routes: list[TruckRoute] = []
    for i, (key, members) in enumerate(sorted(groups.items())):
        area, code = key.split("|")
        truck = catalogue.get(code, catalogue["T17"])
        ordered = _nearest_neighbour(hub, members)
        rs, km, end, pts = _simulate(hub, truck, ordered, depart_min, profile, lifo=False)
        corrs = {corridor_of(hub, s) for s in members}
        routes.append(TruckRoute(
            truck_id=f"BASE-{i + 1}", truck_type=truck, driver=area, corridor=dominant_corridor(hub, members),
            branch="area", stops=tuple(rs), path=pts, km=km, start_min=depart_min, end_min=end,
            cost=route_cost(truck, km, end - depart_min, corrs, profile),
        ))
    return routes


def plan_dispatch(hub: Hub, stops: list[Stop], params: PlanningParams,
                  catalogue: dict[str, TruckType] = TRUCK_CATALOGUE,
                  time_limit_s: int = 4) -> DispatchPlan:
    t0 = time.time()
    profile = effective_profile(params)
    depart = params.shift_start_min + LOADING_MIN
    vehicles, drivers, notes = _build_vehicles(hub, stops, params, catalogue)
    if not vehicles:
        raise ValueError("No trucks selected — choose at least one truck type and count.")

    pts = [(hub.lat, hub.lon)] + [(s.lat, s.lon) for s in stops]
    km = road_km_matrix(pts)

    loads = {}
    result = None
    for attempt in range(3):
        result = solve_vrp(hub, stops, vehicles, km, profile, params.objective, depart,
                           time_limit_s=time_limit_s if attempt == 0 else max(2, time_limit_s // 2))
        loads = {}
        overflow = False
        for veh in vehicles:
            if veh.truck_id not in result.routes:
                continue
            ordered = [stops[i] for i in result.routes[veh.truck_id]]
            lp = pack_truck_lifo(veh.truck_id, veh.truck, ordered)
            loads[veh.truck_id] = lp
            if lp.unplaced:
                overflow = True
                veh.fill_factor = round(veh.fill_factor - 0.07, 2)
                notes.append(f"{veh.truck_id}: {len(lp.unplaced)} cartons did not fit physically; "
                             f"re-planned with fill factor {veh.fill_factor:.2f}.")
        if not overflow:
            break

    assert result is not None
    try:
        from app.data.cities import resolve_city_and_hub
        city_cfg, _ = resolve_city_and_hub(query_hub=hub.hub_id, stops=stops)
        pool_drivers = city_cfg.default_drivers
    except Exception:
        pool_drivers = DEFAULT_DRIVERS
    free_drivers = [d for d in pool_drivers if d not in drivers.values()]
    routes: list[TruckRoute] = []
    for veh in vehicles:
        if veh.truck_id not in result.routes:
            continue
        ordered = [stops[i] for i in result.routes[veh.truck_id]]
        rs, rkm, end, path = _simulate(hub, veh.truck, ordered, depart, profile, lifo=True,
                                       arrivals=result.arrivals[veh.truck_id])
        driver = drivers.get(veh.truck_id) or (free_drivers.pop(0) if free_drivers else veh.truck_id)
        routes.append(TruckRoute(
            truck_id=veh.truck_id, truck_type=veh.truck, driver=driver,
            corridor=dominant_corridor(hub, ordered), branch="solo", stops=tuple(rs), path=path,
            km=rkm, start_min=depart, end_min=end,
            cost=route_cost(veh.truck, rkm, end - depart, {corridor_of(hub, s) for s in ordered}, profile),
            claimed=veh.truck_id in drivers or bool(veh.pinned_stop_ids),
        ))
    labels = label_trunk_and_branches(hub, routes)
    routes = [replace(r, branch=labels.get(r.truck_id, "solo")) for r in routes]
    routes.sort(key=lambda r: (["N", "NE", "E", "SE", "S", "SW", "W", "NW", "-"].index(r.corridor), r.branch))

    baseline_routes = build_baseline(hub, stops, profile, depart, catalogue)
    plan = DispatchPlan(
        plan_id=f"LP-{uuid.uuid4().hex[:6].upper()}", dispatch_date=params.dispatch_date, hub=hub,
        params=params, routes=routes, loads=loads, corridors=build_corridors(hub, stops),
        baseline=_summary("Today (manual, area-based)", baseline_routes, profile, lifo=False),
        optimized=_summary("FleetFlow (optimised)", routes, profile, lifo=True),
        overlap_km=overlap_km(hub, routes), unassigned=[stops[i] for i in result.dropped],
        notes=notes, solve_ms=int((time.time() - t0) * 1000),
    )
    plan.baseline_routes = baseline_routes
    return plan
