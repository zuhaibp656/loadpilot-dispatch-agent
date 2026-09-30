"""OR-Tools heterogeneous-fleet CVRPTW minimising total INR cost.

Objective = Σ fixed vehicle cost (truck day-rate + crew) + Σ arc cost (₹/km incl. fuel)
          + corridor-jump penalties (keeps trucks in one direction, no overlap)
          + overtime soft cost (+ global span for "fastest finish" / "balanced").
Constraints: volume (effective fill factor) + weight capacities, delivery time windows,
shift length, pinned stops for driver-claimed corridors. Stops can be dropped only at a
very high penalty (reported as unassigned instead of failing the whole plan).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

try:
    from app.contracts import CostProfile, Hub, Objective, Stop, TruckType
    from app.optim.corridors import CORRIDOR_CODES, corridor_of
    from app.optim.cost import LOADING_MIN, service_minutes, variable_cost_per_km
except ImportError:  # pragma: no cover
    from contracts import CostProfile, Hub, Objective, Stop, TruckType
    from optim.corridors import CORRIDOR_CODES, corridor_of
    from optim.cost import LOADING_MIN, service_minutes, variable_cost_per_km

logger = logging.getLogger(__name__)


@dataclass
class Vehicle:
    truck_id: str
    truck: TruckType
    fill_factor: float = 0.80
    pinned_stop_ids: tuple[str, ...] = ()


@dataclass
class VrpResult:
    routes: dict[str, list[int]]  # truck_id -> ordered stop indices (0-based into stops)
    arrivals: dict[str, list[int]]  # truck_id -> arrival minute per stop
    end_min: dict[str, int]
    dropped: list[int]
    objective: int


def _corridor_penalty(a: str, b: str) -> int:
    if a == b:
        return 0
    d = abs(CORRIDOR_CODES.index(a) - CORRIDOR_CODES.index(b))
    d = min(d, 8 - d)
    return 40 if d == 1 else 220 * d  # rupees


def solve_vrp(hub: Hub, stops: list[Stop], vehicles: list[Vehicle], km: list[list[float]],
              profile: CostProfile, objective: Objective, depart_min: int,
              time_limit_s: int = 4) -> VrpResult:
    n = len(stops) + 1
    V = len(vehicles)
    manager = pywrapcp.RoutingIndexManager(n, V, 0)
    routing = pywrapcp.RoutingModel(manager)
    corr = ["HUB"] + [corridor_of(hub, s) for s in stops]

    # --- arc cost per vehicle type (centi-rupees) -------------------------------------------
    cost_cbs: dict[str, int] = {}
    for v, veh in enumerate(vehicles):
        code = veh.truck.code
        if code not in cost_cbs:
            per_km = variable_cost_per_km(veh.truck, profile)

            def _cb(i, j, per_km=per_km):
                a, b = manager.IndexToNode(i), manager.IndexToNode(j)
                c = km[a][b] * per_km
                if a and b:
                    c += _corridor_penalty(corr[a], corr[b])
                return int(c * 100)

            cost_cbs[code] = routing.RegisterTransitCallback(_cb)
        routing.SetArcCostEvaluatorOfVehicle(cost_cbs[code], v)
        fixed = veh.truck.fixed_daily_cost_inr + profile.driver_day_cost + profile.helper_day_cost
        if objective == Objective.FEWEST_TRUCKS:
            fixed *= 6
        routing.SetFixedCostOfVehicle(int(fixed * 100), v)

    # --- capacities -------------------------------------------------------------------------
    vol = [0] + [int(s.volume_m3 * 1000) for s in stops]
    wt = [0] + [int(s.weight_kg) for s in stops]
    vol_cb = routing.RegisterUnaryTransitCallback(lambda i: vol[manager.IndexToNode(i)])
    wt_cb = routing.RegisterUnaryTransitCallback(lambda i: wt[manager.IndexToNode(i)])
    routing.AddDimensionWithVehicleCapacity(
        vol_cb, 0, [int(v.truck.volume_m3 * 1000 * v.fill_factor) for v in vehicles], True, "Volume")
    routing.AddDimensionWithVehicleCapacity(
        wt_cb, 0, [int(v.truck.payload_kg * 0.97) for v in vehicles], True, "Weight")

    # --- time (per speed class) -------------------------------------------------------------
    svc = [0] + [int(round(service_minutes(s, profile, lifo_loaded=True))) for s in stops]
    time_cbs: dict[float, int] = {}
    transit = []
    for veh in vehicles:
        sp = veh.truck.avg_speed_kmph
        if sp not in time_cbs:
            def _tcb(i, j, sp=sp):
                a, b = manager.IndexToNode(i), manager.IndexToNode(j)
                return int(round(km[a][b] / sp * 60)) + svc[a]
            time_cbs[sp] = routing.RegisterTransitCallback(_tcb)
        transit.append(time_cbs[sp])
    shift_end = depart_min - LOADING_MIN + int(profile.shift_hours * 60)
    hard_end = shift_end + 150
    routing.AddDimensionWithVehicleTransits(transit, 90, hard_end, False, "Time")
    tdim = routing.GetDimensionOrDie("Time")
    for idx, s in enumerate(stops, start=1):
        tdim.CumulVar(manager.NodeToIndex(idx)).SetRange(s.window_start_min, s.window_end_min)
    ot_cost = int(profile.overtime_per_hour * 2 / 60 * 100)  # centi-rupees per minute
    for v in range(V):
        tdim.CumulVar(routing.Start(v)).SetRange(depart_min, depart_min)
        tdim.SetCumulVarSoftUpperBound(routing.End(v), shift_end, ot_cost)
    if objective == Objective.FASTEST_FINISH:
        tdim.SetGlobalSpanCostCoefficient(400)
    elif objective == Objective.BALANCED:
        tdim.SetGlobalSpanCostCoefficient(80)

    # --- pinned stops (driver claims) & drop penalties --------------------------------------
    sid_to_node = {s.stop_id: i for i, s in enumerate(stops, start=1)}
    pinned_to: dict[int, int] = {}
    for v, veh in enumerate(vehicles):
        for sid in veh.pinned_stop_ids:
            if sid in sid_to_node:
                pinned_to[sid_to_node[sid]] = v
    for node in range(1, n):
        index = manager.NodeToIndex(node)
        if node in pinned_to:
            routing.VehicleVar(index).SetValues([-1, int(pinned_to[node])])
        routing.AddDisjunction([index], 50_000_000)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = time_limit_s
    sol = routing.SolveWithParameters(params)
    if sol is None:
        raise RuntimeError("VRP found no solution (check fleet size / time windows)")

    routes: dict[str, list[int]] = {}
    arrivals: dict[str, list[int]] = {}
    end_min: dict[str, int] = {}
    visited: set[int] = set()
    for v, veh in enumerate(vehicles):
        idx = routing.Start(v)
        seq: list[int] = []
        arr: list[int] = []
        idx = sol.Value(routing.NextVar(idx))
        while not routing.IsEnd(idx):
            node = manager.IndexToNode(idx)
            seq.append(node - 1)
            arr.append(sol.Value(tdim.CumulVar(idx)))
            visited.add(node)
            idx = sol.Value(routing.NextVar(idx))
        if seq:
            routes[veh.truck_id] = seq
            arrivals[veh.truck_id] = arr
            end_min[veh.truck_id] = sol.Value(tdim.CumulVar(idx))
    dropped = [node - 1 for node in range(1, n) if node not in visited]
    return VrpResult(routes, arrivals, end_min, dropped, sol.ObjectiveValue())
