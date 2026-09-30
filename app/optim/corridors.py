"""Corridor engine: compass corridors from the hub, trunk-and-branch splitting, driver claims.

1. Every stop gets a bearing from the hub and is binned into one of 8 compass corridors.
2. Routes that share a corridor are labelled trunk / branch: the truck serving the inner
   (nearer) stops runs the *trunk*; trucks continuing further out become *branches* that
   diverge at the branch point (the last trunk stop).
3. Claims ("Ravi has the West route") pin a corridor's stops to that driver, ordered along
   the trunk (nearest first) until his truck is full; the overflow becomes a branch.
4. Overlap = km of route legs that run *inside another truck's corridor hull* (excluding the
   shared trunk), used as the "no overlap" KPI.
"""

from __future__ import annotations

from collections import defaultdict

try:
    from app.contracts import Corridor, Hub, Stop, TruckRoute
    from app.data.master_data import CORRIDOR_NAMES
    from app.optim.distance import ROAD_FACTOR, bearing_deg, haversine_km
except ImportError:  # pragma: no cover
    from contracts import Corridor, Hub, Stop, TruckRoute
    from data.master_data import CORRIDOR_NAMES
    from optim.distance import ROAD_FACTOR, bearing_deg, haversine_km

CORRIDOR_CODES: list[str] = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

_ALIASES: dict[str, str] = {
    "north": "N", "northeast": "NE", "north-east": "NE", "north east": "NE", "east": "E",
    "southeast": "SE", "south-east": "SE", "south east": "SE", "south": "S",
    "southwest": "SW", "south-west": "SW", "south west": "SW", "west": "W",
    "northwest": "NW", "north-west": "NW", "north west": "NW",
}


def normalize_corridor(text: str) -> str | None:
    t = (text or "").strip().lower().replace("route", "").replace("corridor", "").strip()
    if t.upper() in CORRIDOR_CODES:
        return t.upper()
    for k in sorted(_ALIASES, key=len, reverse=True):
        if k in t:
            return _ALIASES[k]
    return None


def corridor_of(hub: Hub, stop: Stop) -> str:
    b = bearing_deg(hub.lat, hub.lon, stop.lat, stop.lon)
    return CORRIDOR_CODES[int(((b + 22.5) % 360) // 45)]


def build_corridors(hub: Hub, stops: list[Stop]) -> list[Corridor]:
    groups: dict[str, list[Stop]] = defaultdict(list)
    for s in stops:
        groups[corridor_of(hub, s)].append(s)
    out: list[Corridor] = []
    for i, code in enumerate(CORRIDOR_CODES):
        members = groups.get(code, [])
        if not members:
            continue
        members.sort(key=lambda s: haversine_km(hub.lat, hub.lon, s.lat, s.lon))
        out.append(Corridor(
            code=code, name=CORRIDOR_NAMES.get(code, code),
            bearing_from=(i * 45 - 22.5) % 360, bearing_to=(i * 45 + 22.5) % 360,
            stop_ids=tuple(s.stop_id for s in members),
            volume_m3=round(sum(s.volume_m3 for s in members), 2),
            weight_kg=round(sum(s.weight_kg for s in members), 1),
        ))
    return out


def claim_stops(hub: Hub, stops: list[Stop], corridor: str, volume_cap_m3: float,
                weight_cap_kg: float, max_stops: int) -> list[str]:
    """Pick the claimed corridor's stops along the trunk (nearest first) until the truck is full."""
    members = [s for s in stops if corridor_of(hub, s) == corridor]
    members.sort(key=lambda s: haversine_km(hub.lat, hub.lon, s.lat, s.lon))
    chosen: list[str] = []
    vol = wt = 0.0
    for s in members:
        if len(chosen) >= max_stops:
            break
        if vol + s.volume_m3 > volume_cap_m3 or wt + s.weight_kg > weight_cap_kg:
            continue
        chosen.append(s.stop_id)
        vol += s.volume_m3
        wt += s.weight_kg
    return chosen


def dominant_corridor(hub: Hub, route_stops: list[Stop]) -> str:
    if not route_stops:
        return "-"
    counts: dict[str, int] = defaultdict(int)
    for s in route_stops:
        counts[corridor_of(hub, s)] += 1
    return max(counts.items(), key=lambda kv: (kv[1], -CORRIDOR_CODES.index(kv[0])))[0]


def label_trunk_and_branches(hub: Hub, routes: list[TruckRoute]) -> dict[str, str]:
    """truck_id -> 'trunk' | 'branch-A' | ... | 'solo' based on shared corridors."""
    by_corr: dict[str, list[TruckRoute]] = defaultdict(list)
    for r in routes:
        by_corr[r.corridor].append(r)
    labels: dict[str, str] = {}
    for _corr, rs in by_corr.items():
        if len(rs) == 1:
            labels[rs[0].truck_id] = "solo"
            continue

        def reach(r: TruckRoute) -> float:
            if not r.stops:
                return 0.0
            return max(haversine_km(hub.lat, hub.lon, rs_.stop.lat, rs_.stop.lon) for rs_ in r.stops)

        ordered = sorted(rs, key=reach)
        labels[ordered[0].truck_id] = "trunk"
        for k, r in enumerate(ordered[1:]):
            labels[r.truck_id] = f"branch-{chr(65 + k)}"
    return labels


def _hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _inside(pt: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    if len(poly) < 3:
        return False
    x, y = pt
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def overlap_km(hub: Hub, routes: list[TruckRoute]) -> float:
    """Road-km of legs whose midpoint lies inside another truck's delivery hull (excl. hub legs)."""
    hulls = {r.truck_id: _hull([(rs.stop.lon, rs.stop.lat) for rs in r.stops]) for r in routes}
    total = 0.0
    for r in routes:
        pts = [(rs.stop.lat, rs.stop.lon) for rs in r.stops]
        for a, b in zip(pts, pts[1:]):
            mid = ((a[1] + b[1]) / 2, (a[0] + b[0]) / 2)
            for other, hull in hulls.items():
                if other != r.truck_id and _inside(mid, hull):
                    total += haversine_km(*a, *b) * ROAD_FACTOR
                    break
    return round(total, 1)
