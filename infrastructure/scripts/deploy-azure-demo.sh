#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# FireFusion Azure Demo - Automated Deployment
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

SUBSCRIPTION_ID="cfd11b14-72e9-4d19-8357-b7648abd8ac6"
RESOURCE_GROUP="firefusion-demo-rg"
AKS_CLUSTER="aks-firefusion-demo"

TF_DIR="$ROOT_DIR/infrastructure/terraform/environments/dev/azure"
DEMO_DIR="$ROOT_DIR/infrastructure/kubernetes/demo/azure"
ARGO_DIR="$ROOT_DIR/infrastructure/argocd"

TEMP_DIR="/tmp/firefusion-azure-demo"
DEPENDENCIES_BUNDLE="$TEMP_DIR/firefusion-azure-dependencies.yaml"
ARGO_BUNDLE="$TEMP_DIR/firefusion-argocd.yaml"

echo "================================================="
echo " FireFusion Azure Demo - Automated Deployment"
echo "================================================="

# ============================================================
# Pre-flight Checks
# ============================================================

echo ""
echo "[Pre-flight] Checking required tools and files"

for cmd in az terraform kubectl git; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Required command '$cmd' was not found."
    exit 1
  fi
done

if [ ! -d "$TF_DIR" ]; then
  echo "ERROR: Terraform directory not found:"
  echo "$TF_DIR"
  exit 1
fi

if [ ! -d "$DEMO_DIR" ]; then
  echo "ERROR: Azure demo manifest directory not found:"
  echo "$DEMO_DIR"
  exit 1
fi

if [ ! -d "$ARGO_DIR" ]; then
  echo "ERROR: Argo CD configuration directory not found:"
  echo "$ARGO_DIR"
  exit 1
fi

mkdir -p "$TEMP_DIR"

echo "Pre-flight checks passed."

# ============================================================
# 1. Azure Subscription
# ============================================================

echo ""
echo "[1/8] Azure subscription"

az account set \
  --subscription "$SUBSCRIPTION_ID"

az account show \
  --query "{Subscription:name,SubscriptionId:id,Tenant:tenantId}" \
  -o table

# ============================================================
# 2. Terraform Deployment
# ============================================================

echo ""
echo "[2/8] Terraform deployment"

cd "$TF_DIR"

echo "Terraform directory:"
pwd

terraform init

terraform validate

echo ""
echo "Creating Terraform deployment plan..."

terraform plan \
  -out=tfplan

echo ""
echo "Applying Terraform deployment plan..."

terraform apply \
  -auto-approve \
  tfplan

cd "$ROOT_DIR"

# ============================================================
# 3. Verify AKS Provisioning
# ============================================================

echo ""
echo "[3/8] Verify AKS provisioning"

az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query "{Name:name,State:provisioningState,Location:location}" \
  -o table

# ============================================================
# 4. Verify AKS Nodes
# ============================================================

echo ""
echo "[4/8] Verify AKS nodes"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get nodes -o wide"

# ============================================================
# 5. Install / Reconcile Argo CD
# ============================================================

echo ""
echo "[5/8] Install Argo CD"

echo "Creating Argo CD namespace..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -"

echo ""
echo "Installing Argo CD using server-side apply..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply --server-side --force-conflicts -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml"

echo ""
echo "Waiting for Argo CD server..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl rollout status deployment/argocd-server -n argocd --timeout=300s"

echo ""
echo "Argo CD pods:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n argocd"

# ============================================================
# 6. Deploy Azure Demo Runtime Dependencies
# ============================================================

echo ""
echo "[6/8] Apply Azure demo runtime dependencies"

echo "Creating runtime dependency bundle..."

rm -f "$DEPENDENCIES_BUNDLE"

for manifest in \
  "$DEMO_DIR/postgres-init-configmap.yaml" \
  "$DEMO_DIR/runtime-dependencies.yaml" \
  "$DEMO_DIR/dependency-network-policies.yaml"
do
  if [ ! -f "$manifest" ]; then
    echo "ERROR: Required manifest not found:"
    echo "$manifest"
    exit 1
  fi

  echo "---" >> "$DEPENDENCIES_BUNDLE"
  cat "$manifest" >> "$DEPENDENCIES_BUNDLE"
  echo "" >> "$DEPENDENCIES_BUNDLE"
done

echo ""
echo "Dependency bundle created:"
ls -lh "$DEPENDENCIES_BUNDLE"

echo ""
echo "Applying runtime dependencies to AKS..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -f firefusion-azure-dependencies.yaml" \
  --file "$DEPENDENCIES_BUNDLE"

echo ""
echo "Waiting for runtime dependencies..."
sleep 15

echo ""
echo "Runtime dependency status:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods,svc -n firefusion"

# ============================================================
# 7. Apply FireFusion Argo CD Configuration
# ============================================================

echo ""
echo "[7/8] Apply FireFusion Argo CD configuration"

echo "Rendering Argo CD Kustomize configuration locally..."

rm -f "$ARGO_BUNDLE"

kubectl kustomize "$ARGO_DIR" \
  > "$ARGO_BUNDLE"

if [ ! -s "$ARGO_BUNDLE" ]; then
  echo "ERROR: Rendered Argo CD bundle is empty."
  exit 1
fi

echo ""
echo "Argo CD bundle created:"
ls -lh "$ARGO_BUNDLE"

echo ""
echo "Applying FireFusion Argo CD configuration..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -f firefusion-argocd.yaml" \
  --file "$ARGO_BUNDLE"

echo ""
echo "Argo CD projects:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get appprojects -n argocd"

echo ""
echo "Argo CD applications:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get applications -n argocd"

# ============================================================
# 8. Initial FireFusion Deployment Status
# ============================================================

echo ""
echo "[8/8] Initial FireFusion deployment status"

echo "Waiting for Argo CD reconciliation..."
sleep 30

echo ""
echo "Deployments:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get deployments -n firefusion"

echo ""
echo "Pods:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n firefusion -o wide"

echo ""
echo "Services:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n firefusion -o wide"

echo ""
echo "Argo CD application status:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get applications -n argocd"

# ============================================================
# Cleanup Temporary Bundles
# ============================================================

echo ""
echo "Cleaning temporary deployment bundles..."

rm -f "$DEPENDENCIES_BUNDLE"
rm -f "$ARGO_BUNDLE"

# ============================================================
# Complete
# ============================================================

echo ""
echo "================================================="
echo " FireFusion Azure Demo deployment completed"
echo "================================================="
echo ""
echo "Next:"
echo "./infrastructure/scripts/verify-azure-demo.sh"
echo ""
echo "NOTE:"
echo "Run verification before using the environment"
echo "for the FireFusion team demonstration."
echo "================================================="