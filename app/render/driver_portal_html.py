"""Standalone mobile Driver Portal & Live Google Maps Delivery Manifest.

Zero-login, mobile-responsive document & web portal for drivers on the road.
Features:
- Big, high-contrast, touch-friendly UI for non-tech drivers on smartphones.
- 1-Tap official Google Maps Navigation with real-time live traffic.
- 1-Click WhatsApp dispatch sharing for co-drivers/helpers.
- Embedded Live Google Maps with interactive traffic & directions.
- LIFO delivery sequence with store contacts (tap-to-call), carton counts, and exact truck positions.
- Integrated 3D truck packing view (tap any stop to highlight its cartons).
- Printable Delivery Challan / Proof of Delivery (POD) manifest with signature & stamp fields.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

try:
    from app.contracts import DispatchPlan, TruckRoute
    from app.geo.gmaps import (
        gmaps_embed_url, gmaps_route_url, gmaps_stop_nav_url, whatsapp_dispatch_url,
    )
    from app.render.anim_html import plan_to_anim_data
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan, TruckRoute
    from geo.gmaps import (
        gmaps_embed_url, gmaps_route_url, gmaps_stop_nav_url, whatsapp_dispatch_url,
    )
    from render.anim_html import plan_to_anim_data


def _hm(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


_CSS = """
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{margin:0;padding:0;background:#0a0f1d;color:#f1f5f9;font:15px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
a{color:#38bdf8;text-decoration:none}
.container{max-width:840px;margin:0 auto;padding:12px 14px 60px}

/* Top Header */
.header{background:linear-gradient(135deg,#131c35,#0f172a);border:1px solid #1e293b;border-radius:16px;padding:16px;margin-bottom:14px;box-shadow:0 8px 24px rgba(0,0,0,0.4)}
.header-top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;flex-wrap:wrap}
.brand{font-size:12px;font-weight:800;letter-spacing:0.08em;color:#38bdf8;text-transform:uppercase}
.driver-name{font-size:22px;font-weight:800;color:#fff;margin:4px 0 2px}
.truck-badge{display:inline-block;background:#1e293b;color:#94a3b8;font-size:13px;font-weight:700;padding:3px 10px;border-radius:20px;border:1px solid #334155}
.metrics-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:8px;margin-top:14px}
.metric{background:#090d16;border:1px solid #1e293b;border-radius:10px;padding:8px 10px;text-align:center}
.metric-val{font-size:17px;font-weight:800;color:#f8fafc}
.metric-lbl{font-size:11px;color:#94a3b8;text-transform:uppercase;font-weight:600;margin-top:2px}

/* Action Bar */
.actions{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:12px 18px;border-radius:14px;font-size:14px;font-weight:800;cursor:pointer;border:none;transition:transform 0.1s,opacity 0.2s}
.btn:active{transform:scale(0.98)}
.btn-primary{background:linear-gradient(135deg,#22c55e,#16a34a);color:#fff;flex:2;min-width:220px;box-shadow:0 4px 14px rgba(34,197,94,0.35);font-size:15px}
.btn-whatsapp{background:#25d366;color:#fff;flex:1;min-width:140px;box-shadow:0 4px 14px rgba(37,211,102,0.25)}
.btn-outline{background:#1e293b;color:#cbd5e1;border:1px solid #334155;flex:1;min-width:110px}

/* Tabs */
.tabs{display:flex;gap:6px;background:#0f172a;border:1px solid #1e293b;border-radius:14px;padding:4px;margin-bottom:16px}
.tab-btn{flex:1;background:transparent;color:#94a3b8;border:none;border-radius:10px;padding:10px 8px;font-size:13.5px;font-weight:700;cursor:pointer;text-align:center;transition:background 0.2s,color 0.2s}
.tab-btn.active{background:#1e293b;color:#38bdf8;box-shadow:0 2px 8px rgba(0,0,0,0.3)}

/* Tab Panes */
.tab-pane{display:none}
.tab-pane.active{display:block}

/* Delivery Cards */
.stop-card{background:#111827;border:1px solid #1f2937;border-radius:14px;padding:16px;margin-bottom:12px;position:relative;transition:border-color 0.2s}
.stop-card.delivered{opacity:0.65;border-color:#16a34a;background:#06140d}
.stop-card-header{display:flex;align-items:flex-start;gap:12px}
.stop-num{display:flex;align-items:center;justify-content:center;width:34px;height:34px;border-radius:17px;background:#38bdf8;color:#0b1120;font-size:16px;font-weight:900;flex-shrink:0}
.stop-card.delivered .stop-num{background:#22c55e;color:#fff}
.stop-title{font-size:17px;font-weight:800;color:#fff;line-height:1.3}
.stop-address{font-size:13.5px;color:#94a3b8;margin-top:2px}
.stop-details{display:grid;grid-template-columns:1fr 1fr;gap:8px 12px;margin:12px 0 14px;background:#0b1120;padding:10px 12px;border-radius:10px;font-size:13px}
.detail-item span{color:#64748b;font-size:11px;display:block;text-transform:uppercase;font-weight:700}
.detail-item b{color:#e2e8f0;font-weight:700}
.zone-pill{display:inline-block;padding:3px 8px;border-radius:6px;font-size:11.5px;font-weight:800;background:#1e293b;color:#facc15;border:1px solid #475569}
.fragile-pill{display:inline-block;padding:3px 8px;border-radius:6px;font-size:11.5px;font-weight:800;background:#7f1d1d;color:#fca5a5;border:1px solid #991b1b;margin-left:4px}
.stop-actions{display:flex;gap:8px;flex-wrap:wrap}
.btn-nav{background:#0284c7;color:#fff;border:none;border-radius:10px;padding:9px 14px;font-size:13px;font-weight:700;display:inline-flex;align-items:center;gap:6px;cursor:pointer}
.btn-call{background:#1e293b;color:#cbd5e1;border:1px solid #334155;border-radius:10px;padding:9px 12px;font-size:13px;font-weight:700;display:inline-flex;align-items:center;gap:6px}
.pod-toggle{margin-left:auto;display:inline-flex;align-items:center;gap:6px;font-size:13px;font-weight:700;color:#94a3b8;cursor:pointer;user-select:none}
.pod-checkbox{width:20px;height:20px;accent-color:#22c55e;cursor:pointer}

/* Embedded Map */
.map-wrap{border-radius:14px;overflow:hidden;border:1px solid #1e293b;height:480px;position:relative;background:#090d16}
.map-iframe{width:100%;height:100%;border:none}

/* 3D Loading Frame */
.embed-3d{width:100%;height:520px;border:1px solid #1e293b;border-radius:14px;overflow:hidden}

/* Print Only Styles */
@media print{
  body{background:#fff;color:#000;font-size:12px}
  .actions,.tabs,.map-wrap,.embed-3d,.btn-nav,.btn-call{display:none !important}
  .tab-pane{display:block !important}
  .container{max-width:100%;padding:0}
  .header{background:#fff;border:1px solid #000;color:#000;padding:10px;box-shadow:none}
  .driver-name{color:#000;font-size:18px}
  .stop-card{background:#fff;border:1px solid #ccc;color:#000;page-break-inside:avoid;margin-bottom:8px;padding:8px}
  .stop-title{color:#000}
  .stop-details{background:#f8f9fa;color:#000}
  .stop-details b{color:#000}
  .stop-num{background:#000;color:#fff}
  .pod-signature-box{display:block !important;border-top:1px dashed #999;margin-top:8px;padding-top:6px;display:flex;justify-content:space-between}
}
.pod-signature-box{display:none}
"""


def build_driver_portal_html(
    plan: DispatchPlan,
    truck_id: str,
    share_url: str = "",
) -> str:
    """Build a standalone, responsive Driver Run Sheet & Live Google Maps Mobile Portal."""
    r = next((x for x in plan.routes if x.truck_id.lower() == truck_id.lower()), None)
    if r is None:
        return f"<html><body><h3>Truck {html.escape(truck_id)} not in plan.</h3></body></html>"

    lp = plan.loads.get(r.truck_id)
    hub_coords = (plan.hub.lat, plan.hub.lon)
    stop_coords = [(rs.stop.lat, rs.stop.lon) for rs in r.stops]

    # Generate Google Maps universal directions URL (with live traffic)
    gmaps_nav = gmaps_route_url(hub_coords, stop_coords, return_to_hub=True)
    gmaps_embed = gmaps_embed_url(hub_coords, stop_coords, return_to_hub=True)

    # Stops summary for WhatsApp
    stops_summary = [
        {
            "seq": rs.seq,
            "name": rs.stop.name,
            "area": rs.stop.address.split(", ")[-1] or rs.stop.area,
            "n": len(rs.stop.boxes),
            "eta": _hm(rs.arrive_min),
        }
        for rs in r.stops
    ]
    whatsapp_url = whatsapp_dispatch_url(
        driver_name=r.driver,
        truck_id=r.truck_id,
        truck_type=r.truck_type.name.split("(")[0].strip(),
        hub_name=plan.hub.name,
        leave_time=_hm(r.start_min),
        back_time=_hm(r.end_min),
        stops_summary=stops_summary,
        gmaps_url=gmaps_nav,
        driver_portal_url=share_url,
    )

    zones = {z.stop_seq: z for z in lp.zones} if lp else {}
    inner_l = lp.truck_type.inner_l_cm if lp else 500

    # Build Stop Cards
    cards_html = []
    for rs in r.stops:
        s = rs.stop
        z = zones.get(rs.seq)
        if z:
            dist_from_door = max(0, inner_l - z.x_end)
            if dist_from_door < 90:
                pos_badge = f'<span class="zone-pill">🚪 Rear Door ({dist_from_door:.0f}–{inner_l - z.x_start:.0f} cm) · FIRST OFF</span>'
            elif dist_from_door > inner_l - 120:
                pos_badge = f'<span class="zone-pill">🚛 Cab Wall ({dist_from_door:.0f}–{inner_l - z.x_start:.0f} cm) · LAST OFF</span>'
            else:
                pos_badge = f'<span class="zone-pill">📦 Middle ({dist_from_door:.0f}–{inner_l - z.x_start:.0f} cm)</span>'
        else:
            pos_badge = '<span class="zone-pill">📦 Standard</span>'

        fragile_count = sum(1 for b in s.boxes if b.fragile)
        frag_badge = f'<span class="fragile-pill">⚠️ {fragile_count} Fragile</span>' if fragile_count else ""
        stop_gmaps_url = gmaps_stop_nav_url(s.lat, s.lon)
        total_kg = sum(b.weight_kg for b in s.boxes)

        # SKUs list
        skus = {}
        for bx in s.boxes:
            skus[bx.description] = skus.get(bx.description, 0) + 1
        sku_str = ", ".join(f"{cnt}× {d}" for d, cnt in sorted(skus.items(), key=lambda kv: -kv[1])[:3])

        # Pseudo phone for demo
        phone = f"+91 98200 {(rs.seq * 137) % 90000 + 10000}"

        card = f"""
        <div class="stop-card" id="card-{rs.seq}">
          <div class="stop-card-header">
            <div class="stop-num">{rs.seq}</div>
            <div style="flex:1;min-width:0">
              <div class="stop-title">{html.escape(s.name)}</div>
              <div class="stop-address">{html.escape(s.address)}</div>
            </div>
          </div>
          <div class="stop-details">
            <div class="detail-item"><span>ETA & Window</span><b>{_hm(rs.arrive_min)}–{_hm(rs.depart_min)} ({_hm(s.window_start_min)}–{_hm(s.window_end_min)})</b></div>
            <div class="detail-item"><span>Cartons & Weight</span><b>{len(s.boxes)} ctns · {total_kg:,.0f} kg</b></div>
            <div class="detail-item"><span>Truck Location</span>{pos_badge}{frag_badge}</div>
            <div class="detail-item"><span>Consignment</span><b>{html.escape(sku_str)}</b></div>
          </div>
          <div class="stop-actions">
            <a href="{stop_gmaps_url}" target="_blank" class="btn-nav">📍 Navigate in Google Maps</a>
            <a href="tel:{phone.replace(' ', '')}" class="btn-call">📞 Call Store ({phone})</a>
            <label class="pod-toggle">
              <input type="checkbox" class="pod-checkbox" onchange="toggleDelivered({rs.seq}, this.checked)">
              <span>Delivered ✅</span>
            </label>
          </div>
          <div class="pod-signature-box">
            <div>Receiver Sign: ___________________</div>
            <div>Store Stamp: [ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; ]</div>
            <div>Time: _______</div>
          </div>
        </div>
        """
        cards_html.append(card)

    total_cartons = sum(len(rs.stop.boxes) for rs in r.stops)
    total_weight = sum(sum(b.weight_kg for b in rs.stop.boxes) for rs in r.stops)

    # Inlined 3D JSON payload for the 3D tab
    anim_data = plan_to_anim_data(plan, focus_truck_id=r.truck_id, mode="load", only_truck=r.truck_id, start="load")
    anim_payload = json.dumps(anim_data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    engine_js = (Path(__file__).parent / "anim" / "engine.js").read_text(encoding="utf-8")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
  <title>FleetFlow · {html.escape(r.driver)} · {r.truck_id}</title>
  <style>{_CSS}</style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <div class="header">
      <div class="header-top">
        <div>
          <div class="brand">FleetFlow Smart Dispatch</div>
          <div class="driver-name">🚚 {html.escape(r.driver)}</div>
          <span class="truck-badge">{html.escape(r.truck_id)} · {html.escape(r.truck_type.name)}</span>
        </div>
        <div style="text-align:right">
          <div style="font-size:12px;color:#94a3b8">Departure Hub</div>
          <div style="font-size:14px;font-weight:700;color:#f8fafc">{html.escape(plan.hub.name)}</div>
          <div style="font-size:12px;color:#38bdf8;font-weight:700">Leave {_hm(r.start_min)} · Back {_hm(r.end_min)}</div>
        </div>
      </div>
      <div class="metrics-grid">
        <div class="metric"><div class="metric-val">{len(r.stops)}</div><div class="metric-lbl">Drops</div></div>
        <div class="metric"><div class="metric-val">{total_cartons}</div><div class="metric-lbl">Cartons</div></div>
        <div class="metric"><div class="metric-val">{total_weight:,.0f} kg</div><div class="metric-lbl">Payload</div></div>
        <div class="metric"><div class="metric-val">{r.km:.0f} km</div><div class="metric-lbl">Road Distance</div></div>
      </div>
    </div>

    <!-- Quick Action Bar -->
    <div class="actions">
      <a href="{gmaps_nav}" target="_blank" class="btn btn-primary">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>
        Start Google Maps (Live Traffic)
      </a>
      <a href="{whatsapp_url}" target="_blank" class="btn btn-whatsapp">
        💬 WhatsApp
      </a>
      <button onclick="window.print()" class="btn btn-outline">
        🖨️ Print Manifest
      </button>
    </div>

    <!-- Navigation Tabs -->
    <div class="tabs">
      <button class="tab-btn active" onclick="switchTab('stops')">📋 Delivery Stops ({len(r.stops)})</button>
      <button class="tab-btn" onclick="switchTab('map')">🗺️ Live Google Map</button>
      <button class="tab-btn" onclick="switchTab('3d')">📦 3D Loading Plan</button>
    </div>

    <!-- Tab 1: Delivery Stops (LIFO Unload Order) -->
    <div id="tab-stops" class="tab-pane active">
      <div style="background:#131c35;border:1px solid #1e293b;border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:13px;color:#93c5fd">
        ℹ️ <b>Unload in this order (1 → {len(r.stops)}):</b> Stop 1 is right at the rear door. Check off each store as you deliver.
      </div>
      {''.join(cards_html)}
    </div>

    <!-- Tab 2: Embedded Live Google Map -->
    <div id="tab-map" class="tab-pane">
      <div style="margin-bottom:10px;display:flex;justify-content:space-between;align-items:center">
        <span style="font-size:13px;color:#94a3b8">Interactive Google Map with live traffic layer:</span>
        <a href="{gmaps_nav}" target="_blank" style="font-size:13px;font-weight:700;color:#38bdf8">Open in App ↗</a>
      </div>
      <div class="map-wrap">
        <iframe class="map-iframe" src="{gmaps_embed}" loading="lazy" allowfullscreen></iframe>
      </div>
    </div>

    <!-- Tab 3: Interactive 3D Loading View -->
    <div id="tab-3d" class="tab-pane">
      <div style="background:#131c35;border:1px solid #1e293b;border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:13px;color:#93c5fd">
        📦 <b>Truck Packing Layout:</b> Loaded from cab wall to rear door. Click any store to see where its boxes sit.
      </div>
      <div id="lp-app" class="embed-3d"></div>
    </div>
  </div>

  <script>
    function switchTab(id) {{
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + id).classList.add('active');
      event.target.classList.add('active');
    }}

    function toggleDelivered(seq, isDone) {{
      var card = document.getElementById('card-' + seq);
      if (card) {{
        card.classList.toggle('delivered', isDone);
      }}
      try {{
        localStorage.setItem('lp_del_' + seq, isDone ? '1' : '0');
      }} catch(e) {{}}
    }}

    // Restore delivery check states
    document.addEventListener('DOMContentLoaded', function() {{
      for (var i = 1; i <= {len(r.stops)}; i++) {{
        try {{
          if (localStorage.getItem('lp_del_' + i) === '1') {{
            var cb = document.querySelector('#card-' + i + ' .pod-checkbox');
            if (cb) {{ cb.checked = true; toggleDelivered(i, true); }}
          }}
        }} catch(e) {{}}
      }}
    }});

    // Initialize 3D Engine
    window.LP = {anim_payload};
    window.LP_MODE = 'load';
  </script>
  <script>{engine_js}</script>
</body>
</html>
"""
