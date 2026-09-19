#!/usr/bin/env bash

set -euo pipefail

NAMESPACE="${NAMESPACE:-firefusion}"

SERVICES=(
  "firefusion-api"
  "model-api"
  "aggregator-api"
)

echo "============================================================"
echo " FireFusion Kubernetes Smoke Test"
echo "============================================================"
echo "Namespace: ${NAMESPACE}"
echo

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is required but was not found."
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is required but was not found."
  exit 1
fi

if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "ERROR: Kubernetes cluster is not reachable."
  exit 1
fi

echo "[1/4] Checking backend deployments..."

for service in "${SERVICES[@]}"
do
  if ! kubectl get deployment "${service}" \
    -n "${NAMESPACE}" >/dev/null 2>&1
  then
    echo "ERROR: deployment/${service} was not found."
    exit 1
  fi

  echo "PASS: deployment/${service}"
done

echo
echo "[2/4] Checking rollout status..."

for service in "${SERVICES[@]}"
do
  echo "Checking deployment/${service}..."

  kubectl rollout status \
    "deployment/${service}" \
    -n "${NAMESPACE}" \
    --timeout=120s
done

echo
echo "PASS: All deployments successfully rolled out."

echo
echo "[3/4] Checking ready pods..."

for service in "${SERVICES[@]}"
do
  READY_PODS="$(
    kubectl get pods \
      -n "${NAMESPACE}" \
      -l "app.kubernetes.io/name=${service}" \
      --field-selector=status.phase=Running \
      --no-headers 2>/dev/null \
      | awk '$2 ~ /^1\/1$/ {count++} END {print count+0}'
  )"

  if [[ "${READY_PODS}" -lt 1 ]]; then
    echo "ERROR: No ready pod detected for ${service}."
    exit 1
  fi

  echo "PASS: ${service} has ${READY_PODS} ready pod(s)."
done

echo
echo "[4/4] Running /health and /ready endpoint tests..."

for service in "${SERVICES[@]}"
do
  echo
  echo "Testing ${service}..."

  LOCAL_PORT="$(
    python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("", 0))
print(s.getsockname()[1])
s.close()
PY
  )"

  kubectl port-forward \
    -n "${NAMESPACE}" \
    "service/${service}" \
    "${LOCAL_PORT}:8080" \
    >/tmp/firefusion-${service}-portforward.log 2>&1 &

  PF_PID=$!

  cleanup_port_forward() {
    kill "${PF_PID}" >/dev/null 2>&1 || true
    wait "${PF_PID}" >/dev/null 2>&1 || true
  }

  trap cleanup_port_forward EXIT

  SUCCESS=false

  for attempt in {1..15}
  do
    if curl -fsS \
      "http://127.0.0.1:${LOCAL_PORT}/health" \
      >/dev/null 2>&1
    then
      SUCCESS=true
      break
    fi

    sleep 1
  done

  if [[ "${SUCCESS}" != "true" ]]; then
    echo "ERROR: /health failed for ${service}."
    cat "/tmp/firefusion-${service}-portforward.log" || true
    cleanup_port_forward
    trap - EXIT
    exit 1
  fi

  echo "PASS: ${service} /health"

  if ! curl -fsS \
    "http://127.0.0.1:${LOCAL_PORT}/ready" \
    >/dev/null
  then
    echo "ERROR: /ready failed for ${service}."
    cleanup_port_forward
    trap - EXIT
    exit 1
  fi

  echo "PASS: ${service} /ready"

  cleanup_port_forward
  trap - EXIT
done

echo
echo "============================================================"
echo " SMOKE TEST SUCCESSFUL"
echo "============================================================"
echo
echo "Validated:"
echo "  - backend deployments exist"
echo "  - Kubernetes rollouts completed"
echo "  - backend pods are Ready"
echo "  - /health endpoint passed"
echo "  - /ready endpoint passed"
