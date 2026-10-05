# FleetFlow demo data

All demo data is **synthetic and deterministic** (seed 42): a Mumbai Metropolitan Region
order book dispatched from the **Bhiwandi Regional DC** (ABG demo profile) plus a Bengaluru
order book (**Nelamangala & Electronic City DCs**). It is generated from code, snapshotted as
CSV in the repo, and published to **BigQuery** and **Cloud Storage (GCS)** so it can be queried
live by both the Gemini Enterprise agent and the Cloud Run Control Tower UI.

| | Where |
|---|---|
| Explorer page | `https://storage.cloud.google.com/<YOUR_PROJECT_ID>-fleetflow-media/demo-data/loadpilot_demo_data.html` |
| BigQuery dataset | `<YOUR_PROJECT_ID>.fleetflow_demo` (us-central1, labels `app=fleetflow, purpose=demo`) |
| GCS | `gs://<YOUR_PROJECT_ID>-fleetflow-media/demo-data/` → `tables/*.csv`, `samples/*`, `loadpilot_demo_data.html` |
| Repo | `demo_data/*.csv`, `demo_data/loadpilot_demo_data.html`, `app/data/samples/*` |

## How it is generated

| Source | What |
|---|---|
| `app/data/demo_mmr.py` | `HUBS`, `GAZETTEER` (49 localities), `build_demo_stops(seed=42)` → 70 outlets / 1,260 cartons, `baseline_assignment()` (today's manual plan). **Never change** — tests and plan numbers depend on it. |
| `app/data/master_data.py` | `SKU_MASTER`, `INDUSTRY_PROFILES`, `TRUCK_CATALOGUE`, `DEFAULT_FLEET_AVAILABLE`, `DEFAULT_DRIVERS`, `DEFAULT_COST_PROFILE`, `CORRIDOR_NAMES` |
| `app/data/demo_extended.py` | Derived enterprise tables (`build_tables()`), BigQuery schemas (`SCHEMAS`), `DRIVER_RUNS`, indicative `SKU_PRICE_INR` |
| `scripts/generate_demo_assets.py` | Carton photos with decodable QR labels + order files (`--drivers-only` = only driver-run assets) |
| `scripts/publish_demo_data.py` | CSV → `demo_data/` → GCS → BigQuery (WRITE_TRUNCATE, explicit schemas) + row-count check |
| `scripts/build_demo_data_page.py` | Builds and uploads the explorer page |
| `app/data/bq_source.py` | `load_stops_from_bigquery(...)` → `list[Stop]` identical to `build_demo_stops()` |

## Tables (`<YOUR_PROJECT_ID>.fleetflow_demo`)

| Table | Rows | Grain / contents |
|---|---:|---|
| `stores` | 70 | Outlet master: stop_id, name, industry, category, locality, sales_area, corridor (compass from hub), lat/lon, receiving window (min + `HH:MM-HH:MM`), contact person, phone, planner address, postal-style address |
| `orders` | 70 | One order per outlet for the dispatch date: order_id `SO-YYYYMMDD-Sxxx`, cartons, volume_m3, weight_kg, fragile_cartons, value_inr (from `SKU_PRICE_INR`), sku_lines |
| `cartons` | 1,260 | One row per box: box_id, stop_id, sku, description, category, industry, l/w/h cm, kg, volume, fragile, this_side_up, `qr_payload` (`LP1\|box\|stop\|sku\|LxWxH\|kg\|flags`, exactly what is printed on labels) |
| `skus` | 18 | Cross-industry carton catalogue (paints, FMCG, apparel, electronics, building) + indicative price |
| `truck_types` | 5 | ACE, PKP, T14, T17, T20: inner dims, volume, usable volume (80%), payload, fixed/day, ₹/km, km/l, speed |
| `fleet` | 12 | Vehicles available at BHW-DC on the dispatch date (fake registrations) |
| `drivers` | 12 | Every `DEFAULT_DRIVERS` name: full name, phone (fake `+91-9…`), licence class, home corridor, years, preferred truck, helper |
| `driver_runs` | 3 | Ready-made single-driver scenarios (below) |
| `cost_profile` | 17 | Fuel, crew, overtime, shift, CO2 factor, service times, toll per corridor |
| `hubs` | 2 | Bhiwandi DC (default), Taloja satellite DC |
| `corridors` | 8 | Compass corridors N…NW with toll |
| `gazetteer` | 49 | Offline geocoder localities: lat/lon, sales area, corridor, outlets in demo |
| `baseline` | 10 | Today's manual dispatch: one truck per sales area (+ split vehicle in Western Suburbs) with fill % |

`orders.dispatch_date` and `fleet.dispatch_date` are the publish date (default today;
`--date YYYY-MM-DD` to override). Everything else is date-independent.

Example query:

```sql
SELECT s.sales_area, COUNT(*) outlets, SUM(o.cartons) cartons, ROUND(SUM(o.weight_kg)) kg
FROM `<YOUR_PROJECT_ID>.fleetflow_demo.stores` s JOIN `<YOUR_PROJECT_ID>.fleetflow_demo.orders` o USING (stop_id)
GROUP BY 1 ORDER BY kg DESC;
```

## Driver runs (driver-perspective demo)

One driver + one truck + one corridor. Stops are chosen so every outlet's compass corridor
from Bhiwandi DC matches the run (`corridor_of`; Suresh's run spans N + NE) and the cartons fit
(≤ 80% cube, ≤ payload). An ACE (750 kg) cannot carry 6+ outlets of this order book, so the
smallest run uses a PKP. Files are in `app/data/samples/` and `gs://…/demo-data/samples/`.

| run_id | Driver · truck | Stops | Load | Photos (QR decoded) | Order message |
|---|---|---|---|---|---|
| `suresh_t14_north` | Suresh · T14 · North (Bhiwandi / Vajreshwari / Wada / Padgha / Shahapur) | S068 S069 S067 S066 S064 S063 | 107 cartons · 3.22 m³ · 2,283 kg (65% payload) | `driver_suresh_t14_north_cartons_a.jpg` (6/6), `_b.jpg` (6/6) | `driver_suresh_t14_north_orders.txt` |
| `ravi_t17_west` | Ravi · T17 · West (Anjur Phata / Ghodbunder / Mira Road / Bhayandar / Borivali) | S070 S035 S036 S009 S010 S008 S011 S012 | 156 cartons · 4.71 m³ · 2,573 kg (51% payload) | `driver_ravi_t17_west_cartons_a.jpg` (8/8), `_b.jpg` (8/8) | `driver_ravi_t17_west_orders.txt` |
| `imran_pkp_south` | Imran · PKP · South (Mumbra / Airoli / Vashi / Kharghar) | S038 S039 S040 S041 S044 S045 | 82 cartons · 2.43 m³ · 1,293 kg (86% payload) | `driver_imran_pkp_south_cartons_a.jpg` (6/6), `_b.jpg` (6/6) | `driver_imran_pkp_south_orders.txt` |

Each photo shows 2 cartons per stop (first and last box) with real QR labels; `_a` covers the
first half of the stops, `_b` the second half. Exact numbers: `driver_runs` table /
`driver_run_stats()`.

Python: `from app.data.demo_extended import DRIVER_RUNS` → list of dicts with `run_id, driver,
truck_code, corridor, label, stop_ids, photo, photos, order_file`.

## Other sample inputs (`app/data/samples/`)

| File | What |
|---|---|
| `cartons_S003_staging.jpg` | One outlet's 6 cartons on the staging floor |
| `cartons_mixed_dock.jpg` | 8 cartons across S010 / S024 / S031 / S047 at the dock |
| `label_closeup.png` | Single label close-up |
| `orders_email.txt`, `orders_today.csv/.xlsx/.pdf` | Same 12-outlet order list in four formats |
| `bg_dock.jpg`, `bg_staging_floor.jpg` | Generated backgrounds used for compositing |

## Reading from BigQuery in the agent

```python
from app.data.bq_source import load_stops_from_bigquery
stops = load_stops_from_bigquery()                                  # all 70 outlets
stops = load_stops_from_bigquery(stop_ids=DRIVER_RUNS[0]["stop_ids"])  # one driver run
stops = load_stops_from_bigquery(dispatch_date="2026-09-30")        # outlets with an order that day
```

Uses `google.auth.default()` (Agent Engine runtime SA `loadpilot-agent@` — the deploy script
grants `roles/bigquery.dataViewer` + `roles/bigquery.jobUser` and enables
`bigquery.googleapis.com`). Env overrides: `LOADPILOT_BQ_PROJECT`, `LOADPILOT_BQ_DATASET`,
`LOADPILOT_BQ_LOCATION`.

## Regenerate / publish

```bash
.venv/bin/python scripts/generate_demo_assets.py --drivers-only   # driver photos + messages
.venv/bin/python scripts/publish_demo_data.py                     # CSV + GCS + BigQuery (idempotent)
.venv/bin/python scripts/build_demo_data_page.py                  # explorer page (+ upload)
LOADPILOT_LIVE_BQ=1 .venv/bin/python -m pytest tests/unit/test_demo_data.py   # incl. live BQ check
```

Auth for the scripts: `google.auth.default()` (standard `gcloud auth application-default login` or `$FLEETFLOW_ADC_FILE`); set `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` on CloudTop.
