"""Multi-city registry & dynamic geographic resolver for LoadPilot.

Enables seamless dispatch planning across Mumbai, Bangalore, or any arbitrary city
with dynamic real-time hub and corridor assignment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

try:
    from app.contracts import Hub, Stop
    from app.data.demo_blr import (
        BLR_DEFAULT_DRIVERS, DEFAULT_BLR_HUB_ID, GAZETTEER_BLR, HUBS_BLR,
        baseline_blr_assignment, build_blr_demo_stops,
    )
    from app.data.demo_mmr import (
        DEFAULT_HUB_ID as DEFAULT_MMR_HUB_ID,
        GAZETTEER as GAZETTEER_MMR,
        HUBS as HUBS_MMR,
        baseline_assignment as baseline_mmr_assignment,
        build_demo_stops as build_mmr_demo_stops,
    )
    from app.data.master_data import DEFAULT_DRIVERS as MMR_DEFAULT_DRIVERS
except ImportError:  # pragma: no cover
    from contracts import Hub, Stop
    from data.demo_blr import (
        BLR_DEFAULT_DRIVERS, DEFAULT_BLR_HUB_ID, GAZETTEER_BLR, HUBS_BLR,
        baseline_blr_assignment, build_blr_demo_stops,
    )
    from data.demo_mmr import (
        DEFAULT_HUB_ID as DEFAULT_MMR_HUB_ID,
        GAZETTEER as GAZETTEER_MMR,
        HUBS as HUBS_MMR,
        baseline_assignment as baseline_mmr_assignment,
        build_demo_stops as build_mmr_demo_stops,
    )
    from data.master_data import DEFAULT_DRIVERS as MMR_DEFAULT_DRIVERS

ALL_HUBS: dict[str, Hub] = {**HUBS_MMR, **HUBS_BLR}


@dataclass(frozen=True)
class CityConfig:
    city_id: str
    display_name: str
    default_hub_id: str
    hubs: dict[str, Hub]
    gazetteer: dict[str, tuple[float, float, str]]
    build_stops_fn: Callable[[int], list[Stop]]
    baseline_fn: Callable[[list[Stop]], dict[str, list[Stop]]]
    default_drivers: list[str]


CITIES: dict[str, CityConfig] = {
    "mumbai": CityConfig(
        city_id="mumbai",
        display_name="Mumbai Metropolitan Region",
        default_hub_id=DEFAULT_MMR_HUB_ID,
        hubs=HUBS_MMR,
        gazetteer=GAZETTEER_MMR,
        build_stops_fn=build_mmr_demo_stops,
        baseline_fn=baseline_mmr_assignment,
        default_drivers=MMR_DEFAULT_DRIVERS,
    ),
    "bangalore": CityConfig(
        city_id="bangalore",
        display_name="Bengaluru Urban & Rural",
        default_hub_id=DEFAULT_BLR_HUB_ID,
        hubs=HUBS_BLR,
        gazetteer=GAZETTEER_BLR,
        build_stops_fn=build_blr_demo_stops,
        baseline_fn=baseline_blr_assignment,
        default_drivers=BLR_DEFAULT_DRIVERS,
    ),
}

# Aliases
_ALIASES = {
    "mum": "mumbai", "bombay": "mumbai", "bhiwandi": "mumbai", "taloja": "mumbai",
    "bhw": "mumbai", "tlj": "mumbai", "bhw-dc": "mumbai", "tlj-dc": "mumbai",
    "blr": "bangalore", "bengaluru": "bangalore", "nelamangala": "bangalore",
    "ecity": "bangalore", "blr-nlg": "bangalore", "blr-ec": "bangalore",
}


def resolve_city_and_hub(
    query_city: str = "",
    query_hub: str = "",
    stops: list[Stop] | None = None,
) -> tuple[CityConfig, Hub]:
    """Resolve city configuration and active hub dynamically.

    1. Checks explicit query_city or query_hub.
    2. If stops are provided without city hint, auto-detects from stop coordinates.
    3. Defaults cleanly to Mumbai if unspecified.
    """
    token = (query_city or query_hub or "").strip().lower()
    city_key = _ALIASES.get(token, token)

    if city_key in CITIES:
        cfg = CITIES[city_key]
        hub_key = query_hub.upper() if query_hub.upper() in cfg.hubs else cfg.default_hub_id
        return cfg, cfg.hubs[hub_key]

    # Check if query_hub directly matches any known hub
    if query_hub and query_hub.upper() in ALL_HUBS:
        hub = ALL_HUBS[query_hub.upper()]
        for cfg in CITIES.values():
            if hub.hub_id in cfg.hubs:
                return cfg, hub

    # Auto-detect from stop coordinates if provided
    if stops:
        avg_lat = sum(s.lat for s in stops) / len(stops)
        avg_lon = sum(s.lon for s in stops) / len(stops)
        # Bangalore is ~12.8 to 13.3 N, 77.4 to 77.8 E
        if 12.0 <= avg_lat <= 14.0 and 76.5 <= avg_lon <= 78.5:
            cfg = CITIES["bangalore"]
            # Choose closer hub between Nelamangala and Electronic City
            hub = min(cfg.hubs.values(), key=lambda h: (h.lat - avg_lat) ** 2 + (h.lon - avg_lon) ** 2)
            return cfg, hub
        # Mumbai is ~18.5 to 20.0 N, 72.5 to 73.5 E
        if 18.0 <= avg_lat <= 20.5 and 72.0 <= avg_lon <= 74.0:
            cfg = CITIES["mumbai"]
            hub = min(cfg.hubs.values(), key=lambda h: (h.lat - avg_lat) ** 2 + (h.lon - avg_lon) ** 2)
            return cfg, hub
        # For arbitrary new city, create a dynamic hub at the stop centroid
        dynamic_hub = Hub(
            hub_id="DYN-DC",
            name="Regional Distribution Hub",
            lat=round(avg_lat, 4),
            lon=round(avg_lon, 4),
            address=f"Dynamic Dispatch Terminal ({avg_lat:.2f}N, {avg_lon:.2f}E)",
        )
        dynamic_cfg = CityConfig(
            city_id="custom",
            display_name=f"Custom Logistics Area ({avg_lat:.2f}N, {avg_lon:.2f}E)",
            default_hub_id="DYN-DC",
            hubs={"DYN-DC": dynamic_hub},
            gazetteer={},
            build_stops_fn=lambda seed=42: list(stops),
            baseline_fn=lambda s_list: {f"{s.area or 'Zone-1'}|T17": s_list},
            default_drivers=MMR_DEFAULT_DRIVERS,
        )
        return dynamic_cfg, dynamic_hub

    # Default to Mumbai
    cfg = CITIES["mumbai"]
    return cfg, cfg.hubs[cfg.default_hub_id]
