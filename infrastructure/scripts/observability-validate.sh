#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OBSERVABILITY_DIR="${ROOT_DIR}/infrastructure/observability"
OUTPUT_FILE="$(mktemp)"

cleanup() {
  rm -f "${OUTPUT_FILE}"
}

trap cleanup EXIT

echo "============================================================"
echo " FireFusion Observability Validation"
echo "============================================================"
echo

command -v kubectl >/dev/null 2>&1 || {
  echo "ERROR: kubectl is required."
  exit 1
}

echo "[1/7] Rendering complete observability stack..."

kubectl kustomize "${OBSERVABILITY_DIR}" > "${OUTPUT_FILE}"

echo "PASS: Observability stack rendered successfully."
echo

echo "[2/7] Validating monitoring workloads..."

for workload in prometheus grafana loki alloy; do
  grep -q "name: ${workload}$" "${OUTPUT_FILE}" || {
    echo "ERROR: ${workload} was not found in rendered manifests."
    exit 1
  }
done

echo "PASS: Prometheus, Grafana, Loki and Alloy detected."
echo

echo "[3/7] Validating Prometheus metrics collection..."

grep -q 'job_name: firefusion-backend' "${OUTPUT_FILE}" || {
  echo "ERROR: FireFusion Prometheus scrape job was not found."
  exit 1
}

grep -q 'metrics_path: /metrics' "${OUTPUT_FILE}" || {
  echo "ERROR: /metrics scrape path was not found."
  exit 1
}

echo "PASS: FireFusion Prometheus scrape configuration detected."
echo

echo "[4/7] Validating Grafana data sources..."

grep -q 'name: Prometheus' "${OUTPUT_FILE}" || {
  echo "ERROR: Grafana Prometheus datasource was not found."
  exit 1
}

grep -q 'name: Loki' "${OUTPUT_FILE}" || {
  echo "ERROR: Grafana Loki datasource was not found."
  exit 1
}

echo "PASS: Prometheus and Loki Grafana datasources detected."
echo

echo "[5/7] Validating centralized logging..."

grep -q 'loki.source.kubernetes' "${OUTPUT_FILE}" || {
  echo "ERROR: Alloy Kubernetes log source was not found."
  exit 1
}

grep -q 'loki.write' "${OUTPUT_FILE}" || {
  echo "ERROR: Alloy Loki writer was not found."
  exit 1
}

grep -q 'loki/api/v1/push' "${OUTPUT_FILE}" || {
  echo "ERROR: Loki ingestion endpoint was not found."
  exit 1
}

echo "PASS: Alloy-to-Loki centralized logging configuration detected."
echo

echo "[6/7] Validating alerting rules..."

ALERTS=(
  FireFusionBackendServiceUnavailable
  FireFusionNoBackendTargets
  FireFusionHighHTTP5xxRate
  FireFusionHighRequestLatency
)

for alert in "${ALERTS[@]}"; do
  grep -q "alert: ${alert}" "${OUTPUT_FILE}" || {
    echo "ERROR: Alert rule ${alert} was not found."
    exit 1
  }
done

grep -q '/etc/prometheus/rules' "${OUTPUT_FILE}" || {
  echo "ERROR: Prometheus alert-rule mount was not found."
  exit 1
}

echo "PASS: FireFusion alert rules and Prometheus rule loading detected."
echo

echo "[7/7] Validating observability workload security..."

READ_ONLY_COUNT="$(grep -c 'readOnlyRootFilesystem: true' "${OUTPUT_FILE}" || true)"
NO_PRIV_ESC_COUNT="$(grep -c 'allowPrivilegeEscalation: false' "${OUTPUT_FILE}" || true)"
NON_ROOT_COUNT="$(grep -c 'runAsNonRoot: true' "${OUTPUT_FILE}" || true)"

[[ "${READ_ONLY_COUNT}" -ge 4 ]] || {
  echo "ERROR: Expected at least 4 read-only root filesystem controls, found ${READ_ONLY_COUNT}."
  exit 1
}

[[ "${NO_PRIV_ESC_COUNT}" -ge 4 ]] || {
  echo "ERROR: Expected at least 4 privilege-escalation controls, found ${NO_PRIV_ESC_COUNT}."
  exit 1
}

[[ "${NON_ROOT_COUNT}" -ge 4 ]] || {
  echo "ERROR: Expected at least 4 runAsNonRoot controls, found ${NON_ROOT_COUNT}."
  exit 1
}

if grep -qE 'privileged: true|hostPath:|nodes/proxy' "${OUTPUT_FILE}"; then
  echo "ERROR: Forbidden privileged observability configuration detected."
  exit 1
fi

echo "PASS: Observability workload security controls validated."
echo

echo "============================================================"
echo " OBSERVABILITY VALIDATION SUCCESSFUL"
echo "============================================================"
echo "Metrics : Prometheus"
echo "Visuals : Grafana"
echo "Logs    : Loki + Alloy"
echo "Alerts  : 4 FireFusion backend rules"
echo
echo "No resources were deployed."
