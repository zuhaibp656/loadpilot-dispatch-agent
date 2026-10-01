"""Demo dataset: Bangalore Urban & Rural Metropolitan Region (Nelamangala / Electronic City hubs).

Deterministic generation matching real Bangalore retail corridors (North, South, East, West, Central).
Includes retail, FMCG, paints, apparel, and hardware outlets.
Geography-agnostic format matching demo_mmr.py contracts.
"""

from __future__ import annotations

import hashlib
import random

try:
    from app.contracts import Box, Hub, Stop
    from app.data.master_data import INDUSTRY_PROFILES, SKU_MASTER
except ImportError:  # pragma: no cover
    from contracts import Box, Hub, Stop
    from data.master_data import INDUSTRY_PROFILES, SKU_MASTER

HUBS_BLR: dict[str, Hub] = {
    "BLR-NLG": Hub("BLR-NLG", "Nelamangala Logistics Hub", 13.0980, 77.3910,
                   "NH-48 Logistics Corridor, Nelamangala, Bengaluru 562123"),
    "BLR-EC": Hub("BLR-EC", "Electronic City Hub", 12.8399, 77.6770,
                  "Hosur Road, Electronic City Phase 2, Bengaluru 560100"),
}
DEFAULT_BLR_HUB_ID = "BLR-NLG"

# locality -> (lat, lon, sales_area). Sales area = baseline operational division.
GAZETTEER_BLR: dict[str, tuple[float, float, str]] = {
    # North Corridor (NH-44 / Bellary Rd / Outer Ring Rd)
    "Peenya": (13.0285, 77.5197, "North Bangalore"),
    "Yeshwanthpur": (13.0227, 77.5532, "North Bangalore"),
    "Jalahalli": (13.0487, 77.5458, "North Bangalore"),
    "Vidyaranyapura": (13.0760, 77.5570, "North Bangalore"),
    "Hebbal": (13.0358, 77.5970, "North Bangalore"),
    "Yelahanka": (13.1007, 77.5963, "North Bangalore"),
    "Sahakar Nagar": (13.0620, 77.5890, "North Bangalore"),
    "Devanahalli": (13.2484, 77.7126, "North Bangalore"),

    # West Corridor (Tumkur Rd / Magadi Rd / Mysore Rd)
    "Rajajinagar": (12.9982, 77.5530, "West Bangalore"),
    "Malleshwaram": (13.0031, 77.5643, "West Bangalore"),
    "Vijayanagar": (12.9719, 77.5304, "West Bangalore"),
    "Basaveshwaranagar": (12.9880, 77.5390, "West Bangalore"),
    "Nagarbhavi": (12.9610, 77.5110, "West Bangalore"),
    "Kengeri": (12.9177, 77.4838, "West Bangalore"),

    # Central Corridor (CBD & Core Commercial)
    "Majestic": (12.9767, 77.5713, "Central Bangalore"),
    "Gandhi Nagar": (12.9800, 77.5780, "Central Bangalore"),
    "Shivajinagar": (12.9857, 77.6057, "Central Bangalore"),
    "Commercial Street": (12.9822, 77.6083, "Central Bangalore"),
    "MG Road": (12.9756, 77.6066, "Central Bangalore"),
    "Basavanagudi": (12.9421, 77.5753, "Central Bangalore"),

    # East Corridor (Old Madras Rd / ITPB / Whitefield)
    "Indiranagar": (12.9784, 77.6408, "East Bangalore"),
    "Domlur": (12.9609, 77.6387, "East Bangalore"),
    "KR Puram": (13.0075, 77.6959, "East Bangalore"),
    "Mahadevapura": (12.9917, 77.6874, "East Bangalore"),
    "Marathahalli": (12.9591, 77.6974, "East Bangalore"),
    "Hoodi": (12.9920, 77.7150, "East Bangalore"),
    "Whitefield": (12.9698, 77.7499, "East Bangalore"),
    "Kadugodi": (12.9980, 77.7600, "East Bangalore"),

    # South Corridor (Hosur Rd / Outer Ring Rd / Kanakapura Rd)
    "Koramangala": (12.9352, 77.6245, "South Bangalore"),
    "HSR Layout": (12.9121, 77.6446, "South Bangalore"),
    "BTM Layout": (12.9166, 77.6101, "South Bangalore"),
    "Jayanagar": (12.9308, 77.5838, "South Bangalore"),
    "JP Nagar": (12.9063, 77.5857, "South Bangalore"),
    "Bannerghatta Road": (12.8910, 77.5970, "South Bangalore"),
    "Bellandur": (12.9304, 77.6784, "South Bangalore"),
    "Sarjapur Road": (12.9100, 77.6850, "South Bangalore"),
    "Electronic City": (12.8452, 77.6602, "South Bangalore"),
}

_BLR_OUTLET_PREFIX = [
    "Sri Manjunatha", "Sri Balaji", "Sri Venkateshwara", "Cauvery", "Chamundeshwari",
    "SLV", "Nandi", "Mysore", "Karnataka", "Royal", "Annapurna", "Shanthi",
    "Adithya", "Sapthagiri", "Sai Ram", "Mahalakshmi", "Vinayaka", "Navarathna"
]

_BLR_OUTLET_SUFFIX = {
    "paints": ["Paints & Hardware", "Colour World", "Hardware & Electricals"],
    "fmcg": ["Supermart", "Provisions", "Grand Bazaar"],
    "apparel": ["Garments & Silks", "Fashions", "Textiles"],
    "electronics": ["Digital Hub", "Electronics & Appliances"],
    "cement": ["Building Supplies", "Traders & Steels"],
}

