"""Publish media (full-screen HTML, loader MP4) to GCS and return browser-openable URLs.

Order of preference for each object:
  1. V4 signed URL (works in any browser, incl. the A2UI Video component) — requires a signing
     identity: on Agent Engine the runtime service account signs via IAM `signBlob`
     (needs roles/iam.serviceAccountTokenCreator on itself; granted by the deploy script).
  2. Authenticated `storage.cloud.google.com` URL (works for signed-in project users).
"""

from __future__ import annotations

import datetime as dt
import logging
import os

logger = logging.getLogger(__name__)


def media_bucket() -> str:
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or "zuhaibp-ai"
    return os.environ.get("LOADPILOT_MEDIA_BUCKET") or f"{project}-loadpilot-media"


def publish_bytes(data: bytes, object_name: str, content_type: str) -> dict[str, str]:
    """Upload and return {'signed': url|None, 'auth': url}."""
    if not upload_bytes(data, object_name, content_type):
        return {"signed": "", "auth": ""}
    return links_for(object_name)


def upload_bytes(data: bytes, object_name: str, content_type: str) -> bool:
    try:
        from google.cloud import storage

        client = storage.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT") or None)
        blob = client.bucket(media_bucket()).blob(object_name)
        blob.cache_control = "private, max-age=3600"
        blob.upload_from_string(data, content_type=content_type)
        return True
    except Exception as exc:
        logger.warning("GCS upload failed for %s: %s", object_name, exc)
        return False


def links_for(object_name: str) -> dict[str, str]:
    """V4-signed URL (object need not exist yet) + authenticated console URL."""
    bucket_name = media_bucket()
    return {"signed": _sign(bucket_name, object_name) or "",
            "auth": f"https://storage.cloud.google.com/{bucket_name}/{object_name}"}


def _sign(bucket_name: str, object_name: str) -> str | None:
    try:
        import google.auth
        from google.auth.transport.requests import Request
        from google.cloud import storage

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(Request())
        sa_email = getattr(creds, "service_account_email", None)
        if not sa_email or sa_email == "default":
            # Compute / Agent Engine metadata credentials: resolve the real email
            try:
                import urllib.request
                req = urllib.request.Request(
                    "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/email",
                    headers={"Metadata-Flavor": "Google"})
                with urllib.request.urlopen(req, timeout=2) as r:
                    sa_email = r.read().decode().strip()
            except Exception:
                sa_email = None
        blob = storage.Client().bucket(bucket_name).blob(object_name)
        if hasattr(creds, "sign_bytes") and not sa_email:
            return blob.generate_signed_url(version="v4", expiration=dt.timedelta(days=7), method="GET",
                                            credentials=creds)
        if not sa_email:
            return None
        return blob.generate_signed_url(version="v4", expiration=dt.timedelta(days=7), method="GET",
                                        service_account_email=sa_email, access_token=creds.token)
    except Exception as exc:
        logger.info("signed URL unavailable (%s); using authenticated URL", exc)
        return None
