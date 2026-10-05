#!/usr/bin/env bash
# FleetFlow one-command deploy: resources + Agent Engine (create or update in place) + Gemini Enterprise.
#
#   ./scripts/deploy.sh                       # zuhaibp-ai / us-central1, auto-discover GE apps
#   PROJECT=my-proj REGION=us-central1 GE_APP_ID=my-ge-app VIEWER_DOMAIN=example.com ./scripts/deploy.sh
#
# Prereqs: uv (https://docs.astral.sh/uv/), and either `gcloud auth application-default login`
# or GCP_ACCESS_TOKEN / GOOGLE_APPLICATION_CREDENTIALS (service-account key) with Owner/Editor-level
# rights on the project (enables APIs, creates buckets + a service account, sets IAM).
set -euo pipefail

cd "$(dirname "$0")/.."
PROJECT="${PROJECT:-${GOOGLE_CLOUD_PROJECT:-zuhaibp-ai}}"
REGION="${REGION:-us-central1}"
MODEL="${MODEL:-gemini-2.5-flash}"

export GOOGLE_API_USE_CLIENT_CERTIFICATE=false
command -v uv >/dev/null || { echo "Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }

uv sync --python 3.13 --quiet
echo "==> Unit tests"
LOADPILOT_PUBLISH_MEDIA=false uv run pytest tests/unit -q

echo "==> Deploying FleetFlow to ${PROJECT} (${REGION})"
ARGS=(--project "$PROJECT" --region "$REGION" --model "$MODEL")
[[ -n "${GE_APP_ID:-}" ]] && ARGS+=(--gemini-app-id "$GE_APP_ID" --gemini-app-location "${GE_APP_LOCATION:-global}")
[[ -n "${VIEWER_DOMAIN:-}" ]] && ARGS+=(--viewer-domain "$VIEWER_DOMAIN")
[[ -n "${SKIP_GE:-}" ]] && ARGS+=(--skip-ge)
uv run python scripts/deploy_to_gemini_enterprise.py "${ARGS[@]}"
