"""Demo dataset: Mumbai Metropolitan Region, Bhiwandi distribution hub (ABG demo profile).

Geography-agnostic by design: swap GAZETTEER + HUB for any city. Stops are generated
deterministically (seeded) from a gazetteer of real localities with a multi-industry
SKU mix (paints + FMCG led, with apparel / electronics / building materials).
Includes the *baseline* dispatch as it is done today (one truck per sales area).
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

HUBS: dict[str, Hub] = {
    "BHW-DC": Hub("BHW-DC", "Bhiwandi Regional DC", 19.2813, 73.0483,
                  "Mankoli Naka, Bhiwandi, Thane 421302"),
    "TLJ-DC": Hub("TLJ-DC", "Taloja Satellite DC", 19.0640, 73.1180,
                  "MIDC Taloja, Navi Mumbai 410208"),
}
DEFAULT_HUB_ID = "BHW-DC"

# locality -> (lat, lon, sales_area). Sales area = how dispatch is split *today*.
GAZETTEER: dict[str, tuple[float, float, str]] = {
    # North-West
    "Vasai": (19.3919, 72.8397, "Vasai-Virar"), "Virar": (19.4559, 72.8111, "Vasai-Virar"),
    "Nalasopara": (19.4180, 72.8190, "Vasai-Virar"), "Palghar": (19.6970, 72.7650, "Vasai-Virar"),
    "Boisar": (19.8000, 72.7550, "Vasai-Virar"),
    # West
    "Bhayandar": (19.3010, 72.8510, "Western Suburbs"), "Mira Road": (19.2813, 72.8721, "Western Suburbs"),
    "Borivali": (19.2307, 72.8567, "Western Suburbs"), "Kandivali": (19.2045, 72.8519, "Western Suburbs"),
    "Malad": (19.1860, 72.8485, "Western Suburbs"), "Goregaon": (19.1663, 72.8526, "Western Suburbs"),
    "Andheri": (19.1197, 72.8468, "Western Suburbs"),
    # South-West (city + eastern suburbs)
    "Powai": (19.1176, 72.9060, "Eastern Suburbs"), "Ghatkopar": (19.0860, 72.9081, "Eastern Suburbs"),
    "Kurla": (19.0726, 72.8845, "Eastern Suburbs"), "Chembur": (19.0522, 72.9005, "Eastern Suburbs"),
    "Mulund": (19.1726, 72.9565, "Eastern Suburbs"), "Bhandup": (19.1440, 72.9370, "Eastern Suburbs"),
    "Bandra": (19.0596, 72.8295, "Mumbai City"), "Dadar": (19.0178, 72.8478, "Mumbai City"),
    "Worli": (19.0176, 72.8162, "Mumbai City"), "Colaba": (18.9067, 72.8147, "Mumbai City"),
    # South (Thane + Navi Mumbai)
    "Thane West": (19.2183, 72.9781, "Thane"), "Ghodbunder Road": (19.2600, 72.9700, "Thane"),
    "Kalwa": (19.2000, 72.9990, "Thane"), "Mumbra": (19.1760, 73.0220, "Thane"),
    "Airoli": (19.1590, 72.9986, "Navi Mumbai"), "Vashi": (19.0771, 72.9986, "Navi Mumbai"),
    "Nerul": (19.0330, 73.0297, "Navi Mumbai"), "Belapur": (19.0213, 73.0390, "Navi Mumbai"),
    "Kharghar": (19.0470, 73.0699, "Navi Mumbai"), "Panvel": (18.9894, 73.1175, "Navi Mumbai"),
    "Kamothe": (19.0183, 73.0960, "Navi Mumbai"), "Ulwe": (18.9700, 73.0250, "Navi Mumbai"),
    # East / South-East
    "Kalyan": (19.2437, 73.1355, "Kalyan-Dombivli"), "Dombivli": (19.2183, 73.0867, "Kalyan-Dombivli"),
    "Ulhasnagar": (19.2215, 73.1645, "Kalyan-Dombivli"), "Ambernath": (19.2090, 73.1860, "Ambernath-Badlapur"),
    "Badlapur": (19.1550, 73.2650, "Ambernath-Badlapur"), "Titwala": (19.2950, 73.2030, "Kalyan-Dombivli"),
    "Neral": (19.0270, 73.3180, "Ambernath-Badlapur"), "Karjat": (18.9107, 73.3236, "Ambernath-Badlapur"),
    # North / North-East
    "Shahapur": (19.4520, 73.3280, "Rural North"), "Padgha": (19.3650, 73.1870, "Rural North"),
    "Murbad": (19.2530, 73.3930, "Rural North"), "Wada": (19.6530, 73.1330, "Rural North"),
    "Vajreshwari": (19.4860, 73.0340, "Rural North"), "Bhiwandi City": (19.2967, 73.0631, "Rural North"),
    "Anjur Phata": (19.2640, 73.0170, "Thane"),
}

_OUTLET_PREFIX = ["Shree Ganesh", "Om Sai", "Jai Ambe", "New India", "Mahalaxmi", "Royal",
                  "Balaji", "Siddhivinayak", "Krishna", "Metro", "Sunrise", "Patel",
                  "Gurukrupa", "Navkar", "Star", "Classic", "Trimurti", "Vighnaharta"]
_OUTLET_SUFFIX = {"paints": ["Paints", "Colour House", "Hardware & Paints"],
                  "fmcg": ["Supermart", "Kirana Stores", "Provision Mart"],
                  "apparel": ["Fashions", "Garments"],
                  "electronics": ["Electronics", "Digital World"],
                  "cement": ["Building Materials", "Traders"]}

# Stops per locality in the demo (weighted toward dense demand areas).
_LOCALITY_STOPS: dict[str, int] = {
    "Vasai": 2, "Virar": 2, "Nalasopara": 1, "Palghar": 1, "Boisar": 1, "Bhayandar": 1,
    "Mira Road": 2, "Borivali": 2, "Kandivali": 1, "Malad": 2, "Goregaon": 1, "Andheri": 2,
    "Powai": 1, "Ghatkopar": 2, "Kurla": 1, "Chembur": 1, "Mulund": 2, "Bhandup": 1,
    "Bandra": 1, "Dadar": 2, "Worli": 1, "Colaba": 1, "Thane West": 3, "Ghodbunder Road": 2,
    "Kalwa": 1, "Mumbra": 1, "Airoli": 1, "Vashi": 2, "Nerul": 1, "Belapur": 1,
    "Kharghar": 2, "Panvel": 2, "Kamothe": 1, "Ulwe": 1, "Kalyan": 3, "Dombivli": 2,
    "Ulhasnagar": 2, "Ambernath": 1, "Badlapur": 2, "Titwala": 1, "Neral": 1, "Karjat": 1,
    "Shahapur": 1, "Padgha": 1, "Murbad": 1, "Wada": 1, "Vajreshwari": 1,
    "Bhiwandi City": 2, "Anjur Phata": 1,
}

# Baseline (today): each sales area gets its own truck, picked by the area supervisor.
BASELINE_AREA_TRUCKS: dict[str, str] = {
    "Vasai-Virar": "T17", "Western Suburbs": "T17", "Eastern Suburbs": "T14",
    "Mumbai City": "T14", "Thane": "T14", "Navi Mumbai": "T17",
    "Kalyan-Dombivli": "T20", "Ambernath-Badlapur": "PKP", "Rural North": "T20",
}
# Areas whose demand the supervisor splits across two vehicles today.
BASELINE_SPLIT_AREAS: dict[str, str] = {"Western Suburbs": "PKP"}


def _jitter(name: str, idx: int) -> tuple[float, float]:
    h = hashlib.md5(f"{name}-{idx}".encode()).digest()
    return ((h[0] - 128) / 128 * 0.012, (h[1] - 128) / 128 * 0.012)


def geocode_locality(text: str) -> tuple[float, float, str] | None:
    """Offline gazetteer lookup (case-insensitive substring match on locality names)."""
    t = (text or "").lower()
    best: tuple[int, str] | None = None
    for name in GAZETTEER:
        if name.lower() in t and (best is None or len(name) > best[0]):
            best = (len(name), name)
    if best is None:
        return None
    return GAZETTEER[best[1]]


def _pick_industry(rng: random.Random) -> str:
    return rng.choices(["paints", "fmcg", "apparel", "electronics", "cement"],
                       weights=[45, 35, 8, 6, 6])[0]


def make_boxes_for_stop(stop_id: str, industry: str, n_boxes: int, rng: random.Random,
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


def build_demo_stops(seed: int = 42) -> list[Stop]:
    """Generate the deterministic demo order book (~75 stops, ~1,400 cartons)."""
    rng = random.Random(seed)
    stops: list[Stop] = []
    n = 0
    for loc, count in _LOCALITY_STOPS.items():
        lat, lon, area = GAZETTEER[loc]
        for k in range(count):
            n += 1
            sid = f"S{n:03d}"
            industry = _pick_industry(rng)
            name = f"{rng.choice(_OUTLET_PREFIX)} {rng.choice(_OUTLET_SUFFIX[industry])}"
            dlat, dlon = _jitter(loc, k)
            n_boxes = rng.randint(10, 26)
            # ~20% of outlets have a morning receiving window
            if rng.random() < 0.2:
                ws, we = 8 * 60, 13 * 60
            else:
                ws, we = 9 * 60, 19 * 60
            stops.append(Stop(
                stop_id=sid, name=name, address=f"{name}, {loc}", lat=round(lat + dlat, 5),
                lon=round(lon + dlon, 5), window_start_min=ws, window_end_min=we,
                boxes=tuple(make_boxes_for_stop(sid, industry, n_boxes, rng)), area=area,
            ))
    return stops


def baseline_assignment(stops: list[Stop]) -> dict[str, list[Stop]]:
    """Today's manual plan: one truck per sales area (+ a split vehicle in the busiest area)."""
    groups: dict[str, list[Stop]] = {}
    for s in stops:
        groups.setdefault(s.area, []).append(s)
    plan: dict[str, list[Stop]] = {}
    for area, members in groups.items():
        code = BASELINE_AREA_TRUCKS.get(area, "T14")
        if area in BASELINE_SPLIT_AREAS:
            half = len(members) // 2
            plan[f"{area}|{code}"] = members[:half]
            plan[f"{area}|{BASELINE_SPLIT_AREAS[area]}"] = members[half:]
        else:
            plan[f"{area}|{code}"] = members
    return plan
