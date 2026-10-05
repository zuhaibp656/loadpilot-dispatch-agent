"""Agent card capabilities declaration for Gemini Enterprise and Agent Registry.

Declares ADK executor and A2UI v0.9 extension support.
"""

from __future__ import annotations

from typing import Any
from a2a.types import AgentCapabilities, AgentExtension

ADK_AGENT_EXECUTOR_EXTENSION_URI: str = (
    "https://google.github.io/adk-docs/a2a/a2a-extension/"
)
A2UI_V09_EXTENSION_URI: str = "https://a2ui.org/a2a-extension/a2ui/v0.9"
DEFAULT_GE_CATALOG_ID: str = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
)


def build_agent_capabilities() -> AgentCapabilities:
    """Build the comprehensive A2A capabilities descriptor for the agent card.

    Advertises streaming and the A2UI v0.9 extension to Gemini Enterprise.
    Without this declaration, Gemini Enterprise treats the agent as text-only.
    """
    from google.protobuf.struct_pb2 import Struct

    catalog_params = Struct()
    catalog_params.update({"supportedCatalogIds": [DEFAULT_GE_CATALOG_ID]})

    return AgentCapabilities(
        streaming=True,
        extensions=[
            AgentExtension(
                uri=ADK_AGENT_EXECUTOR_EXTENSION_URI,
                description="Ability to use the modern ADK agent executor implementation",
            ),
            AgentExtension(
                uri=A2UI_V09_EXTENSION_URI,
                description="Ability to render rich A2UI v0.9 interactive components (VegaChart, Canvas, Material 3)",
                params=catalog_params,
            ),
        ],
    )


def get_agent_card() -> dict[str, Any]:
    """Compatibility agent card dictionary for JSON-RPC endpoints."""
    return {
        "id": "FLEETFLOW-DISPATCH",
        "name": "FleetFlow Dispatch Engine",
        "version": "1.0.0",
        "protocol": "a2a-jsonrpc-1.0",
        "description": "Truck LIFO loading, corridor route optimisation and cost savings for retail / CPG dispatch with animated A2UI surfaces",
        "endpoints": {
            "jsonrpc": "/a2a/fleetflow_agent",
            "agent_card": "/a2a/fleetflow_agent/.well-known/agent-card.json",
        },
        "capabilities": {
            "streaming": True,
            "extensions": [
                ADK_AGENT_EXECUTOR_EXTENSION_URI,
                A2UI_V09_EXTENSION_URI,
            ],
        },
    }
