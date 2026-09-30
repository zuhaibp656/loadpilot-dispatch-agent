"""LoadPilot root agent: truck LIFO loading + corridor route optimisation for retail / CPG dispatch.

In : chat ("plan today's dispatch", "Ravi has the West route", "show T17-1"), the planning form
     (A2UI `optimiseDispatch` button action), pasted/attached order lists, carton photos.
Out: a short model headline + deterministic Markdown report (tables <= 5 cols, headed links) +
     an A2UI surface (planning wizard, or the dispatch Canvas with route / 3D loading animations).
Rule: the model never authors UI or numbers tables; Python callbacks attach them deterministically.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import uuid
from typing import Any

if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "zuhaibp-ai")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

import google.auth
import google.oauth2.credentials
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

_ARGOLIS_ADC = os.path.expanduser("~/.config/gcloud/argolis_admin_adc.json")


class _GcloudCliCredentials(google.oauth2.credentials.Credentials):
    """Self-refreshing OAuth2 credentials backed by Argolis ADC or `gcloud auth print-access-token`."""

    def __init__(self) -> None:
        super().__init__(token=self._fetch())

    @staticmethod
    def _fetch() -> str:
        if os.path.exists(_ARGOLIS_ADC):
            from google.auth.transport.requests import Request
            c = google.oauth2.credentials.Credentials.from_authorized_user_file(
                _ARGOLIS_ADC, scopes=["https://www.googleapis.com/auth/cloud-platform"])
            c.refresh(Request())
            return c.token
        return subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()

    def refresh(self, request: Any) -> None:
        self.token = self._fetch()


_ORIG_GOOGLE_AUTH_DEFAULT = google.auth.default


def _patched_google_auth_default(*args: Any, **kwargs: Any) -> tuple[Any, str | None]:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or "zuhaibp-ai"
    if os.path.exists(_ARGOLIS_ADC):
        try:
            from google.auth.transport.requests import Request
            c = google.oauth2.credentials.Credentials.from_authorized_user_file(
                _ARGOLIS_ADC, scopes=["https://www.googleapis.com/auth/cloud-platform"])
            c.refresh(Request())
            return c, project
        except Exception:
            pass
    return _ORIG_GOOGLE_AUTH_DEFAULT(*args, **kwargs)


if os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "FALSE").upper() == "TRUE" and os.path.exists(_ARGOLIS_ADC):
    google.auth.default = _patched_google_auth_default

try:
    from app.contracts import Objective
    from app.data.master_data import TRUCK_CATALOGUE
    from app.integration.media import wait_publishing
    from app.integration.tools import (
        ALL_TOOLS, PENDING_KEY, params_from_state, parse_claims, save_params, session,
    )
    from app.render.a2ui_envelope import A2A_DATA_PART_CLOSE_TAG, A2A_DATA_PART_OPEN_TAG
    from app.render.markdown import dispatch_markdown, truck_markdown
    from app.render.surfaces import WIZARD_EVENT, build_dispatch_surface, build_wizard_surface
except ImportError:  # pragma: no cover
    from contracts import Objective
    from data.master_data import TRUCK_CATALOGUE
    from integration.media import wait_publishing
    from integration.tools import (
        ALL_TOOLS, PENDING_KEY, params_from_state, parse_claims, save_params, session,
    )
    from render.a2ui_envelope import A2A_DATA_PART_CLOSE_TAG, A2A_DATA_PART_OPEN_TAG
    from render.markdown import dispatch_markdown, truck_markdown
    from render.surfaces import WIZARD_EVENT, build_dispatch_surface, build_wizard_surface

logger = logging.getLogger(__name__)

MODEL: str = os.environ.get("LOADPILOT_MODEL", "gemini-2.5-flash")
IS_LOCAL = os.path.exists(os.path.expanduser("~/.config/gcloud")) and not os.environ.get("K_SERVICE") \
    and not os.environ.get("GOOGLE_CLOUD_AGENT_ENGINE_ID")
WIZARD_NOTE = "[Planning form submitted: optimiseDispatch with the form values]"


# ==============================================================================
# Wizard action parsing (A2UI Button event -> new user turn)
# ==============================================================================
def _iter_json_objects(text: str):
    dec = json.JSONDecoder()
    i = 0
    while True:
        j = text.find("{", i)
        if j == -1:
            return
        try:
            obj, end = dec.raw_decode(text[j:])
            yield obj
            i = j + end
        except ValueError:
            i = j + 1


def _find_form(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        if any(k.startswith("n_") for k in obj) or {"objective", "types"} <= set(obj):
            return obj
        for v in obj.values():
            f = _find_form(v)
            if f is not None:
                return f
    elif isinstance(obj, list):
        for v in obj:
            f = _find_form(v)
            if f is not None:
                return f
    return None


def extract_wizard_form(content: types.Content | None) -> dict[str, Any] | None:
    if content is None or not content.parts:
        return None
    blobs: list[str] = []
    for p in content.parts:
        if getattr(p, "text", None):
            blobs.append(p.text)
        inline = getattr(p, "inline_data", None)
        if inline is not None and inline.data and "json" in (inline.mime_type or "") + "text":
            try:
                blobs.append(inline.data.decode("utf-8", errors="ignore"))
            except Exception:
                pass
    for text in blobs:
        if WIZARD_EVENT not in text and "n_T17" not in text:
            continue
        for obj in _iter_json_objects(text):
            form = _find_form(obj)
            if form is not None:
                return form
    return None


def _first(v: Any) -> str:
    if isinstance(v, list):
        return str(v[0]) if v else ""
    if isinstance(v, dict):
        return str(v.get("value", v.get("literalString", "")))
    return "" if v is None else str(v)


def _num(v: Any) -> float:
    try:
        return float(re.sub(r"[^\d.]", "", _first(v)) or 0)
    except ValueError:
        return 0.0


def apply_wizard_form(state: Any, form: dict[str, Any]) -> None:
    p = params_from_state(state)
    date = _first(form.get("date"))
    if date:
        p.dispatch_date = date[:10]
        m = re.search(r"T(\d{2}):(\d{2})", date)
        if m:
            p.shift_start_min = int(m.group(1)) * 60 + int(m.group(2))
    if _first(form.get("hub")):
        p.hub_id = _first(form.get("hub"))
    if _first(form.get("source")):
        p.order_source = _first(form.get("source"))
    types_sel = form.get("types")
    types_sel = set(types_sel) if isinstance(types_sel, list) and types_sel else set(TRUCK_CATALOGUE)
    counts = {c: int(_num(form.get(f"n_{c}"))) for c in TRUCK_CATALOGUE if c in types_sel}
    counts = {c: n for c, n in counts.items() if n > 0}
    if counts:
        p.truck_counts = counts
    obj = _first(form.get("objective"))
    if obj in {o.value for o in Objective}:
        p.objective = Objective(obj)
    p.corridor_claims = parse_claims(_first(form.get("claims")))
    p.fuel_price_per_litre = _num(form.get("fuel")) or None
    p.driver_day_cost = _num(form.get("driver")) or None
    save_params(state, p)


# ==============================================================================
# Callbacks
# ==============================================================================
def capture_user_turn(callback_context: CallbackContext | None = None, **_: Any) -> None:
    """before_agent: stash attachments for tools and apply a submitted planning form."""
    if callback_context is None:
        return None
    content = callback_context.user_content
    sess = session(callback_context.state)
    atts = []
    if content and content.parts:
        for p in content.parts:
            inline = getattr(p, "inline_data", None)
            if inline is not None and inline.data and not (inline.mime_type or "").startswith("text/plain"):
                if "json" in (inline.mime_type or "") and WIZARD_EVENT.encode() in inline.data:
                    continue
                atts.append((inline.data, inline.mime_type or "", getattr(inline, "display_name", "") or ""))
    sess["attachments"] = atts
    form = extract_wizard_form(content)
    if form is not None:
        apply_wizard_form(callback_context.state, form)
        callback_context.state["lp_form_submitted"] = True
    else:
        callback_context.state["lp_form_submitted"] = False
    return None


def _remove_datapart_blobs(text: str) -> str:
    out: list[str] = []
    rest = text
    while True:
        start = rest.find(A2A_DATA_PART_OPEN_TAG)
        if start == -1:
            out.append(rest)
            return "".join(out)
        out.append(rest[:start])
        end = rest.find(A2A_DATA_PART_CLOSE_TAG, start)
        if end == -1:
            return "".join(out)
        rest = rest[end + len(A2A_DATA_PART_CLOSE_TAG):]


def sanitize_llm_request_history(callback_context: CallbackContext | None = None,
                                 llm_request: LlmRequest | None = None, **_: Any) -> None:
    """before_model: drop A2UI blobs and old images; turn a form submission into a clear note."""
    if llm_request is None or not llm_request.contents:
        return None
    last_user = max((i for i, c in enumerate(llm_request.contents) if c.role == "user"), default=-1)
    for i, content in enumerate(llm_request.contents):
        if not content.parts:
            continue
        cleaned: list[types.Part] = []
        for part in content.parts:
            inline = getattr(part, "inline_data", None)
            if inline is not None:
                mime = inline.mime_type or ""
                if i == last_user and mime.startswith("image/") and len(inline.data or b"") < 4_000_000:
                    cleaned.append(part)
                elif i == last_user and not mime.startswith("image/") and inline.data \
                        and WIZARD_EVENT.encode() in inline.data:
                    cleaned.append(types.Part(text=WIZARD_NOTE))
                elif i == last_user:
                    cleaned.append(types.Part(text=f"[attached file: {mime}]"))
                continue
            text = getattr(part, "text", None)
            if text and (A2A_DATA_PART_OPEN_TAG in text or WIZARD_EVENT in text):
                if WIZARD_EVENT in text and content.role == "user":
                    cleaned.append(types.Part(text=WIZARD_NOTE))
                    continue
                stripped = _remove_datapart_blobs(text)
                if stripped.strip():
                    cleaned.append(types.Part(text=stripped))
            else:
                cleaned.append(part)
        content.parts = cleaned or [types.Part(text="[visual surface rendered in UI]")]
    cfg = llm_request.config or types.GenerateContentConfig()
    cfg.max_output_tokens = 4096
    cfg.temperature = 0.0
    cfg.thinking_config = types.ThinkingConfig(thinking_budget=0)
    llm_request.config = cfg
    return None


def _headline_only(text: str) -> str:
    """Keep the model's headline bullets; drop any tables/headings it wrote (the verified report
    that follows is the single source of truth)."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith(("#", "|", "---", "```")):
            break
        out.append(line)
    return "\n".join(out).rstrip()


