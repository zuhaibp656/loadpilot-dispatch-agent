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
    assert out["loadpilot"]["trucks"] < out["today"]["trucks"]
    assert out["saved_inr_per_day"] > 0 and out["lifo_verified_all"]
    assert ctx.state[T.PENDING_KEY]["kind"] == "dispatch"
    assert len(json.dumps(ctx.state)) < 4000  # heavy objects stay out of session state


def test_report_and_surface(planned):
    ctx, _ = planned
    resp = A.LlmResponse(content=types.Content(role="model", parts=[types.Part(text="- 8 trucks")]))
    resp = A.append_report(ctx, resp)
    md = resp.content.parts[-1].text
    assert "### Today vs LoadPilot" in md and "### Truck plan (copy-ready)" in md
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
    assert r["lifo_ok"] and ctx.state[T.PENDING_KEY] == {"kind": "truck", "focus": tid}
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
