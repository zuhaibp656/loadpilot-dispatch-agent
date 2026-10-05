# 🚚 FleetFlow: truck load and route optimiser (ADK + Gemini Enterprise)

FleetFlow is a cross-industry autonomous dispatch engine for retail and CPG companies (paints, FMCG, apparel, electronics, building materials).

**The problem.** Every morning, trucks leave a hub with 8–12 fixed deliveries each. Today, dispatch is planned by sales area:

- trucks overlap on the same roads;
- cartons are loaded in random order, so drivers dig for boxes at every stop;
- nobody knows the true cost of the plan.

**What FleetFlow does:**

1. **Corridors.** It splits stops into 8 compass corridors from the hub. When a driver claims a corridor (for example, "Ravi has the West route"), the best stops in that corridor are pinned to his truck. Other trucks going the same way branch off a shared trunk.
2. **Routes.** It chooses the truck mix, stop order and time windows with an OR-Tools CVRPTW solver, costed per truck type. You can optimise for lowest cost, fewest trucks, fastest finish or balanced workload.
3. **LIFO loading.** It uses a 3D height-map packer. The last delivery goes against the cab wall and the first delivery sits at the rear door. Heavy cartons go on the floor, and fragile cartons get limits on what can be stacked on them. Every truck is checked for LIFO accessibility and geometry.
4. **Cost vs today.** It compares truck day-rate, per-km cost, diesel, tolls, crew and overtime against today's plan, plus time spent digging for boxes.
5. **Visuals.** Everything is produced deterministically in Python:
   - an A2UI Canvas with a Stepper and Tabs: an Overview map with KPIs, an animated corridor route replay, an animated 3D LIFO loading view (orbit, truck chips, unload replay), and a loader MP4 for the dock team;
   - a Markdown report with copy-ready tables (5 columns or fewer).

Demo data covers Mumbai MMR from the Bhiwandi DC: 70 outlets and about 1,260 cartons across 5 truck types. On the demo, the typical result is **10 → 8 trucks** and **about ₹18.7k saved per day (−29%)**.

## Architecture

```
app/
  contracts.py            dataclasses (TruckType, Stop, Box, PlanningParams, DispatchPlan, ...)
  data/                   truck catalogue, cost profile, SKU master, demo MMR gazetteer + samples/
  optim/                  distance, corridors, vrp (OR-Tools), lifo_packer, cost, dispatch
  ingest/orders.py        email / CSV / XLSX / PDF -> stops (Gemini structured extraction + parser)
  capture/sources.py      pluggable box capture: QR (OpenCV) -> Gemini vision labels -> Live stub
  render/                 A2UI surfaces, Canvas2D animation engine (anim/engine.js), MP4, Vega, Markdown
  integration/            ADK agent (callbacks), tools, background media publishing
scripts/
  deploy.sh               one-command deploy (tests + resources + Agent Engine + Gemini Enterprise)
  deploy_to_gemini_enterprise.py
  generate_demo_assets.py carton photos with real QR labels + sample order files
  local_e2e.py            run the agent headless through an ADK Runner
```

The model only writes a 3-bullet headline. Tables, links and UI are attached by callbacks:

- `before_agent` captures attachments and the planning-form action;
- `before_model` strips A2UI blobs and old images from the history;
- `after_model` appends the Markdown report;
- `after_agent` emits the A2UI surface.

Heavy objects live in a module cache keyed by a small token held in session state.

## Tools

| Tool | Purpose |
| :--- | :--- |
| `show_planning_wizard` | A2UI form: date, hub, truck types and counts, objective, claims, costs |
| `plan_dispatch` | Optimise: corridors → routes → LIFO loading → cost vs today |
| `claim_corridor` | "Ravi has the West route": pin the corridor and re-plan |
| `get_truck_load_plan` | Loading sheet, 3D animation and MP4 for one truck |
| `ingest_delivery_orders` | Pasted or attached order list (email, CSV, XLSX, PDF) |
| `scan_box_manifest` | Carton photos → QR / label reading → cartons added to the plan |
| `list_fleet_and_costs`, `reset_to_demo_data` | Reference data and reset |

## Run locally

```bash
uv sync --python 3.13
LOADPILOT_PUBLISH_MEDIA=false uv run pytest tests/unit -q
uv run adk web --port 8501 .          # open http://localhost:8501, pick "app"
uv run python scripts/local_e2e.py "Plan today's dispatch" "Ravi has the West route" "Show T17-1"
```

To reach Vertex AI from CloudTop, set `GOOGLE_API_USE_CLIENT_CERTIFICATE=false`. Use ADC from `gcloud auth application-default login`, or `GEMINI_API_KEY`.

## Deploy (reusable)

```bash
PROJECT=my-proj REGION=us-central1 VIEWER_DOMAIN=example.com ./scripts/deploy.sh
```

The script is idempotent. It does the following:

1. Enables the required APIs.
2. Creates the `<project>-agent-staging` and `<project>-loadpilot-media` buckets.
3. Creates the `loadpilot-agent@` runtime service account and grants its IAM roles (including the self token-creator role needed for V4 signed media URLs).
4. Creates the Agent Engine, or **updates the same engine in place** on later runs.
5. Registers or patches the agent in every Gemini Enterprise app in the project. To target a single app, set `GE_APP_ID`.

## Configuration

| Env var | Default | Meaning |
| :--- | :--- | :--- |
| `LOADPILOT_MODEL` | `gemini-2.5-flash` | Agent model |
| `LOADPILOT_UI_MODE` | `canvas` | `card` = fallback Card with VegaCharts only |
| `LOADPILOT_MEDIA_BUCKET` | `<project>-loadpilot-media` | HTML / MP4 publishing bucket |
| `LOADPILOT_PUBLISH_MEDIA` | `true` | Set to `false` to skip GCS publishing (tests, offline) |
| `LOADPILOT_DISTANCE_PROVIDER` | `haversine` | `routes_api` (+ `GOOGLE_MAPS_API_KEY`) for road distances |

## Box capture roadmap

The POC scans photos: QR labels first (exact), then Gemini vision reads the printed labels. `BoxCaptureSource` keeps capture pluggable, so a barcode gun, or a phone app / PWA using the **Gemini Live API** camera stream, can call the same tool contract.
