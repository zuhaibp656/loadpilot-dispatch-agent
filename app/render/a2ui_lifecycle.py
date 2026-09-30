"""A2UI v0.9 lifecycle message builders for Gemini Enterprise chat surfaces.

In : Surface identifiers, UI component trees, and data model dictionaries.
Out: A2uiMessage contract objects ready to be wrapped by a2ui_envelope.
Rule: Pure functions only. Adheres strictly to A2UI v0.9 schema conventions.
"""

from __future__ import annotations

from typing import Any

try:
    from app.contracts import A2uiCatalogVersion, A2uiMessage
except ImportError:
    from contracts import A2uiCatalogVersion, A2uiMessage

DEFAULT_GE_CATALOG_ID: str = (
    "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
)


def build_create_surface(
    surface_id: str,
    catalog_id: str = DEFAULT_GE_CATALOG_ID,
) -> A2uiMessage:
    """Build a 'createSurface' message to initialize a new visual surface in chat."""
    if not surface_id:
        raise ValueError("surface_id cannot be empty when creating a surface.")

    return A2uiMessage(
        message_type="createSurface",
        surface_id=surface_id,
        payload={"catalogId": catalog_id},
        catalog_version=A2uiCatalogVersion.V0_9,
    )


def build_update_components(
    surface_id: str,
    components: list[dict[str, Any]],
) -> A2uiMessage:
    """Build an 'updateComponents' message to declare or replace the UI hierarchy."""
    if not surface_id:
        raise ValueError("surface_id cannot be empty when updating components.")
    if not components:
        raise ValueError("components list cannot be empty in updateComponents.")

    return A2uiMessage(
        message_type="updateComponents",
        surface_id=surface_id,
        payload={"components": components},
        catalog_version=A2uiCatalogVersion.V0_9,
    )


def build_update_data_model(
    surface_id: str,
    value: dict[str, Any],
    path: str | None = None,
) -> A2uiMessage:
    """Build an 'updateDataModel' message to bind bulk data to the surface.

    CRITICAL: The payload key is 'value', NOT 'data'.
    Sending 'data' causes Gemini Enterprise to fail with:
    'Expected undefined, received undefined /updateDataModel'.
    """
    if not surface_id:
        raise ValueError("surface_id cannot be empty when updating data model.")
    if not isinstance(value, dict):
        raise TypeError(f"value must be a dictionary, got {type(value).__name__}.")

    payload: dict[str, Any] = {"value": value}
    if path:
        payload["path"] = path

    return A2uiMessage(
        message_type="updateDataModel",
        surface_id=surface_id,
        payload=payload,
        catalog_version=A2uiCatalogVersion.V0_9,
    )


def build_delete_surface(surface_id: str) -> A2uiMessage:
    """Build a 'deleteSurface' message to tear down an active surface canvas."""
    if not surface_id:
        raise ValueError("surface_id cannot be empty when deleting a surface.")

    return A2uiMessage(
        message_type="deleteSurface",
        surface_id=surface_id,
        payload={},
        catalog_version=A2uiCatalogVersion.V0_9,
    )
