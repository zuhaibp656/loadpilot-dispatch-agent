"""Unit tests for Google Maps integration, live traffic links, and the driver portal."""

from __future__ import annotations

from app.contracts import PlanningParams
from app.data.demo_mmr import HUBS, build_demo_stops
from app.geo.gmaps import (
    gmaps_embed_url, gmaps_route_url, gmaps_stop_nav_url, whatsapp_dispatch_url,
)
from app.optim.dispatch import plan_dispatch
from app.render.driver_portal_html import build_driver_portal_html
from app.render.markdown import briefings_markdown, driver_markdown


def test_gmaps_universal_urls():
    hub = (19.2965, 73.0620)
    stops = [(19.2403, 73.1305), (19.2183, 73.1558)]

    # Route URL
    route_url = gmaps_route_url(hub, stops, return_to_hub=True)
    assert "https://www.google.com/maps/dir/?" in route_url
    assert "origin=19.296500%2C73.062000" in route_url
    assert "destination=19.296500%2C73.062000" in route_url
    assert "waypoints=19.240300%2C73.130500%7C19.218300%2C73.155800" in route_url
    assert "travelmode=driving" in route_url
    assert "dir_action=navigate" in route_url

    # Stop nav URL
    stop_nav = gmaps_stop_nav_url(19.2403, 73.1305)
    assert "destination=19.240300%2C73.130500" in stop_nav
    assert "dir_action=navigate" in stop_nav

    # Embed URL
    embed_url = gmaps_embed_url(hub, stops, return_to_hub=True)
    assert "https://maps.google.com/maps?" in embed_url
    assert "output=embed" in embed_url
    assert "+to:" in embed_url


def test_whatsapp_dispatch_url():
    wa_url = whatsapp_dispatch_url(
        driver_name="Ramesh Kumar",
        truck_id="T17-1",
        truck_type="17 ft Truck",
        hub_name="Nelamangala Logistics Hub",
        leave_time="07:00",
        back_time="16:45",
        stops_summary=[{"seq": 1, "name": "Kalyan Retail", "area": "Kalyan", "n": 6, "eta": "08:15"}],
        gmaps_url="https://www.google.com/maps/dir/?api=1&origin=13.0,77.4",
        driver_portal_url="https://storage.googleapis.com/test/portal.html",
    )
    assert "https://api.whatsapp.com/send?text=" in wa_url
    assert "Ramesh" in wa_url
    assert "T17-1" in wa_url
    assert "google.com/maps" in wa_url


def test_driver_portal_generation():
    p = PlanningParams()
    plan = plan_dispatch(HUBS["BHW-DC"], build_demo_stops(), p)
    tid = plan.routes[0].truck_id
    html = build_driver_portal_html(plan, tid, share_url="https://storage.googleapis.com/loadpilot/driver.html")

    assert "<!doctype html>" in html
    assert plan.routes[0].driver in html
    assert "Start Google Maps" in html
    assert "https://www.google.com/maps/dir/?" in html
    assert "api.whatsapp.com" in html
    assert "window.print()" in html
    assert "pod-checkbox" in html
    assert "Delivered ✅" in html
    assert "Rear Door" in html or "Cab Wall" in html or "Middle" in html


def test_markdown_reports_include_gmaps():
    p = PlanningParams()
    plan = plan_dispatch(HUBS["BHW-DC"], build_demo_stops(), p)
    tid = plan.routes[0].truck_id

    d_md = driver_markdown(plan, tid)
    assert "Start Google Maps Navigation (Live Traffic)" in d_md
    assert "https://www.google.com/maps/dir/?" in d_md
    assert "api.whatsapp.com" in d_md

    b_md = briefings_markdown(plan)
    assert "Google Maps (Live Traffic)" in b_md
    assert "1-Click WhatsApp Dispatch Message" in b_md
    assert "Dispatch board & Share links" in b_md

    # Test single-driver scoped briefing (follow-up query)
    b_ravi = briefings_markdown(plan, driver="Ravi")
    assert "Driver instructions · Ravi" in b_ravi
    assert "Ravi" in b_ravi
    assert "Google Maps (Live Traffic)" in b_ravi
    assert "Dispatch summary · Ravi" in b_ravi
    # Must NOT include other drivers in single-driver scoped output
    assert "Suresh" not in b_ravi
    assert "Imran" not in b_ravi


def test_driver_briefings_tool_scoping():
    from unittest.mock import MagicMock
    from app.integration.tools import driver_briefings, PENDING_KEY

    ctx = MagicMock()
    ctx.state = {}

    # 1. Call driver_briefings with driver="Ravi"
    res = driver_briefings(ctx, driver="Ravi")
    assert res.get("driver") == "Ravi"
    assert "truck" in res
    assert ctx.state.get(PENDING_KEY, {}).get("driver") == "Ravi"
    assert ctx.state.get("lp_last_driver") == "Ravi"

    # 2. Conversational pronoun follow-up "his" -> resolves to Ravi
    res_pronoun = driver_briefings(ctx, driver="his")
    assert res_pronoun.get("driver") == "Ravi"

