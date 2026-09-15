#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# Demo Runtime Credentials
# ============================================================

# Demo-only credentials.
# Environment variables can override these values.
# The Kubernetes Secret is generated during deployment and is
# never stored in a committed Kubernetes Secret manifest.

POSTGRES_PASSWORD="${FIREFUSION_POSTGRES_PASSWORD:-FireFusionDemoDB2026}"
RABBITMQ_PASSWORD="${FIREFUSION_RABBITMQ_PASSWORD:-FireFusionDemoMQ2026}"
API_KEY="${FIREFUSION_API_KEY:-FireFusionDemoAPI2026}"

BROKER_URL="amqp://firefusion:${RABBITMQ_PASSWORD}@broker.firefusion.svc.cluster.local:5672/"
CACHE_URL="redis://cache.firefusion.svc.cluster.local:6379/0"
DB_URL="postgresql://postgres:${POSTGRES_PASSWORD}@relational-db.firefusion.svc.cluster.local:5432/postgres"
RELATIONAL_DB_URL="$DB_URL"

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
echo "[5/8] Install and expose Argo CD"

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

# ------------------------------------------------------------
# Expose Argo CD UI
# ------------------------------------------------------------

echo ""
echo "Exposing Argo CD UI using Azure LoadBalancer..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl patch svc argocd-server -n argocd --type merge -p '{\"spec\":{\"type\":\"LoadBalancer\"}}'"

echo ""
echo "Waiting for Azure LoadBalancer public IP..."

sleep 30

echo ""
echo "Argo CD service:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc argocd-server -n argocd -o wide"

# ============================================================
# 6. Deploy Azure Demo Runtime Dependencies
# ============================================================

echo ""
echo "[6/8] Apply Azure demo runtime dependencies"

# ------------------------------------------------------------
# Create FireFusion namespace
# ------------------------------------------------------------

echo "Creating FireFusion namespace..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl create namespace firefusion --dry-run=client -o yaml | kubectl apply -f -"

echo ""
echo "Verifying FireFusion namespace..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get namespace firefusion"

# ------------------------------------------------------------
# Create FireFusion runtime Secret
# ------------------------------------------------------------

echo ""
echo "Creating FireFusion runtime Secret..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl create secret generic firefusion-runtime-secrets \
    -n firefusion \
    --from-literal=POSTGRES_PASSWORD='$POSTGRES_PASSWORD' \
    --from-literal=RABBITMQ_PASSWORD='$RABBITMQ_PASSWORD' \
    --from-literal=BROKER_URL='$BROKER_URL' \
    --from-literal=CACHE_URL='$CACHE_URL' \
    --from-literal=DB_URL='$DB_URL' \
    --from-literal=RELATIONAL_DB_URL='$RELATIONAL_DB_URL' \
    --from-literal=VALID_API_KEY='$API_KEY' \
    --from-literal=API_KEY='$API_KEY' \
    --dry-run=client -o yaml | kubectl apply -f -"

echo ""
echo "Verifying FireFusion runtime Secret..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get secret firefusion-runtime-secrets -n firefusion"

# ------------------------------------------------------------
# Create runtime dependency bundle
# ------------------------------------------------------------

echo ""
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

# ------------------------------------------------------------
# Apply runtime dependencies
# ------------------------------------------------------------

echo ""
echo "Applying runtime dependencies to AKS..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -f firefusion-azure-dependencies.yaml" \
  --file "$DEPENDENCIES_BUNDLE"

# ------------------------------------------------------------
# Wait for runtime dependencies
# ------------------------------------------------------------

echo ""
echo "Waiting for runtime dependencies..."
sleep 30

# ------------------------------------------------------------
# Verify runtime dependencies
# ------------------------------------------------------------

echo ""
echo "Runtime dependency pods:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n firefusion -o wide"

echo ""
echo "Runtime dependency services:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n firefusion -o wide"

echo ""
echo "Runtime dependency deployments:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get deployments -n firefusion"

# ============================================================
# 7. Apply FireFusion Argo CD Configuration
# ============================================================

echo ""
echo "[7/8] Apply FireFusion Argo CD configuration"

echo "Rendering Argo CD Kustomize configuration locally..."

rm -f "$ARGO_BUNDLE"

kubectl kustomize "$ARGO_DIR" > "$ARGO_BUNDLE"

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
echo "Waiting for Argo CD to process the applications..."

sleep 15

echo ""
echo "Argo CD projects:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get appprojects -n argocd" || true

echo ""
echo "Argo CD applications:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get applications -n argocd" || true

# ============================================================
# 8. Initial FireFusion Deployment Status
# ============================================================

echo ""
echo "[8/8] Initial FireFusion deployment status"

echo "Waiting for Argo CD reconciliation..."
sleep 60

echo ""
echo "Argo CD application status:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get applications -n argocd" || true

echo ""
echo "FireFusion deployments:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get deployments -n firefusion" || true

echo ""
echo "FireFusion pods:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n firefusion -o wide" || true

echo ""
echo "FireFusion services:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n firefusion -o wide" || true

echo ""
echo "All cluster deployments:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get deployments -A" || true

# ============================================================
# Demo Access Information
# ============================================================

echo ""
echo "================================================="
echo " FireFusion Demo Access Information"
echo "================================================="

echo ""
echo "Argo CD UI service:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc argocd-server -n argocd -o wide" || true

echo ""
echo "Argo CD username:"
echo "admin"

echo ""
echo "To retrieve the Argo CD initial admin password:"
echo ""
echo "az aks command invoke \\"
echo "  --resource-group $RESOURCE_GROUP \\"
echo "  --name $AKS_CLUSTER \\"
echo "  --command \"kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d; echo\""

echo ""
echo "FireFusion services:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n firefusion -o wide" || true

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
echo "Expected final state:"
echo "  AKS                  : Ready"
echo "  Argo CD              : Running"
echo "  Argo CD UI           : LoadBalancer"
echo "  FireFusion namespace : Active"
echo "  Runtime Secret       : Created"
echo "  PostgreSQL           : Running"
echo "  RabbitMQ             : Running"
echo "  Redis                : Running"
echo "  FireFusion Azure app : Synced / Healthy"
echo ""
echo "NOTE:"
echo "Argo CD is publicly exposed only for the"
echo "temporary FireFusion demonstration environment."
echo "================================================="