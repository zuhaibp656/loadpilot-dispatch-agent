"""Google Maps Navigation, Live Traffic integration, and Driver Share utilities.

Features:
- Official Google Maps Universal URLs (directions, turn-by-turn navigation, real-time traffic).
- Multi-stop route URL generation (Hub -> Stop 1 -> Stop 2 -> ... -> Hub) with live congestion.
- Direct 1-tap navigation URLs for individual stops.
- Keyless embedded Google Maps URL with live route & directions.
- 1-Click WhatsApp dispatch message with full itinerary, stop sequence, and direct Maps links.
"""

from __future__ import annotations

import urllib.parse
from typing import Any


def gmaps_route_url(
    hub_coords: tuple[float, float],
    stop_coords: list[tuple[float, float]],
    return_to_hub: bool = True,
    max_waypoints: int = 9,
) -> str:
    """Generate official Google Maps Universal Directions URL.

    When opened on Android/iOS, this launches the native Google Maps app with live traffic
    and turn-by-turn driving navigation.
    Google Maps Universal URL supports up to 9-10 intermediate waypoints.
    """
    if not stop_coords:
        return f"https://www.google.com/maps/dir/?api=1&destination={hub_coords[0]:.6f},{hub_coords[1]:.6f}&travelmode=driving"

    origin = f"{hub_coords[0]:.6f},{hub_coords[1]:.6f}"
    
    if return_to_hub:
        dest = origin
        # Use intermediate stops as waypoints (capped to max_waypoints)
        wps = stop_coords[:max_waypoints]
    else:
        dest = f"{stop_coords[-1][0]:.6f},{stop_coords[-1][1]:.6f}"
        wps = stop_coords[:-1][:max_waypoints]

    wps_str = "|".join(f"{lat:.6f},{lon:.6f}" for lat, lon in wps)
    params = {
        "api": "1",
        "origin": origin,
        "destination": dest,
        "travelmode": "driving",
        "dir_action": "navigate",
    }
    if wps_str:
        params["waypoints"] = wps_str

    return f"https://www.google.com/maps/dir/?{urllib.parse.urlencode(params)}"


def gmaps_stop_nav_url(lat: float, lon: float, query: str = "") -> str:
    """1-Tap turn-by-turn Google Maps navigation URL to an individual stop."""
    params = {
        "api": "1",
        "destination": f"{lat:.6f},{lon:.6f}",
        "travelmode": "driving",
        "dir_action": "navigate",
    }
    if query:
        params["destination_place_id"] = query
    return f"https://www.google.com/maps/dir/?{urllib.parse.urlencode(params)}"


def gmaps_embed_url(
    hub_coords: tuple[float, float],
    stop_coords: list[tuple[float, float]],
    return_to_hub: bool = True,
) -> str:
    """Embeddable keyless Google Maps directions iframe URL showing route and traffic."""
    saddr = f"{hub_coords[0]:.6f},{hub_coords[1]:.6f}"
    stops_to_show = stop_coords[:10]  # Limit to 10 points for clean embed query
    if not stops_to_show:
        return f"https://maps.google.com/maps?q={saddr}&z=13&output=embed"

    if return_to_hub:
        daddr = "+to:".join([f"{lat:.6f},{lon:.6f}" for lat, lon in stops_to_show] + [saddr])
    else:
        daddr = "+to:".join(f"{lat:.6f},{lon:.6f}" for lat, lon in stops_to_show)

    return f"https://maps.google.com/maps?saddr={saddr}&daddr={daddr}&output=embed"


def whatsapp_dispatch_url(
    driver_name: str,
    truck_id: str,
    truck_type: str,
    hub_name: str,
    leave_time: str,
    back_time: str,
    stops_summary: list[dict[str, Any]],
    gmaps_url: str,
    driver_portal_url: str = "",
) -> str:
    """Create a 1-click WhatsApp dispatch message URL for the driver/helper."""
    total_cartons = sum(s.get("n", 0) for s in stops_summary)
    lines = [
        f"🚚 *LoadPilot Dispatch · {driver_name}*",
        f"🚛 *Truck:* {truck_id} ({truck_type})",
        f"📍 *Hub:* {hub_name}",
        f"⏰ *Shift:* Leave {leave_time} | Return {back_time}",
        f"📦 *Consignment:* {len(stops_summary)} Drops | {total_cartons} Cartons",
        "",
        "🗺️ *Start Google Maps (Live Traffic Navigation):*",
        gmaps_url,
    ]

    if driver_portal_url:
        lines += [
            "",
            "📱 *Your Mobile Run Sheet & 3D Packing:*",
            driver_portal_url,
        ]

    lines += [
        "",
        "📋 *Delivery Sequence (LIFO Unload Order):*",
    ]

    for s in stops_summary[:12]:
        seq = s.get("seq", 1)
        name = s.get("name", "")
        area = s.get("area", "")
        n = s.get("n", 0)
        eta = s.get("eta", "")
        lines.append(f"  {seq}. *{name}* ({area}) · {n} ctns [ETA {eta}]")

    if len(stops_summary) > 12:
        lines.append(f"  ... +{len(stops_summary) - 12} more stops (see full link)")

    lines += [
        "",
        "⚠️ *Reminder:* Load cab-to-door (Stop 1 at rear door). Check fragile cartons.",
        "Drive safe! 🚦",
    ]

    msg = "\n".join(lines)
    return f"https://api.whatsapp.com/send?text={urllib.parse.quote(msg)}"
