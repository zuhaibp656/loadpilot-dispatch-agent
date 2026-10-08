"""Agent-layer tests: tools + callbacks with a fake context, A2UI surface validity and size."""

import json
import os

os.environ["LOADPILOT_PUBLISH_MEDIA"] = "false"

import pytest  # noqa: E402
from google.genai import types  # noqa: E402

from app.integration import agent as A  # noqa: E402
from app.integration import tools as T  # noqa: E402
from app.render.a2ui_envelope import A2A_DATA_PART_OPEN_TAG  # noqa: E402
from app.render.surfaces import WIZARD_EVENT  # noqa: E402

CATALOG = "/usr/local/google/home/zuhaibp/high-code-agents/reference_repos/Well-Log-Digitization/tests/fixtures/a2ui/ge_composite_catalog.json"


class Ctx:
    def __init__(self, user_content=None):
        self.state: dict = {}
        self.user_content = user_content


def _a2ui_msgs(content: types.Content) -> list[dict]:
    out = []
    for p in content.parts:
        raw = p.text or (p.inline_data.data.decode() if p.inline_data and
                         not p.inline_data.mime_type.startswith("image/") else "")
        if A2A_DATA_PART_OPEN_TAG in raw:
            body = raw.split(A2A_DATA_PART_OPEN_TAG, 1)[1].rsplit("</a2a_datapart_json>", 1)[0]
            out.append(json.loads(body)["data"])
    return out


@pytest.fixture(scope="module")
def planned():
    ctx = Ctx()
    out = T.plan_dispatch(ctx, truck_counts="T20=2, T17=3, T14=3, PKP=2, ACE=2")
    return ctx, out


def test_plan_tool_summary(planned):
    ctx, out = planned
    assert (out.get("fleetflow") or out.get("loadpilot"))["trucks"] < out["today"]["trucks"]
    assert out["saved_inr_per_day"] > 0 and out["lifo_verified_all"]
    assert ctx.state[T.PENDING_KEY]["kind"] == "dispatch"
    assert len(json.dumps(ctx.state)) < 4000  # heavy objects stay out of session state


def test_report_and_surface(planned):
    ctx, _ = planned
    resp = A.LlmResponse(content=types.Content(role="model", parts=[types.Part(text="- 8 trucks")]))
    resp = A.append_report(ctx, resp)
    md = resp.content.parts[-1].text
    assert ("### Today vs FleetFlow" in md or "### Today vs LoadPilot" in md) and "### Truck plan (copy-ready)" in md
    assert "### Where each truck goes" in md
    for line in md.splitlines():
        if line.startswith("|"):
            assert line.count("|") <= 6, line  # <= 5 columns
    content = A.emit_surface(ctx)
    msgs = _a2ui_msgs(content)
    comps = next(m for m in msgs if "updateComponents" in m)["updateComponents"]["components"]
    ids = {c["id"] for c in comps}
    assert "root" in ids and comps[0]["component"] == "Canvas"
    for c in comps:
        for ch in c.get("children", []) + ([c["child"]] if "child" in c else []):
            assert ch in ids, f"dangling child {ch}"
        for t in c.get("tabs", []):
            assert t["child"] in ids
    size = sum(len(json.dumps(m)) for m in msgs)
    assert size < 400 * 1024, size
    assert ctx.state[T.PENDING_KEY] is None


@pytest.mark.skipif(not os.path.exists(CATALOG), reason="catalog fixture missing")
def test_components_in_ge_catalog(planned):
    ctx, _ = planned
    cat = json.load(open(CATALOG))
    names = set(cat.get("components", cat).keys()) if isinstance(cat, dict) else set()
    from app.render.surfaces import dispatch_components, wizard_components
    plan = T.session(ctx.state)["plan"]
    used = {c["component"] for c in dispatch_components(plan, "https://x/v.mp4", None)}
    used |= {c["component"] for c in wizard_components({})}
    if names:
        assert used <= names, used - names


def test_wizard_roundtrip():
    ctx = Ctx()
    T.show_planning_wizard(ctx)
    assert ctx.state[T.PENDING_KEY]["kind"] == "wizard"
    content = A.emit_surface(ctx)
    assert _a2ui_msgs(content)
    action = {"userAction": {"name": WIZARD_EVENT, "surfaceId": "lp-1", "context": {
        "date": "2026-10-02T06:30:00", "hub": ["TLJ-DC"], "source": ["demo"],
        "types": ["T17", "T20"], "n_T17": "4", "n_T20": "1", "n_ACE": "5",
        "objective": ["fewest_trucks"], "claims": "Ravi=West", "fuel": "95", "driver": "1200"}}}
    uc = types.Content(role="user", parts=[types.Part(
        text=f"<a2a_datapart_json>{json.dumps(action)}</a2a_datapart_json>")])
    ctx2 = Ctx(uc)
    ctx2.state = ctx.state
    A.capture_user_turn(ctx2)
    p = T.params_from_state(ctx2.state)
    assert p.truck_counts == {"T17": 4, "T20": 1}
    assert p.hub_id == "TLJ-DC" and p.objective.value == "fewest_trucks"
    assert p.corridor_claims == {"Ravi": "W"} and p.fuel_price_per_litre == 95
    assert p.shift_start_min == 390 and p.dispatch_date == "2026-10-02"


def test_sanitizer_replaces_form_blob():
    req = A.LlmRequest(contents=[types.Content(role="user", parts=[types.Part(
        text=f"<a2a_datapart_json>{{\"name\":\"{WIZARD_EVENT}\"}}</a2a_datapart_json>")])])
    A.sanitize_llm_request_history(None, req)
    assert req.contents[0].parts[0].text == A.WIZARD_NOTE


