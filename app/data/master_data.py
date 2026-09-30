"""Master data: truck catalogue, cost sheet, and cross-industry carton catalogue.

These are the *data-driven* inputs of the cost model. Every value here can be
overridden per plan (wizard form / chat) or replaced by an uploaded fleet sheet.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from app.contracts import CostProfile, TruckType
except ImportError:  # pragma: no cover
    from contracts import CostProfile, TruckType


# ------------------------------------------------------------------------------
# Truck catalogue (Indian standard bodies, internal cargo dims in cm)
# ------------------------------------------------------------------------------
TRUCK_CATALOGUE: dict[str, TruckType] = {
    t.code: t
    for t in [
        TruckType("ACE", "Mini Truck 7 ft (Tata Ace class)", 210, 145, 125, 750,
                  700, 3.5, 17.0, 23, "#34a853"),
        TruckType("PKP", "Pickup 8.5 ft (Dost / Bolero class)", 260, 165, 160, 1500,
                  950, 4.2, 14.0, 24, "#fbbc04"),
        TruckType("T14", "14 ft LCV (Eicher Pro 2049 class)", 425, 200, 200, 3500,
                  1800, 6.0, 9.0, 25, "#4285f4"),
        TruckType("T17", "17 ft ICV (Tata 1109 class)", 520, 215, 215, 5000,
                  2300, 7.2, 7.5, 25, "#a142f4"),
        TruckType("T20", "20 ft Container (Tata 1512 class)", 610, 240, 240, 7000,
                  2900, 8.5, 6.0, 24, "#ea4335"),
    ]
}

# Fleet available at the hub today (type -> count); editable in the wizard.
DEFAULT_FLEET_AVAILABLE: dict[str, int] = {"ACE": 2, "PKP": 2, "T14": 3, "T17": 3, "T20": 2}

DEFAULT_DRIVERS: list[str] = [
    "Ravi", "Sanjay", "Imran", "Deepak", "Arjun", "Manoj", "Farhan", "Suresh",
    "Vikram", "Naveen", "Prakash", "Kiran",
]

CORRIDOR_NAMES: dict[str, str] = {
    "N": "North (Wada / Vajreshwari)",
    "NE": "North-East (Shahapur / Padgha)",
    "E": "East (Kalyan / Ambernath / Badlapur)",
    "SE": "South-East (Dombivli / Karjat)",
    "S": "South (Thane / Navi Mumbai / Panvel)",
    "SW": "South-West (Mumbai City / Eastern Suburbs)",
    "W": "West (Mira-Bhayandar / Western Suburbs)",
    "NW": "North-West (Vasai / Virar / Palghar)",
}

DEFAULT_COST_PROFILE = CostProfile(
    fuel_price_per_litre=92.0,
    driver_day_cost=1100.0,
    helper_day_cost=700.0,
    overtime_per_hour=180.0,
    shift_hours=10.0,
    toll_by_corridor={"N": 0, "NE": 120, "E": 0, "SE": 60, "S": 145, "SW": 240, "W": 85, "NW": 95},
)


# ------------------------------------------------------------------------------
# Cross-industry carton catalogue (SKU master)
# ------------------------------------------------------------------------------
@dataclass(frozen=True)
class Sku:
    sku: str
    description: str
    l_cm: float
    w_cm: float
    h_cm: float
    weight_kg: float
    fragile: bool
    this_side_up: bool
    category: str
    industry: str


SKU_MASTER: dict[str, Sku] = {
    s.sku: s
    for s in [
        # Paints & coatings
        Sku("PNT-EMU-20L", "Interior emulsion 20 L pail carton", 34, 34, 38, 24.0, False, True,
            "paints", "paints"),
        Sku("PNT-EXT-10L", "Exterior emulsion 10 L pail carton", 28, 28, 31, 13.0, False, True,
            "paints", "paints"),
        Sku("PNT-ENM-4x4L", "Enamel 4 L tins (case of 4)", 36, 36, 24, 18.5, False, True,
            "paints", "paints"),
        Sku("PNT-PRM-12x1L", "Primer 1 L tins (case of 12)", 40, 30, 19, 15.0, False, True,
            "paints", "paints"),
        Sku("PNT-PTY-20KG", "Wall putty 20 kg carton", 50, 34, 16, 20.5, False, False,
            "paints", "paints"),
        Sku("PNT-TNT-48", "Tinter bottles (case of 48)", 32, 24, 22, 9.5, True, True,
            "paints", "paints"),
        # FMCG / CPG
        Sku("FMC-DET-24", "Detergent 1 kg packs (carton of 24)", 46, 32, 30, 25.0, False, False,
            "fmcg", "fmcg"),
        Sku("FMC-BIS-96", "Biscuits (carton of 96)", 44, 30, 28, 7.5, False, False,
            "fmcg", "fmcg"),
        Sku("FMC-SHM-36", "Shampoo 340 ml (carton of 36)", 38, 26, 24, 13.5, False, True,
            "fmcg", "fmcg"),
        Sku("FMC-OIL-15L", "Edible oil 15 L tin", 25, 25, 35, 15.5, False, True,
            "fmcg", "fmcg"),
        Sku("FMC-JAR-24", "Glass jar spreads (carton of 24)", 32, 30, 20, 11.0, True, True,
            "fmcg", "fmcg"),
        Sku("FMC-BEV-24", "Beverage PET 600 ml (tray of 24)", 40, 27, 24, 15.0, False, True,
            "fmcg", "fmcg"),
        # Apparel & footwear retail
        Sku("APP-GAR-40", "Folded garments (master carton)", 60, 40, 40, 11.0, False, False,
            "apparel", "apparel"),
        Sku("APP-SHO-12", "Footwear (carton of 12 pairs)", 52, 36, 30, 9.0, False, False,
            "apparel", "apparel"),
        # Consumer electronics
        Sku("ELC-TV-43", "43-inch LED TV", 105, 16, 66, 12.0, True, True,
            "electronics", "electronics"),
        Sku("ELC-MXR-4", "Mixer grinders (carton of 4)", 48, 40, 34, 16.0, True, True,
            "electronics", "electronics"),
        # Building materials
        Sku("BLD-CEM-50", "Cement 50 kg bag (palletised)", 60, 40, 14, 50.0, False, False,
            "building", "cement"),
        Sku("BLD-TIL-4", "Floor tiles 600x600 (box of 4)", 62, 62, 9, 28.0, True, False,
            "building", "cement"),
    ]
}

# Industry profile -> weighted SKU mix used by the demo generator.
INDUSTRY_PROFILES: dict[str, dict[str, float]] = {
    "paints": {"PNT-EMU-20L": 4, "PNT-EXT-10L": 3, "PNT-ENM-4x4L": 2, "PNT-PRM-12x1L": 2,
               "PNT-PTY-20KG": 2, "PNT-TNT-48": 1},
    "fmcg": {"FMC-DET-24": 3, "FMC-BIS-96": 3, "FMC-SHM-36": 2, "FMC-OIL-15L": 2,
             "FMC-JAR-24": 1, "FMC-BEV-24": 2},
    "apparel": {"APP-GAR-40": 3, "APP-SHO-12": 2},
    "electronics": {"ELC-TV-43": 1, "ELC-MXR-4": 2},
    "cement": {"BLD-CEM-50": 3, "BLD-TIL-4": 2},
}
