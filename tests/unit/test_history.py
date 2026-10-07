"""Unit tests for FleetFlow history, audit trail, and reporting."""

import pytest
from fastapi.testclient import TestClient

from app.data.history import (
    generate_dispatch_manifest_csv,
    generate_dispatch_report_html,
    get_history_analytics,
    get_history_detail,
    get_history_list,
    record_dispatch_run,
)
from app.fast_api_app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_history_list_and_analytics():
    runs = get_history_list(limit=10)
    assert len(runs) >= 1
    sample = runs[0]
    assert "plan_id" in sample
    assert "audit_hash" in sample

    analytics = get_history_analytics()
    assert analytics["total_dispatches"] >= 1
    assert analytics["total_savings_inr"] > 0
    assert analytics["total_trucks_eliminated"] >= 0


def test_manifest_and_report_generation():
    runs = get_history_list(limit=1)
    plan_id = runs[0]["plan_id"]
    detail = get_history_detail(plan_id)
    assert detail is not None

    csv_text = generate_dispatch_manifest_csv(detail)
    assert "dispatch_id" in csv_text
    assert "outlet_name" in csv_text

    html_text = generate_dispatch_report_html(detail)
    assert "Executive Dispatch Report & Audit Certificate" in html_text
    assert "FLEETFLOW" in html_text or "Cryptographic Audit" in html_text


def test_api_history_endpoints(client):
    res = client.get("/api/history")
    assert res.status_code == 200
    runs = res.json()
    assert isinstance(runs, list)
    assert len(runs) >= 1

    plan_id = runs[0]["plan_id"]

    res_an = client.get("/api/history/analytics")
    assert res_an.status_code == 200
    assert res_an.json()["total_dispatches"] >= 1

    res_det = client.get(f"/api/history/{plan_id}")
    assert res_det.status_code == 200

    res_rep = client.get(f"/api/history/{plan_id}/report")
    assert res_rep.status_code == 200
    assert "text/html" in res_rep.headers["content-type"]

    res_man = client.get(f"/api/history/{plan_id}/manifest.csv")
    assert res_man.status_code == 200
    assert "text/csv" in res_man.headers["content-type"]

    res_rest = client.post(f"/api/history/{plan_id}/restore")
    assert res_rest.status_code == 200
    assert res_rest.json()["plan_id"] == plan_id
