"""Extended demo tables are consistent with build_demo_stops (offline) + live BigQuery check."""

from __future__ import annotations

import os

import pytest

from app.capture.sources import decode_qr_payload
from app.data.bq_source import rows_to_stops
from app.data.demo_extended import DRIVER_RUNS, SCHEMAS, build_tables, driver_run_stats
from app.data.demo_mmr import build_demo_stops
from app.data.master_data import DEFAULT_DRIVERS, DEFAULT_FLEET_AVAILABLE, SKU_MASTER, TRUCK_CATALOGUE
from app.optim.corridors import corridor_of
from app.data.demo_mmr import DEFAULT_HUB_ID, HUBS

STOPS = build_demo_stops(seed=42)
TABLES = build_tables(dispatch_date="2026-09-30")


def test_tables_match_schemas():
    assert set(TABLES) == set(SCHEMAS)
    for name, rows in TABLES.items():
        assert rows, name
        fields = [f for f, _, _ in SCHEMAS[name][1]]
        for r in rows:
            assert list(r) == fields, name


def test_stores_orders_cartons_consistent():
    by_id = {s.stop_id: s for s in STOPS}
    assert [r["stop_id"] for r in TABLES["stores"]] == [s.stop_id for s in STOPS]
    assert len(TABLES["orders"]) == len(STOPS)
    assert len(TABLES["cartons"]) == sum(len(s.boxes) for s in STOPS)
    for o in TABLES["orders"]:
        s = by_id[o["stop_id"]]
        assert o["cartons"] == len(s.boxes)
        assert o["weight_kg"] == pytest.approx(s.weight_kg, abs=0.05)
        assert o["volume_m3"] == pytest.approx(s.volume_m3, abs=0.001)
        assert o["value_inr"] > 0
    for c in TABLES["cartons"]:
        b = decode_qr_payload(c["qr_payload"])
        assert b is not None and b.box_id == c["box_id"] and b.stop_id == c["stop_id"]
        assert c["sku"] in SKU_MASTER


def test_rows_to_stops_roundtrip_equals_build_demo_stops():
    stores = {r["stop_id"]: r for r in TABLES["stores"]}
    joined = [{**stores[c["stop_id"]], **c} for c in TABLES["cartons"]]
    joined.sort(key=lambda r: (r["stop_id"], r["box_id"]))
    assert rows_to_stops(joined) == STOPS


def test_master_tables():
    assert {d["name"] for d in TABLES["drivers"]} == set(DEFAULT_DRIVERS)
    assert all(d["phone"].startswith("+91-9") for d in TABLES["drivers"])
    assert len(TABLES["fleet"]) == sum(DEFAULT_FLEET_AVAILABLE.values())
    assert {t["truck_code"] for t in TABLES["truck_types"]} == set(TRUCK_CATALOGUE)
    assert sum(b["stops"] for b in TABLES["baseline"]) == len(STOPS)


def test_driver_runs_fit_and_match_corridor():
    hub = HUBS[DEFAULT_HUB_ID]
    by_id = {s.stop_id: s for s in STOPS}
    assert len(DRIVER_RUNS) == 3
    for run in DRIVER_RUNS:
        assert 6 <= len(run["stop_ids"]) <= 9
        assert run["driver"] in DEFAULT_DRIVERS and run["truck_code"] in TRUCK_CATALOGUE
        assert driver_run_stats(run, STOPS)["fits"], run["run_id"]
        corrs = {corridor_of(hub, by_id[s]) for s in run["stop_ids"]}
        assert run["corridor"] in corrs
        for f in run["photos"] + [run["order_file"]]:
            assert os.path.exists(os.path.join("app", "data", "samples", f)), f


@pytest.mark.skipif(os.environ.get("LOADPILOT_LIVE_BQ") != "1", reason="set LOADPILOT_LIVE_BQ=1 to hit BigQuery")
def test_live_bigquery_matches_demo():
    from app.data.bq_source import load_stops_from_bigquery

    assert load_stops_from_bigquery() == STOPS
    run = DRIVER_RUNS[0]
    sub = load_stops_from_bigquery(stop_ids=run["stop_ids"])
    assert [s.stop_id for s in sub] == sorted(run["stop_ids"])
