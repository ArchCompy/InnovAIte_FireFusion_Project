#!/usr/bin/env bash

set -euo pipefail

PROVIDER="${1:-}"

if [[ -z "${PROVIDER}" ]]; then
  echo "Usage: $0 <azure|aws|gcp>"
  exit 1
fi

case "${PROVIDER}" in
  azure|aws|gcp)
    ;;
  *)
    echo "ERROR: Unsupported provider '${PROVIDER}'."
    echo "Supported providers: azure, aws, gcp"
    exit 1
    ;;
esac

REPO_ROOT="$(git rev-parse --show-toplevel)"
OVERLAY="${REPO_ROOT}/infrastructure/kubernetes/overlays/${PROVIDER}"

OUTPUT_FILE="$(mktemp "/tmp/firefusion-${PROVIDER}-XXXXXX.yaml")"

cleanup() {
  rm -f "${OUTPUT_FILE}"
}

trap cleanup EXIT

echo "============================================================"
echo " FireFusion Kubernetes Deployment Validation"
echo "============================================================"
echo "Provider : ${PROVIDER}"
echo "Overlay  : ${OVERLAY}"
echo

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is required but was not found."
  exit 1
fi

if [[ ! -f "${OVERLAY}/kustomization.yaml" ]]; then
  echo "ERROR: Kustomize overlay not found:"
  echo "${OVERLAY}/kustomization.yaml"
  exit 1
fi

echo "[1/7] Rendering Kustomize overlay..."

kubectl kustomize "${OVERLAY}" > "${OUTPUT_FILE}"

if [[ ! -s "${OUTPUT_FILE}" ]]; then
  echo "ERROR: Rendered manifest is empty."
  exit 1
fi

echo "PASS: Overlay rendered successfully."
echo

echo "[2/7] Validating core Kubernetes resources..."

DEPLOYMENT_COUNT="$(grep -c '^kind: Deployment$' "${OUTPUT_FILE}" || true)"
SERVICE_COUNT="$(grep -c '^kind: Service$' "${OUTPUT_FILE}" || true)"
NAMESPACE_COUNT="$(grep -c '^kind: Namespace$' "${OUTPUT_FILE}" || true)"

[[ "${DEPLOYMENT_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected 3 Deployments, found ${DEPLOYMENT_COUNT}."
  exit 1
}

[[ "${SERVICE_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected 3 Services, found ${SERVICE_COUNT}."
  exit 1
}

[[ "${NAMESPACE_COUNT}" -eq 1 ]] || {
  echo "ERROR: Expected 1 Namespace, found ${NAMESPACE_COUNT}."
  exit 1
}

echo "PASS: 3 Deployments, 3 Services and 1 Namespace detected."
echo

echo "[3/7] Validating health and readiness probes..."

HEALTH_COUNT="$(grep -c 'path: /health' "${OUTPUT_FILE}" || true)"
READY_COUNT="$(grep -c 'path: /ready' "${OUTPUT_FILE}" || true)"

[[ "${HEALTH_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected 3 /health probes, found ${HEALTH_COUNT}."
  exit 1
}

[[ "${READY_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected 3 /ready probes, found ${READY_COUNT}."
  exit 1
}

echo "PASS: All backend services contain health and readiness probes."
echo

echo "[4/7] Validating container security controls..."

NON_ROOT_COUNT="$(grep -c 'runAsNonRoot: true' "${OUTPUT_FILE}" || true)"
READ_ONLY_COUNT="$(grep -c 'readOnlyRootFilesystem: true' "${OUTPUT_FILE}" || true)"
NO_PRIV_ESC_COUNT="$(grep -c 'allowPrivilegeEscalation: false' "${OUTPUT_FILE}" || true)"
SECCOMP_COUNT="$(grep -c 'type: RuntimeDefault' "${OUTPUT_FILE}" || true)"

[[ "${NON_ROOT_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected runAsNonRoot on all 3 workloads."
  exit 1
}

[[ "${READ_ONLY_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected readOnlyRootFilesystem on all 3 workloads."
  exit 1
}

[[ "${NO_PRIV_ESC_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected allowPrivilegeEscalation=false on all 3 workloads."
  exit 1
}

[[ "${SECCOMP_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected RuntimeDefault seccomp profile on all 3 workloads."
  exit 1
}

echo "PASS: Container security controls validated."
echo

echo "[5/7] Validating RBAC and network security..."

ROLE_BINDING_COUNT="$(grep -c '^kind: RoleBinding$' "${OUTPUT_FILE}" || true)"
NETWORK_POLICY_COUNT="$(grep -c '^kind: NetworkPolicy$' "${OUTPUT_FILE}" || true)"

[[ "${ROLE_BINDING_COUNT}" -eq 1 ]] || {
  echo "ERROR: Expected 1 RoleBinding, found ${ROLE_BINDING_COUNT}."
  exit 1
}

[[ "${NETWORK_POLICY_COUNT}" -eq 4 ]] || {
  echo "ERROR: Expected 4 NetworkPolicies, found ${NETWORK_POLICY_COUNT}."
  exit 1
}

grep -q 'name: allow-prometheus-metrics' "${OUTPUT_FILE}" || {
  echo "ERROR: Prometheus metrics ingress NetworkPolicy was not found."
  exit 1
}

echo "PASS: RBAC and NetworkPolicy controls validated."
echo

echo "[6/7] Validating provider metadata..."

PROVIDER_LABEL_COUNT="$(
  grep -c "cloud.firefusion.io/provider: ${PROVIDER}" "${OUTPUT_FILE}" || true
)"

if [[ "${PROVIDER_LABEL_COUNT}" -lt 1 ]]; then
  echo "ERROR: Provider label '${PROVIDER}' not found."
  exit 1
fi

echo "PASS: Provider-specific metadata detected."
echo

echo "[7/7] Validating backend image definitions..."

for image in \
  "firefusion/firefusion-api" \
  "firefusion/model-api" \
  "firefusion/aggregator-api"
do
  if ! grep -q "image: ${image}:" "${OUTPUT_FILE}"; then
    echo "ERROR: Expected image reference not found: ${image}"
    exit 1
  fi

  echo "PASS: ${image}"
done

echo
echo "============================================================"
echo " VALIDATION SUCCESSFUL"
echo "============================================================"
echo "Provider: ${PROVIDER}"
echo
echo "The FireFusion Kubernetes overlay passed:"
echo "  - resource validation"
echo "  - health/readiness validation"
echo "  - container security validation"
echo "  - RBAC validation"
echo "  - NetworkPolicy validation"
echo "  - provider metadata validation"
echo "  - image definition validation"
echo
echo "No resources were deployed."
