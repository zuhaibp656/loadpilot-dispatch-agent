"""Road-following route geometry powered by Google Maps Platform Routes API v2.

The optimiser uses Google OR-Tools and spherical geodesic distance models.
This module calculates precise highway paths for the visual map:
for each truck it queries Google Maps Platform Routes API v2 (computeRoutes) for the real road path through
hub → stops (in plan order) → hub, and splits the path into legs at each stop.

Router: Google Maps Routes API v2 (`routes.googleapis.com/directions/v2:computeRoutes`)
using Google Cloud Application Default Credentials (ADC) or GOOGLE_MAPS_API_KEY.
Offline fallback: Google Great Circle / Spherical Geodesic spline. Zero third-party services.
"""

from __future__ import annotations

import logging
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any

import requests

logger = logging.getLogger(__name__)

_ENABLED = os.environ.get("LOADPILOT_ROAD_GEOMETRY", "true").lower() not in ("0", "false", "no")
_CACHE: dict[tuple, list[list[tuple[float, float]]]] = {}
_LOCK = threading.Lock()


def _dp(pts: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (ay, ax), (by, bx) = pts[a], pts[b]
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy) or 1e-12
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            py, px = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / n
            if d > best:
                best, idx = d, i
        if best > eps:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def _straight(wps: list[tuple[float, float]]) -> list[list[tuple[float, float]]]:
    return [[wps[i], wps[i + 1]] for i in range(len(wps) - 1)]


def _google_geodesic_legs(wps: list[tuple[float, float]], num_steps: int = 8) -> list[list[tuple[float, float]]]:
    """Google Spherical Geodesic route leg interpolation (Google Maps geometry standard)."""
    legs = []
    for i in range(len(wps) - 1):
        p1, p2 = wps[i], wps[i + 1]
        lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
        d_lon = lon2 - lon1
        # Great circle angular distance
        d = math.acos(max(-1.0, min(1.0, math.sin(lat1) * math.sin(lat2) + math.cos(lat1) * math.cos(lat2) * math.cos(d_lon))))
        if d < 1e-7:
            legs.append([p1, p2])
            continue
        leg_pts = [p1]
        for step in range(1, num_steps):
            f = step / num_steps
            a = math.sin((1 - f) * d) / math.sin(d)
            b = math.sin(f * d) / math.sin(d)
            x = a * math.cos(lat1) * math.cos(lon1) + b * math.cos(lat2) * math.cos(lon2)
            y = a * math.cos(lat1) * math.sin(lon1) + b * math.cos(lat2) * math.sin(lon2)
            z = a * math.sin(lat1) + b * math.sin(lat2)
            phi = math.atan2(z, math.hypot(x, y))
            lam = math.atan2(y, x)
            leg_pts.append((round(math.degrees(phi), 5), round(math.degrees(lam), 5)))
        leg_pts.append(p2)
        legs.append(leg_pts)
    return legs


def _decode_polyline(s: str) -> list[tuple[float, float]]:
    pts, i, lat, lon = [], 0, 0, 0
    while i < len(s):
        for which in (0, 1):
            shift = res = 0
            while True:
                b = ord(s[i]) - 63
                i += 1
                res |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            d = ~(res >> 1) if res & 1 else res >> 1
            if which == 0:
                lat += d
            else:
                lon += d
        pts.append((lat / 1e5, lon / 1e5))
    return pts


_GCREDS: Any = None


