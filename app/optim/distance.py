"""Distance / travel-time providers.

Default: haversine x road-factor (offline, deterministic, zero cost).
Optional: Google Maps Routes API `computeRouteMatrix` when LOADPILOT_DISTANCE_PROVIDER=routes_api
and GOOGLE_MAPS_API_KEY is set (falls back to haversine on any error).
"""

from __future__ import annotations

import json
import logging
import math
import os
import urllib.request

logger = logging.getLogger(__name__)

ROAD_FACTOR: float = 1.35  # urban circuity factor (straight-line -> road km)
EARTH_R_KM: float = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial compass bearing from point 1 to point 2 (0 = North, clockwise)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def road_km_matrix(points: list[tuple[float, float]]) -> list[list[float]]:
    """Symmetric road-distance matrix in km for [(lat, lon), ...]."""
    provider = os.environ.get("LOADPILOT_DISTANCE_PROVIDER", "haversine").lower()
    if provider == "routes_api" and os.environ.get("GOOGLE_MAPS_API_KEY") and len(points) <= 25:
        try:
            return _routes_api_matrix(points)
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Routes API matrix failed, using haversine: %s", exc)
    n = len(points)
    m = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            d = haversine_km(*points[i], *points[j]) * ROAD_FACTOR
            m[i][j] = m[j][i] = d
    return m


def _routes_api_matrix(points: list[tuple[float, float]]) -> list[list[float]]:  # pragma: no cover
    """Google Maps Routes API computeRouteMatrix (<= 25x25 elements per call)."""
    wp = [{"waypoint": {"location": {"latLng": {"latitude": a, "longitude": b}}}} for a, b in points]
    body = json.dumps({"origins": wp, "destinations": wp, "travelMode": "DRIVE",
                       "routingPreference": "TRAFFIC_UNAWARE"}).encode()
    req = urllib.request.Request(
        "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix", data=body,
        headers={"Content-Type": "application/json",
                 "X-Goog-Api-Key": os.environ["GOOGLE_MAPS_API_KEY"],
                 "X-Goog-FieldMask": "originIndex,destinationIndex,distanceMeters"},
        method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        rows = json.loads(resp.read().decode())
    n = len(points)
    m = [[0.0] * n for _ in range(n)]
    for r in rows:
        m[r["originIndex"]][r["destinationIndex"]] = r.get("distanceMeters", 0) / 1000.0
    return m
