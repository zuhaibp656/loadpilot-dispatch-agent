#!/usr/bin/env bash
# ==============================================================================
# FleetFlow Unified Deployment CLI (Zero Hardcoded Accounts/Projects)
# ==============================================================================
# Supports deploying either or both surfaces sharing the exact same backend:
#   1. Gemini Enterprise + Vertex AI Agent Engine (--target gemini-enterprise)
#   2. Cloud Run Web Control Tower & 3D Load Studio UI (--target ui)
#   3. Both surfaces together (--target all)
#
# Usage Examples:
#   ./scripts/deploy.sh --target ui --project my-gcp-project
#   ./scripts/deploy.sh --target gemini-enterprise --project my-gcp-project --ge-app-id my-ge-app
#   ./scripts/deploy.sh --target all --project my-gcp-project
#   ./scripts/deploy.sh   # Interactive selector menu if run in terminal
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

# Load .env if present
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

TARGET="${DEPLOY_TARGET:-}"
PROJECT="${PROJECT:-${GOOGLE_CLOUD_PROJECT:-${GCP_PROJECT_ID:-}}}"
REGION="${REGION:-${GOOGLE_CLOUD_LOCATION:-us-central1}}"
MODEL="${MODEL:-gemini-2.5-flash}"
GE_APP_ID="${GE_APP_ID:-}"
GE_APP_LOCATION="${GE_APP_LOCATION:-global}"
VIEWER_DOMAIN="${VIEWER_DOMAIN:-}"
SKIP_TESTS="${SKIP_TESTS:-false}"
PUBLISH_DATA="${PUBLISH_DATA:-false}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target|-t)
      TARGET="$2"
      shift 2
      ;;
    --project|-p)
      PROJECT="$2"
      shift 2
      ;;
    --region|-r)
      REGION="$2"
      shift 2
      ;;
    --ge-app-id)
      GE_APP_ID="$2"
      shift 2
      ;;
    --viewer-domain)
      VIEWER_DOMAIN="$2"
      shift 2
      ;;
    --publish-data)
      PUBLISH_DATA="true"
      shift 1
      ;;
    --skip-tests)
      SKIP_TESTS="true"
      shift 1
      ;;
    --help|-h)
      echo "Usage: ./scripts/deploy.sh [--target gemini-enterprise|ui|all] [--project GCP_PROJECT_ID] [--region REGION] [--ge-app-id APP_ID] [--publish-data]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Auto-detect project from gcloud if not set via flag or env
if [[ -z "${PROJECT}" ]] && command -v gcloud >/dev/null 2>&1; then
  PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
  [[ "${PROJECT}" == "(unset)" ]] && PROJECT=""
fi

if [[ -z "${PROJECT}" ]]; then
  echo "❌ Error: No Google Cloud Project ID specified."
  echo "   Pass --project <YOUR_PROJECT_ID> or set GOOGLE_CLOUD_PROJECT in .env"
  exit 1
fi

export GOOGLE_CLOUD_PROJECT="${PROJECT}"
export GOOGLE_CLOUD_LOCATION="${REGION}"
export GOOGLE_API_USE_CLIENT_CERTIFICATE=false

# Interactive target selection if not passed on CLI
if [[ -z "${TARGET}" ]]; then
  if [[ -t 0 ]]; then
    echo "=================================================================="
    echo " 🚚 FleetFlow Deployment Target Selector"
    echo " Project : ${PROJECT}"
    echo " Region  : ${REGION}"
    echo "=================================================================="
    echo "  1) Gemini Enterprise Agent (Vertex AI Agent Engine + A2UI)"
    echo "  2) Web Control Tower & 3D Load Studio UI (Google Cloud Run)"
    echo "  3) Both (Full Dual-Surface Enterprise Deployment)"
    echo "------------------------------------------------------------------"
    read -rp "Select deployment option [1/2/3] (default: 3): " choice
    case "${choice:-3}" in
      1) TARGET="gemini-enterprise" ;;
      2) TARGET="ui" ;;
      3|*) TARGET="all" ;;
    esac
  else
    TARGET="gemini-enterprise"
  fi
fi

command -v uv >/dev/null || { echo "Install uv first: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
uv sync --quiet

if [[ "${SKIP_TESTS}" != "true" ]]; then
  echo "==> Running unit test suite..."
  LOADPILOT_PUBLISH_MEDIA=false uv run pytest tests/unit -q
fi

if [[ "${PUBLISH_DATA}" == "true" ]]; then
  echo "==> Publishing demo order book to BigQuery & Cloud Storage in ${PROJECT}..."
  uv run python scripts/publish_demo_data.py
fi

case "${TARGET}" in
  gemini-enterprise|ge|agent)
    echo "==> [Target: Gemini Enterprise] Deploying Vertex AI Agent Engine & GE Registration to ${PROJECT} (${REGION})..."
    ARGS=(--project "$PROJECT" --region "$REGION" --model "$MODEL")
    [[ -n "${GE_APP_ID:-}" ]] && ARGS+=(--gemini-app-id "$GE_APP_ID" --gemini-app-location "${GE_APP_LOCATION}")
    [[ -n "${VIEWER_DOMAIN:-}" ]] && ARGS+=(--viewer-domain "$VIEWER_DOMAIN")
    [[ -n "${SKIP_GE:-}" ]] && ARGS+=(--skip-ge)
    uv run python scripts/deploy_to_gemini_enterprise.py "${ARGS[@]}"
    ;;
  ui|web|cloud-run|control-tower)
    echo "==> [Target: Web UI] Deploying FleetFlow Control Tower & 3D Load Studio to Cloud Run in ${PROJECT} (${REGION})..."
    GOOGLE_CLOUD_PROJECT="${PROJECT}" GOOGLE_CLOUD_LOCATION="${REGION}" bash scripts/deploy_cloud_run.sh
    ;;
  all|both)
    echo "==> [1/2] Deploying Vertex AI Agent Engine & Gemini Enterprise to ${PROJECT} (${REGION})..."
    ARGS=(--project "$PROJECT" --region "$REGION" --model "$MODEL")
    [[ -n "${GE_APP_ID:-}" ]] && ARGS+=(--gemini-app-id "$GE_APP_ID" --gemini-app-location "${GE_APP_LOCATION}")
    [[ -n "${VIEWER_DOMAIN:-}" ]] && ARGS+=(--viewer-domain "$VIEWER_DOMAIN")
    [[ -n "${SKIP_GE:-}" ]] && ARGS+=(--skip-ge)
    uv run python scripts/deploy_to_gemini_enterprise.py "${ARGS[@]}"

    echo "==> [2/2] Deploying FleetFlow Control Tower & 3D Load Studio UI to Cloud Run in ${PROJECT} (${REGION})..."
    GOOGLE_CLOUD_PROJECT="${PROJECT}" GOOGLE_CLOUD_LOCATION="${REGION}" bash scripts/deploy_cloud_run.sh
    ;;
  *)
    echo "❌ Unknown target '${TARGET}'. Use: gemini-enterprise | ui | all"
    exit 1
    ;;
esac

echo "✅ FleetFlow deployment (${TARGET}) finished successfully!"
