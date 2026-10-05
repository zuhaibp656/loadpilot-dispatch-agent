#!/usr/bin/env bash
# Deploy FleetFlow Supply Chain Control Tower & 3D Load Studio to Google Cloud Run.
# Shares the exact same ADK agent backend, BigQuery dataset, Google Maps Routes API,
# and Cloud Storage media bucket as the Gemini Enterprise deployment.

set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-zuhaibp-ai}"
REGION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-fleetflow-control-tower}"
SA_EMAIL="loadpilot-agent@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=================================================================="
echo " Deploying FleetFlow Control Tower Container to Google Cloud Run"
echo " Project : ${PROJECT_ID}"
echo " Region  : ${REGION}"
echo " Service : ${SERVICE_NAME}"
echo "=================================================================="

gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project "${PROJECT_ID}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --service-account "${SA_EMAIL}" \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 20 \
  --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=true,LOADPILOT_BQ_PROJECT=${PROJECT_ID},LOADPILOT_BQ_DATASET=loadpilot_demo,LOADPILOT_MEDIA_BUCKET=${PROJECT_ID}-loadpilot-media"

echo "✅ Cloud Run deployment complete!"
