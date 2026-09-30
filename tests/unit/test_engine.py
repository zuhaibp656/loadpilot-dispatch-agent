"""Engine tests: LIFO packer, VRP/dispatch, corridors, QR codec, parsers."""

import random

import pytest

from app.capture.sources import decode_qr_payload, encode_qr_payload
from app.contracts import PlanningParams
from app.data.demo_mmr import HUBS, build_demo_stops
from app.data.master_data import TRUCK_CATALOGUE
from app.integration.tools import parse_claims, parse_truck_counts
from app.optim.corridors import normalize_corridor
from app.optim.dispatch import plan_dispatch
from app.optim.lifo_packer import pack_truck_lifo, verify_geometry, verify_lifo_accessibility


@pytest.fixture(scope="module")
def stops():
    return build_demo_stops(seed=42)


@pytest.fixture(scope="module")
def plan(stops):
    return plan_dispatch(HUBS["BHW-DC"], stops, PlanningParams(dispatch_date="2026-10-01",
                                                               hub_id="BHW-DC"))


@pytest.mark.parametrize("seed", [1, 7, 42])
@pytest.mark.parametrize("code", ["T14", "T17", "T20"])
def test_packer_lifo_and_geometry(stops, seed, code):
    rng = random.Random(seed)
    ordered = rng.sample(stops, 8)
    truck = TRUCK_CATALOGUE[code]
    lp = pack_truck_lifo(f"{code}-X", truck, ordered)
    assert verify_geometry(lp)
    assert verify_lifo_accessibility(lp.placed)
    placed = {p.box.box_id for p in lp.placed}
    assert len(placed) == len(lp.placed)
    for p in lp.placed:
        assert p.x >= -1e-6 and p.x2 <= truck.inner_l_cm + 1e-6
        assert p.z2 <= truck.inner_h_cm + 1e-6


def test_first_delivery_nearest_door(stops):
    ordered = stops[:6]
    lp = pack_truck_lifo("T17-X", TRUCK_CATALOGUE["T17"], ordered)
    if lp.unplaced:
        pytest.skip("overflow case")
    zones = {z.stop_seq: z for z in lp.zones}
    assert zones[1].x_end >= zones[max(zones)].x_end


def test_plan_beats_baseline(plan):
    assert plan.optimized.cost_total < plan.baseline.cost_total
    assert plan.optimized.trucks <= plan.baseline.trucks
    assert not plan.unassigned
    assert all(lp.lifo_ok and not lp.unplaced for lp in plan.loads.values())
    served = sum(len(r.stops) for r in plan.routes)
    assert served == 70


def test_claim_pins_corridor(stops):
    p = PlanningParams(dispatch_date="2026-10-01", hub_id="BHW-DC", corridor_claims={"Ravi": "W"})
    plan = plan_dispatch(HUBS["BHW-DC"], stops, p)
    ravi = [r for r in plan.routes if r.driver == "Ravi"]
    assert ravi and ravi[0].claimed and ravi[0].corridor in ("W", "SW", "NW")


def test_qr_roundtrip(stops):
    b = stops[0].boxes[0]
    b2 = decode_qr_payload(encode_qr_payload(b))
    assert b2 and b2.box_id == b.box_id and b2.stop_id == b.stop_id and b2.weight_kg == b.weight_kg
    assert decode_qr_payload("garbage") is None


def test_parsers():
    assert parse_truck_counts("T17=3, T14:2, ACE 1, 2 x T20") == {"T17": 3, "T14": 2, "ACE": 1, "T20": 2}
    assert parse_claims("Ravi=West; Imran: North-East") == {"Ravi": "W", "Imran": "NE"}
    assert normalize_corridor("west") == "W"
    assert normalize_corridor("north east") == "NE"
