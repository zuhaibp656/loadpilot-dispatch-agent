"""Deterministic Markdown report appended after the model's short headline.

Rules (Gemini Enterprise): tables <= 5 columns, clear `###` headings, links in their own section.
"""

from __future__ import annotations

try:
    from app.contracts import DispatchPlan
    from app.data.master_data import CORRIDOR_NAMES
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan
    from data.master_data import CORRIDOR_NAMES


def _hm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _inr(v: float) -> str:
    return f"₹{v:,.0f}"


DOTS = ["🔵", "🟠", "🟢", "🔴", "🟡", "🟣", "🟤", "⚪", "🔵", "🟠", "🟢", "🔴"]


def _locality(stop) -> str:
    return stop.address.split(", ")[-1].strip() or stop.area


def _itinerary(r) -> str:
    """'Ulhasnagar (2) → Kalyan (3) → Dombivli (2) → Vashi (2)' — consecutive drops grouped by locality."""
    groups: list[list] = []
    for rs in r.stops:
        loc = _locality(rs.stop)
        if groups and groups[-1][0] == loc:
            groups[-1][1] += 1
        else:
            groups.append([loc, 1])
    return " → ".join(f"{g[0]}" + (f" ({g[1]})" if g[1] > 1 else "") for g in groups)


def dispatch_markdown(plan: DispatchPlan, links: dict[str, str] | None = None,
                      focus_truck_id: str | None = None) -> str:
    b, o = plan.baseline, plan.optimized
    pct = 100 * plan.savings_inr / b.cost_total if b.cost_total else 0
    out: list[str] = []
    out.append("\n\n---\n\n### Today vs LoadPilot\n")
    out.append("| Metric | Today (manual) | LoadPilot | Change |")
    out.append("| :--- | ---: | ---: | ---: |")
    rows = [("Trucks on the road", b.trucks, o.trucks, ""), ("Road km", b.km, o.km, " km"),
            ("Crew hours", b.hours, o.hours, " h"), ("Diesel", b.litres, o.litres, " L"),
            ("CO₂", b.co2_kg, o.co2_kg, " kg"), ("Time digging for cartons", b.unload_search_hours,
                                                   o.unload_search_hours, " h")]
    for name, bv, ov, u in rows:
        out.append(f"| {name} | {bv:,.0f}{u} | **{ov:,.0f}{u}** | {ov - bv:+,.0f}{u} |")
    out.append(f"| **Cost of the day** | {_inr(b.cost_total)} | **{_inr(o.cost_total)}** | "
               f"**−{_inr(plan.savings_inr)} ({pct:.0f}%)** |")

    out.append("\n### Truck plan (copy-ready)\n")
    out.append("| Truck · Driver | Corridor | Drops · Cartons | Time · Km | Cost |")
    out.append("| :--- | :--- | ---: | ---: | ---: |")
    for r in plan.routes:
        lp = plan.loads.get(r.truck_id)
        br = "" if r.branch in ("solo", "") else f" · {r.branch}"
        out.append(f"| {r.truck_id} · {r.driver} | {r.corridor}{br} | {len(r.stops)} · "
                   f"{len(lp.placed) if lp else 0} | {_hm(r.start_min)}–{_hm(r.end_min)} · {r.km:.0f} | "
                   f"{_inr(r.cost.total)} |")

    out.append("\n### Where each truck goes\n")
    for i, r in enumerate(plan.routes):
        claim = " · 🙋 driver's claim" if r.claimed else ""
        br = "" if r.branch in ("solo", "") else f" ({r.branch})"
        out.append(f"{DOTS[i % len(DOTS)]} **{r.truck_id} · {r.driver}**: "
                   f"{CORRIDOR_NAMES.get(r.corridor, r.corridor)}{br}{claim}  ")
        out.append(f"Hub → {_itinerary(r)} → Hub\n")

    out.append("### How to load\n")
    out.append("- Load in **reverse drop order**: the last drop goes in first, against the cab, and drop 1 goes "
               "in last, at the door.")
    out.append("- Heavy cartons go on the floor and fragile ones on top. Every truck passed the door check "
               + ("✅" if all(lp.lifo_ok for lp in plan.loads.values()) else "⚠️ (review flagged trucks)") + ".")
    out.append("- For a carton-by-carton sheet, say **\"load plan for "
               f"{focus_truck_id or (plan.routes[0].truck_id if plan.routes else 'T17-1')}\"**.")

    if links and (links.get("html") or links.get("video")):
        out.append("\n### Open the interactive views\n")
        if links.get("html"):
            out.append(f"- 🗺️ **[Interactive road map + 3D truck loading (full screen) ↗]({links['html']})**: "
                       "click any numbered stop or truck")
        if links.get("video"):
            out.append(f"- 🎬 **[Loading video · {focus_truck_id or 'focus truck'} (MP4) ↗]({links['video']})**")
    return "\n".join(out) + "\n"


