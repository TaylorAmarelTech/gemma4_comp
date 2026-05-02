#!/usr/bin/env bash
# GCP Cloud Run deploy for Duecare.
# Scale-to-zero serverless containers; pays $0 when idle.
#
# Prerequisites:
#   - gcloud CLI + `gcloud auth login` + `gcloud config set project <PROJECT>`
#   - Cloud Run API enabled: `gcloud services enable run.googleapis.com`
#
# Usage:
#   bash infra/gcp/cloudrun-deploy.sh
#   REGION=asia-southeast1 bash infra/gcp/cloudrun-deploy.sh    # SE Asia
#
# Cost at NGO scale (50 reqs/day): ~$0.50/mo. Cost at enterprise
# (1k reqs/day): ~$15/mo. Idle: $0.

set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-duecare-chat}"
REGION="${REGION:-us-central1}"
IMAGE="${IMAGE:-ghcr.io/tayloramareltech/duecare-llm:latest}"
CPU="${CPU:-1}"
MEMORY="${MEMORY:-1Gi}"
MAX_INSTANCES="${MAX_INSTANCES:-10}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"            # 0 = scale to zero

echo "Deploying $SERVICE_NAME to Cloud Run in $REGION ..."

gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --cpu "$CPU" \
    --memory "$MEMORY" \
    --max-instances "$MAX_INSTANCES" \
    --min-instances "$MIN_INSTANCES" \
    --timeout 300 \
    --concurrency 80 \
    --set-env-vars="DUECARE_LOG_LEVEL=info"

URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region "$REGION" \
    --format 'value(status.url)')

echo ""
echo "==> Duecare chat is live at: $URL"
echo "==> Healthcheck: $URL/healthz"
echo ""
echo "To attach an Ollama server, deploy it as a separate Cloud Run service"
echo "with a private endpoint, then set OLLAMA_HOST to that URL via:"
echo "  gcloud run services update $SERVICE_NAME --region $REGION \\"
echo "      --set-env-vars OLLAMA_HOST=https://<ollama-cloudrun-url>"
echo ""
echo "For GPU inference: use Cloud Run for Anthos w/ GKE backing or run"
echo "Ollama on a GKE GPU node and point OLLAMA_HOST at that internal address."
