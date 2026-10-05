"""Deterministic Markdown report appended after the model's short headline.

Rules (Gemini Enterprise): tables <= 5 columns, clear `###` headings, links in their own section.
"""

from __future__ import annotations

try:
    from app.contracts import DispatchPlan
    from app.data.master_data import CORRIDOR_NAMES
    from app.geo.gmaps import gmaps_route_url, whatsapp_dispatch_url
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan
    from data.master_data import CORRIDOR_NAMES
    from geo.gmaps import gmaps_route_url, whatsapp_dispatch_url



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


def _why_rows(plan: DispatchPlan) -> list[str]:
    """Explain uneven drop counts: every truck is capped by space, payload or shift hours."""
    shift = plan.params.cost_profile.shift_hours * 60 if getattr(plan, "params", None) and \
        getattr(plan.params, "cost_profile", None) else 540
    out = []
    for r in plan.routes:
        lp = plan.loads.get(r.truck_id)
        if lp is None:
            continue
        t = lp.truck_type
        used = 100 * (r.end_min - r.start_min) / shift if shift else 0
        caps = {"payload (kg)": lp.weight_fill_pct, "space (m³)": lp.volume_fill_pct, "shift hours": used}
        lim, val = max(caps.items(), key=lambda kv: kv[1])
        kg = sum(sum(b.weight_kg for b in rs.stop.boxes) for rs in r.stops)
        if val >= 85:
            why = f"full on **{lim}** ({val:.0f}%)"
        else:
            why = f"{r.corridor} corridor has only these drops left after the bigger trucks were filled"
        out.append(f"| {r.truck_id} · {r.driver} | {t.name.split('(')[0].strip()} · {t.payload_kg / 1000:g} t · "
                   f"{t.volume_m3:.1f} m³ | {len(r.stops)} · {kg:,.0f} kg | {lp.weight_fill_pct:.0f}% · "
                   f"{lp.volume_fill_pct:.0f}% · {used:.0f}% | {why} |")
    return out


def dispatch_markdown(plan: DispatchPlan, links: dict[str, str] | None = None,
                      focus_truck_id: str | None = None) -> str:
    b, o = plan.baseline, plan.optimized
    pct = 100 * plan.savings_inr / b.cost_total if b.cost_total else 0
    out: list[str] = []
    out.append("\n\n---\n\n### Today vs FleetFlow\n")
    out.append("| Metric | Today (manual) | FleetFlow | Change |")
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

    why = _why_rows(plan)
    if why:
        out.append("\n### Why some trucks have more drops\n")
        out.append("Every truck is filled until it hits a limit: payload, space or the shift. Drop counts depend "
                   "on the truck size and on how much each store ordered, so the number of drops is not the "
                   "measure. A 7 ft Tata Ace (0.75 t) fills up after 3–4 heavy drops, while a 17 ft truck "
                   "(about 5 t) can take 15 lighter ones. Fragile and this-side-up rules and the LIFO door "
                   "order are checked for every carton.\n")
        out.append("| Truck · Driver | Truck (payload · space) | Drops · kg | Payload · space · shift used | Why this many |")
        out.append("| :--- | :--- | ---: | ---: | :--- |")
        out += why

    out.append("\n### Where each truck goes\n")
    for i, r in enumerate(plan.routes):
        claim = " · 🙋 driver's claim" if r.claimed else ""
        br = "" if r.branch in ("solo", "") else f" ({r.branch})"
        out.append(f"{DOTS[i % len(DOTS)]} **{r.truck_id} · {r.driver}**: "
                   f"{CORRIDOR_NAMES.get(r.corridor, r.corridor)}{br}{claim}  ")
        out.append(f"Hub → {_itinerary(r)} → Hub\n")

    out.append("### How to load & Safety Compliance\n")
    out.append("- Load in **reverse drop order**: the last drop goes in first, against the cab, and drop 1 goes "
               "in last, at the door.")
    out.append("- Heavy cartons go on the floor and fragile ones on top. Every truck passed the door check "
               + ("✅" if all(lp.lifo_ok for lp in plan.loads.values()) else "⚠️ (review flagged trucks)") + ".")
    cmvr_ok = all(lp.cmvr_axle_compliant for lp in plan.loads.values())
    out.append(f"- **CMVR Rule 93 Axle Balance**: {'✅ 100% Compliant' if cmvr_ok else '⚠️ Review'}. "
               "Cargo center-of-gravity ensures 32–45% steer axle / 55–68% drive axle load distribution.")
    out.append(f"- **ESG Green Fleet Impact**: **{plan.diesel_saved_litres:,.1f} L diesel** and "
               f"**{plan.co2_saved_kg:,.1f} kg CO₂** saved today (equiv. to **{plan.annual_trees_offset_equiv:,} mature trees/yr** offset).")
    out.append("- For a carton-by-carton sheet, say **\"load plan for "
               f"{focus_truck_id or (plan.routes[0].truck_id if plan.routes else 'T17-1')}\"**.")

    if links and (links.get("html") or links.get("video")):
        out.append("\n### Open the interactive views\n")
        if links.get("html"):
            out.append(f"- 🗺️ **[Interactive road map + 3D truck loading (full screen) ↗]({links['html']})**: "
                       "click any numbered stop or truck")
        if focus_truck_id or (plan.routes and plan.routes[0]):
            r_focus = next((x for x in plan.routes if x.truck_id == (focus_truck_id or plan.routes[0].truck_id)), plan.routes[0] if plan.routes else None)
            if r_focus:
                hub_coords = (plan.hub.lat, plan.hub.lon)
                stop_coords = [(rs.stop.lat, rs.stop.lon) for rs in r_focus.stops]
                gmaps_focus = gmaps_route_url(hub_coords, stop_coords, return_to_hub=True)
                out.append(f"- 🚦 **[Start Google Maps Navigation with Live Traffic ({r_focus.driver} · {r_focus.truck_id}) ↗]({gmaps_focus})**")
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
    hub_coords = (plan.hub.lat, plan.hub.lon)
    stop_coords = [(rs.stop.lat, rs.stop.lon) for rs in r.stops]
    gmaps_nav = gmaps_route_url(hub_coords, stop_coords, return_to_hub=True)
    portal_link = (links.get("html") if links else "") or ""
    stops_summary = [{"seq": rs.seq, "name": rs.stop.name, "area": _locality(rs.stop), "n": len(rs.stop.boxes), "eta": _hm(rs.arrive_min)} for rs in r.stops]
    wa_url = whatsapp_dispatch_url(
        r.driver, r.truck_id, r.truck_type.name.split("(")[0].strip(), plan.hub.name,
        _hm(r.start_min), _hm(r.end_min), stops_summary, gmaps_nav, portal_link,
    )

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

    out.append("\n### Share with driver / Open on mobile\n")
    out.append(f"- 🗺️ **[Start Google Maps Navigation (Live Traffic) ↗]({gmaps_nav})**: launches Google Maps app with turn-by-turn driving & live traffic.")
    if portal_link:
        out.append(f"- 📱 **[Driver Run Sheet & Mobile Delivery Portal ↗]({portal_link})**: store contacts, tap-a-store 3D packing & digital POD.")
    out.append(f"- 💬 **[Share Route to Driver on WhatsApp ↗]({wa_url})**: 1-click formatted message ready to send.")
    if links and links.get("video"):
        out.append(f"- 🎬 **[Loading video (MP4) ↗]({links['video']})**")
    return "\n".join(out) + "\n"