def truck_markdown(plan: DispatchPlan, truck_id: str) -> str:
    r = next((x for x in plan.routes if x.truck_id.lower() == truck_id.lower()), None)
    if r is None:
        return f"\n\nTruck `{truck_id}` is not in plan {plan.plan_id}."
    lp = plan.loads[r.truck_id]
    out = [f"\n\n---\n\n### Loading sheet · {r.truck_id} · {r.driver} ({r.truck_type.name})\n",
           "Load from the **cab wall toward the door** in this order. Stop 1 goes in last, at the door.\n",
           "| Load # | Stop · Outlet | Cartons | Zone (cm from cab) | ETA |",
           "| ---: | :--- | ---: | :--- | :--- |"]
    zones = {z.stop_seq: z for z in lp.zones}
    for k, rs in enumerate(sorted(r.stops, key=lambda s: -s.seq), start=1):
        z = zones.get(rs.seq)
        out.append(f"| {k} | S{rs.seq} · {rs.stop.name} | {len(rs.stop.boxes)} | "
                   f"{f'{z.x_start:.0f}–{z.x_end:.0f}' if z else '-'} | {_hm(rs.arrive_min)} |")
    heavy = sorted(lp.placed, key=lambda p: -p.box.weight_kg)[:3]
    frag = sum(1 for p in lp.placed if p.box.fragile)
    out.append(f"\n- Heaviest cartons ({', '.join(f'{p.box.sku} {p.box.weight_kg:g} kg' for p in heavy)}) sit on the floor.")
    out.append(f"- {frag} fragile cartons carry nothing heavier than 12 kg (or an identical carton).")
    out.append(f"- Volume {lp.volume_fill_pct}% · payload {lp.weight_fill_pct}% · front-half weight "
               f"{lp.front_axle_share_pct}% · LIFO {'✅ verified' if lp.lifo_ok else '⚠️ review'}")
    return "\n".join(out) + "\n"


def _load_line(r) -> str:
    order = sorted(r.stops, key=lambda s: -s.seq)
    return " → ".join(f"S{rs.seq} ({len(rs.stop.boxes)})" for rs in order)


