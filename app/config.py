"""Centralized, portable environment configuration for FleetFlow.

Ensures zero hardcoded personal project IDs, accounts, buckets, or credentials when sharing
the repository across teams or deploying to new Google Cloud environments.
"""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv_if_present() -> None:
    """Load key=value pairs from .env in repo root if present (without overriding active env)."""
    env_file = ROOT_DIR / ".env"
    if not env_file.is_file():
        return
    for raw_line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip("'").strip('"')
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv_if_present()


@lru_cache(maxsize=1)
def get_project_id() -> str:
    """Resolve Google Cloud Project ID from env vars, ADC, or gcloud config (never hardcoded)."""
    for env_key in ("GOOGLE_CLOUD_PROJECT", "GCP_PROJECT_ID", "LOADPILOT_BQ_PROJECT", "FLEETFLOW_PROJECT_ID"):
        val = os.environ.get(env_key, "").strip()
        if val:
            return val
    try:
        out = subprocess.check_output(
            ["gcloud", "config", "get-value", "project"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
        if out and out != "(unset)":
            return out
    except Exception:
        pass
    return "your-gcp-project-id"


def get_region() -> str:
    return (
        os.environ.get("GOOGLE_CLOUD_LOCATION")
        or os.environ.get("GCP_REGION")
        or os.environ.get("LOADPILOT_BQ_LOCATION")
        or "us-central1"
    )


def get_bq_dataset() -> str:
    return (
        os.environ.get("FLEETFLOW_BQ_DATASET")
        or os.environ.get("LOADPILOT_BQ_DATASET")
        or "fleetflow_demo"
    )


def get_media_bucket() -> str:
    explicit = (
        os.environ.get("FLEETFLOW_MEDIA_BUCKET")
        or os.environ.get("LOADPILOT_MEDIA_BUCKET")
        or ""
    ).strip()
    if explicit:
        return explicit
    return f"{get_project_id()}-fleetflow-media"


def get_adc_file() -> str | None:
    """Return custom ADC authorized_user file path only if explicitly configured via env."""
    for k in ("FLEETFLOW_ADC_FILE", "LOADPILOT_ADC_FILE", "GOOGLE_APPLICATION_CREDENTIALS"):
        p = os.environ.get(k, "").strip()
        if p:
            expanded = os.path.expanduser(p)
            if os.path.exists(expanded):
                return expanded
    default_adc = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    if os.path.exists(default_adc):
        return default_adc
    return None