def briefings_markdown(plan: DispatchPlan, links_by_truck: dict[str, str] | None = None, driver: str = "") -> str:
    """Fleet manager: ready-to-send instruction blocks. If driver is specified, filters to that driver only."""
    links_by_truck = links_by_truck or {}
    routes = plan.routes
    who = (driver or "").strip().lower()
    if who:
        routes = [r for r in routes if who in (r.driver.lower(), r.truck_id.lower())]
    if not routes:
        return f"\n\nNo driver or truck matching '{driver}' found in plan {plan.plan_id}."

    is_single = len(routes) == 1
    header_title = f"### Driver instructions · {routes[0].driver} ({routes[0].truck_id})" if is_single else "### Driver instructions (send one to each driver)"
    out = [f"\n\n---\n\n{header_title}\n"]
    hub_coords = (plan.hub.lat, plan.hub.lon)
    table_rows = []
    for i, r in enumerate(routes):
        lp = plan.loads.get(r.truck_id)
        first = r.stops[0].stop if r.stops else None
        stop_coords = [(rs.stop.lat, rs.stop.lon) for rs in r.stops]
        gmaps_nav = gmaps_route_url(hub_coords, stop_coords, return_to_hub=True)
        portal_link = links_by_truck.get(r.truck_id) or ""
        stops_summary = [{"seq": rs.seq, "name": rs.stop.name, "area": _locality(rs.stop), "n": len(rs.stop.boxes), "eta": _hm(rs.arrive_min)} for rs in r.stops]
        wa_url = whatsapp_dispatch_url(
            r.driver, r.truck_id, r.truck_type.name.split("(")[0].strip(), plan.hub.name,
            _hm(r.start_min), _hm(r.end_min), stops_summary, gmaps_nav, portal_link,
        )

        out.append(f"#### {DOTS[i % len(DOTS)]} {r.driver} · {r.truck_id} ({r.truck_type.code})\n")
        out.append(f"- **Report** {_hm(r.start_min - 30)} at dock · **leave** {_hm(r.start_min)} · "
                   f"**back** {_hm(r.end_min)} · {len(r.stops)} drops · {r.km:.0f} km")
        out.append(f"- **Route**: Hub → {_itinerary(r)} → Hub")
        out.append(f"- **First drop**: {first.name if first else '-'} at {_hm(r.stops[0].arrive_min) if r.stops else '-'}")
        out.append(f"- **Load (cab → door)**: {_load_line(r)}")
        if lp is not None:
            frag = sum(1 for p in lp.placed if p.box.fragile)
            out.append(f"- **Cartons**: {len(lp.placed)} ({frag} fragile, on top) · fill {lp.volume_fill_pct}%")
        out.append(f"- 🗺️ **[Google Maps (Live Traffic) ↗]({gmaps_nav})**")
        if portal_link:
            out.append(f"- 📱 **[Driver Run Sheet & Digital POD ↗]({portal_link})**")
        out.append(f"- 💬 **[1-Click WhatsApp Dispatch Message ↗]({wa_url})**")
        out.append("")

        table_rows.append(f"| {r.driver} · {r.truck_id} | {_hm(r.start_min)}–{_hm(r.end_min)} | "
                          f"{len(r.stops)} drops · {len(lp.placed) if lp else 0} ctn | "
                          f"[🗺️ Maps ↗]({gmaps_nav}) | [💬 WhatsApp ↗]({wa_url}) |")

    table_title = f"### Dispatch summary · {routes[0].driver} (copy-ready)\n" if is_single else "### Dispatch board & Share links (copy-ready)\n"
    out.append(table_title)
    out.append("| Driver · Truck | Shift | Drops · Cartons | Live Google Maps | WhatsApp Share |")
    out.append("| :--- | :--- | ---: | :--- | :--- |")
    out.extend(table_rows)
    return "\n".join(out) + "\n"