_BLR_LOCALITY_STOPS: dict[str, int] = {
    # North (12 stops)
    "Peenya": 3, "Yeshwanthpur": 2, "Jalahalli": 1, "Vidyaranyapura": 1,
    "Hebbal": 2, "Yelahanka": 2, "Sahakar Nagar": 1,
    # West (10 stops)
    "Rajajinagar": 2, "Malleshwaram": 2, "Vijayanagar": 2,
    "Basaveshwaranagar": 1, "Nagarbhavi": 1, "Kengeri": 2,
    # Central (9 stops)
    "Majestic": 2, "Gandhi Nagar": 1, "Shivajinagar": 2,
    "Commercial Street": 1, "MG Road": 1, "Basavanagudi": 2,
    # East (16 stops)
    "Indiranagar": 2, "Domlur": 1, "KR Puram": 2, "Mahadevapura": 2,
    "Marathahalli": 2, "Hoodi": 2, "Whitefield": 3, "Kadugodi": 2,
    # South (18 stops)
    "Koramangala": 3, "HSR Layout": 2, "BTM Layout": 2, "Jayanagar": 2,
    "JP Nagar": 2, "Bannerghatta Road": 2, "Bellandur": 2, "Sarjapur Road": 2, "Electronic City": 1,
}

BASELINE_BLR_AREA_TRUCKS: dict[str, str] = {
    "North Bangalore": "T14",
    "West Bangalore": "T14",
    "Central Bangalore": "T14",
    "East Bangalore": "T17",
    "South Bangalore": "T17",
}

BASELINE_BLR_SPLIT_AREAS: dict[str, str] = {
    "East Bangalore": "PKP",
    "South Bangalore": "T14",
}

BLR_DEFAULT_DRIVERS = [
    "Ramesh Kumar", "Suresh Nair", "Karthik Gowda", "Venkatesh Rao",
    "Manjunath B", "Anand Swamy", "Prashanth Shetty", "Naveen Reddy",
    "Shivakumar", "Girish M", "Raghavendra", "Deepak Rao",
]


def _jitter_blr(name: str, idx: int) -> tuple[float, float]:
    h = hashlib.md5(f"blr-{name}-{idx}".encode()).digest()
    return ((h[0] - 128) / 128 * 0.012, (h[1] - 128) / 128 * 0.012)


def _pick_blr_industry(rng: random.Random) -> str:
    return rng.choices(["paints", "fmcg", "apparel", "electronics", "cement"],
                       weights=[40, 38, 10, 6, 6])[0]


def make_blr_boxes_for_stop(stop_id: str, industry: str, n_boxes: int, rng: random.Random,
                            start_idx: int = 1) -> list[Box]:
    mix = INDUSTRY_PROFILES[industry]
    skus = list(mix.keys())
    weights = list(mix.values())
    boxes: list[Box] = []
    for i in range(n_boxes):
        s = SKU_MASTER[rng.choices(skus, weights=weights)[0]]
        boxes.append(Box(
            box_id=f"{stop_id}-B{start_idx + i:02d}", stop_id=stop_id, sku=s.sku,
            description=s.description, l_cm=s.l_cm, w_cm=s.w_cm, h_cm=s.h_cm,
            weight_kg=s.weight_kg, fragile=s.fragile, this_side_up=s.this_side_up,
            category=s.category,
        ))
    return boxes


def build_blr_demo_stops(seed: int = 42) -> list[Stop]:
    """Generate deterministic Bangalore retail order book (~65 stops, ~1,300 cartons)."""
    rng = random.Random(seed)
    stops: list[Stop] = []
    n = 0
    for loc, count in _BLR_LOCALITY_STOPS.items():
        if loc not in GAZETTEER_BLR:
            continue
        lat, lon, area = GAZETTEER_BLR[loc]
        for k in range(count):
            n += 1
            sid = f"BLR-S{n:03d}"
            industry = _pick_blr_industry(rng)
            name = f"{rng.choice(_BLR_OUTLET_PREFIX)} {rng.choice(_BLR_OUTLET_SUFFIX[industry])}"
            dlat, dlon = _jitter_blr(loc, k)
            n_boxes = rng.randint(10, 26)
            if rng.random() < 0.25:
                ws, we = 8 * 60, 13 * 60
            else:
                ws, we = 9 * 60, 19 * 60
            stops.append(Stop(
                stop_id=sid, name=name, address=f"{name}, {loc}, Bengaluru",
                lat=round(lat + dlat, 5), lon=round(lon + dlon, 5),
                window_start_min=ws, window_end_min=we,
                boxes=tuple(make_blr_boxes_for_stop(sid, industry, n_boxes, rng)),
                area=area,
            ))
    return stops


def baseline_blr_assignment(stops: list[Stop]) -> dict[str, list[Stop]]:
    """Today's manual Bangalore distribution plan: one truck per sales area (+ split for busy areas)."""
    groups: dict[str, list[Stop]] = {}
    for s in stops:
        groups.setdefault(s.area, []).append(s)
    plan: dict[str, list[Stop]] = {}
    for area, members in groups.items():
        code = BASELINE_BLR_AREA_TRUCKS.get(area, "T14")
        if area in BASELINE_BLR_SPLIT_AREAS:
            half = len(members) // 2
            plan[f"{area}|{code}"] = members[:half]
            plan[f"{area}|{BASELINE_BLR_SPLIT_AREAS[area]}"] = members[half:]
        else:
            plan[f"{area}|{code}"] = members
    return plan
