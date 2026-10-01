"""Domain contracts for LoadPilot — pure dataclasses, no side effects.

Coordinate frame for truck loading:
    x = 0 at the CAB WALL  ->  x = L at the REAR DOOR
    y = 0 left wall        ->  y = W right wall
    z = 0 floor            ->  z = H roof
Units: centimetres, kilograms, minutes (from midnight), kilometres, INR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ==============================================================================
# A2UI (render layer)
# ==============================================================================
class A2uiCatalogVersion(str, Enum):
    """Supported A2UI catalog schema versions."""

    V0_8 = "v0.8"
    V0_9 = "v0.9"


ACTIVE_A2UI_CATALOG_VERSION: A2uiCatalogVersion = A2uiCatalogVersion.V0_9


@dataclass(frozen=True)
class A2uiMessage:
    """In-memory representation of an individual A2UI lifecycle event."""

    message_type: str  # createSurface | updateComponents | updateDataModel | deleteSurface
    surface_id: str
    payload: dict[str, Any]
    catalog_version: A2uiCatalogVersion = ACTIVE_A2UI_CATALOG_VERSION


# ==============================================================================
# Fleet & cost master data
# ==============================================================================
@dataclass(frozen=True)
class TruckType:
    """A standard truck body with fixed internal cargo dimensions and cost profile."""

    code: str
    name: str
    inner_l_cm: float
    inner_w_cm: float
    inner_h_cm: float
    payload_kg: float
    fixed_daily_cost_inr: float  # EMI / lease / insurance per operating day
    cost_per_km_inr: float  # maintenance + tyres per km (fuel computed separately)
    km_per_litre: float
    avg_speed_kmph: float
    color: str = "#1a73e8"

    @property
    def volume_m3(self) -> float:
        return self.inner_l_cm * self.inner_w_cm * self.inner_h_cm / 1e6


@dataclass(frozen=True)
class CostProfile:
    """Operating cost parameters — always sourced from data (cost sheet) and overridable."""

    currency: str = "INR"
    fuel_price_per_litre: float = 92.0
    driver_day_cost: float = 1100.0
    helper_day_cost: float = 700.0
    overtime_per_hour: float = 180.0
    shift_hours: float = 9.0
    co2_kg_per_litre: float = 2.68
    toll_by_corridor: dict[str, float] = field(default_factory=dict)
    service_min_base: float = 8.0  # parking + paperwork per stop
    service_min_per_box: float = 0.35
    unsorted_search_min_per_stop: float = 9.0  # baseline: digging for boxes when not LIFO-loaded


@dataclass(frozen=True)
class Hub:
    hub_id: str
    name: str
    lat: float
    lon: float
    address: str = ""


# ==============================================================================
# Orders & boxes
# ==============================================================================
@dataclass(frozen=True)
class Box:
    box_id: str
    stop_id: str
    sku: str
    description: str
    l_cm: float
    w_cm: float
    h_cm: float
    weight_kg: float
    fragile: bool = False
    this_side_up: bool = False
    category: str = "general"
    source: str = "manifest"  # manifest | photo | qr | live

    @property
    def volume_m3(self) -> float:
        return self.l_cm * self.w_cm * self.h_cm / 1e6


@dataclass(frozen=True)
class Stop:
    stop_id: str
    name: str
    address: str
    lat: float
    lon: float
    window_start_min: int = 8 * 60
    window_end_min: int = 19 * 60
    boxes: tuple[Box, ...] = ()
    area: str = ""

    @property
    def volume_m3(self) -> float:
        return sum(b.volume_m3 for b in self.boxes)

    @property
    def weight_kg(self) -> float:
        return sum(b.weight_kg for b in self.boxes)


# ==============================================================================
# Planning inputs
# ==============================================================================
class Objective(str, Enum):
    LOWEST_COST = "lowest_cost"
    FEWEST_TRUCKS = "fewest_trucks"
    FASTEST_FINISH = "fastest_finish"
    BALANCED = "balanced"


@dataclass
class PlanningParams:
    """Everything the dispatcher sets before planning (wizard form or chat)."""

    dispatch_date: str = ""
    shift_start_min: int = 6 * 60
    hub_id: str = ""
    truck_counts: dict[str, int] = field(default_factory=dict)  # truck type code -> count
    objective: Objective = Objective.LOWEST_COST
    corridor_claims: dict[str, str] = field(default_factory=dict)  # driver/truck label -> corridor
    fuel_price_per_litre: float | None = None
    driver_day_cost: float | None = None
    order_source: str = "demo"


# ==============================================================================
# Planning outputs
# ==============================================================================
@dataclass(frozen=True)
class Corridor:
    code: str  # N, NE, E, SE, S, SW, W, NW
    name: str
    bearing_from: float
    bearing_to: float
    stop_ids: tuple[str, ...]
    volume_m3: float
    weight_kg: float


@dataclass(frozen=True)
class PlacedBox:
    box: Box
    x: float
    y: float
    z: float
    l: float  # placed extent along x
    w: float  # placed extent along y
    h: float  # placed extent along z
    load_step: int  # 1 = first box loaded (deepest, at cab)
    stop_seq: int  # delivery sequence of the box's stop (1 = first delivery)

    @property
    def x2(self) -> float:
        return self.x + self.l

    @property
    def y2(self) -> float:
        return self.y + self.w

    @property
    def z2(self) -> float:
        return self.z + self.h


@dataclass(frozen=True)
class StopZone:
    stop_id: str
    stop_seq: int
    x_start: float
    x_end: float
    boxes: int


@dataclass(frozen=True)
class TruckLoadPlan:
    truck_id: str
    truck_type: TruckType
    placed: tuple[PlacedBox, ...]
    zones: tuple[StopZone, ...]
    volume_fill_pct: float
    weight_kg: float
    weight_fill_pct: float
    lifo_ok: bool
    front_axle_share_pct: float  # % of cargo weight in the front half of the body
    unplaced: tuple[Box, ...] = ()

    @property
    def cmvr_axle_compliant(self) -> bool:
        """Central Motor Vehicle Rules (CMVR) Rule 93 safe weight envelope (30-52% on steer axle)."""
        return 30.0 <= self.front_axle_share_pct <= 52.0

    @property
    def cmvr_axle_status(self) -> str:
        rear_share = round(100.0 - self.front_axle_share_pct, 1)
        front_share = round(self.front_axle_share_pct, 1)
        if self.cmvr_axle_compliant:
            return f"CMVR Compliant ({front_share}% steer / {rear_share}% drive axle)"
        return f"Warning: Axle Imbalance ({front_share}% steer / {rear_share}% drive axle)"


@dataclass(frozen=True)
class RouteStop:
    stop: Stop
    seq: int
    arrive_min: int
    depart_min: int
    km_from_prev: float


@dataclass(frozen=True)
class CostBreakdown:
    fixed: float
    distance: float
    fuel: float
    tolls: float
    crew: float
    overtime: float
    litres: float
    co2_kg: float

    @property
    def total(self) -> float:
        return self.fixed + self.distance + self.fuel + self.tolls + self.crew + self.overtime


@dataclass(frozen=True)
class TruckRoute:
    truck_id: str
    truck_type: TruckType
    driver: str
    corridor: str
    branch: str  # "trunk", "branch-A", ...
    stops: tuple[RouteStop, ...]
    path: tuple[tuple[float, float], ...]  # (lat, lon) incl. hub at both ends
    km: float
    start_min: int
    end_min: int
    cost: CostBreakdown
    claimed: bool = False


@dataclass(frozen=True)
class FleetSummary:
    label: str
    trucks: int
    km: float
    hours: float
    litres: float
    co2_kg: float
    cost_total: float
    unload_search_hours: float
    by_type: dict[str, int] = field(default_factory=dict)


@dataclass
class DispatchPlan:
    plan_id: str
    dispatch_date: str
    hub: Hub
    params: PlanningParams
    routes: list[TruckRoute]
    loads: dict[str, TruckLoadPlan]
    corridors: list[Corridor]
    baseline: FleetSummary
    optimized: FleetSummary
    overlap_km: float
    unassigned: list[Stop] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    solve_ms: int = 0
    focus_truck_id: str | None = None
    baseline_routes: list[TruckRoute] = field(default_factory=list)

    @property
    def savings_inr(self) -> float:
        return self.baseline.cost_total - self.optimized.cost_total

    @property
    def trucks_saved(self) -> int:
        return self.baseline.trucks - self.optimized.trucks

    @property
    def diesel_saved_litres(self) -> float:
        return max(0.0, round(self.baseline.litres - self.optimized.litres, 1))

    @property
    def co2_saved_kg(self) -> float:
        return max(0.0, round(self.baseline.co2_kg - self.optimized.co2_kg, 1))

    @property
    def annual_trees_offset_equiv(self) -> int:
        return int(round((self.co2_saved_kg * 300) / 21.77))
