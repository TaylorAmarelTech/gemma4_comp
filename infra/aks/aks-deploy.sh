#!/usr/bin/env bash
# Azure AKS + Helm deploy for Duecare.
#
# Prerequisites:
#   - az CLI + `az login`
#   - subscription set: `az account set --subscription <SUB_ID>`
#   - helm v3
#
# Usage:
#   bash infra/aks/aks-deploy.sh
#   LOCATION=southeastasia bash infra/aks/aks-deploy.sh
#
# Cost: free control plane + ~$60/mo for two B2ms workers.

set -euo pipefail

RESOURCE_GROUP="${RESOURCE_GROUP:-duecare-rg}"
CLUSTER_NAME="${CLUSTER_NAME:-duecare}"
LOCATION="${LOCATION:-eastus}"
NODE_COUNT="${NODE_COUNT:-2}"
NODE_SIZE="${NODE_SIZE:-Standard_B2ms}"

# 1. Resource group
echo "Creating resource group $RESOURCE_GROUP in $LOCATION ..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

# 2. AKS cluster
echo "Creating AKS cluster $CLUSTER_NAME ..."
az aks create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --node-count "$NODE_COUNT" \
    --node-vm-size "$NODE_SIZE" \
    --enable-managed-identity \
    --enable-addons monitoring \
    --generate-ssh-keys

# 3. Credentials
echo "Fetching kubeconfig ..."
az aks get-credentials \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --overwrite-existing

# 4. Helm install
echo "Installing duecare Helm chart ..."
helm upgrade --install duecare ./infra/helm/duecare \
    --namespace duecare --create-namespace \
    --set image.repository=ghcr.io/tayloramareltech/duecare-llm \
    --set service.type=LoadBalancer

echo ""
echo "Wait for the LoadBalancer to provision (1-2 min):"
echo "  kubectl -n duecare get svc duecare-chat -w"
echo ""
echo "For TLS + custom domain: use cert-manager + Azure DNS or" \
     "AGIC (Application Gateway Ingress Controller)."
