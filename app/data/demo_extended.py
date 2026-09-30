"""Extended, customer-showable demo tables derived from the deterministic MMR demo.

Everything here is *derived* from `build_demo_stops(seed=42)` + master data, so the order
book / plan numbers never change. Adds the "enterprise master data" a customer expects to
see (drivers, outlet master, orders, cartons with QR payloads, fleet, costs, baseline) plus
3 ready-made single-driver scenarios (`DRIVER_RUNS`) for the driver-perspective demo.

`build_tables()` returns {table_name: list[row dict]}; `SCHEMAS` gives the BigQuery schema
(name, type, description) for each table. Used by scripts/publish_demo_data.py and
scripts/build_demo_data_page.py; `app/data/bq_source.py` reads stores + cartons back.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
from collections import Counter

try:
    from app.capture.sources import encode_qr_payload
    from app.contracts import Stop
    from app.data.demo_mmr import (BASELINE_AREA_TRUCKS, BASELINE_SPLIT_AREAS, DEFAULT_HUB_ID,
                                   GAZETTEER, HUBS, _LOCALITY_STOPS, baseline_assignment,
                                   build_demo_stops)
    from app.data.master_data import (CORRIDOR_NAMES, DEFAULT_COST_PROFILE, DEFAULT_DRIVERS,
                                      DEFAULT_FLEET_AVAILABLE, SKU_MASTER, TRUCK_CATALOGUE)
    from app.optim.corridors import corridor_of
except ImportError:  # pragma: no cover
    from capture.sources import encode_qr_payload
    from contracts import Stop
    from data.demo_mmr import (BASELINE_AREA_TRUCKS, BASELINE_SPLIT_AREAS, DEFAULT_HUB_ID,
                               GAZETTEER, HUBS, _LOCALITY_STOPS, baseline_assignment,
                               build_demo_stops)
    from data.master_data import (CORRIDOR_NAMES, DEFAULT_COST_PROFILE, DEFAULT_DRIVERS,
                                  DEFAULT_FLEET_AVAILABLE, SKU_MASTER, TRUCK_CATALOGUE)
    from optim.corridors import corridor_of

DEMO_SEED = 42
USABLE_VOLUME_SHARE = 0.8  # practical cube utilisation used when sizing a single-driver run

# Indicative distributor price per carton (INR) — used for order value estimates only.
SKU_PRICE_INR: dict[str, float] = {
    "PNT-EMU-20L": 5200, "PNT-EXT-10L": 3900, "PNT-ENM-4x4L": 3400, "PNT-PRM-12x1L": 2900,
    "PNT-PTY-20KG": 850, "PNT-TNT-48": 4300,
    "FMC-DET-24": 2600, "FMC-BIS-96": 1450, "FMC-SHM-36": 5400, "FMC-OIL-15L": 2350,
    "FMC-JAR-24": 4100, "FMC-BEV-24": 720,
    "APP-GAR-40": 14000, "APP-SHO-12": 9600,
    "ELC-TV-43": 24500, "ELC-MXR-4": 11200,
    "BLD-CEM-50": 420, "BLD-TIL-4": 1650,
}

# Driver profiles (every name in DEFAULT_DRIVERS). corridor codes as in CORRIDOR_NAMES.
_DRIVER_PROFILE: dict[str, tuple[str, int, str]] = {  # name -> (home corridor, years, truck)
    "Ravi": ("W", 11, "T17"), "Sanjay": ("SW", 8, "T14"), "Imran": ("S", 9, "PKP"),
    "Deepak": ("E", 6, "T20"), "Arjun": ("NW", 5, "T17"), "Manoj": ("SE", 12, "T20"),
    "Farhan": ("SW", 4, "PKP"), "Suresh": ("N", 7, "T14"), "Vikram": ("NE", 14, "T20"),
    "Naveen": ("S", 3, "ACE"), "Prakash": ("E", 10, "T14"), "Kiran": ("W", 2, "ACE"),
}
_SURNAMES = ["Patil", "Yadav", "Shaikh", "Pawar", "Jadhav", "More", "Khan", "Gaikwad",
             "Singh", "Nair", "Shinde", "Kamble"]
_CONTACT_FIRST = ["Rajesh", "Anil", "Sunil", "Mahesh", "Ramesh", "Vijay", "Ashok", "Nitin",
                  "Santosh", "Ganesh", "Prashant", "Rahul", "Amit", "Sachin", "Mukesh", "Dinesh"]
_CONTACT_LAST = ["Shah", "Patel", "Mehta", "Jain", "Gupta", "Desai", "Kulkarni", "Joshi",
                 "Agarwal", "Chavan", "Naik", "Sawant"]
_STREETS = ["Station Road", "Link Road", "Market Yard", "Main Bazaar", "SV Road", "LBS Marg",
            "Old Agra Road", "MG Road", "Gokhale Road", "Tilak Chowk", "Sector 17", "Naka Road"]


def _run(run_id: str, driver: str, truck: str, corridor: str, label: str, stop_ids: list[str]) -> dict:
    photos = [f"driver_{run_id}_cartons_a.jpg", f"driver_{run_id}_cartons_b.jpg"]
    return {"run_id": run_id, "driver": driver, "truck_code": truck, "corridor": corridor,
            "label": label, "stop_ids": stop_ids, "photo": photos[0], "photos": photos,
            "order_file": f"driver_{run_id}_orders.txt"}


# Ready-made single-driver scenarios (driver perspective demo). Every stop's compass corridor
# from Bhiwandi DC (`corridor_of`) matches the run corridor (Suresh: N + NE), and cartons fit
# the truck (<= 80% cube, <= payload). ACE (750 kg) cannot carry 6+ outlets of this order
# book, so the smallest run uses a PKP.
DRIVER_RUNS: list[dict] = [
    _run("suresh_t14_north", "Suresh", "T14", "N",
         "Suresh · T14 (Eicher 2049) · North: Bhiwandi / Vajreshwari / Wada / Padgha / Shahapur",
         ["S068", "S069", "S067", "S066", "S064", "S063"]),
    _run("ravi_t17_west", "Ravi", "T17", "W",
         "Ravi · T17 (Tata 1109) · West: Anjur Phata / Ghodbunder / Mira Road / Bhayandar / Borivali",
         ["S070", "S035", "S036", "S009", "S010", "S008", "S011", "S012"]),
    _run("imran_pkp_south", "Imran", "PKP", "S",
         "Imran · PKP (Bolero Pickup) · South: Mumbra / Airoli / Vashi / Kharghar",
         ["S038", "S039", "S040", "S041", "S044", "S045"]),
]


# ------------------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------------------
def _h(key: str) -> int:
    return int.from_bytes(hashlib.md5(key.encode()).digest()[:6], "big")


def _phone(key: str) -> str:
    n = _h("ph-" + key)
    return f"+91-9{n % 10000:04d}-{(n // 10000) % 100000:05d}"


def _hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def locality_of(stop: Stop) -> str:
    return stop.address.rsplit(", ", 1)[-1]


def industry_of(stop: Stop) -> str:
    return Counter(SKU_MASTER[b.sku].industry for b in stop.boxes).most_common(1)[0][0]


def licence_class(truck_code: str) -> str:
    return {"ACE": "LMV-TR", "PKP": "LMV-TR", "T14": "TRANS (MGV)"}.get(truck_code, "TRANS (HGMV)")


def _r(x: float, n: int = 3) -> float:
    return round(float(x), n)


# ------------------------------------------------------------------------------
# tables
# ------------------------------------------------------------------------------
def drivers_table() -> list[dict]:
    rows = []
    for i, name in enumerate(DEFAULT_DRIVERS):
        corr, years, truck = _DRIVER_PROFILE.get(name, ("S", 5, "T14"))
        rows.append({
            "driver_id": f"DRV-{i + 1:03d}", "name": name,
            "full_name": f"{name} {_SURNAMES[_h('sn-' + name) % len(_SURNAMES)]}",
            "phone": _phone("drv-" + name), "licence_class": licence_class(truck),
            "home_corridor": corr, "home_corridor_name": CORRIDOR_NAMES[corr],
            "years_experience": years, "preferred_truck_type": truck,
            "helper_assigned": truck in ("T17", "T20", "T14"),
        })
    return rows


def stores_table(stops: list[Stop]) -> list[dict]:
    hub = HUBS[DEFAULT_HUB_ID]
    rows = []
    for s in stops:
        loc = locality_of(s)
        ind = industry_of(s)
        k = _h("st-" + s.stop_id)
        contact = f"{_CONTACT_FIRST[k % len(_CONTACT_FIRST)]} {_CONTACT_LAST[(k // 97) % len(_CONTACT_LAST)]}"
        rows.append({
            "stop_id": s.stop_id, "name": s.name, "industry": ind,
            "category": SKU_MASTER[s.boxes[0].sku].category, "locality": loc,
            "sales_area": s.area, "corridor": corridor_of(hub, s), "lat": s.lat, "lon": s.lon,
            "window_start_min": s.window_start_min, "window_end_min": s.window_end_min,
            "receiving_window": f"{_hhmm(s.window_start_min)}-{_hhmm(s.window_end_min)}",
            "contact_person": contact, "phone": _phone("st-" + s.stop_id),
            "address": s.address,
            "street_address": f"Shop {1 + k % 48}, {_STREETS[(k // 7) % len(_STREETS)]}, {loc}, Maharashtra",
        })
    return rows


def orders_table(stops: list[Stop], dispatch_date: str) -> list[dict]:
    ymd = dispatch_date.replace("-", "")
    rows = []
    for s in stops:
        rows.append({
            "order_id": f"SO-{ymd}-{s.stop_id}", "stop_id": s.stop_id, "dispatch_date": dispatch_date,
            "hub_id": DEFAULT_HUB_ID, "cartons": len(s.boxes), "volume_m3": _r(s.volume_m3),
            "weight_kg": _r(s.weight_kg, 1), "fragile_cartons": sum(b.fragile for b in s.boxes),
            "value_inr": float(sum(SKU_PRICE_INR.get(b.sku, 1000) for b in s.boxes)),
            "sku_lines": len({b.sku for b in s.boxes}),
        })
    return rows


def cartons_table(stops: list[Stop]) -> list[dict]:
    rows = []
    for s in stops:
        for b in s.boxes:
            rows.append({
                "box_id": b.box_id, "stop_id": b.stop_id, "sku": b.sku, "description": b.description,
                "category": b.category, "industry": SKU_MASTER[b.sku].industry,
                "l_cm": float(b.l_cm), "w_cm": float(b.w_cm), "h_cm": float(b.h_cm),
                "weight_kg": float(b.weight_kg), "volume_m3": _r(b.volume_m3, 4),
                "fragile": bool(b.fragile), "this_side_up": bool(b.this_side_up),
                "qr_payload": encode_qr_payload(b),
            })
    return rows


def skus_table() -> list[dict]:
    return [{"sku": s.sku, "description": s.description, "category": s.category,
             "industry": s.industry, "l_cm": float(s.l_cm), "w_cm": float(s.w_cm),
             "h_cm": float(s.h_cm), "weight_kg": float(s.weight_kg),
             "volume_m3": _r(s.l_cm * s.w_cm * s.h_cm / 1e6, 4), "fragile": s.fragile,
             "this_side_up": s.this_side_up, "price_inr": float(SKU_PRICE_INR.get(s.sku, 0))}
            for s in SKU_MASTER.values()]


def truck_types_table() -> list[dict]:
    return [{"truck_code": t.code, "name": t.name, "inner_l_cm": float(t.inner_l_cm),
             "inner_w_cm": float(t.inner_w_cm), "inner_h_cm": float(t.inner_h_cm),
             "volume_m3": _r(t.volume_m3, 2), "usable_volume_m3": _r(t.volume_m3 * USABLE_VOLUME_SHARE, 2),
             "payload_kg": float(t.payload_kg), "fixed_daily_cost_inr": float(t.fixed_daily_cost_inr),
             "cost_per_km_inr": float(t.cost_per_km_inr), "km_per_litre": float(t.km_per_litre),
             "avg_speed_kmph": float(t.avg_speed_kmph), "color": t.color}
            for t in TRUCK_CATALOGUE.values()]


def fleet_table(dispatch_date: str) -> list[dict]:
    rows = []
    for code, n in DEFAULT_FLEET_AVAILABLE.items():
        for i in range(n):
            rows.append({"vehicle_id": f"MH04-{code}-{i + 1:02d}", "truck_code": code,
                         "registration": f"MH-04-{'ABCDEFGHJK'[_h(code + str(i)) % 10]}"
                                         f"{'LMNPQRSTUV'[_h(str(i) + code) % 10]}-{1000 + _h('rg' + code + str(i)) % 9000}",
                         "hub_id": DEFAULT_HUB_ID, "dispatch_date": dispatch_date, "available": True})
    return rows


def cost_profile_table() -> list[dict]:
    c = DEFAULT_COST_PROFILE
    rows = [
        ("fuel_price_per_litre", c.fuel_price_per_litre, "INR/litre", "Diesel price at the hub pump"),
        ("driver_day_cost", c.driver_day_cost, "INR/day", "Driver wage per shift"),
        ("helper_day_cost", c.helper_day_cost, "INR/day", "Loader/helper wage per shift"),
        ("overtime_per_hour", c.overtime_per_hour, "INR/hour", "Crew overtime beyond shift_hours"),
        ("shift_hours", c.shift_hours, "hours", "Standard shift length"),
        ("co2_kg_per_litre", c.co2_kg_per_litre, "kg/litre", "Diesel CO2 emission factor"),
        ("service_min_base", c.service_min_base, "min/stop", "Parking + paperwork per stop"),
        ("service_min_per_box", c.service_min_per_box, "min/carton", "Unloading time per carton"),
        ("unsorted_search_min_per_stop", c.unsorted_search_min_per_stop, "min/stop",
         "Baseline: time lost digging for cartons when not LIFO-loaded"),
    ]
    out = [{"parameter": k, "value": float(v), "unit": u, "description": d} for k, v, u, d in rows]
    for code, toll in c.toll_by_corridor.items():
        out.append({"parameter": f"toll_{code}", "value": float(toll), "unit": "INR/trip",
                    "description": f"Toll per trip, corridor {CORRIDOR_NAMES[code]}"})
    return out


def hubs_table() -> list[dict]:
    return [{"hub_id": h.hub_id, "name": h.name, "lat": h.lat, "lon": h.lon, "address": h.address,
             "is_default": h.hub_id == DEFAULT_HUB_ID} for h in HUBS.values()]


def gazetteer_table() -> list[dict]:
    hub = HUBS[DEFAULT_HUB_ID]
    return [{"locality": loc, "lat": lat, "lon": lon, "sales_area": area,
             "corridor": corridor_of(hub, Stop("x", loc, loc, lat, lon)),
             "demo_stops": _LOCALITY_STOPS.get(loc, 0)} for loc, (lat, lon, area) in GAZETTEER.items()]


def corridors_table() -> list[dict]:
    tolls = DEFAULT_COST_PROFILE.toll_by_corridor
    return [{"corridor": k, "name": v, "toll_inr": float(tolls.get(k, 0))} for k, v in CORRIDOR_NAMES.items()]


def baseline_table(stops: list[Stop]) -> list[dict]:
    rows = []
    for i, (key, members) in enumerate(baseline_assignment(stops).items(), 1):
        area, code = key.split("|")
        t = TRUCK_CATALOGUE[code]
        vol = sum(s.volume_m3 for s in members)
        kg = sum(s.weight_kg for s in members)
        rows.append({"vehicle_label": f"BL-{i:02d}", "sales_area": area, "truck_code": code,
                     "split_vehicle": area in BASELINE_SPLIT_AREAS and code == BASELINE_SPLIT_AREAS[area],
                     "stops": len(members), "stop_ids": ",".join(s.stop_id for s in members),
                     "cartons": sum(len(s.boxes) for s in members), "volume_m3": _r(vol),
                     "weight_kg": _r(kg, 1), "volume_fill_pct": _r(100 * vol / t.volume_m3, 1),
                     "weight_fill_pct": _r(100 * kg / t.payload_kg, 1)})
    return rows


def driver_run_stats(run: dict, stops: list[Stop]) -> dict:
    by_id = {s.stop_id: s for s in stops}
    members = [by_id[sid] for sid in run["stop_ids"]]
    t = TRUCK_CATALOGUE[run["truck_code"]]
    vol = sum(s.volume_m3 for s in members)
    kg = sum(s.weight_kg for s in members)
    return {"stops": len(members), "cartons": sum(len(s.boxes) for s in members),
            "volume_m3": _r(vol), "weight_kg": _r(kg, 1),
            "volume_fill_pct": _r(100 * vol / t.volume_m3, 1),
            "weight_fill_pct": _r(100 * kg / t.payload_kg, 1),
            "fits": vol <= t.volume_m3 * USABLE_VOLUME_SHARE and kg <= t.payload_kg}


def driver_runs_table(stops: list[Stop]) -> list[dict]:
    rows = []
    for r in DRIVER_RUNS:
        by_id = {s.stop_id: s for s in stops}
        st = driver_run_stats(r, stops)
        rows.append({"run_id": r["run_id"], "driver": r["driver"], "truck_code": r["truck_code"],
                     "corridor": r["corridor"], "corridor_name": CORRIDOR_NAMES[r["corridor"]],
                     "label": r["label"], "stop_ids": ",".join(r["stop_ids"]),
                     "localities": " / ".join(dict.fromkeys(locality_of(by_id[s]) for s in r["stop_ids"])),
                     **{k: v for k, v in st.items() if k != "fits"},
                     "photos": ",".join(r["photos"]), "order_file": r["order_file"]})
    return rows


def build_tables(dispatch_date: str | None = None, seed: int = DEMO_SEED) -> dict[str, list[dict]]:
    """All demo tables, keyed by BigQuery table name."""
    d = dispatch_date or _dt.date.today().isoformat()
    stops = build_demo_stops(seed=seed)
    return {
        "stores": stores_table(stops), "orders": orders_table(stops, d), "cartons": cartons_table(stops),
        "skus": skus_table(), "truck_types": truck_types_table(), "fleet": fleet_table(d),
        "drivers": drivers_table(), "driver_runs": driver_runs_table(stops),
        "cost_profile": cost_profile_table(), "hubs": hubs_table(), "corridors": corridors_table(),
        "gazetteer": gazetteer_table(), "baseline": baseline_table(stops),
    }


# ------------------------------------------------------------------------------
# BigQuery schemas: table -> (description, [(field, type, description)])
# ------------------------------------------------------------------------------
S, I, F, B, D = "STRING", "INT64", "FLOAT64", "BOOL", "DATE"
SCHEMAS: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "stores": ("Outlet / store master (delivery points) for the MMR demo", [
        ("stop_id", S, "Outlet id (S001..)"), ("name", S, "Outlet name"), ("industry", S, "Industry profile"),
        ("category", S, "Primary carton category"), ("locality", S, "Gazetteer locality"),
        ("sales_area", S, "Sales area (today's manual dispatch split)"),
        ("corridor", S, "Compass corridor from Bhiwandi DC"), ("lat", F, "Latitude"), ("lon", F, "Longitude"),
        ("window_start_min", I, "Receiving window start (minutes from midnight)"),
        ("window_end_min", I, "Receiving window end (minutes from midnight)"),
        ("receiving_window", S, "Receiving window HH:MM-HH:MM"), ("contact_person", S, "Store contact"),
        ("phone", S, "Store phone (fake)"), ("address", S, "Planner address (name, locality)"),
        ("street_address", S, "Postal-style address (fake)")]),
    "orders": ("One delivery order per outlet for the dispatch date", [
        ("order_id", S, "Sales order id"), ("stop_id", S, "Outlet id"), ("dispatch_date", D, "Dispatch date"),
        ("hub_id", S, "Dispatch hub"), ("cartons", I, "Carton count"), ("volume_m3", F, "Total volume m3"),
        ("weight_kg", F, "Total weight kg"), ("fragile_cartons", I, "Fragile cartons"),
        ("value_inr", F, "Estimated order value INR"), ("sku_lines", I, "Distinct SKUs")]),
    "cartons": ("One row per carton (box) with dimensions and the printed QR payload", [
        ("box_id", S, "Carton id"), ("stop_id", S, "Outlet id"), ("sku", S, "SKU"), ("description", S, "SKU description"),
        ("category", S, "Carton category"), ("industry", S, "Industry"), ("l_cm", F, "Length cm"),
        ("w_cm", F, "Width cm"), ("h_cm", F, "Height cm"), ("weight_kg", F, "Weight kg"),
        ("volume_m3", F, "Volume m3"), ("fragile", B, "Fragile"), ("this_side_up", B, "This side up"),
        ("qr_payload", S, "QR label payload LP1|box|stop|sku|LxWxH|kg|flags")]),
    "skus": ("Cross-industry carton catalogue (SKU master)", [
        ("sku", S, "SKU"), ("description", S, "Description"), ("category", S, "Category"), ("industry", S, "Industry"),
        ("l_cm", F, "Length cm"), ("w_cm", F, "Width cm"), ("h_cm", F, "Height cm"), ("weight_kg", F, "Weight kg"),
        ("volume_m3", F, "Volume m3"), ("fragile", B, "Fragile"), ("this_side_up", B, "This side up"),
        ("price_inr", F, "Indicative price per carton INR")]),
    "truck_types": ("Truck body catalogue with internal dims and cost parameters", [
        ("truck_code", S, "Truck type code"), ("name", S, "Name"), ("inner_l_cm", F, "Inner length cm"),
        ("inner_w_cm", F, "Inner width cm"), ("inner_h_cm", F, "Inner height cm"), ("volume_m3", F, "Body volume m3"),
        ("usable_volume_m3", F, "Practical usable volume (80%)"), ("payload_kg", F, "Payload kg"),
        ("fixed_daily_cost_inr", F, "Fixed cost per operating day INR"), ("cost_per_km_inr", F, "Maintenance INR/km"),
        ("km_per_litre", F, "Fuel efficiency km/l"), ("avg_speed_kmph", F, "Average city speed"),
        ("color", S, "Display colour")]),
    "fleet": ("Vehicles available at the hub on the dispatch date", [
        ("vehicle_id", S, "Vehicle id"), ("truck_code", S, "Truck type"), ("registration", S, "Registration (fake)"),
        ("hub_id", S, "Hub"), ("dispatch_date", D, "Dispatch date"), ("available", B, "Available today")]),
    "drivers": ("Driver roster", [
        ("driver_id", S, "Driver id"), ("name", S, "First name (used in plans)"), ("full_name", S, "Full name"),
        ("phone", S, "Phone (fake)"), ("licence_class", S, "Licence class"), ("home_corridor", S, "Usual corridor code"),
        ("home_corridor_name", S, "Usual corridor"), ("years_experience", I, "Years of experience"),
        ("preferred_truck_type", S, "Preferred truck type"), ("helper_assigned", B, "Travels with a helper")]),
    "driver_runs": ("Ready-made single-driver scenarios for the driver-perspective demo", [
        ("run_id", S, "Run id"), ("driver", S, "Driver"), ("truck_code", S, "Truck type"), ("corridor", S, "Corridor code"),
        ("corridor_name", S, "Corridor"), ("label", S, "Display label"), ("stop_ids", S, "Comma-separated outlet ids"),
        ("localities", S, "Localities covered"), ("stops", I, "Stops"), ("cartons", I, "Cartons"),
        ("volume_m3", F, "Volume m3"), ("weight_kg", F, "Weight kg"), ("volume_fill_pct", F, "Body volume fill %"),
        ("weight_fill_pct", F, "Payload fill %"), ("photos", S, "Carton photo files (demo-data/samples)"),
        ("order_file", S, "Manager order message file")]),
    "cost_profile": ("Operating cost parameters (data-driven cost model)", [
        ("parameter", S, "Parameter"), ("value", F, "Value"), ("unit", S, "Unit"), ("description", S, "Description")]),
    "hubs": ("Distribution hubs", [
        ("hub_id", S, "Hub id"), ("name", S, "Name"), ("lat", F, "Latitude"), ("lon", F, "Longitude"),
        ("address", S, "Address"), ("is_default", B, "Default demo hub")]),
    "corridors": ("Compass corridors from the hub", [
        ("corridor", S, "Code"), ("name", S, "Name"), ("toll_inr", F, "Toll per trip INR")]),
    "gazetteer": ("Offline locality gazetteer (geocoding for order lists)", [
        ("locality", S, "Locality"), ("lat", F, "Latitude"), ("lon", F, "Longitude"), ("sales_area", S, "Sales area"),
        ("corridor", S, "Corridor from Bhiwandi DC"), ("demo_stops", I, "Outlets in demo order book")]),
    "baseline": ("Today's manual dispatch: one truck per sales area (+ a split vehicle)", [
        ("vehicle_label", S, "Baseline vehicle"), ("sales_area", S, "Sales area"), ("truck_code", S, "Truck type"),
        ("split_vehicle", B, "Second vehicle for a split area"), ("stops", I, "Stops"),
        ("stop_ids", S, "Comma-separated outlet ids"), ("cartons", I, "Cartons"), ("volume_m3", F, "Volume m3"),
        ("weight_kg", F, "Weight kg"), ("volume_fill_pct", F, "Volume fill %"), ("weight_fill_pct", F, "Payload fill %")]),
}
