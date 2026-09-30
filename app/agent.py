"""Root entry point for the LoadPilot dispatch agent (truck LIFO loading + route optimisation).

Delegates agent construction to app.integration.agent, keeping the scaffold separate from the
domain integration code.
"""

from app.integration.agent import app, root_agent

__all__ = ["root_agent", "app"]
