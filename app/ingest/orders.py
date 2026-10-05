"""Order ingestion from any format -> list[Stop].

Supported: pasted list / email body (text), CSV, XLSX, PDF (text layer).
Pipeline: tabular -> heuristic column mapping; free text -> Gemini structured extraction
(fallback: deterministic line parser). Geocoding via the offline gazetteer (optionally Google
Geocoding API when GOOGLE_MAPS_API_KEY is set). Cartons are expanded from SKU quantities,
or synthesised from volume / carton counts when only totals are given.
"""

from __future__ import annotations

import io
import json
import logging
import os
import random
import re
import urllib.parse
import urllib.request

try:
    from app.contracts import Stop
    from app.data.demo_blr import GAZETTEER_BLR, geocode_blr_locality
    from app.data.demo_mmr import GAZETTEER, geocode_locality, make_boxes_for_stop
    from app.data.master_data import SKU_MASTER
except ImportError:  # pragma: no cover
    from contracts import Stop
    from data.demo_blr import GAZETTEER_BLR, geocode_blr_locality
    from data.demo_mmr import GAZETTEER, geocode_locality, make_boxes_for_stop
    from data.master_data import SKU_MASTER

logger = logging.getLogger(__name__)

EXTRACT_MODEL = os.environ.get("LOADPILOT_EXTRACT_MODEL", "gemini-2.5-flash")

_ALL_GAZETTEER = {**GAZETTEER, **GAZETTEER_BLR}

_COLS = {
    "name": ["customer", "outlet", "store", "retailer", "dealer", "name", "consignee", "party"],
    "address": ["address", "location", "locality", "area", "city", "delivery point", "destination"],
    "cartons": ["cartons", "boxes", "cases", "packages", "qty", "quantity", "units", "ctn"],
    "sku": ["sku", "item", "product", "material"],
    "weight": ["weight", "kg"],
    "window": ["window", "slot", "time", "timing"],
    "industry": ["category", "industry", "segment", "division"],
}


def _geocode(text: str) -> tuple[float, float, str] | None:
    hit = geocode_locality(text) or geocode_blr_locality(text)
    if hit:
        return hit
    key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not key:
        return None
    try:  # pragma: no cover - network path
        url = ("https://maps.googleapis.com/maps/api/geocode/json?"
               + urllib.parse.urlencode({"address": text, "key": key}))
        with urllib.request.urlopen(url, timeout=10) as r:
            res = json.loads(r.read().decode()).get("results", [])
        if res:
            loc = res[0]["geometry"]["location"]
            return (loc["lat"], loc["lng"], "")
    except Exception as exc:
        logger.warning("geocode failed for %s: %s", text, exc)
    return None


def _industry_guess(text: str) -> str:
    t = (text or "").lower()
    for key, ind in (("paint", "paints"), ("colour", "paints"), ("hardware", "paints"),
                     ("fashion", "apparel"), ("garment", "apparel"), ("electronic", "electronics"),
                     ("digital", "electronics"), ("cement", "cement"), ("building", "cement")):
        if key in t:
            return ind
    return "fmcg"


