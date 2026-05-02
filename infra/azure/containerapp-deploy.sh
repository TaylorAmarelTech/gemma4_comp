#!/usr/bin/env bash
# Azure Container Apps deploy for Duecare.
# Same scale-to-zero niche as Cloud Run, on Azure.
#
# Prerequisites:
#   - az CLI + `az login`
#   - subscription set: `az account set --subscription <SUB_ID>`
#
# Usage:
#   bash infra/azure/containerapp-deploy.sh
#   LOCATION=southeastasia bash infra/azure/...    # SE Asia
#
# Cost: $0 idle, ~$0.0001/vCPU-second + memory. NGO scale: ~$5/mo.

set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-duecare-rg}"
LOCATION="${LOCATION:-eastus}"
ENV_NAME="${ENV_NAME:-duecare-env}"
APP_NAME="${APP_NAME:-duecare-chat}"
IMAGE="${IMAGE:-ghcr.io/tayloramareltech/duecare-llm:latest}"

# 1. Resource group
echo "Creating resource group $RESOURCE_GROUP in $LOCATION ..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

# 2. Container Apps environment
echo "Creating Container Apps environment $ENV_NAME ..."
az containerapp env create \
    --name "$ENV_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --location "$LOCATION" >/dev/null

# 3. The chat app
echo "Deploying $APP_NAME ..."
az containerapp create \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --environment "$ENV_NAME" \
    --image "$IMAGE" \
    --target-port 8080 \
    --ingress external \
    --min-replicas 0 \
    --max-replicas 10 \
    --cpu 1 \
    --memory 2Gi \
    --env-vars "DUECARE_LOG_LEVEL=info"

URL=$(az containerapp show \
    --name "$APP_NAME" \
    --resource-group "$RESOURCE_GROUP" \
    --query "properties.configuration.ingress.fqdn" -o tsv)

echo ""
echo "==> Duecare chat is live at: https://$URL"
echo "==> Healthcheck: https://$URL/healthz"
echo ""
echo "To add a custom domain:"
echo "  az containerapp hostname add --hostname your-domain.com \\"
echo "      --name $APP_NAME --resource-group $RESOURCE_GROUP"
