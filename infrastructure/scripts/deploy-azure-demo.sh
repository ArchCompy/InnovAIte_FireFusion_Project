#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

SUBSCRIPTION_ID="cfd11b14-72e9-4d19-8357-b7648abd8ac6"
RESOURCE_GROUP="firefusion-demo-rg"
AKS_CLUSTER="aks-firefusion-demo"

TF_DIR="$ROOT_DIR/infrastructure/terraform/azure"

echo "================================================="
echo " FireFusion Azure Demo - Automated Deployment"
echo "================================================="

echo ""
echo "[1/8] Azure subscription"
az account set --subscription "$SUBSCRIPTION_ID"

az account show \
  --query "{Subscription:name,SubscriptionId:id,Tenant:tenantId}" \
  -o table

echo ""
echo "[2/8] Terraform deployment"

cd "$TF_DIR"

terraform init
terraform validate
terraform plan -out=tfplan
terraform apply -auto-approve tfplan

cd "$ROOT_DIR"

echo ""
echo "[3/8] Waiting for AKS"

az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query "{Name:name,State:provisioningState,Location:location}" \
  -o table

echo ""
echo "[4/8] Verify AKS nodes"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get nodes -o wide"

echo ""
echo "[5/8] Install Argo CD"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl rollout status deployment/argocd-server -n argocd --timeout=300s"

echo ""
echo "[6/8] Apply Azure demo runtime dependencies"

cd "$ROOT_DIR"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -f infrastructure/kubernetes/demo/azure/" \
  --file .

echo ""
echo "[7/8] Apply FireFusion Argo CD configuration"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -k infrastructure/argocd" \
  --file .

echo ""
echo "[8/8] Initial deployment status"

sleep 20

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods,svc,deployments -n firefusion"

echo ""
echo "================================================="
echo " FireFusion Azure Demo deployment completed"
echo " Run verify-azure-demo.sh next"
echo "================================================="