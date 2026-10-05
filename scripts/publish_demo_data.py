"""Publish the LoadPilot demo data: CSVs in the repo, files in GCS, tables in BigQuery.

1. Builds every table from app.data.demo_extended.build_tables() (derived from the seeded
   demo order book) and writes demo_data/<table>.csv (small, commit-friendly).
2. Uploads the CSVs to gs://<bucket>/demo-data/tables/ and every app/data/samples/* file to
   gs://<bucket>/demo-data/samples/ (plus demo_data/loadpilot_demo_data.html if built).
3. Creates BigQuery dataset <project>.loadpilot_demo (us-central1, labelled) if missing and
   loads every table from its GCS CSV with an explicit schema (WRITE_TRUNCATE -> idempotent).
4. Verifies row counts with a query and prints console / GCS links.

Auth: authorized-user ADC file ($FLEETFLOW_ADC_FILE / $GOOGLE_APPLICATION_CREDENTIALS)
if present, else google.auth.default().

Run:  .venv/bin/python scripts/publish_demo_data.py [--skip-bq] [--skip-gcs] [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import csv
import mimetypes
import os
import sys
import time
import urllib.parse

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.config import get_adc_file, get_bq_dataset, get_media_bucket, get_project_id, get_region  # noqa: E402
from app.data.bq_source import run_query  # noqa: E402
from app.data.demo_extended import SCHEMAS, build_tables  # noqa: E402

PROJECT = get_project_id()
DATASET = get_bq_dataset()
LOCATION = get_region()
BUCKET = get_media_bucket()
PREFIX = "demo-data"
OUT_DIR = os.path.join(ROOT, "demo_data")
SAMPLES_DIR = os.path.join(ROOT, "app", "data", "samples")
ADC_FILE = get_adc_file()
LABELS = {"app": "fleetflow", "purpose": "demo", "datacloud": "ai-agent"}
_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

BQ_CONSOLE = (f"https://console.cloud.google.com/bigquery?project={PROJECT}"
              f"&ws=!1m4!1m3!3m2!1s{PROJECT}!2s{DATASET}")


def bq_table_link(table: str) -> str:
    return (f"https://console.cloud.google.com/bigquery?project={PROJECT}"
            f"&ws=!1m5!1m4!4m3!1s{PROJECT}!2s{DATASET}!3s{table}")


def gcs_link(path: str) -> str:
    return f"https://storage.cloud.google.com/{BUCKET}/{PREFIX}/{path}"


def get_credentials():
    if ADC_FILE and os.path.exists(ADC_FILE):
        from google.oauth2.credentials import Credentials
        return Credentials.from_authorized_user_file(ADC_FILE, scopes=_SCOPES)
    import google.auth
    return google.auth.default(scopes=_SCOPES)[0]


def session(creds=None):
    from google.auth.transport.requests import AuthorizedSession
    return AuthorizedSession(creds or get_credentials())


# ------------------------------------------------------------------------------
# CSV
# ------------------------------------------------------------------------------
def _cell(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    return v


def write_csvs(tables: dict[str, list[dict]]) -> list[str]:
    os.makedirs(OUT_DIR, exist_ok=True)
    paths = []
    for name, rows in tables.items():
        fields = [f for f, _, _ in SCHEMAS[name][1]]
        p = os.path.join(OUT_DIR, f"{name}.csv")
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(fields)
            for r in rows:
                w.writerow([_cell(r[k]) for k in fields])
        paths.append(p)
    return paths


# ------------------------------------------------------------------------------
# GCS
# ------------------------------------------------------------------------------
def gcs_upload(sess, local_path: str, object_name: str, cache_control: str | None = None) -> str:
    ctype = mimetypes.guess_type(local_path)[0] or "application/octet-stream"
    if local_path.endswith((".txt", ".csv", ".html")):
        ctype += "; charset=utf-8"
    url = (f"https://storage.googleapis.com/upload/storage/v1/b/{BUCKET}/o?uploadType=media&name="
           + urllib.parse.quote(object_name, safe=""))
    with open(local_path, "rb") as f:
        r = sess.post(url, data=f.read(), headers={"Content-Type": ctype}, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"GCS upload {object_name} failed {r.status_code}: {r.text[:300]}")
    if cache_control:
        sess.patch(f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o/"
                   + urllib.parse.quote(object_name, safe=""), json={"cacheControl": cache_control}, timeout=60)
    return f"gs://{BUCKET}/{object_name}"


def upload_all(sess, csv_paths: list[str]) -> list[str]:
    done = []
    for p in csv_paths:
        done.append(gcs_upload(sess, p, f"{PREFIX}/tables/{os.path.basename(p)}", "no-cache"))
    for fn in sorted(os.listdir(SAMPLES_DIR)):
        fp = os.path.join(SAMPLES_DIR, fn)
        if os.path.isfile(fp):
            done.append(gcs_upload(sess, fp, f"{PREFIX}/samples/{fn}"))
    page = os.path.join(OUT_DIR, "loadpilot_demo_data.html")
    if os.path.exists(page):
        done.append(gcs_upload(sess, page, f"{PREFIX}/loadpilot_demo_data.html", "no-cache"))
    return done


# ------------------------------------------------------------------------------
# BigQuery
# ------------------------------------------------------------------------------
def ensure_dataset(sess) -> None:
    base = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/datasets"
    r = sess.get(f"{base}/{DATASET}", timeout=60)
    if r.status_code == 404:
        body = {"datasetReference": {"projectId": PROJECT, "datasetId": DATASET}, "location": LOCATION,
                "description": "LoadPilot demo data (Mumbai MMR, Bhiwandi DC) - outlets, orders, cartons, "
                               "fleet, drivers, costs. Generated by scripts/publish_demo_data.py.",
                "labels": LABELS}
        r = sess.post(base, json=body, timeout=60)
        if r.status_code >= 400:
            raise RuntimeError(f"create dataset failed {r.status_code}: {r.text[:300]}")
        print(f"[CREATED] dataset {PROJECT}.{DATASET} ({LOCATION})")
    elif r.status_code >= 400:
        raise RuntimeError(f"get dataset failed {r.status_code}: {r.text[:300]}")
    else:
        sess.patch(f"{base}/{DATASET}", json={"labels": LABELS}, timeout=60)
        print(f"[OK] dataset {PROJECT}.{DATASET} ({r.json().get('location')})")


def load_table(sess, name: str) -> str:
    desc, fields = SCHEMAS[name]
    schema = {"fields": [{"name": f, "type": t, "mode": "NULLABLE", "description": d} for f, t, d in fields]}
    body = {
        "configuration": {
            "labels": LABELS,
            "load": {
                "sourceUris": [f"gs://{BUCKET}/{PREFIX}/tables/{name}.csv"],
                "sourceFormat": "CSV", "skipLeadingRows": 1, "encoding": "UTF-8",
                "destinationTable": {"projectId": PROJECT, "datasetId": DATASET, "tableId": name},
                "schema": schema, "writeDisposition": "WRITE_TRUNCATE",
                "createDisposition": "CREATE_IF_NEEDED",
                "destinationTableProperties": {"description": desc, "labels": LABELS},
            },
        },
        "jobReference": {"projectId": PROJECT, "location": LOCATION},
    }
    r = sess.post(f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/jobs", json=body, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"load {name} failed {r.status_code}: {r.text[:400]}")
    return r.json()["jobReference"]["jobId"]


def wait_job(sess, job_id: str, name: str) -> None:
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/jobs/{job_id}?location={LOCATION}"
    for _ in range(120):
        j = sess.get(url, timeout=60).json()
        st = j.get("status", {})
        if st.get("state") == "DONE":
            if st.get("errorResult"):
                raise RuntimeError(f"load {name}: {st['errorResult']} {st.get('errors', [])[:3]}")
            # schema/column descriptions are applied from the load; set table description again
            return
        time.sleep(1.5)
    raise TimeoutError(f"load {name} timed out")


def verify_counts(creds, tables: dict[str, list[dict]]) -> dict[str, int]:
    sql = " UNION ALL ".join(f"SELECT '{t}' AS t, COUNT(*) AS n FROM `{PROJECT}.{DATASET}.{t}`" for t in tables)
    rows = run_query(sql + " ORDER BY t", project=PROJECT, location=LOCATION, credentials=creds)
    counts = {r["t"]: r["n"] for r in rows}
    for t, rs in tables.items():
        ok = counts.get(t) == len(rs)
        print(f"  {'OK ' if ok else 'BAD'} {t:<13} bq={counts.get(t)} expected={len(rs)}")
    return counts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="dispatch date (default today)")
    ap.add_argument("--skip-bq", action="store_true")
    ap.add_argument("--skip-gcs", action="store_true")
    a = ap.parse_args()

    tables = build_tables(dispatch_date=a.date)
    csvs = write_csvs(tables)
    print(f"[OK] wrote {len(csvs)} CSVs to {OUT_DIR}: " + ", ".join(f"{k}={len(v)}" for k, v in tables.items()))
    if a.skip_gcs:
        return
    creds = get_credentials()
    sess = session(creds)
    up = upload_all(sess, csvs)
    print(f"[OK] uploaded {len(up)} objects to gs://{BUCKET}/{PREFIX}/")
    if not a.skip_bq:
        ensure_dataset(sess)
        jobs = {t: load_table(sess, t) for t in tables}
        for t, j in jobs.items():
            wait_job(sess, j, t)
            print(f"[LOADED] {PROJECT}.{DATASET}.{t} ({len(tables[t])} rows)")
        print("[VERIFY] row counts:")
        verify_counts(creds, tables)
    print("\nBigQuery dataset:", BQ_CONSOLE)
    for t in tables:
        print(f"  {t:<13} {bq_table_link(t)}")
    print("\nGCS:")
    print("  folder  https://console.cloud.google.com/storage/browser/" f"{BUCKET}/{PREFIX}?project={PROJECT}")
    print("  explorer", gcs_link("loadpilot_demo_data.html"))
    for t in tables:
        print(f"  {gcs_link('tables/' + t + '.csv')}")


if __name__ == "__main__":
    main()
