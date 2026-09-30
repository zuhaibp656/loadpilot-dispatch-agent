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


def dispatch_markdown(plan: DispatchPlan, links: dict[str, str] | None = None,
                      focus_truck_id: str | None = None) -> str:
    b, o = plan.baseline, plan.optimized
    pct = 100 * plan.savings_inr / b.cost_total if b.cost_total else 0
    out: list[str] = []
    out.append("\n\n---\n\n### 1. Dispatch summary: today vs LoadPilot\n")
    out.append("| Metric | Today (manual) | LoadPilot | Change |")
    out.append("| :--- | ---: | ---: | ---: |")
    rows = [("Trucks on the road", b.trucks, o.trucks, ""), ("Road km", b.km, o.km, " km"),
            ("Crew hours", b.hours, o.hours, " h"), ("Diesel", b.litres, o.litres, " L"),
            ("CO₂", b.co2_kg, o.co2_kg, " kg"), ("Time digging for boxes", b.unload_search_hours,
                                                   o.unload_search_hours, " h")]
    for name, bv, ov, u in rows:
        out.append(f"| {name} | {bv:,.1f}{u} | **{ov:,.1f}{u}** | {ov - bv:+,.1f}{u} |".replace(".0", ""))
    out.append(f"| **Total cost / day** | {_inr(b.cost_total)} | **{_inr(o.cost_total)}** | "
               f"**−{_inr(plan.savings_inr)} ({pct:.0f}%)** |")
    out.append(f"\nSolved in {plan.solve_ms / 1000:.1f} s · route overlap outside shared trunks: "
               f"{plan.overlap_km:.0f} km · unassigned stops: {len(plan.unassigned)}")
    if plan.notes:
        out.append("\n" + "\n".join(f"- {n}" for n in plan.notes if "did not fit" not in n))

    out.append("\n---\n\n### 2. Truck-by-truck route & loading directives\n")
    for r in plan.routes:
        lp = plan.loads.get(r.truck_id)
        branch = "" if r.branch == "solo" else f" · **{r.branch}**"
        claim = " · 🙋 claimed" if r.claimed else ""
        out.append(f"#### {r.truck_id} · {r.driver} · {CORRIDOR_NAMES.get(r.corridor, r.corridor)}{branch}{claim}")
        seq = " ➔ ".join(f"{rs.seq}. {rs.stop.name.split(' ')[0]} {rs.stop.address.split(', ')[-1]} ({_hm(rs.arrive_min)})"
                         for rs in r.stops)
        out.append(f"- **Route**: Hub {_hm(r.start_min)} ➔ {seq} ➔ Hub {_hm(r.end_min)} · {r.km:.0f} km")
        if lp:
            order = " → ".join(f"S{z.stop_seq}" for z in sorted(lp.zones, key=lambda z: -z.stop_seq))
            out.append(f"- **Load order (cab ➔ door)**: {order} · {len(lp.placed)} cartons · volume "
                       f"{lp.volume_fill_pct}% · payload {lp.weight_fill_pct}% · front-half weight "
                       f"{lp.front_axle_share_pct}% · LIFO {'✅' if lp.lifo_ok else '⚠️ review'}")
        out.append(f"- **Cost**: {_inr(r.cost.total)} (fuel {_inr(r.cost.fuel)}, crew {_inr(r.cost.crew)}, "
                   f"truck {_inr(r.cost.fixed + r.cost.distance)}, tolls {_inr(r.cost.tolls)}"
                   + (f", overtime {_inr(r.cost.overtime)}" if r.cost.overtime else "") + ")\n")

    out.append("---\n\n### 3. Dispatch ledger (copy-ready for Google Sheets)\n")
    out.append("| Truck · Driver | Corridor · Branch | Stops · Cartons | Km · Hours | Cost (₹) |")
    out.append("| :--- | :--- | ---: | ---: | ---: |")
    for r in plan.routes:
        lp = plan.loads.get(r.truck_id)
        out.append(f"| {r.truck_id} · {r.driver} | {r.corridor} · {r.branch} | {len(r.stops)} · "
                   f"{len(lp.placed) if lp else 0} | {r.km:.0f} · {(r.end_min - r.start_min) / 60 + 1:.1f} | "
                   f"{r.cost.total:,.0f} |")

    out.append("\n### 4. Cost breakdown by component (copy-ready)\n")
    out.append("| Component | Today (₹) | LoadPilot (₹) | Saved (₹) |")
    out.append("| :--- | ---: | ---: | ---: |")
    comps = ["fixed", "distance", "fuel", "tolls", "crew", "overtime"]
    labels = {"fixed": "Truck day-rate", "distance": "Per-km (tyres, maint.)", "fuel": "Diesel",
              "tolls": "Tolls", "crew": "Driver + helper", "overtime": "Overtime"}
    for c in comps:
        bv = sum(getattr(r.cost, c) for r in plan.baseline_routes)
        ov = sum(getattr(r.cost, c) for r in plan.routes)
        out.append(f"| {labels[c]} | {bv:,.0f} | {ov:,.0f} | {bv - ov:,.0f} |")

    if links:
        out.append("\n---\n\n### 5. Interactive views & loader video\n")
        if links.get("html"):
            out.append(f"👉 **[Open full-screen animated dispatch (routes + 3D loading) ↗]({links['html']})**\n")
        if links.get("video"):
            out.append(f"🎬 **[Download loader video for {focus_truck_id or 'focus truck'} (MP4) ↗]({links['video']})**\n")
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
