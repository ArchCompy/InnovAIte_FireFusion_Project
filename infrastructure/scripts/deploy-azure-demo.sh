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
OBSERVABILITY_DIR="$ROOT_DIR/infrastructure/observability"
OBSERVABILITY_VALIDATE="$ROOT_DIR/infrastructure/scripts/observability-validate.sh"

TEMP_DIR="/tmp/firefusion-azure-demo"

DEPENDENCIES_BUNDLE="$TEMP_DIR/firefusion-azure-dependencies.yaml"
ARGO_BUNDLE="$TEMP_DIR/firefusion-argocd.yaml"
OBSERVABILITY_BUNDLE="$TEMP_DIR/firefusion-observability.yaml"
GRAFANA_SECRET_BUNDLE="$TEMP_DIR/grafana-admin-secret.yaml"

# ============================================================
# Demo Runtime Credentials
# ============================================================

# Demo-only credentials.
# Environment variables can override these values.
# Kubernetes Secret manifests are generated at runtime and are
# never stored as committed Secret manifests.

POSTGRES_PASSWORD="${FIREFUSION_POSTGRES_PASSWORD:-FireFusionDemoDB2026}"
RABBITMQ_PASSWORD="${FIREFUSION_RABBITMQ_PASSWORD:-FireFusionDemoMQ2026}"
API_KEY="${FIREFUSION_API_KEY:-FireFusionDemoAPI2026}"

BROKER_URL="amqp://firefusion:${RABBITMQ_PASSWORD}@broker.firefusion.svc.cluster.local:5672/"
CACHE_URL="redis://cache.firefusion.svc.cluster.local:6379/0"
DB_URL="postgresql://postgres:${POSTGRES_PASSWORD}@relational-db.firefusion.svc.cluster.local:5432/postgres"
RELATIONAL_DB_URL="$DB_URL"

# Grafana credentials.
# A password may be supplied using:
# FIREFUSION_GRAFANA_ADMIN_PASSWORD
#
# Otherwise a random demo password is generated.

GRAFANA_ADMIN_USER="${FIREFUSION_GRAFANA_ADMIN_USER:-admin}"

if [ -n "${FIREFUSION_GRAFANA_ADMIN_PASSWORD:-}" ]; then
  GRAFANA_ADMIN_PASSWORD="$FIREFUSION_GRAFANA_ADMIN_PASSWORD"
else
  GRAFANA_ADMIN_PASSWORD="$(openssl rand -hex 16)"
fi

# ============================================================
# Cleanup
# ============================================================

cleanup() {
  rm -f "$DEPENDENCIES_BUNDLE"
  rm -f "$ARGO_BUNDLE"
  rm -f "$OBSERVABILITY_BUNDLE"
  rm -f "$GRAFANA_SECRET_BUNDLE"
}

trap cleanup EXIT

# ============================================================
# Helper - Wait for LoadBalancer IP
# ============================================================

