#!/usr/bin/env bash
# AWS Lightsail Container deploy for Duecare.
# Cheapest production-grade single-container path on AWS — no EKS, no
# K8s overhead, $7/mo Nano up to $40/mo Large.
#
# Prerequisites:
#   - aws-cli v2 + `aws configure` done
#   - IAM permissions: lightsail:*
#
# Usage:
#   bash infra/aws/lightsail-deploy.sh                  # nano, default region
#   AWS_REGION=ap-southeast-1 POWER=micro bash ./...    # SE Asia, micro tier
#
# After deploy, the public URL prints; takes ~3 min for the container
# to come up healthy.

set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-duecare}"
AWS_REGION="${AWS_REGION:-us-west-2}"
POWER="${POWER:-nano}"             # nano $7 | micro $10 | small $20 | medium $40 | large $80
SCALE="${SCALE:-1}"
IMAGE="${IMAGE:-ghcr.io/tayloramareltech/duecare-llm:latest}"

echo "Creating Lightsail container service '$SERVICE_NAME' in $AWS_REGION ..."
aws lightsail create-container-service \
    --region "$AWS_REGION" \
    --service-name "$SERVICE_NAME" \
    --power "$POWER" \
    --scale "$SCALE" \
    || echo "(service may already exist; continuing to deploy)"

echo "Waiting for service to become READY ..."
for i in {1..30}; do
    STATE=$(aws lightsail get-container-services \
        --region "$AWS_REGION" \
        --service-name "$SERVICE_NAME" \
        --query 'containerServices[0].state' --output text)
    echo "  state: $STATE"
    [[ "$STATE" == "READY" ]] && break
    sleep 10
done

echo "Creating deployment ..."
DEPLOYMENT=$(cat <<EOF
{
  "chat": {
    "image": "$IMAGE",
    "environment": {
      "DUECARE_LOG_LEVEL": "info"
    },
    "ports": {
      "8080": "HTTP"
    }
  }
}
EOF
)

ENDPOINT=$(cat <<EOF
{
  "containerName": "chat",
  "containerPort": 8080,
  "healthCheck": {
    "path": "/healthz",
    "intervalSeconds": 30,
    "timeoutSeconds": 5,
    "healthyThreshold": 2,
    "unhealthyThreshold": 3,
    "successCodes": "200"
  }
}
EOF
)

aws lightsail create-container-service-deployment \
    --region "$AWS_REGION" \
    --service-name "$SERVICE_NAME" \
    --containers "$DEPLOYMENT" \
    --public-endpoint "$ENDPOINT"

echo ""
echo "Waiting for deployment to become ACTIVE ..."
for i in {1..60}; do
    STATE=$(aws lightsail get-container-services \
        --region "$AWS_REGION" \
        --service-name "$SERVICE_NAME" \
        --query 'containerServices[0].currentDeployment.state' --output text)
    echo "  deployment: $STATE"
    [[ "$STATE" == "ACTIVE" ]] && break
    sleep 10
done

URL=$(aws lightsail get-container-services \
    --region "$AWS_REGION" \
    --service-name "$SERVICE_NAME" \
    --query 'containerServices[0].url' --output text)

echo ""
echo "==> Duecare chat is live at: $URL"
echo ""
echo "For HTTPS + custom domain, attach a Lightsail certificate:"
echo "  aws lightsail create-certificate --certificate-name $SERVICE_NAME-cert \\"
echo "      --domain-name your-domain.com"
echo ""
echo "To update later: re-run this script with the same SERVICE_NAME."
