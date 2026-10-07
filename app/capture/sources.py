"""Box capture sources: photo (QR + label vision), QR-only, and a Gemini Live stub.

`BoxCaptureSource` keeps the scanning method open: the POC uses photos; a phone app with the
Gemini Live API (camera stream) or a barcode gun can implement the same `capture()` contract.

QR payload format (printed on every LoadPilot label):
    LP1|<box_id>|<stop_id>|<sku>|<L>x<W>x<H>|<kg>|<flags>     flags: F=fragile, U=this side up
"""

from __future__ import annotations

import json
import logging
import os
from typing import Protocol

try:
    from app.contracts import Box
    from app.data.master_data import SKU_MASTER
except ImportError:  # pragma: no cover
    from contracts import Box
    from data.master_data import SKU_MASTER

logger = logging.getLogger(__name__)

VISION_MODEL = os.environ.get("LOADPILOT_VISION_MODEL", "gemini-3.7-flash")


class BoxCaptureSource(Protocol):
    def capture(self, images: list[tuple[bytes, str]]) -> tuple[list[Box], list[str]]: ...


def encode_qr_payload(b: Box) -> str:
    flags = ("F" if b.fragile else "") + ("U" if b.this_side_up else "")
    return f"LP1|{b.box_id}|{b.stop_id}|{b.sku}|{b.l_cm:g}x{b.w_cm:g}x{b.h_cm:g}|{b.weight_kg:g}|{flags}"


def decode_qr_payload(text: str, source: str = "qr") -> Box | None:
    parts = (text or "").strip().split("|")
    if len(parts) < 6 or parts[0] != "LP1":
        return None
    try:
        l, w, h = (float(v) for v in parts[4].lower().split("x"))
        kg = float(parts[5])
    except ValueError:
        return None
    flags = parts[6] if len(parts) > 6 else ""
    sku = SKU_MASTER.get(parts[3])
    return Box(box_id=parts[1], stop_id=parts[2], sku=parts[3],
               description=sku.description if sku else parts[3], l_cm=l, w_cm=w, h_cm=h,
               weight_kg=kg, fragile="F" in flags, this_side_up="U" in flags,
               category=sku.category if sku else "general", source=source)


def decode_qr_codes(image_bytes: bytes) -> list[str]:
    """Decode every QR code in an image with OpenCV (deterministic, offline)."""
    try:
        import cv2
        import numpy as np
    except Exception:  # pragma: no cover
        return []
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return []
    found: list[str] = []

    def run(im) -> None:
        dets = []
        if hasattr(cv2, "QRCodeDetectorAruco"):
            dets.append(cv2.QRCodeDetectorAruco())
        dets.append(cv2.QRCodeDetector())
        for det in dets:
            try:
                ok, decoded, _pts, _ = det.detectAndDecodeMulti(im)
                if ok:
                    found.extend(d for d in decoded if d and d not in found)
            except Exception:  # pragma: no cover
                pass
        if not found:
            try:
                d, _pts, _ = cv2.QRCodeDetector().detectAndDecode(im)
                if d and d not in found:
                    found.append(d)
            except Exception:  # pragma: no cover
                pass

    run(img)
    h, w = img.shape[:2]
    if max(h, w) < 2400:
        run(cv2.resize(img, (w * 2, h * 2), interpolation=cv2.INTER_CUBIC))
    # overlapping tiles catch small labels in wide shots
    for ty in range(3):
        for tx in range(3):
            y0, x0 = int(ty * h / 4), int(tx * w / 4)
            tile = img[y0:y0 + h // 2, x0:x0 + w // 2]
            if tile.size:
                run(cv2.resize(tile, (tile.shape[1] * 2, tile.shape[0] * 2), interpolation=cv2.INTER_CUBIC))
    return found


class QrSource:
    def capture(self, images: list[tuple[bytes, str]]) -> tuple[list[Box], list[str]]:
        boxes: dict[str, Box] = {}
        issues: list[str] = []
        for i, (data, _mime) in enumerate(images, start=1):
            codes = decode_qr_codes(data)
            if not codes:
                issues.append(f"Photo {i}: no QR codes detected")
            for c in codes:
                b = decode_qr_payload(c)
                if b:
                    boxes[b.box_id] = b
        return list(boxes.values()), issues


class PhotoSource:
    """QR first (exact), then Gemini Vision reads printed labels for anything the QR missed."""

    def capture(self, images: list[tuple[bytes, str]]) -> tuple[list[Box], list[str]]:
        qr_boxes, issues = QrSource().capture(images)
        found = {b.box_id: b for b in qr_boxes}
        for i, (data, mime) in enumerate(images, start=1):
            for b in _vision_read_labels(data, mime):
                if b.box_id not in found:
                    found[b.box_id] = b
        if found:
            issues = [s for s in issues if "no QR" not in s] or issues
        return list(found.values()), issues


class LiveSource:  # pragma: no cover - Phase 5
    """Placeholder for a Gemini Live API camera session calling the same tool contract."""

    def capture(self, images: list[tuple[bytes, str]]) -> tuple[list[Box], list[str]]:
        return [], ["Gemini Live capture runs in the LoadPilot mobile PWA (Phase 5)."]


def _vision_read_labels(data: bytes, mime: str) -> list[Box]:
    try:
        from google import genai
        from google.genai import types
    except Exception:  # pragma: no cover
        return []
    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "box_id": {"type": "STRING"}, "stop_id": {"type": "STRING"}, "sku": {"type": "STRING"},
                "length_cm": {"type": "NUMBER"}, "width_cm": {"type": "NUMBER"},
                "height_cm": {"type": "NUMBER"}, "weight_kg": {"type": "NUMBER"},
                "fragile": {"type": "BOOLEAN"}, "this_side_up": {"type": "BOOLEAN"},
            },
            "required": ["box_id", "stop_id"],
        },
    }
    try:
        client = genai.Client()
        resp = client.models.generate_content(
            model=VISION_MODEL,
            contents=[types.Part.from_bytes(data=data, mime_type=mime or "image/jpeg"),
                      "Read every shipping label visible on the cartons. Return one row per carton "
                      "with box_id (e.g. S012-B03), stop_id (e.g. S012), sku, dimensions in cm, weight "
                      "in kg, fragile and this-side-up flags. If dimensions are not printed, estimate "
                      "them from the carton's proportions and the label size (label = 10x15 cm)."],
            config=types.GenerateContentConfig(
                temperature=0.0, response_mime_type="application/json", response_schema=schema,
                thinking_config=types.ThinkingConfig(thinking_budget=0)),
        )
        rows = json.loads(resp.text or "[]")
    except Exception as exc:
        logger.warning("vision label read failed: %s", exc)
        return []
    out: list[Box] = []
    for r in rows:
        sku = SKU_MASTER.get(r.get("sku", ""))
        l = r.get("length_cm") or (sku.l_cm if sku else 40)
        w = r.get("width_cm") or (sku.w_cm if sku else 30)
        h = r.get("height_cm") or (sku.h_cm if sku else 30)
        kg = r.get("weight_kg") or (sku.weight_kg if sku else 10)
        out.append(Box(box_id=r["box_id"], stop_id=r["stop_id"], sku=r.get("sku", "UNKNOWN"),
                       description=sku.description if sku else "Carton (vision)", l_cm=float(l),
                       w_cm=float(w), h_cm=float(h), weight_kg=float(kg),
                       fragile=bool(r.get("fragile")), this_side_up=bool(r.get("this_side_up")),
                       category=sku.category if sku else "general", source="photo"))
    return out
