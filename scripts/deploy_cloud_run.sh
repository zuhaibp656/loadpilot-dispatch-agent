#!/usr/bin/env bash
# Deploy FleetFlow Supply Chain Control Tower & 3D Load Studio to Google Cloud Run.
# Shares the exact same ADK agent backend, BigQuery dataset, Google Maps Routes API,
# and Cloud Storage media bucket as the Gemini Enterprise deployment.
# Zero hardcoded project IDs: resolves from GOOGLE_CLOUD_PROJECT, .env, or gcloud config.

set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-${GCP_PROJECT_ID:-}}"
if [[ -z "${PROJECT_ID}" ]] && command -v gcloud >/dev/null 2>&1; then
  PROJECT_ID="$(gcloud config get-value project 2>/dev/null || true)"
  [[ "${PROJECT_ID}" == "(unset)" ]] && PROJECT_ID=""
fi

if [[ -z "${PROJECT_ID}" ]]; then
  echo "❌ Error: Set GOOGLE_CLOUD_PROJECT=<your-project-id> before running deploy_cloud_run.sh"
  exit 1
fi

REGION="${GOOGLE_CLOUD_LOCATION:-${GCP_REGION:-us-central1}}"
SERVICE_NAME="${SERVICE_NAME:-fleetflow-control-tower}"
BQ_DATASET="${FLEETFLOW_BQ_DATASET:-${LOADPILOT_BQ_DATASET:-fleetflow_demo}}"
MEDIA_BUCKET="${FLEETFLOW_MEDIA_BUCKET:-${LOADPILOT_MEDIA_BUCKET:-${PROJECT_ID}-fleetflow-media}}"
SA_NAME="${FLEETFLOW_SA_NAME:-loadpilot-agent}"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=================================================================="
echo " Deploying FleetFlow Control Tower Container to Google Cloud Run"
echo " Project : ${PROJECT_ID}"
echo " Region  : ${REGION}"
echo " Service : ${SERVICE_NAME}"
echo " Dataset : ${PROJECT_ID}.${BQ_DATASET}"
echo " Bucket  : gs://${MEDIA_BUCKET}"
echo "=================================================================="

SA_ARGS=()
if gcloud iam service-accounts describe "${SA_EMAIL}" --project "${PROJECT_ID}" >/dev/null 2>&1; then
  SA_ARGS=(--service-account "${SA_EMAIL}")
fi

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  "${SA_ARGS[@]}" \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 20 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=true,LOADPILOT_BQ_PROJECT=${PROJECT_ID},LOADPILOT_BQ_DATASET=${BQ_DATASET},LOADPILOT_MEDIA_BUCKET=${MEDIA_BUCKET}"

echo "✅ Cloud Run deployment complete!"