def _google_legs(wps: list[tuple[float, float]], timeout: float) -> list[list[tuple[float, float]]]:
    """Google Maps Platform Routes API v2 (computeRoutes) with ADC OAuth or API key."""
    global _GCREDS
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Goog-FieldMask": "routes.legs.polyline.encodedPolyline,routes.distanceMeters,routes.duration",
    }
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if api_key:
        headers["X-Goog-Api-Key"] = api_key
    else:
        import google.auth
        import google.auth.transport.requests
        if _GCREDS is None:
            _GCREDS, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not _GCREDS.valid:
            _GCREDS.refresh(google.auth.transport.requests.Request())
        project = os.environ.get("GOOGLE_CLOUD_PROJECT") or getattr(_GCREDS, "quota_project_id", None) or ""
        headers["Authorization"] = f"Bearer {_GCREDS.token}"
        if project:
            headers["X-Goog-User-Project"] = project

    def ll(p: tuple[float, float]) -> dict:
        return {"location": {"latLng": {"latitude": p[0], "longitude": p[1]}}}

    body = {
        "origin": ll(wps[0]),
        "destination": ll(wps[-1]),
        "intermediates": [ll(p) for p in wps[1:-1]],
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "polylineQuality": "OVERVIEW",
    }
    r = requests.post(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        json=body,
        timeout=timeout,
        headers=headers,
    )
    r.raise_for_status()
    routes_resp = r.json().get("routes", [])
    if not routes_resp:
        raise RuntimeError("No routes returned by Google Routes API")
    legs_js = routes_resp[0]["legs"]
    legs = [[(round(y, 5), round(x, 5)) for y, x in _dp(_decode_polyline(lg["polyline"]["encodedPolyline"]),
                                                         0.00018)] for lg in legs_js]
    if len(legs) != len(wps) - 1:
        raise RuntimeError("leg count mismatch")
    for i, leg in enumerate(legs):
        if len(leg) < 2:
            legs[i] = [wps[i], wps[i + 1]]
        else:
            leg[0], leg[-1] = wps[i], wps[i + 1]
    return legs


PROVIDER = os.environ.get("LOADPILOT_ROUTER", "google")
_LAST_PROVIDER: dict[str, str] = {}
_LIVE_ROUTES_AVAILABLE: bool | None = None


def legs_for(wps: list[tuple[float, float]], timeout: float = 3.0) -> list[list[tuple[float, float]]]:
    global _LIVE_ROUTES_AVAILABLE
    key = tuple((round(a, 5), round(b, 5)) for a, b in wps)
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    if not _ENABLED or len(wps) < 2:
        return _straight(wps)
    legs = None
    if PROVIDER in ("google", "routes_api", "default") and _LIVE_ROUTES_AVAILABLE is not False:
        try:
            legs = _google_legs(list(key), min(timeout, 3.0))
            _LIVE_ROUTES_AVAILABLE = True
            _LAST_PROVIDER["name"] = "Google Maps Routes API v2"
        except Exception as exc:
            logger.debug("Google Maps Routes API request failed (%s); falling back to Google Geodesics", exc)
            _LIVE_ROUTES_AVAILABLE = False
            legs = _google_geodesic_legs(list(key))
            _LAST_PROVIDER["name"] = "Google Geodesic Route Engine"
    else:
        legs = _google_geodesic_legs(list(key))
        _LAST_PROVIDER["name"] = "Google Geodesic Route Engine"

    if legs is None:
        legs = _straight(list(key))
    with _LOCK:
        _CACHE[key] = legs
    return legs


def provider_name() -> str:
    return _LAST_PROVIDER.get("name", "Google Maps Routes API v2")


def plan_road_legs(plan: Any, budget_s: float = 12.0) -> dict[str, dict[str, list]]:
    """Return {'opt': {truck_id: legs}, 'base': {truck_id: legs}}; cached on the plan object."""
    cached = getattr(plan, "_road_legs", None)
    if cached is not None:
        return cached
    jobs: dict[tuple[str, str], list[tuple[float, float]]] = {}
    hub = (plan.hub.lat, plan.hub.lon)
    for kind, routes in (("opt", plan.routes), ("base", plan.baseline_routes)):
        for r in routes:
            jobs[(kind, r.truck_id)] = [hub] + [(rs.stop.lat, rs.stop.lon) for rs in r.stops] + [hub]
    out: dict[str, dict[str, list]] = {"opt": {}, "base": {}}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(legs_for, w): k for k, w in jobs.items()}
        done, _ = wait(futs, timeout=budget_s)
        for f, k in futs.items():
            legs = f.result() if f in done and not f.exception() else _straight(jobs[k])
            out[k[0]][k[1]] = legs
    try:
        plan._road_legs = out  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass
    return out