wait_for_load_balancer() {
  local namespace="$1"
  local service="$2"
  local timeout_seconds="${3:-300}"

  echo "Waiting for $service LoadBalancer public IP..."

  az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$AKS_CLUSTER" \
    --command "set -e
ATTEMPTS=$((timeout_seconds / 10))

for i in \$(seq 1 \$ATTEMPTS); do
  IP=\$(kubectl get svc '$service' -n '$namespace' \
    -o jsonpath='{.status.loadBalancer.ingress[0].ip}' \
    2>/dev/null || true)

  if [ -n \"\$IP\" ]; then
    echo '$service public IP:' \"\$IP\"
    exit 0
  fi

  echo 'Waiting for $service public IP...' \"\$i/\$ATTEMPTS\"
  sleep 10
done

echo 'ERROR: Timed out waiting for $service public IP.'
exit 1"
}

echo "================================================="
echo " FireFusion Azure Demo - Automated Deployment"
echo "================================================="

# ============================================================
# Pre-flight Checks
# ============================================================

echo ""
echo "[Pre-flight] Checking required tools and files"

for cmd in az terraform kubectl git openssl; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Required command '$cmd' was not found."
    exit 1
  fi
done

for directory in \
  "$TF_DIR" \
  "$DEMO_DIR" \
  "$ARGO_DIR" \
  "$OBSERVABILITY_DIR"
do
  if [ ! -d "$directory" ]; then
    echo "ERROR: Required directory not found:"
    echo "$directory"
    exit 1
  fi
done

if [ ! -x "$OBSERVABILITY_VALIDATE" ]; then
  echo "ERROR: Observability validation script is missing or not executable:"
  echo "$OBSERVABILITY_VALIDATE"
  exit 1
fi

mkdir -p "$TEMP_DIR"

echo "Pre-flight checks passed."

# ============================================================
# 1. Azure Subscription
# ============================================================

echo ""
echo "[1/9] Azure subscription"

az account set \
  --subscription "$SUBSCRIPTION_ID"

az account show \
  --query "{Subscription:name,SubscriptionId:id,Tenant:tenantId}" \
  -o table

# ============================================================
# 2. Terraform Deployment
# ============================================================

echo ""
echo "[2/9] Terraform deployment"

cd "$TF_DIR"

echo "Terraform directory:"
pwd

terraform init
terraform validate

echo ""
echo "Creating Terraform deployment plan..."

rm -f tfplan

terraform plan \
  -out=tfplan

echo ""
echo "Applying Terraform deployment plan..."

terraform apply \
  -auto-approve \
  tfplan

rm -f tfplan

cd "$ROOT_DIR"

# ============================================================
# 3. Verify AKS Provisioning
# ============================================================

echo ""
echo "[3/9] Verify AKS provisioning"

az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query "{Name:name,State:provisioningState,Location:location}" \
  -o table

# ============================================================
# 4. Verify AKS Nodes
# ============================================================

echo ""
echo "[4/9] Verify AKS nodes"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get nodes -o wide"

# ============================================================
# 5. Install / Reconcile Argo CD
# ============================================================

echo ""
echo "[5/9] Install and expose Argo CD"

echo ""
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
  --command "set -e
kubectl rollout status deployment/argocd-server \
  -n argocd \
  --timeout=300s"

echo ""
echo "Argo CD pods:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n argocd"

echo ""
echo "Exposing Argo CD UI using Azure LoadBalancer..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl patch svc argocd-server \
    -n argocd \
    --type merge \
    -p '{\"spec\":{\"type\":\"LoadBalancer\"}}'"

echo ""

wait_for_load_balancer "argocd" "argocd-server" 300

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
echo "[6/9] Apply Azure demo runtime dependencies"

echo ""
echo "Creating FireFusion namespace..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl create namespace firefusion \
    --dry-run=client -o yaml | kubectl apply -f -"

echo ""
echo "Verifying FireFusion namespace..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get namespace firefusion"

# ------------------------------------------------------------
# FireFusion Runtime Secret
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
# Runtime Dependency Bundle
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

echo ""
echo "Applying runtime dependencies to AKS..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -f firefusion-azure-dependencies.yaml" \
  --file "$DEPENDENCIES_BUNDLE"

# ------------------------------------------------------------
# Wait for Runtime Dependencies
# ------------------------------------------------------------

echo ""
echo "Waiting for PostgreSQL, RabbitMQ and Redis..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e
kubectl rollout status deployment/relational-db \
  -n firefusion --timeout=300s

kubectl rollout status deployment/broker \
  -n firefusion --timeout=300s

kubectl rollout status deployment/cache \
  -n firefusion --timeout=300s"

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
echo "[7/9] Apply FireFusion Argo CD configuration"

echo ""
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
echo "Waiting for Argo CD applications to be created..."

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
# 8. Wait for FireFusion GitOps Deployment
# ============================================================

echo ""
echo "[8/9] Wait for FireFusion GitOps deployment"

echo ""
echo "Waiting for FireFusion application workloads..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e

for i in \$(seq 1 30); do
  if kubectl get deployment firefusion-api \
      -n firefusion >/dev/null 2>&1 &&
     kubectl get deployment model-api \
      -n firefusion >/dev/null 2>&1 &&
     kubectl get deployment aggregator-api \
      -n firefusion >/dev/null 2>&1 &&
     kubectl get deployment firefusion-frontend \
      -n firefusion >/dev/null 2>&1; then

    echo 'FireFusion application deployments detected.'
    break
  fi

  if [ \"\$i\" -eq 30 ]; then
    echo 'ERROR: Timed out waiting for FireFusion deployments.'
    exit 1
  fi

  echo \"Waiting for Argo CD application deployment... \$i/30\"
  sleep 10
done

kubectl rollout status deployment/firefusion-api \
  -n firefusion --timeout=300s

kubectl rollout status deployment/model-api \
  -n firefusion --timeout=300s

kubectl rollout status deployment/aggregator-api \
  -n firefusion --timeout=300s

kubectl rollout status deployment/firefusion-frontend \
  -n firefusion --timeout=300s"

echo ""
echo "Waiting for FireFusion Azure Argo CD application to become Synced / Healthy..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e

for i in \$(seq 1 30); do
  SYNC=\$(kubectl get application firefusion-azure \
    -n argocd \
    -o jsonpath='{.status.sync.status}' \
    2>/dev/null || true)

  HEALTH=\$(kubectl get application firefusion-azure \
    -n argocd \
    -o jsonpath='{.status.health.status}' \
    2>/dev/null || true)

  echo \"FireFusion Azure: sync=\$SYNC health=\$HEALTH\"

  if [ \"\$SYNC\" = 'Synced' ] && [ \"\$HEALTH\" = 'Healthy' ]; then
    echo 'FireFusion Azure application is Synced / Healthy.'
    exit 0
  fi

  sleep 10
done

echo 'ERROR: FireFusion Azure application did not become Synced / Healthy.'
exit 1"

echo ""
echo "Argo CD application status:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get applications -n argocd"

echo ""
echo "FireFusion deployments:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get deployments -n firefusion"

echo ""
echo "FireFusion pods:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n firefusion -o wide"

echo ""
echo "FireFusion services:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n firefusion -o wide"

echo ""
echo "Waiting for FireFusion frontend public IP..."

wait_for_load_balancer "firefusion" "firefusion-frontend" 300

# ============================================================
# 9. Deploy Observability Stack
# ============================================================

echo ""
echo "[9/9] Deploy FireFusion observability stack"

echo ""
echo "Validating observability manifests..."

"$OBSERVABILITY_VALIDATE"

# ------------------------------------------------------------
# Monitoring Namespace
# ------------------------------------------------------------

echo ""
echo "Creating monitoring namespace..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl create namespace monitoring \
    --dry-run=client -o yaml | kubectl apply -f -"

# ------------------------------------------------------------
# Grafana Runtime Secret
# ------------------------------------------------------------

echo ""
echo "Generating Grafana runtime Secret..."

rm -f "$GRAFANA_SECRET_BUNDLE"

kubectl create secret generic grafana-admin \
  --namespace monitoring \
  --from-literal=admin-user="$GRAFANA_ADMIN_USER" \
  --from-literal=admin-password="$GRAFANA_ADMIN_PASSWORD" \
  --dry-run=client \
  -o yaml > "$GRAFANA_SECRET_BUNDLE"

chmod 600 "$GRAFANA_SECRET_BUNDLE"

echo ""
echo "Applying Grafana runtime Secret..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -f grafana-admin-secret.yaml" \
  --file "$GRAFANA_SECRET_BUNDLE"

rm -f "$GRAFANA_SECRET_BUNDLE"

echo ""
echo "Verifying Grafana runtime Secret..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get secret grafana-admin -n monitoring"

# ------------------------------------------------------------
# Render Observability Stack
# ------------------------------------------------------------

echo ""
echo "Rendering observability Kustomize configuration..."

rm -f "$OBSERVABILITY_BUNDLE"

kubectl kustomize "$OBSERVABILITY_DIR" > "$OBSERVABILITY_BUNDLE"

if [ ! -s "$OBSERVABILITY_BUNDLE" ]; then
  echo "ERROR: Rendered observability bundle is empty."
  exit 1
fi

echo ""
echo "Observability bundle created:"
ls -lh "$OBSERVABILITY_BUNDLE"

# ------------------------------------------------------------
# Apply Observability Stack
# ------------------------------------------------------------

echo ""
echo "Applying observability stack to AKS..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl apply -f firefusion-observability.yaml" \
  --file "$OBSERVABILITY_BUNDLE"

# ------------------------------------------------------------
# Wait for Observability Workloads
# ------------------------------------------------------------

echo ""
echo "Waiting for observability workloads..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e

kubectl rollout status deployment/prometheus \
  -n monitoring --timeout=300s

kubectl rollout status deployment/grafana \
  -n monitoring --timeout=300s

kubectl rollout status deployment/loki \
  -n monitoring --timeout=300s

kubectl rollout status deployment/alloy \
  -n monitoring --timeout=300s"

# ------------------------------------------------------------
# Expose Grafana and Prometheus
# ------------------------------------------------------------

echo ""
echo "Exposing Grafana and Prometheus for temporary demo access..."

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e

kubectl patch svc grafana \
  -n monitoring \
  --type merge \
  -p '{\"spec\":{\"type\":\"LoadBalancer\"}}'

kubectl patch svc prometheus \
  -n monitoring \
  --type merge \
  -p '{\"spec\":{\"type\":\"LoadBalancer\"}}'"

echo ""

wait_for_load_balancer "monitoring" "grafana" 300

echo ""

wait_for_load_balancer "monitoring" "prometheus" 300

# ------------------------------------------------------------
# Verify Observability Stack
# ------------------------------------------------------------

echo ""
echo "Observability deployments:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get deployments -n monitoring"

echo ""
echo "Observability pods:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n monitoring -o wide"

echo ""
echo "Observability services:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n monitoring -o wide"

# ============================================================
# Demo Access Information
# ============================================================

echo ""
echo "================================================="
echo " FireFusion Demo Access Information"
echo "================================================="

echo ""
echo "FireFusion frontend:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc firefusion-frontend -n firefusion -o wide"

echo ""
echo "Argo CD UI:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc argocd-server -n argocd -o wide"

echo ""
echo "Grafana UI:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc grafana -n monitoring -o wide"

echo ""
echo "Prometheus UI:"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc prometheus -n monitoring -o wide"

echo ""
echo "Grafana username:"
echo "$GRAFANA_ADMIN_USER"

echo ""
echo "Grafana password:"
echo "$GRAFANA_ADMIN_PASSWORD"

echo ""
echo "IMPORTANT:"
echo "The Grafana password above is generated for this demo deployment."
echo "Do not commit it to Git or include it in screenshots."

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

# ============================================================
# Final Cluster Summary
# ============================================================

echo ""
echo "================================================="
echo " Final Kubernetes Deployment Summary"
echo "================================================="

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get deployments -A"

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
echo "  FireFusion APIs      : Running"
echo "  FireFusion frontend  : Running"
echo "  FireFusion Azure app : Synced / Healthy"
echo "  Prometheus           : Running"
echo "  Grafana              : Running"
echo "  Loki                 : Running"
echo "  Alloy                : Running"
echo "  Grafana UI           : LoadBalancer"
echo "  Prometheus UI        : LoadBalancer"
echo ""
echo "NOTE:"
echo "Argo CD, Grafana and Prometheus are publicly exposed only"
echo "for the temporary FireFusion demonstration environment."
echo "================================================="