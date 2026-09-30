"""Road-following route geometry for maps (OSRM-compatible router, straight-line fallback).

The optimiser uses a fast haversine/circuity distance model. This module only draws the map.
For each truck it asks a routing engine for the real road path through
hub → stops (in plan order) → hub, and splits the path into legs at each stop.

Router: env LOADPILOT_OSRM_URL (default public OSRM demo server; swap for a private OSRM or
Google Routes proxy in production). Results are cached in memory and simplified.
If the router can't be reached, each leg falls back to a straight line.
"""

from __future__ import annotations

import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from typing import Any

import requests

OSRM_URL = os.environ.get("LOADPILOT_OSRM_URL", "https://router.project-osrm.org").rstrip("/")
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


def _osrm_legs(wps: list[tuple[float, float]], timeout: float) -> list[list[tuple[float, float]]]:
    coords = ";".join(f"{lon:.5f},{lat:.5f}" for lat, lon in wps)
    r = requests.get(f"{OSRM_URL}/route/v1/driving/{coords}",
                     params={"overview": "full", "geometries": "geojson", "steps": "false"},
                     timeout=timeout)
    r.raise_for_status()
    js = r.json()
    if js.get("code") != "Ok":
        raise RuntimeError(js.get("code"))
    line = [(c[1], c[0]) for c in js["routes"][0]["geometry"]["coordinates"]]
    snaps = [(w["location"][1], w["location"][0]) for w in js["waypoints"]]
    # split the full line at the vertex nearest to each intermediate snapped waypoint
    cuts, j = [0], 0
    for k in range(1, len(snaps) - 1):
        sy, sx = snaps[k]
        best, bi = 1e18, j
        for i in range(j, len(line)):
            d = (line[i][0] - sy) ** 2 + (line[i][1] - sx) ** 2
            if d < best:
                best, bi = d, i
            if d < 1e-10:
                break
        cuts.append(bi)
        j = bi
    cuts.append(len(line) - 1)
    legs = []
    for a, b in zip(cuts, cuts[1:]):
        seg = line[a:b + 1] if b > a else [line[a], line[b]]
        legs.append([(round(y, 5), round(x, 5)) for y, x in _dp(seg, 0.00018)])
    if len(legs) != len(wps) - 1:
        raise RuntimeError("leg split mismatch")
    # stitch exact stop coordinates onto the ends so markers sit on the line
    for i, leg in enumerate(legs):
        leg[0], leg[-1] = wps[i], wps[i + 1]
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
    """Google Maps Platform Routes API (computeRoutes) with OAuth from the runtime identity."""
    global _GCREDS
    import google.auth
    import google.auth.transport.requests
    if _GCREDS is None:
        _GCREDS, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not _GCREDS.valid:
        _GCREDS.refresh(google.auth.transport.requests.Request())
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or getattr(_GCREDS, "quota_project_id", None) or ""

    def ll(p: tuple[float, float]) -> dict:
        return {"location": {"latLng": {"latitude": p[0], "longitude": p[1]}}}

    body = {"origin": ll(wps[0]), "destination": ll(wps[-1]),
            "intermediates": [ll(p) for p in wps[1:-1]], "travelMode": "DRIVE",
            "polylineQuality": "OVERVIEW"}
    r = requests.post("https://routes.googleapis.com/directions/v2:computeRoutes", json=body, timeout=timeout,
                      headers={"Authorization": f"Bearer {_GCREDS.token}", "X-Goog-User-Project": project,
                               "X-Goog-FieldMask": "routes.legs.polyline.encodedPolyline"})
    r.raise_for_status()
    legs_js = r.json()["routes"][0]["legs"]
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


PROVIDER = os.environ.get("LOADPILOT_ROUTER", "google,osrm")
_LAST_PROVIDER: dict[str, str] = {}


def legs_for(wps: list[tuple[float, float]], timeout: float = 8.0) -> list[list[tuple[float, float]]]:
    key = tuple((round(a, 5), round(b, 5)) for a, b in wps)
    with _LOCK:
        if key in _CACHE:
            return _CACHE[key]
    if not _ENABLED or len(wps) < 2:
        return _straight(wps)
    legs = None
    for prov in [p.strip() for p in PROVIDER.split(",") if p.strip()]:
        try:
            legs = (_google_legs if prov == "google" else _osrm_legs)(list(key), timeout)
            _LAST_PROVIDER["name"] = "Google Maps Routes API" if prov == "google" else "OSRM (OpenStreetMap)"
            break
        except Exception:  # noqa: BLE001 — try next provider
            continue
    if legs is None:
        return _straight(list(key))
    with _LOCK:
        _CACHE[key] = legs
    return legs


def provider_name() -> str:
    return _LAST_PROVIDER.get("name", "straight-line estimate")


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
