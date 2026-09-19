#!/usr/bin/env bash

set -euo pipefail

SUBSCRIPTION_ID="cfd11b14-72e9-4d19-8357-b7648abd8ac6"
RESOURCE_GROUP="firefusion-demo-rg"
AKS_CLUSTER="aks-firefusion-demo"

echo "================================================="
echo " FireFusion Azure Demo - Verification"
echo "================================================="

az account set --subscription "$SUBSCRIPTION_ID"

# ============================================================
# 1. AKS Infrastructure
# ============================================================

echo ""
echo "[1/10] AKS cluster and nodes"

az aks show \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --query "{Name:name,State:provisioningState,Location:location}" \
  -o table

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get nodes -o wide"

# ============================================================
# 2. FireFusion Deployments
# ============================================================

echo ""
echo "[2/10] FireFusion deployments"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e
kubectl rollout status deployment/firefusion-api -n firefusion --timeout=180s
kubectl rollout status deployment/model-api -n firefusion --timeout=180s
kubectl rollout status deployment/aggregator-api -n firefusion --timeout=180s
kubectl rollout status deployment/firefusion-frontend -n firefusion --timeout=180s
kubectl rollout status deployment/relational-db -n firefusion --timeout=180s
kubectl rollout status deployment/broker -n firefusion --timeout=180s
kubectl rollout status deployment/cache -n firefusion --timeout=180s
kubectl get deployments -n firefusion"

# ============================================================
# 3. FireFusion Pods
# ============================================================

echo ""
echo "[3/10] FireFusion pods"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n firefusion -o wide"

# ============================================================
# 4. FireFusion Services
# ============================================================

echo ""
echo "[4/10] FireFusion services"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n firefusion -o wide"

# ============================================================
# 5. Argo CD
# ============================================================

echo ""
echo "[5/10] Argo CD GitOps status"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e
kubectl rollout status deployment/argocd-server -n argocd --timeout=180s
kubectl get applications -n argocd
kubectl get svc argocd-server -n argocd -o wide"

# ============================================================
# 6. Observability Deployments
# ============================================================

echo ""
echo "[6/10] Observability deployments"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e
kubectl rollout status deployment/prometheus -n monitoring --timeout=180s
kubectl rollout status deployment/grafana -n monitoring --timeout=180s
kubectl rollout status deployment/loki -n monitoring --timeout=180s
kubectl rollout status deployment/alloy -n monitoring --timeout=180s
kubectl get deployments -n monitoring"

# ============================================================
# 7. Observability Pods
# ============================================================

echo ""
echo "[7/10] Observability pods"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get pods -n monitoring -o wide"

# ============================================================
# 8. Observability Services
# ============================================================

echo ""
echo "[8/10] Observability services"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc -n monitoring -o wide"

# ============================================================
# 9. Prometheus FireFusion Targets
# ============================================================

echo ""
echo "[9/10] Prometheus FireFusion backend targets"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e
PROM_POD=\$(kubectl get pod -n monitoring -l app.kubernetes.io/name=prometheus -o jsonpath='{.items[0].metadata.name}')

echo \"Prometheus pod: \$PROM_POD\"

kubectl exec -n monitoring \"\$PROM_POD\" -- \
  promtool query instant http://localhost:9090 \
  'up{job=\"firefusion-backend\"}'"

# ============================================================
# 10. Logging and Final Status
# ============================================================

echo ""
echo "[10/10] Loki / Alloy logging status"

az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "set -e
echo '=== LOKI ==='
kubectl get deployment loki -n monitoring
kubectl get pod -n monitoring -l app.kubernetes.io/name=loki

echo ''
echo '=== ALLOY ==='
kubectl get deployment alloy -n monitoring
kubectl logs -n monitoring deployment/alloy --tail=15"

# ============================================================
# Final Access Information
# ============================================================

echo ""
echo "================================================="
echo " Demo Public Endpoints"
echo "================================================="

echo ""
echo "FireFusion frontend:"
az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc firefusion-frontend -n firefusion -o wide"

echo ""
echo "Argo CD:"
az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc argocd-server -n argocd -o wide"

echo ""
echo "Grafana:"
az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc grafana -n monitoring -o wide"

echo ""
echo "Prometheus:"
az aks command invoke \
  --resource-group "$RESOURCE_GROUP" \
  --name "$AKS_CLUSTER" \
  --command "kubectl get svc prometheus -n monitoring -o wide"

echo ""
echo "================================================="
echo " FIREFUSION AZURE DEMO VERIFICATION SUCCESSFUL"
echo "================================================="
echo ""
echo "Validated:"
echo "  AKS                  : Running"
echo "  FireFusion APIs      : Available"
echo "  FireFusion frontend  : Available"
echo "  PostgreSQL           : Available"
echo "  RabbitMQ             : Available"
echo "  Redis                : Available"
echo "  Argo CD              : Running"
echo "  Prometheus           : Running"
echo "  Grafana              : Running"
echo "  Loki                 : Running"
echo "  Alloy                : Running"
echo "  Backend metrics      : Queried through Prometheus"
echo "  Centralized logs     : Alloy active"
echo "================================================="