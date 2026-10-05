"""Unit tests for the FleetFlow Supply Chain Control Tower & 3D Load Studio Web API & UI."""

from __future__ import annotations

import os

os.environ["LOADPILOT_PUBLISH_MEDIA"] = "false"

from fastapi.testclient import TestClient

from app.fast_api_app import app

client = TestClient(app)


def test_control_tower_root_and_ui_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "FleetFlow Control Tower" in r.text
    assert "mountFleetFlowEngine" in r.text

    r_ui = client.get("/control-tower")
    assert r_ui.status_code == 200
    assert "3D Load Studio" in r_ui.text

    r_health = client.get("/healthz")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"


def test_api_meta_and_initial_plan():
    r = client.get("/api/meta")
    assert r.status_code == 200
    data = r.json()
    assert len(data["cities"]) >= 2
    assert len(data["truck_types"]) == 5
    assert len(data["skus"]) >= 10
    assert len(data["gcp_services"]) >= 6
    assert "initial_plan" in data
    assert data["initial_plan"]["kpi"]["optimized_trucks"] >= 1
    assert "anim_data" in data["initial_plan"]


def test_api_plan_scoping_1_3_all():
    # Scope to 1 truck
    r1 = client.post("/api/plan", json={"scope": "1"})
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["active_trucks"] is not None
    assert len(b1["active_trucks"]) == 1
    assert sum(1 for rt in b1["routes"] if rt["active"]) == 1

    # Scope to 3 trucks
    r3 = client.post("/api/plan", json={"scope": "3"})
    assert r3.status_code == 200
    b3 = r3.json()
    assert b3["active_trucks"] is not None
    assert len(b3["active_trucks"]) == 3
    assert sum(1 for rt in b3["routes"] if rt["active"]) == 3

    # Scope to all trucks
    ra = client.post("/api/plan", json={"scope": "all"})
    assert ra.status_code == 200
    ba = ra.json()
    assert ba["active_trucks"] is None
    assert all(rt["active"] for rt in ba["routes"])


def test_api_repack_truck_calculator():
    r = client.post(
        "/api/repack-truck",
        json={
            "source_truck_id": "",
            "target_truck_code": "T14",
            "extra_boxes": [
                {"sku": "PNT-EMU-20L", "qty": 5, "stop_seq": 1},
            ],
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["status"] == "ok"
    assert out["stats"]["truck_code"] == "T14"
    assert out["stats"]["placed_count"] > 0
    assert "boxes" in out["truck_anim"]


def test_api_bigquery_studio_and_agent_chat():
    r_bq = client.post(
        "/api/bigquery/query",
        json={
            "sql": "SELECT corridor, COUNT(*) AS trucks, SUM(stops) AS total_stops FROM `fleetflow_project.fleetflow_demo.routes` GROUP BY corridor",
            "use_live_bq": False,
        },
    )
    assert r_bq.status_code == 200
    bq = r_bq.json()
    assert bq["row_count"] >= 1
    assert "corridor" in bq["columns"]

    r_chat = client.post("/api/agent-chat", json={"prompt": "Only show Ravi"})
    assert r_chat.status_code == 200
    ch = r_chat.json()
    assert "reply" in ch
    assert ch["bundle"]["active_trucks"] is not None
    assert len(ch["bundle"]["active_trucks"]) == 1


def test_api_launchpad_hub_context_and_smaller_truck_overflow():
    # Staged Launchpad readiness: /api/meta?include_plan=false returns null initial_plan
    r_meta = client.get("/api/meta?include_plan=false")
    assert r_meta.status_code == 200
    assert r_meta.json()["initial_plan"] is None

    # Mumbai hub context (BHW-DC) -> Mumbai regional drivers (Ravi, Sanjay...)
    r_mum = client.get("/api/hub-context?hub_id=BHW-DC&order_source=sample_mumbai")
    assert r_mum.status_code == 200
    mum = r_mum.json()
    assert mum["hub"]["id"] == "BHW-DC"
    assert "Ravi" in mum["driver_names"]
    assert mum["total_stops"] >= 15
    assert len(mum["corridor_summary"]) >= 3

    # Bengaluru hub context (BLR-NLG) -> Bengaluru regional drivers (Karthik Gowda, Naveen Reddy...)
    r_blr = client.get("/api/hub-context?hub_id=BLR-NLG&order_source=sample_bengaluru")
    assert r_blr.status_code == 200
    blr = r_blr.json()
    assert blr["hub"]["id"] == "BLR-NLG"
    assert any("Karthik" in d for d in blr["driver_names"])
    assert "Ravi" not in blr["driver_names"]
    assert blr["total_stops"] >= 10

    # Assign Ravi to West (W) with a smaller truck (T14) -> Ravi gets T14 on W, overflow distributed to another truck
    r_plan = client.post(
        "/api/plan",
        json={
            "hub_id": "BHW-DC",
            "order_source": "sample_mumbai",
            "driver_assignments": [
                {"driver": "Ravi", "corridor": "W", "truck_type": "T14"},
            ],
            "scope": "all",
        },
    )
    assert r_plan.status_code == 200
    plan = r_plan.json()
    ravi_routes = [rt for rt in plan["routes"] if rt["driver"] == "Ravi"]
    assert len(ravi_routes) == 1
    assert ravi_routes[0]["truck_code"] == "T14"
    assert "W" in ravi_routes[0]["corridor"]
    # Verify overflow note is recorded when smaller truck T14 cannot fit all 9 West corridor stops
    assert any("Overflow" in n or "T14" in n for n in plan["notes"])


def test_api_upload_manifest_csv():
    csv_text = (
        "store,locality,sku,qty\n"
        "dadar_test_depot,Dadar,PNT-EMU-20L,12\n"
        "bandra_test_depot,Bandra,PNT-PRM-10L,18\n"
    )
    r_up = client.post(
        "/api/upload-manifest",
        json={"filename": "morning_wave.csv", "raw_text": csv_text, "hub_id": "BHW-DC"},
    )
    assert r_up.status_code == 200
    up = r_up.json()
    assert up["status"] == "ok"
    assert up["OrderCount"] == 2
    assert up["TotalCartons"] == 30