def _parse_window(text: str) -> tuple[int, int]:
    m = re.findall(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", (text or "").lower())
    mins = []
    for h, mm, ap in m[:2]:
        h = int(h) % 24
        if ap == "pm" and h < 12:
            h += 12
        mins.append(h * 60 + int(mm or 0))
    if len(mins) == 2 and mins[1] > mins[0]:
        return mins[0], mins[1]
    return 9 * 60, 19 * 60


def _mk_stop(idx: int, name: str, address: str, cartons: int, industry: str,
             window: tuple[int, int], sku_qty: dict[str, int] | None, rng: random.Random) -> Stop | None:
    geo = _geocode(f"{address} {name}")
    if geo is None:
        return None
    sid = f"S{idx:03d}"
    boxes = []
    if sku_qty:
        from app.contracts import Box
        k = 1
        for sku, q in sku_qty.items():
            s = SKU_MASTER.get(sku)
            if s is None:
                continue
            for _ in range(int(q)):
                boxes.append(Box(f"{sid}-B{k:02d}", sid, s.sku, s.description, s.l_cm, s.w_cm, s.h_cm,
                                 s.weight_kg, s.fragile, s.this_side_up, s.category, source="order"))
                k += 1
    if not boxes:
        boxes = make_boxes_for_stop(sid, industry, max(1, cartons), rng)
    return Stop(stop_id=sid, name=name.strip() or address, address=address, lat=geo[0], lon=geo[1],
                window_start_min=window[0], window_end_min=window[1], boxes=tuple(boxes), area=geo[2])


def _map_columns(cols: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for c in cols:
        lc = str(c).lower()
        for field, keys in _COLS.items():
            if field not in mapping and any(k in lc for k in keys):
                mapping[field] = c
                break
    return mapping


def from_dataframe(df) -> tuple[list[Stop], list[str]]:
    rng = random.Random(7)
    m = _map_columns(list(df.columns))
    stops: list[Stop] = []
    issues: list[str] = []
    for i, row in enumerate(df.to_dict("records"), start=1):
        name = str(row.get(m.get("name", ""), "") or "")
        addr = str(row.get(m.get("address", ""), "") or name)
        cartons = int(float(row.get(m.get("cartons", ""), 12) or 12))
        ind = _industry_guess(f"{row.get(m.get('industry', ''), '')} {name}")
        win = _parse_window(str(row.get(m.get("window", ""), "") or ""))
        s = _mk_stop(i, name, addr, cartons, ind, win, None, rng)
        if s is None:
            issues.append(f"Row {i}: could not geocode '{addr}'")
        else:
            stops.append(s)
    return stops, issues


def _gemini_extract(text: str) -> list[dict] | None:
    """Structured extraction of delivery rows from free text (email / pasted list / PDF text)."""
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover
        return None
    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "customer": {"type": "STRING"}, "locality": {"type": "STRING"},
                "cartons": {"type": "INTEGER"}, "category": {"type": "STRING"},
                "window": {"type": "STRING"}, "assigned_to": {"type": "STRING"},
            },
            "required": ["customer", "locality"],
        },
    }
    try:
        client = genai.Client()
        resp = client.models.generate_content(
            model=EXTRACT_MODEL,
            contents=("Extract every delivery (one row per customer drop) from this dispatch message. "
                      "locality = the town/suburb name. cartons = number of boxes/cases (default 12). "
                      "category = paints/fmcg/apparel/electronics/cement. window = delivery time window "
                      "if stated. assigned_to = driver or route name if stated.\n\n" + text[:30000]),
            config=types.GenerateContentConfig(
                temperature=0.0, response_mime_type="application/json", response_schema=schema,
                thinking_config=types.ThinkingConfig(thinking_budget=0)),
        )
        return json.loads(resp.text or "[]")
    except Exception as exc:
        logger.warning("Gemini extraction failed, falling back to line parser: %s", exc)
        return None


def _line_parse(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip(" -*•\t")
        if not line:
            continue
        geo = _geocode(line)
        if not geo:
            continue
        loc = next((n for n in sorted(_ALL_GAZETTEER, key=len, reverse=True) if n.lower() in line.lower()), geo[2] or "Area")
        num = re.search(r"(\d+)\s*(?:cartons|boxes|cases|ctn|pkgs|packages)", line, re.I)
        name = re.split(r"[,\-–|:]", line)[0].strip()
        rows.append({"customer": name if loc.lower() not in name.lower() else f"Outlet {loc}",
                     "locality": loc, "cartons": int(num.group(1)) if num else 12,
                     "category": _industry_guess(line), "window": line})
    return rows


def from_text(text: str, use_llm: bool = True) -> tuple[list[Stop], list[str]]:
    rng = random.Random(11)
    rows = (_gemini_extract(text) if use_llm else None) or _line_parse(text)
    stops: list[Stop] = []
    issues: list[str] = []
    for i, r in enumerate(rows, start=1):
        s = _mk_stop(i, r.get("customer", ""), r.get("locality", ""), int(r.get("cartons") or 12),
                     _industry_guess(f"{r.get('category', '')} {r.get('customer', '')}"),
                     _parse_window(r.get("window", "") or ""), None, rng)
        if s is None:
            issues.append(f"Could not geocode '{r.get('locality')}' ({r.get('customer')})")
        else:
            stops.append(s)
    return stops, issues


def from_file_bytes(data: bytes, mime: str, filename: str = "") -> tuple[list[Stop], list[str]]:
    import pandas as pd

    name = (filename or "").lower()
    if "csv" in mime or name.endswith(".csv"):
        return from_dataframe(pd.read_csv(io.BytesIO(data)))
    if "sheet" in mime or "excel" in mime or name.endswith((".xlsx", ".xls")):
        return from_dataframe(pd.read_excel(io.BytesIO(data)))
    if "pdf" in mime or name.endswith(".pdf"):
        from pypdf import PdfReader
        text = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
        return from_text(text)
    return from_text(data.decode("utf-8", errors="ignore"))
