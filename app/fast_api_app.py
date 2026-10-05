"""FastAPI server application for the LoadPilot Dispatch Agent.

Integrates Google ADK Runner, A2A protocol routes, and Vertex AI Reasoning Engine adapters.
"""

import contextlib
import os
from collections.abc import AsyncIterator

from a2a.server.tasks import InMemoryTaskStore
from dotenv import load_dotenv
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app
from google.adk.runners import Runner

from app.app_utils import services
from app.app_utils.a2a import attach_a2a_routes
from app.app_utils.reasoning_engine_adapter import (
    attach_reasoning_engine_routes,
)

load_dotenv()
otel_to_cloud = os.environ.get(
    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", ""
).lower() in ("true", "1")
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    from app.agent import app as adk_app
    from app.agent import root_agent

    runner = Runner(
        app=adk_app,
        session_service=services.get_session_service(),
        artifact_service=services.get_artifact_service(),
        auto_create_session=True,
    )
    app.state.runner = runner
    app.state.agent_app_name = adk_app.name

    from app.integration.agent_card import build_agent_capabilities
    from app.integration.executor import A2uiNegotiatingExecutor

    await attach_a2a_routes(
        app,
        agent=root_agent,
        runner=runner,
        task_store=InMemoryTaskStore(),
        rpc_path=f"/a2a/{adk_app.name}",
        capabilities=build_agent_capabilities(),
        executor=A2uiNegotiatingExecutor(runner=runner),
    )
    yield


app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=services.ARTIFACT_SERVICE_URI,
    allow_origins=allow_origins,
    session_service_uri=services.SESSION_SERVICE_URI,
    otel_to_cloud=otel_to_cloud,
    lifespan=lifespan,
)
app.title = "FleetFlow Dispatch Engine & Control Tower"
app.description = "Dual-deployment Supply Chain Control Tower UI & Gemini Enterprise Agent Engine"

attach_reasoning_engine_routes(app)

from app.web.api import router as web_router, serve_control_tower_ui  # noqa: E402

# Override root '/' so container / local root opens the FleetFlow Control Tower UI directly
app.router.routes = [r for r in app.router.routes if getattr(r, "path", None) != "/"]
app.add_api_route("/", serve_control_tower_ui, methods=["GET"], include_in_schema=False)
app.include_router(web_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8085"))
    uvicorn.run(app, host="0.0.0.0", port=port)

