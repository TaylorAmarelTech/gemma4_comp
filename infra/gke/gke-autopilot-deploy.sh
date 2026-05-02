#!/usr/bin/env bash
# GKE Autopilot + Helm deploy for Duecare.
# Cleanest managed K8s — Google sizes the nodes, you only pay
# pod-resources.
#
# Prerequisites:
#   - gcloud CLI + `gcloud auth login` + `gcloud config set project <PROJECT>`
#   - helm v3
#   - container.googleapis.com API enabled
#
# Usage:
#   bash infra/gke/gke-autopilot-deploy.sh
#   REGION=asia-southeast1 bash infra/gke/...

set -euo pipefail

CLUSTER_NAME="${CLUSTER_NAME:-duecare}"
REGION="${REGION:-us-central1}"
RELEASE_CHANNEL="${RELEASE_CHANNEL:-regular}"

# 1. Cluster
echo "Creating GKE Autopilot cluster '$CLUSTER_NAME' in $REGION ..."
gcloud container clusters create-auto "$CLUSTER_NAME" \
    --region "$REGION" \
    --release-channel "$RELEASE_CHANNEL"

echo "Fetching credentials ..."
gcloud container clusters get-credentials "$CLUSTER_NAME" --region "$REGION"

# 2. Helm install
echo "Installing duecare Helm chart ..."
helm upgrade --install duecare ./infra/helm/duecare \
    --namespace duecare \
    --create-namespace \
    --set image.repository=ghcr.io/tayloramareltech/duecare-llm \
    --set service.type=LoadBalancer

# 3. Wait for the LB
echo "Waiting for chat LoadBalancer to provision (can take 1-2 min) ..."
for i in {1..30}; do
    IP=$(kubectl -n duecare get svc duecare-chat \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
    if [[ -n "$IP" ]]; then break; fi
    echo "  ... still waiting"
    sleep 10
done

if [[ -n "$IP" ]]; then
    echo ""
    echo "==> Duecare chat is live at: http://$IP:8080"
    echo "==> Healthcheck: http://$IP:8080/healthz"
    echo ""
    echo "For HTTPS + custom domain:"
    echo "  - Reserve a static IP: gcloud compute addresses create duecare-ip --global"
    echo "  - Set up cert-manager + Google-managed Certificate"
    echo "  - Re-run helm with --set ingress.enabled=true and your hostname"
else
    echo "LoadBalancer not yet ready. Check status with:"
    echo "  kubectl -n duecare get svc duecare-chat -w"
fi