def append_report(callback_context: CallbackContext | None = None,
                  llm_response: LlmResponse | None = None, **_: Any) -> LlmResponse | None:
    """after_model: strip fabricated A2UI; on the final text turn append the deterministic report."""
    if llm_response is None or llm_response.content is None:
        return None
    parts = llm_response.content.parts or []
    has_call = any(getattr(p, "function_call", None) is not None for p in parts)
    cleaned: list[types.Part] = []
    for p in parts:
        t = getattr(p, "text", None)
        if t and A2A_DATA_PART_OPEN_TAG in t:
            t = _remove_datapart_blobs(t)
            if t.strip():
                cleaned.append(types.Part(text=t))
        else:
            cleaned.append(p)
    if has_call or callback_context is None:
        llm_response.content.parts = cleaned
        return llm_response
    pending = callback_context.state.get(PENDING_KEY) or {}
    sess = session(callback_context.state)
    plan = sess.get("plan")
    extra = ""
    if plan is not None and pending.get("kind") == "dispatch":
        extra = dispatch_markdown(plan, sess.get("links"), pending.get("focus"))
    elif plan is not None and pending.get("kind") == "truck":
        extra = truck_markdown(plan, pending.get("focus", ""))
        links = sess.get("links") or {}
        if links.get("video") or links.get("html"):
            extra += "\n---\n\n### Share with the dock team\n"
            if links.get("video"):
                extra += f"\n🎬 **[Loader video · {pending.get('focus')} (MP4) ↗]({links['video']})**\n"
            if links.get("html"):
                extra += f"\n👉 **[Full-screen 3D loading animation ↗]({links['html']})**\n"
    if extra:
        idx = max((i for i, p in enumerate(cleaned) if getattr(p, "text", None)), default=-1)
        if idx >= 0:
            cleaned[idx] = types.Part(text=_headline_only(cleaned[idx].text or "") + extra)
        else:
            cleaned.append(types.Part(text=extra.lstrip()))
    llm_response.content.parts = cleaned
    return llm_response


