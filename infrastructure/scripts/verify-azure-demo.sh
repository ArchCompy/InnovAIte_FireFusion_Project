#!/usr/bin/env bash

set -euo pipefail

SUBSCRIPTION_ID="cfd11b14-72e9-4d19-8357-b7648abd8ac6"
RESOURCE_GROUP="firefusion-demo-rg"
AKS_CLUSTER="aks-firefusion-demo"

echo "=========================================="
echo " FireFusion Azure Demo - Verification"
echo "=========================================="

az account set --subscription "$SUBSCRIPTION_ID"

echo ""
echo "[1/5] AKS nodes"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get nodes -o wide"

echo ""
echo "[2/5] FireFusion deployments"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get deployments -n firefusion"

echo ""
echo "[3/5] FireFusion pods"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n firefusion -o wide"

echo ""
echo "[4/5] FireFusion services"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n firefusion -o wide"

echo ""
echo "[5/5] Argo CD application"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get applications -n argocd"

echo ""
echo "Verification completed."