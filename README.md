# 🚚 FleetFlow — Autonomous Truck Load & Route Optimiser

FleetFlow is a dual-surface autonomous dispatch engine for retail and CPG distribution (paints, FMCG, apparel, electronics, building materials). It can be deployed either to **Gemini Enterprise** (conversational A2UI agent via Vertex AI Agent Engine) or as a standalone **Cloud Run Web Application** (Supply Chain Control Tower & 3D Load Studio)—both powered by the exact same deterministic Python solver and Google Cloud backend.

---

## 🎯 The Operational Problem & Solution

Every morning, trucks leave a distribution hub with 8–12 fixed retail deliveries. Under manual area-based planning:
- Multiple trucks overlap on the same highway trunks;
- Cartons are loaded in random order, forcing drivers to dig for buried boxes at every stop (~14 min lost per stop);
- Planners lack visibility into true per-route cost and 3D truck volume utilisation.

### What FleetFlow Does Automatically
1. **8-Way Compass Corridors & Trunk-and-Branch Routing**: Clusters stops by bearing from the hub (`N`, `NE`, `E`, `SE`, `S`, `SW`, `W`, `NW`). When a driver claims a corridor (e.g., *"Ravi has the West route"*), the inner stops are pinned to his truck while overflow stops branch cleanly off the shared highway trunk.
2. **Heterogeneous Fleet CVRPTW (Google OR-Tools)**: Selects the optimal mix of `ACE`, `PKP`, `T14`, `T17`, and `T20` vehicles, stop sequence, and delivery time windows under 4 selectable objectives (`lowest_cost`, `fewest_trucks`, `fastest_completion`, `balanced`).
3. **3D LIFO Height-Map Bin Packing**: Places every carton at exact `(x, y, z)` coordinates (`1 cm` grid resolution) so the **last delivery goes first against the cab wall (`X=0`)** and **Stop 1 sits right at the rear door**—enforcing floor-only placement for heavy items (`>20 kg`) and crush limits for fragile cartons.
4. **Cost vs. Manual Baseline**: Computes day-rate, per-km running cost, diesel, highway tolls, crew wages, overtime, and LIFO unloading time saved against the manual plan (typically **10 → 7–8 trucks** and **~₹19.7k saved per day, −30%**).
5. **Zero-Hallucination Guardrails**: The LLM (`gemini-2.5-flash`) writes only a 3-bullet summary headline (`≤60 words`) and calls tools; all tables, rupees, coordinates, 2D road maps, and 3D WebGL/Canvas animations are attached deterministically by Python callbacks.

---

## 🏛️ Dual-Surface Architecture

FleetFlow shares a single core engine (`app/`) across two interchangeable user surfaces:

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION SURFACES                             │
│                                                                              │
│  Surface 1: Gemini Enterprise (A2UI)     Surface 2: Cloud Run Control Tower  │
│  • Natural-language multi-turn chat      • Left-rail Google Gemini Light UI  │
│  • Inline A2UI Canvas & Planning Wizard  • Interactive 2D Map + 3D Studio    │
│  • Copy-ready ≤5-col Markdown tables     • Dock QR Intake, Fleet & SQL tabs  │
└───────────────────┬──────────────────────────────────────┬───────────────────┘
                    │                                      │
                    ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                 SHARED PYTHON CORE ENGINE (app/)                             │
│  • app/integration/agent.py & tools.py   (ADK Agent + 11 Tools + Callbacks)  │
│  • app/optim/                            (Corridors, OR-Tools VRP, 3D LIFO)  │
│  • app/render/                           (2D Map, 3D WebGL/Canvas, MP4)      │
│  • app/data/bq_source.py                 (Live BigQuery + Demo Fallback)     │
└───────┬──────────────────┬──────────────────────┬────────────────────┬───────┘
        │                  │                      │                    │
        ▼                  ▼                      ▼                    ▼
  ┌───────────┐    ┌───────────────┐    ┌──────────────────┐   ┌──────────────┐
  │ BigQuery  │    │ Cloud Storage │    │ Google Maps API  │   │ Model Armor  │
  │ 7 Tables  │    │ Signed Media  │    │ Routes & Traffic │   │ & Cloud DLP  │
  └───────────┘    └───────────────┘    └──────────────────┘   └──────────────┘
```

### Repository Structure
```text
app/
  config.py               Portable config resolver (env / .env / gcloud project; zero hardcoded IDs)
  contracts.py            Typed dataclasses (TruckType, Stop, Box, PlanningParams, DispatchPlan)
  data/                   BigQuery connector (bq_source.py), truck catalogue, Mumbai & Bangalore hubs
  geo/roads.py            Google Maps Routes API v2 + OSRM real road network & polyline engine
  optim/                  8-sector corridors, OR-Tools CVRPTW solver, 3D height-map LIFO packer, cost
  ingest/orders.py        Email / CSV / XLSX / PDF order extraction
  capture/sources.py      Dock carton capture: OpenCV QR decoder + Gemini Vision label OCR
  render/                 A2UI surfaces, Canvas2D/Three.js engine (anim/engine.js), MP4, Mobile Portal
  integration/            ADK root_agent, deterministic callbacks, 11 tools, background media publisher
  web/                    FastAPI REST API (api.py) & Gemini Light/Dark Control Tower UI (ui_html.py)