def emit_surface(callback_context: CallbackContext | None = None, **_: Any) -> types.Content | None:
    """after_agent: attach the queued A2UI surface (wizard or dispatch canvas)."""
    if callback_context is None:
        return None
    pending = callback_context.state.get(PENDING_KEY)
    if not pending:
        return None
    callback_context.state[PENDING_KEY] = None
    sess = session(callback_context.state)
    surface_id = f"lp-{uuid.uuid4().hex[:8]}"
    parts: list[types.Part] = []
    try:
        if pending.get("kind") == "wizard":
            from app.data.master_data import DEFAULT_COST_PROFILE as cp
            p = params_from_state(callback_context.state)
            parts += build_wizard_surface(surface_id, p, p.fuel_price_per_litre or cp.fuel_price_per_litre,
                                          p.driver_day_cost or cp.driver_day_cost)
        else:
            plan = sess.get("plan")
            if plan is None:
                return None
            wait_publishing(sess)
            links = sess.get("links") or {}
            if IS_LOCAL and sess.get("poster"):
                parts.append(types.Part.from_bytes(data=sess["poster"], mime_type="image/png"))
            parts += build_dispatch_surface(surface_id, plan, video_url=links.get("video") or None,
                                            focus_truck_id=pending.get("focus"))
    except Exception as exc:
        logger.exception("emit_surface failed: %s", exc)
    if not parts:
        return None
    return types.Content(role="model", parts=parts)


