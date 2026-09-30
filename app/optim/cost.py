"""Cost model — every rate comes from data (truck catalogue + cost sheet), overridable per plan."""

from __future__ import annotations

try:
    from app.contracts import CostBreakdown, CostProfile, Stop, TruckType
except ImportError:  # pragma: no cover
    from contracts import CostBreakdown, CostProfile, Stop, TruckType

LOADING_MIN: int = 60  # dock loading before departure (counted inside the shift)


def service_minutes(stop: Stop, profile: CostProfile, lifo_loaded: bool) -> float:
    base = profile.service_min_base + profile.service_min_per_box * len(stop.boxes)
    return base if lifo_loaded else base + profile.unsorted_search_min_per_stop


def variable_cost_per_km(truck: TruckType, profile: CostProfile) -> float:
    return truck.cost_per_km_inr + profile.fuel_price_per_litre / truck.km_per_litre


def route_cost(truck: TruckType, km: float, route_minutes: float, corridors: set[str],
               profile: CostProfile) -> CostBreakdown:
    litres = km / truck.km_per_litre
    shift_min = profile.shift_hours * 60
    overtime_h = max(0.0, (route_minutes + LOADING_MIN) - shift_min) / 60
    return CostBreakdown(
        fixed=truck.fixed_daily_cost_inr,
        distance=round(km * truck.cost_per_km_inr, 2),
        fuel=round(litres * profile.fuel_price_per_litre, 2),
        tolls=float(sum(profile.toll_by_corridor.get(c, 0.0) for c in corridors)),
        crew=profile.driver_day_cost + profile.helper_day_cost,
        overtime=round(overtime_h * profile.overtime_per_hour * 2, 2),  # driver + helper
        litres=round(litres, 2),
        co2_kg=round(litres * profile.co2_kg_per_litre, 2),
    )
