"""A2UI message envelope serializer for the Google ADK to Gemini Enterprise bridge.

In : An A2uiMessage contract object containing a single lifecycle message.
Out: An ADK types.Part encoded with wire markers for runtime transport.
Rule: Wraps exactly ONE message per Part. Never bundle multiple messages into a single Part.
"""

from __future__ import annotations

import json
from typing import Any

from google.genai import types

try:
    from app.contracts import A2uiMessage
except ImportError:
    from contracts import A2uiMessage

A2A_DATA_PART_OPEN_TAG: str = "<a2a_datapart_json>"
A2A_DATA_PART_CLOSE_TAG: str = "</a2a_datapart_json>"
A2UI_MIME: str = "application/json+a2ui"


def wrap_a2ui_part(message: A2uiMessage) -> types.Part:
    """Serialize a single A2UI lifecycle message into an ADK transport Part.

    Architectural Rules (Learned from ADK/A2UI Runtime Specification):
    1. One message per Part:
       Gemini Enterprise processes A2UI as an event stream. Each event must be its own Part.
    2. The 'kind': 'data' envelope with 'metadata': {'mimeType': 'application/json+a2ui'}.
    3. The text/plain MIME type on the ADK side:
       The Part must be created as 'text/plain' containing the <a2a_datapart_json> wrapper.
       ADK's part_converter converts this into a native A2A DataPart with
       'application/json+a2ui' before delivering to the Gemini Enterprise browser client.
    """
    if not message.surface_id:
        raise ValueError("A2uiMessage must have a non-empty surface_id.")
    if not message.message_type:
        raise ValueError("A2uiMessage must have a non-empty message_type.")

    version_str = (
        message.catalog_version.value
        if hasattr(message.catalog_version, "value")
        else str(message.catalog_version)
    )

    raw_message_body: dict[str, Any] = {
        "version": version_str,
        message.message_type: {
            "surfaceId": message.surface_id,
            **message.payload,
        },
    }

    payload_envelope: dict[str, Any] = {
        "kind": "data",
        "metadata": {"mimeType": A2UI_MIME},
        "data": raw_message_body,
    }

    json_str = json.dumps(payload_envelope, separators=(",", ":"))
    wire_payload = (
        f"{A2A_DATA_PART_OPEN_TAG}"
        f"{json_str}"
        f"{A2A_DATA_PART_CLOSE_TAG}"
    ).encode("utf-8")

    return types.Part(
        inline_data=types.Blob(
            data=wire_payload,
            mime_type="text/plain",
        ),
        part_metadata={"mimeType": A2UI_MIME},
    )