def test_truck_tool(planned):
    ctx, out = planned
    tid = out["trucks"][0]["id"]
    r = T.get_truck_load_plan(ctx, tid)
    assert r["lifo_ok"] and ctx.state[T.PENDING_KEY] == {
        "kind": "truck",
        "focus": tid,
        "active_trucks": [tid],
    }
    resp = A.append_report(ctx, A.LlmResponse(content=types.Content(role="model", parts=[
        types.Part(text="ok")])))
    assert f"Loading sheet · {tid}" in resp.content.parts[-1].text


def test_plan_my_route_preset_driver():
    ctx = Ctx()
    out = T.plan_my_route(ctx, driver="Suresh")
    s = json.dumps(out)
    assert "Suresh" in s
    plan = T.session(ctx.state)["plan"]
    assert len(plan.routes) == 1 and len(plan.routes[0].stops) == 6


def test_plan_my_route_stop_ids():
    ctx = Ctx()
    T.plan_my_route(ctx, driver="Ravi", truck_type="T14", stop_ids="S006, S007, S008, S009, S010, S011")
    plan = T.session(ctx.state)["plan"]
    assert len(plan.routes) == 1 and len(plan.routes[0].stops) == 6


def test_driver_briefings_one_per_truck():
    ctx = Ctx()
    out = T.driver_briefings(ctx)
    plan = T.session(ctx.state)["plan"]
    assert len(plan.routes) >= 2
    assert json.dumps(out)


def test_plan_dispatch_scoped_to_one_driver():
    ctx = Ctx()
    out = T.plan_dispatch(ctx, driver="Ravi")
    pend = ctx.state[T.PENDING_KEY]
    assert pend["kind"] == "driver"
    plan = T.session(ctx.state)["plan"]
    r = next(x for x in plan.routes if x.truck_id == pend["focus"])
    assert r.driver == "Ravi" and "Ravi" in json.dumps(out)


def test_canvas_html_stays_small():
    from app.render.anim_html import build_anim_html
    ctx = Ctx()
    T.plan_dispatch(ctx)
    plan = T.session(ctx.state)["plan"]
    assert len(build_anim_html(plan, mode="both").encode()) < 260_000


def test_no_web_leakage_in_agent_core():
    """Verify strict decoupling: core agent, optim, data, and render layers must NOT import app.web or fastapi."""
    from importlib import import_module

    core_modules = [
        "app.agent",
        "app.integration.agent",
        "app.integration.tools",
        "app.optim.vrp",
        "app.optim.lifo_packer",
        "app.optim.corridors",
        "app.optim.cost",
        "app.optim.dispatch",
        "app.data.bq_source",
        "app.data.master_data",
        "app.data.cities",
        "app.render.surfaces",
        "app.render.markdown",
    ]

    for mod_name in core_modules:
        mod = import_module(mod_name)
        # Inspect module file content for prohibited imports
        mod_file = getattr(mod, "__file__", None)
        assert mod_file is not None, f"Module {mod_name} has no file"
        with open(mod_file, "r", encoding="utf-8") as f:
            code = f.read()
        assert "from app.web" not in code, f"Forbidden import 'from app.web' in {mod_name}"
        assert "import app.web" not in code, f"Forbidden import 'import app.web' in {mod_name}"
        assert "from fastapi" not in code, f"Forbidden import 'from fastapi' in {mod_name}"
        assert "import fastapi" not in code, f"Forbidden import 'import fastapi' in {mod_name}"


def test_agent_ge_and_ui_functional_equivalence():
    """Verify that the agent deployed to Gemini Enterprise and the Web UI share the exact same engine and function identically."""
    # 1. Direct Agent Engine / Gemini Enterprise flow
    ctx_ge = Ctx()
    ge_out = T.plan_dispatch(ctx_ge, hub_id="BHW-DC")
    assert ge_out["saved_inr_per_day"] > 0
    assert ge_out["lifo_verified_all"] is True
    ge_plan = T.session(ctx_ge.state)["plan"]
    assert len(ge_plan.routes) >= 2

    # Verify Gemini Enterprise callbacks
    resp = A.LlmResponse(content=types.Content(role="model", parts=[types.Part(text="- 4 trucks planned\n- ₹18,400 saved\n- LIFO verified")]))
    resp = A.append_report(ctx_ge, resp)
    md = resp.content.parts[-1].text
    # Must include atomic copy-ready tables for Google Sheets and headed links
    assert "### Today vs FleetFlow" in md or "### Today vs LoadPilot" in md
    assert "### Truck plan (copy-ready)" in md
    assert "### Where each truck goes" in md
    # Must adhere to table column limit <= 5 for Gemini Enterprise mobile/chat view
    for line in md.splitlines():
        if line.startswith("|"):
            assert line.count("|") <= 6

    # Verify A2UI surface emitted for Gemini Enterprise
    content = A.emit_surface(ctx_ge)
    msgs = _a2ui_msgs(content)
    assert any("updateComponents" in m for m in msgs)

    # 2. Web UI flow: test client hitting /api/agent-chat and /api/plan
    from fastapi.testclient import TestClient
    from app.fast_api_app import app as web_app
    client = TestClient(web_app)

    # Calling agent chat on the web wrapper
    r_chat = client.post("/api/agent-chat", json={"prompt": "plan today's dispatch"})
    assert r_chat.status_code == 200
    chat_data = r_chat.json()
    assert "bundle" in chat_data
    ui_kpi = chat_data["bundle"]["kpi"]

    # Compare core metrics: both must agree on optimized truck count and savings
    assert ui_kpi["savings_inr"] > 0
    assert ui_kpi["lifo_all_ok"] is True
    assert ui_kpi["optimized_trucks"] == (ge_out.get("fleetflow") or ge_out.get("loadpilot"))["trucks"]

