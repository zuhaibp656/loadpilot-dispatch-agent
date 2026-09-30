"""Load the demo order book (stores + cartons) from BigQuery.

Reads `<project>.<dataset>.stores` and `.cartons` (written by scripts/publish_demo_data.py)
with the BigQuery REST API (jobs.query, parameterised) using `google.auth.default()` — the
Agent Engine runtime service account in production, ADC locally. Reconstructs `Stop` / `Box`
dataclasses exactly as `build_demo_stops()` builds them, so plans are identical.
"""

from __future__ import annotations

import logging
import os

try:
    from app.contracts import Box, Stop
except ImportError:  # pragma: no cover
    from contracts import Box, Stop

logger = logging.getLogger(__name__)

DEFAULT_PROJECT = os.environ.get("LOADPILOT_BQ_PROJECT", "zuhaibp-ai")
DEFAULT_DATASET = os.environ.get("LOADPILOT_BQ_DATASET", "loadpilot_demo")
DEFAULT_LOCATION = os.environ.get("LOADPILOT_BQ_LOCATION", "us-central1")
_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def _session(credentials=None):
    import google.auth
    from google.auth.transport.requests import AuthorizedSession

    if credentials is None:
        credentials, _ = google.auth.default(scopes=_SCOPES)
    return AuthorizedSession(credentials)


def run_query(sql: str, params: list[dict] | None = None, project: str = DEFAULT_PROJECT,
              location: str = DEFAULT_LOCATION, credentials=None, timeout_s: int = 60) -> list[dict]:
    """Run a standard-SQL query via REST and return rows as {column: python value}."""
    sess = _session(credentials)
    base = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project}"
    body = {"query": sql, "useLegacySql": False, "location": location, "maxResults": 10000,
            "timeoutMs": timeout_s * 1000, "parameterMode": "NAMED",
            "queryParameters": params or [], "labels": {"app": "loadpilot", "datacloud": "ai-agent"}}
    r = sess.post(f"{base}/queries", json=body, timeout=timeout_s + 30)
    if r.status_code >= 400:
        raise RuntimeError(f"BigQuery query failed {r.status_code}: {r.text[:400]}")
    res = r.json()
    job_id = res.get("jobReference", {}).get("jobId")
    while not res.get("jobComplete", False):
        r = sess.get(f"{base}/queries/{job_id}", params={"location": location, "maxResults": 10000,
                                                         "timeoutMs": timeout_s * 1000}, timeout=timeout_s + 30)
        r.raise_for_status()
        res = r.json()
    fields = res["schema"]["fields"]
    rows = list(res.get("rows", []))
    token = res.get("pageToken")
    while token:
        r = sess.get(f"{base}/queries/{job_id}", params={"location": location, "pageToken": token,
                                                         "maxResults": 10000}, timeout=timeout_s + 30)
        r.raise_for_status()
        page = r.json()
        rows += page.get("rows", [])
        token = page.get("pageToken")
    return [{f["name"]: _cast(cell.get("v"), f["type"]) for f, cell in zip(fields, row["f"])}
            for row in rows]


def _cast(v, typ: str):
    if v is None:
        return None
    if typ in ("INTEGER", "INT64"):
        return int(v)
    if typ in ("FLOAT", "FLOAT64", "NUMERIC", "BIGNUMERIC"):
        return float(v)
    if typ in ("BOOLEAN", "BOOL"):
        return v in (True, "true", "True")
    return v


def load_stops_from_bigquery(project: str = DEFAULT_PROJECT, dataset: str = DEFAULT_DATASET,
                             dispatch_date: str | None = None, stop_ids: list[str] | None = None,
                             location: str = DEFAULT_LOCATION, credentials=None) -> list[Stop]:
    """Stops (with boxes) from BigQuery, ordered by stop_id / box_id like build_demo_stops().

    dispatch_date: only outlets with an order on that date (orders table), e.g. "2026-09-30".
    stop_ids: restrict to these outlet ids (e.g. a driver run's stops).
    """
    where, params = [], []
    if dispatch_date:
        where.append(f"s.stop_id IN (SELECT stop_id FROM `{project}.{dataset}.orders` "
                     "WHERE dispatch_date = @dispatch_date)")
        params.append({"name": "dispatch_date", "parameterType": {"type": "DATE"},
                       "parameterValue": {"value": dispatch_date}})
    if stop_ids:
        where.append("s.stop_id IN UNNEST(@stop_ids)")
        params.append({"name": "stop_ids", "parameterType": {"type": "ARRAY", "arrayType": {"type": "STRING"}},
                       "parameterValue": {"arrayValues": [{"value": s} for s in stop_ids]}})
    sql = (
        "SELECT s.stop_id, s.name, s.address, s.lat, s.lon, s.window_start_min, s.window_end_min, "
        "s.sales_area, c.box_id, c.sku, c.description, c.l_cm, c.w_cm, c.h_cm, c.weight_kg, "
        "c.fragile, c.this_side_up, c.category "
        f"FROM `{project}.{dataset}.stores` s JOIN `{project}.{dataset}.cartons` c USING (stop_id) "
        + (("WHERE " + " AND ".join(where) + " ") if where else "")
        + "ORDER BY s.stop_id, c.box_id"
    )
    rows = run_query(sql, params, project=project, location=location, credentials=credentials)
    return rows_to_stops(rows)


def rows_to_stops(rows: list[dict]) -> list[Stop]:
    """Group joined store+carton rows (sorted by stop_id, box_id) into Stop dataclasses."""
    stops: list[Stop] = []
    cur: dict | None = None
    boxes: list[Box] = []

    def flush() -> None:
        if cur is not None:
            stops.append(Stop(stop_id=cur["stop_id"], name=cur["name"], address=cur["address"],
                              lat=cur["lat"], lon=cur["lon"], window_start_min=cur["window_start_min"],
                              window_end_min=cur["window_end_min"], boxes=tuple(boxes),
                              area=cur["sales_area"]))

    for r in rows:
        if cur is None or r["stop_id"] != cur["stop_id"]:
            flush()
            cur, boxes = r, []
        boxes.append(Box(box_id=r["box_id"], stop_id=r["stop_id"], sku=r["sku"],
                         description=r["description"], l_cm=r["l_cm"], w_cm=r["w_cm"], h_cm=r["h_cm"],
                         weight_kg=r["weight_kg"], fragile=bool(r["fragile"]),
                         this_side_up=bool(r["this_side_up"]), category=r["category"]))
    flush()
    logger.info("loaded %d stops / %d cartons from BigQuery", len(stops), sum(len(s.boxes) for s in stops))
    return stops
