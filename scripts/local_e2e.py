"""Local test harness: run LoadPilot through an in-memory ADK Runner (no UI) and dump outputs."""

import asyncio
import json
import os
import sys
import time

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
sys.path.insert(0, os.getcwd())

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from app.agent import root_agent  # noqa: E402

OUT = "/tmp/lp_e2e"
os.makedirs(OUT, exist_ok=True)


async def turn(runner, sid, msg, idx):
    t0 = time.time()
    parts = [types.Part(text=msg)] if isinstance(msg, str) else msg
    texts, a2ui, calls, imgs = [], [], [], 0
    async for ev in runner.run_async(user_id="u", session_id=sid,
                                     new_message=types.Content(role="user", parts=parts)):
        for p in (ev.content.parts if ev.content else []) or []:
            if p.function_call:
                calls.append(f"{p.function_call.name}({json.dumps(p.function_call.args)[:160]})")
            if p.text:
                texts.append(p.text)
            if p.inline_data:
                if p.inline_data.mime_type.startswith("image/"):
                    imgs += 1
                else:
                    a2ui.append(p.inline_data.data.decode("utf-8", "ignore"))
    dt = time.time() - t0
    size = sum(len(a) for a in a2ui)
    with open(f"{OUT}/turn{idx}.md", "w") as f:
        f.write("\n".join(texts))
    with open(f"{OUT}/turn{idx}_a2ui.txt", "w") as f:
        f.write("\n".join(a2ui))
    print(f"--- turn {idx} [{dt:.1f}s] calls={calls} a2ui_parts={len(a2ui)} bytes={size} imgs={imgs}")
    print("\n".join(texts)[:700])


async def main():
    runner = InMemoryRunner(agent=root_agent, app_name="loadpilot_agent")
    s = await runner.session_service.create_session(app_name="loadpilot_agent", user_id="u")
    msgs = sys.argv[1:] or ["Plan today's dispatch", "Ravi has the West route", "Show me T17-1's loading plan"]
    for i, m in enumerate(msgs, start=1):
        if m.startswith("@form:"):
            m = [types.Part(text="<a2a_datapart_json>" + m[6:] + "</a2a_datapart_json>")]
        await turn(runner, s.id, m, i)


asyncio.run(main())