scripts/
  deploy.sh               Unified CLI deployer (--target ui | gemini-enterprise | all)
  deploy_cloud_run.sh     Cloud Run Web UI deployment script
  deploy_to_gemini_enterprise.py  Discovery Engine A2UI registration helper
  publish_demo_data.py    Idempotent BigQuery (7 tables) + GCS media bucket provisioner
```

---

## ☁️ Why & How Each Google Cloud Service Is Used

| Google Cloud Service | Why We Use It | How It Is Implemented in FleetFlow |
| :--- | :--- | :--- |
| **BigQuery** (`<project>.<dataset>`) | Enterprise-scale relational storage and real-time analytics across multi-city hubs (`BHW-DC` Mumbai & `BLR-DC` Bangalore) with 7 tables (`stores`, `orders`, `cartons`, `skus`, `fleet`, `drivers`, `kpi_runs`). | Queried live via parameterized REST SQL in `app/data/bq_source.py` (`load_stops_from_bq`, `run_readonly_sql`) to hydrate daily store manifests, log optimization runs, and power the interactive **BigQuery SQL Studio** tab. Automatically falls back to deterministic in-memory data if offline. |
| **Cloud Storage (GCS)** (`gs://<project>-fleetflow-media`) | Zero-login external distribution of rich visual artifacts to warehouse dock loaders and truck drivers on mobile phones without requiring corporate IAM accounts. | `app/render/publish.py` uploads 3D LIFO loading MP4 videos, standalone interactive HTML5 canvases, **Mobile Driver Portals** (`driver_<id>.html`), and dock QR carton photos, then signs **IAM V4 Signed URLs** (`signBlob`, valid 24h) embedded directly into agent responses and WhatsApp briefings. |
| **Vertex AI Agent Engine** (`ReasoningEngine` + Gemini 2.5 Flash) | Managed, auto-scaling runtime for the Google ADK agent (`FleetFlowAdkApp`) with session state persistence and multimodal tool orchestration. | Runs `root_agent` in `app/integration/agent.py` with `before_agent`, `before_model`, `after_model`, and `after_agent` callbacks that strip fabricated markup and deterministically attach verified Markdown tables and A2UI surfaces. |
| **Cloud Run** (`fleetflow-control-tower`) | Serverless container hosting for the standalone **Supply Chain Control Tower & 3D Load Studio Web UI** (`FastAPI` + `Uvicorn`). | Containerized via `Dockerfile` and deployed with `scripts/deploy_cloud_run.sh`, exposing `/api/plan`, `/api/load-studio`, `/api/agent-chat`, `/api/bq/query`, and `/api/scan-photo` over HTTPS. |
| **Google Maps Routes API** (`routes.googleapis.com/directions/v2`) | Real road distances, highway travel times, and turn-by-turn navigation rather than straight-line estimates. | `app/geo/roads.py` fetches actual highway polylines (`WEH`, `EEH`, `NH48`, `Sion-Panvel`, `ORR`) and builds 1-tap **Universal Google Maps Navigation URLs** (`google.com/maps/dir/?api=1&travelmode=driving`) for drivers. |
| **Model Armor & Cloud DLP** | Enterprise security, prompt-injection defense, PII/GSTIN redaction, and mathematical integrity. | Pre-turn input screening blocks prompt injection/jailbreaks, Cloud DLP masks phone/GSTIN PII in unstructured emails, and the isolated Python math enclave guarantees LLM hallucination cannot alter coordinates or costs. |

---

## 🧭 Step-by-Step How-To Guide

### 1. Using the Cloud Run Web Control Tower UI
1. **Select a Workspace (Left Navigation Rail)**:
   - **🗺️ Dispatch & Map**: View the 4 core operational KPIs (*Trucks Dispatched*, *Daily Cost Savings*, *Deliveries & Cargo*, *Total Route Distance*), inspect the 2D Road Network Map, and filter by **All Trucks**, **Top 3**, or a **Single Truck** (non-selected routes automatically dim).
   - **📦 3D Load Studio**: Inspect interactive 3D WebGL/Canvas LIFO truck loading, step through carton placement (`Play/Pause`, `Cab View`, `Rear Door`, `Top Down`, `X-Ray`), or use the **Interactive Truck Load Calculator** to test custom carton dimensions and see recommended trucks.
   - **🚛 Fleet & Cost Simulator**: Adjust vehicle counts (`ACE`, `PKP`, `T14`, `T17`, `T20`) and cost assumptions (diesel ₹/L, driver day wage) and re-solve in real time.
   - **📸 Dock QR & Intake**: Decode dock carton photos via OpenCV QR / Gemini Vision or paste raw order CSV/JSON lines to re-plan immediately.
   - **📱 Driver Hub & BigQuery**: Open 1-click **Mobile Driver Portals** (with live Google Maps navigation, Digital POD checklist, and Printable LR Challan) or run live read-only SQL queries in the **BigQuery SQL Studio**.
   - **📘 Architecture & How-To**: Built-in reference guide covering workflows, GCP architecture, and deployment commands.
