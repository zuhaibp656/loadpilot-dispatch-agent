"""Background media publishing: full-screen animated HTML + loader MP4 + poster PNG.

Links are computed up-front (V4 signing does not need the object to exist) so the Markdown report
can reference them immediately; rendering/uploading runs in a thread that the after_agent callback
joins before emitting the surface (so the Video component URL resolves).
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any

try:
    from app.contracts import DispatchPlan
    from app.render.anim_html import build_anim_html
    from app.render.publish import links_for, upload_bytes
    from app.render.video_mp4 import render_loading_mp4, render_poster_png
except ImportError:  # pragma: no cover
    from contracts import DispatchPlan
    from render.anim_html import build_anim_html
    from render.publish import links_for, upload_bytes
    from render.video_mp4 import render_loading_mp4, render_poster_png

logger = logging.getLogger(__name__)


def media_enabled() -> bool:
    return os.environ.get("LOADPILOT_PUBLISH_MEDIA", "true").lower() not in ("0", "false", "no")


def start_publishing(sess: dict[str, Any], plan: DispatchPlan, focus: str | None,
                     only_truck: str | None = None) -> dict[str, str]:
    """Kick off rendering+upload; return {'html','video'} browser links (may be empty).

    only_truck: driver view (that truck's route + load only).
    """
    route = next((r for r in plan.routes if r.truck_id == focus), None)
    lp = plan.loads.get(focus) if focus else None
    sess["poster"] = None
    links: dict[str, str] = {}
    html_obj = f"plans/{plan.plan_id}/{'driver' if only_truck else 'dispatch'}_{focus or 'all'}.html"
    mp4_obj = f"plans/{plan.plan_id}/loading_{focus}.mp4"
    if media_enabled():
        h, v = links_for(html_obj), links_for(mp4_obj)
        links = {"html": h["signed"] or h["auth"], "video": (v["signed"] or v["auth"]) if lp else "",
                 "video_signed": v["signed"] if lp else "", "html_auth": h["auth"]}

    def work() -> None:
        try:
            if route and lp:
                sess["poster"] = render_poster_png(route, lp)
            if not media_enabled():
                return
            if only_truck:
                try:
                    from app.render.driver_portal_html import build_driver_portal_html
                except ImportError:
                    from render.driver_portal_html import build_driver_portal_html
                html = build_driver_portal_html(plan, only_truck, share_url=links.get("html", ""))
            else:
                html = build_anim_html(plan, mode="both", focus_truck_id=focus, only_truck=only_truck)
            ok = upload_bytes(html.encode("utf-8"), html_obj, "text/html; charset=utf-8")
            if not ok:
                links.clear()
                return
            if route and lp:
                upload_bytes(render_loading_mp4(route, lp), mp4_obj, "video/mp4")
        except Exception as exc:  # pragma: no cover
            logger.warning("media publishing failed: %s", exc)

    t = threading.Thread(target=work, name=f"lp-media-{plan.plan_id}", daemon=True)
    t.start()
    sess["media_thread"] = t
    return links


def start_briefings(sess: dict[str, Any], plan: DispatchPlan) -> dict[str, str]:
    """Publish one driver page per truck (route + tap-a-store 3D load). Returns {truck_id: url}."""
    out: dict[str, str] = {}
    if not media_enabled():
        return out
    objs = {r.truck_id: f"plans/{plan.plan_id}/driver_{r.truck_id}.html" for r in plan.routes}
    for tid, obj in objs.items():
        lk = links_for(obj)
        out[tid] = lk["signed"] or lk["auth"]

    def work() -> None:
        try:
            for tid, obj in objs.items():
                try:
                    from app.render.driver_portal_html import build_driver_portal_html
                except ImportError:
                    from render.driver_portal_html import build_driver_portal_html
                html = build_driver_portal_html(plan, tid, share_url=out.get(tid, ""))
                upload_bytes(html.encode("utf-8"), obj, "text/html; charset=utf-8")
        except Exception as exc:  # pragma: no cover
            logger.warning("briefing publishing failed: %s", exc)


    t = threading.Thread(target=work, name=f"lp-brief-{plan.plan_id}", daemon=True)
    t.start()
    sess["brief_thread"] = t
    return out


def wait_publishing(sess: dict[str, Any], timeout: float = 75.0) -> None:
    for key in ("media_thread", "brief_thread"):
        t = sess.get(key)
        if t is not None:
            t.join(timeout)