INSTRUCTION = """You are LoadPilot, a dispatch co-pilot for retail / CPG distribution (paints, FMCG,
apparel, electronics, building materials). Each morning trucks leave a hub with 8-12 fixed
deliveries. You (1) group stops into corridors so no two trucks drive the same road, (2) choose the
truck mix and stop order, (3) load each truck LIFO (last delivery at the cab, first delivery at the
door) and (4) cost the plan against today's manual, area-based plan.

TOOLS
- show_planning_wizard: when the user wants to start / set up planning, or no fleet info is given.
- plan_dispatch: to optimise. Pass only values the user states (truck counts, objective, claims,
  diesel/driver cost, hub, date, order source). If the user message is
  "[Planning form submitted: optimiseDispatch ...]", call plan_dispatch() with NO arguments.
- claim_corridor: "Ravi has the West route" / "give T20-1 the north-east".
- get_truck_load_plan: loading sheet / animation / video for one truck or driver.
- ingest_delivery_orders: the user pastes or attaches an order list (email, CSV, Excel, PDF).
  Then call plan_dispatch(order_source="chat").
- scan_box_manifest: the user attaches carton / label photos. Then plan_dispatch(order_source="photos").
- list_fleet_and_costs, reset_to_demo_data: as named.
If the user says "plan today's dispatch" (or similar) with no details, call plan_dispatch() directly.

RESPONSE RULES (strict)
- After tools finish, write ONLY a 3-bullet headline (<= 60 words total) using the tool's numbers:
  trucks today vs LoadPilot, INR saved per day (and %), and one operational insight (claims,
  branches, LIFO). No tables, no links, no JSON, no UI markup; the detailed report, tables, links
  and the visual dispatch canvas are attached automatically after your text.
- For the wizard: one sentence telling the user to fill the form and press Optimise.
- Never invent numbers. Currency is INR (₹). Never write loading sheets, per-stop lists, weights
  or volumes yourself; the verified loading sheet is attached automatically.
"""

root_agent = Agent(
    name="loadpilot_agent",
    description="LoadPilot: truck LIFO loading + corridor route optimisation with cost savings for "
                "retail / CPG dispatch, with animated 3D loading and route plans.",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=4096, temperature=0.0,
        thinking_config=types.ThinkingConfig(thinking_budget=0)),
    instruction=INSTRUCTION,
    tools=ALL_TOOLS,
    before_agent_callback=capture_user_turn,
    before_model_callback=sanitize_llm_request_history,
    after_model_callback=append_report,
    after_agent_callback=emit_surface,
)

app = App(root_agent=root_agent, name="loadpilot_agent")

try:
    from vertexai.preview.reasoning_engines import AdkApp

    class LoadPilotAdkApp(AdkApp):
        """Agent Engine wrapper that pins Vertex env vars for query / stream_query."""

        def __init__(self, agent: Agent = root_agent, **kwargs: Any) -> None:
            super().__init__(agent=agent, **kwargs)

        @staticmethod
        def _env() -> None:
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
            os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "zuhaibp-ai")
            os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")

        def query(self, *args: Any, **kwargs: Any) -> Any:
            self._env()
            return super().query(*args, **kwargs)

        def stream_query(self, *args: Any, **kwargs: Any) -> Any:
            self._env()
            yield from super().stream_query(*args, **kwargs)

    def get_app() -> LoadPilotAdkApp:
        return LoadPilotAdkApp(agent=root_agent, enable_tracing=True)

except ImportError:  # pragma: no cover
    pass