2. **Switch Theme**: Toggle between the default **Google Gemini Minimalist Light Theme** (`☀️ Light Theme`) and Dark Mode (`🌙 Dark Theme`) from the bottom of the left navigation rail.
3. **Ask the Embedded FleetFlow AI Agent**: Click the bottom-right **FleetFlow AI Agent** button to run multi-turn natural language commands that automatically synchronize the active UI tab and truck filter.

### 2. Using the Agent in Gemini Enterprise (or Chat)
| User Persona | Example Prompts | What Happens |
| :--- | :--- | :--- |
| **Fleet Manager** | *"Plan today's dispatch for Bhiwandi DC"*<br>*"Only show Ravi"* / *"Show 3 trucks"*<br>*"Ravi has the West route"*<br>*"Send each driver his instructions"* | Runs the full pipeline (`Corridors → OR-Tools CVRPTW → 3D LIFO → Cost`), scopes the map/table to 1, 3, or all trucks, pins corridors, or generates per-driver briefing links. |
| **Warehouse Loader** | *"Show the 3D load plan for T17-1"*<br>*"Read these carton photos and re-plan"* | Renders the interactive 3D LIFO loading sequence (Stop N at cab wall → Stop 1 at rear door) plus a downloadable MP4 video for the loading bay. |
| **Truck Driver** | *"I'm Suresh, how do I load my truck and what is my route?"* | Returns only Suresh's truck, departure/return time, first drop, cab-wall loading order, and his zero-login Mobile Driver Portal link. |
| **Architect / New User** | *"How do I use FleetFlow and how are BigQuery and Cloud Storage used?"* | Calls `get_architecture_and_howto` to return the complete user guide, GCP service breakdown, and deployment commands. |

---

## ⚙️ Portable Configuration & Local Development

This repository contains **zero hardcoded project IDs or personal credentials**. All cloud settings resolve automatically from environment variables, a local `.env` file, or your active `gcloud config get-value project`.

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env and set GOOGLE_CLOUD_PROJECT=your-gcp-project-id
```

| Environment Variable | Default | Description |
| :--- | :--- | :--- |
| `GOOGLE_CLOUD_PROJECT` | Active `gcloud` project | Target Google Cloud Project ID |
| `GOOGLE_CLOUD_LOCATION` | `us-central1` | Vertex AI & Cloud Run region |
| `FLEETFLOW_BQ_DATASET` | `fleetflow_demo` | BigQuery dataset name |
| `FLEETFLOW_MEDIA_BUCKET` | `<project>-fleetflow-media` | Cloud Storage bucket for signed 3D MP4s & driver portals |
| `LOADPILOT_MODEL` | `gemini-2.5-flash` | Gemini model used by the ADK agent |
| `LOADPILOT_PUBLISH_MEDIA` | `true` | Set to `false` for fast offline unit tests |

### 2. Run Unit Tests & Local Servers
```bash
# Install dependencies
uv sync --python 3.13

# Run deterministic unit test suite
LOADPILOT_PUBLISH_MEDIA=false uv run pytest tests/unit -q

# Launch the Supply Chain Control Tower & 3D Load Studio Web UI locally
uv run uvicorn app.fast_api_app:app --host 0.0.0.0 --port 8085
# Open http://localhost:8085/

# Or launch the ADK Developer Web UI
uv run adk web --port 8501 .
```

---

## 🚀 Dual-Target Deployment (`./scripts/deploy.sh`)

A single unified deployment script (`./scripts/deploy.sh`) lets you deploy to **Gemini Enterprise**, **Cloud Run Web UI**, or **both**:

```bash
# Interactive selector menu (choose 1: Gemini Enterprise, 2: Cloud Run UI, or 3: Both)
./scripts/deploy.sh

# Option 1: Deploy ONLY the Standalone Control Tower Web UI to Cloud Run
./scripts/deploy.sh --target ui --project YOUR_GCP_PROJECT_ID

# Option 2: Deploy ONLY the Conversational A2UI Agent to Vertex AI Agent Engine + Gemini Enterprise
./scripts/deploy.sh --target gemini-enterprise --project YOUR_GCP_PROJECT_ID

# Option 3: Deploy BOTH surfaces + provision BigQuery (7 tables) & Cloud Storage media bucket
./scripts/deploy.sh --target all --publish-data --project YOUR_GCP_PROJECT_ID
```

### What `./scripts/deploy.sh` Automates
1. Runs the unit test suite (`pytest tests/unit -q`) before touching cloud resources.
2. Optionally seeds the 7 BigQuery tables (`<project>.fleetflow_demo.*`) and GCS media bucket (`--publish-data`).
3. For `--target gemini-enterprise`: provisions the staging/media buckets and runtime service account, updates the existing Vertex AI Agent Engine (`ReasoningEngine`) **in-place** (or creates one on first run), and registers the agent across Gemini Enterprise (`Discovery Engine`) apps.
4. For `--target ui`: builds and deploys the containerized FastAPI Control Tower Web App to Google Cloud Run (`fleetflow-control-tower`) and outputs the live HTTPS URL.