def driver_markdown(plan: DispatchPlan, truck_id: str, links: dict[str, str] | None = None,
                    source_note: str = "") -> str:
    """One driver's day: numbered route, where each store's cartons go, and how to load."""
    r = next((x for x in plan.routes if x.truck_id == truck_id), None)
    if r is None:
        return f"\n\nTruck `{truck_id}` is not in plan {plan.plan_id}."
    lp = plan.loads[r.truck_id]
    zones = {z.stop_seq: z for z in lp.zones}
    L = lp.truck_type.inner_l_cm
    out = [f"\n\n---\n\n### Your day · {r.driver} · {r.truck_id} ({r.truck_type.name})\n",
           f"Leave **{plan.hub.name}** at **{_hm(r.start_min)}**, {len(r.stops)} drops, "
           f"{sum(len(rs.stop.boxes) for rs in r.stops)} cartons, {r.km:.0f} km, back by **{_hm(r.end_min)}**."
           + (f"  \n{source_note}" if source_note else "") + "\n",
           "| # | Store | Area · ETA | Cartons | Where in the truck |",
           "| ---: | :--- | :--- | ---: | :--- |"]
    for rs in r.stops:
        z = zones.get(rs.seq)
        pos = f"{max(0, L - z.x_end):.0f}–{L - z.x_start:.0f} cm from door" if z else "-"
        out.append(f"| {rs.seq} | {rs.stop.name} | {_locality(rs.stop)} · {_hm(rs.arrive_min)} | "
                   f"{len(rs.stop.boxes)} | {pos} |")
    out.append("\n### How to load your truck\n")
    out.append(f"1. Start at the **cab wall** with stop {len(r.stops)} (your last drop), then work back to the door.")
    out.append(f"2. Load order: **{_load_line(r)}** (stop · cartons).")
    out.append("3. Heavy cartons on the floor, fragile on top. Stop 1 goes in last, right at the door.")
    out.append(f"4. Check: volume {lp.volume_fill_pct}% · payload {lp.weight_fill_pct}% · "
               f"LIFO {'✅ nothing to dig at any stop' if lp.lifo_ok else '⚠️ review'}.")
    if links and links.get("html"):
        out.append("\n### Open on your phone\n")
        out.append(f"- 📱 **[Your route map + tap-a-store 3D loading ↗]({links['html']})**")
        if links.get("video"):
            out.append(f"- 🎬 **[Loading video (MP4) ↗]({links['video']})**")
    return "\n".join(out) + "\n"


def briefings_markdown(plan: DispatchPlan, links_by_truck: dict[str, str] | None = None) -> str:
    """Fleet manager: one ready-to-send instruction block per driver."""
    links_by_truck = links_by_truck or {}
    out = ["\n\n---\n\n### Driver instructions (send one to each driver)\n"]
    for i, r in enumerate(plan.routes):
        lp = plan.loads.get(r.truck_id)
        first = r.stops[0].stop if r.stops else None
        out.append(f"#### {DOTS[i % len(DOTS)]} {r.driver} · {r.truck_id} ({r.truck_type.code})\n")
        out.append(f"- **Report** {_hm(r.start_min - 30)} at dock · **leave** {_hm(r.start_min)} · "
                   f"**back** {_hm(r.end_min)} · {len(r.stops)} drops · {r.km:.0f} km")
        out.append(f"- **Route**: Hub → {_itinerary(r)} → Hub")
        out.append(f"- **First drop**: {first.name if first else '-'} at {_hm(r.stops[0].arrive_min) if r.stops else '-'}")
        out.append(f"- **Load (cab → door)**: {_load_line(r)}")
        if lp is not None:
            frag = sum(1 for p in lp.placed if p.box.fragile)
            out.append(f"- **Cartons**: {len(lp.placed)} ({frag} fragile, on top) · fill {lp.volume_fill_pct}%")
        if links_by_truck.get(r.truck_id):
            out.append(f"- 📱 **[Driver view: map + 3D loading ↗]({links_by_truck[r.truck_id]})**")
        out.append("")
    out.append("### Summary (copy-ready)\n")
    out.append("| Driver · Truck | Leave · Back | Drops · Cartons | Km | First drop |")
    out.append("| :--- | :--- | ---: | ---: | :--- |")
    for r in plan.routes:
        lp = plan.loads.get(r.truck_id)
        out.append(f"| {r.driver} · {r.truck_id} | {_hm(r.start_min)} · {_hm(r.end_min)} | {len(r.stops)} · "
                   f"{len(lp.placed) if lp else 0} | {r.km:.0f} | {r.stops[0].stop.name if r.stops else '-'} |")
    return "\n".join(out) + "\n"
