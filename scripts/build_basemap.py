"""Build a compact vector basemap (coastline + major roads) for the demo region from OpenStreetMap.

Output: app/data/basemap_<name>.json — used by the route map inside the Gemini Enterprise
IFrameSrcdoc. That iframe cannot load map tiles, so the basemap is inlined. The full-screen page
also draws live CARTO/OSM tiles on top.

Usage:  .venv/bin/python scripts/build_basemap.py [--bbox S,W,N,E] [--name mmr]
Data © OpenStreetMap contributors (ODbL).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
CLASSES = {"motorway": 0.0006, "trunk": 0.0007, "primary": 0.0009, "coast": 0.0007, "rail": 0.0009}


def _dp(pts: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
    """Douglas-Peucker simplification (iterative)."""
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        n = math.hypot(dx, dy) or 1e-12
        best, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = pts[i]
            d = abs(dy * px - dx * py + bx * ay - by * ax) / n
            if d > best:
                best, idx = d, i
        if best > eps:
            keep[idx] = True
            stack += [(a, idx), (idx, b)]
    return [p for p, k in zip(pts, keep) if k]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bbox", default="18.88,72.76,19.92,73.42")
    ap.add_argument("--name", default="mmr")
    a = ap.parse_args()
    s, w, n, e = (float(x) for x in a.bbox.split(","))
    filters = ['way["highway"~"^(motorway|trunk)$"]', 'way["highway"="primary"]',
               'way["natural"="coastline"]', 'way["railway"="rail"]["usage"="main"]']
    grid = 2
    cells = [(s + (n - s) * i / grid, w + (e - w) * j / grid, s + (n - s) * (i + 1) / grid,
              w + (e - w) * (j + 1) / grid) for i in range(grid) for j in range(grid)]
    seen: set[int] = set()
    elements: list[dict] = []
    for f in filters:
        for (cs, cw, cn, ce) in cells:
            q = f"[out:json][timeout:60];{f}({cs},{cw},{cn},{ce});out geom;"
            ok = False
            for url in OVERPASS:
                try:
                    r = requests.get(url, params={"data": q}, timeout=90,
                                     headers={"User-Agent": "loadpilot-basemap/1.0 (demo)",
                                              "Accept": "application/json"})
                    r.raise_for_status()
                    for el in r.json().get("elements", []):
                        if el.get("id") not in seen:
                            seen.add(el.get("id"))
                            elements.append(el)
                    ok = True
                    break
                except Exception as ex:  # noqa: BLE001
                    print("overpass failed", url.split("/")[2], f, ex.__class__.__name__, flush=True)
            print("chunk", f, "ok" if ok else "MISSING", len(elements), flush=True)
    if not elements:
        raise SystemExit("no overpass endpoint reachable")
    data = {"elements": elements}
    out: dict[str, list] = {k: [] for k in CLASSES}
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        geom = el.get("geometry") or []
        if len(geom) < 2:
            continue
        if tags.get("natural") == "coastline":
            cls = "coast"
        elif tags.get("railway") == "rail":
            cls = "rail"
        else:
            cls = tags.get("highway")
        if cls not in CLASSES:
            continue
        pts = [(g["lon"], g["lat"]) for g in geom]
        pts = _dp(pts, CLASSES[cls])
        # integer micro-degrees ×1e4, delta-encoded: [lon0, lat0, dlon1, dlat1, ...]
        flat, plon, plat = [], 0, 0
        for lon, lat in pts:
            ilon, ilat = round(lon * 1e4), round(lat * 1e4)
            flat += [ilon - plon, ilat - plat]
            plon, plat = ilon, ilat
        out[cls].append(flat)
    res = {"bbox": [s, w, n, e], "scale": 1e4, "encoding": "delta-int lon,lat", "attribution":
           "© OpenStreetMap contributors", **out}
    path = ROOT / "app" / "data" / f"basemap_{a.name}.json"
    path.write_text(json.dumps(res, separators=(",", ":")))
    print(path, f"{path.stat().st_size / 1024:.0f} KB", {k: len(v) for k, v in out.items()})


if __name__ == "__main__":
    main()
