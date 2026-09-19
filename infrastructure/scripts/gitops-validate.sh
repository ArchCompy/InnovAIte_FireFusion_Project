#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
ARGOCD_DIR="${REPO_ROOT}/infrastructure/argocd"

echo "============================================================"
echo " FireFusion Argo CD GitOps Validation"
echo "============================================================"
echo

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is required."
  exit 1
fi

OUTPUT_FILE="$(mktemp /tmp/firefusion-argocd-XXXXXX.yaml)"

cleanup() {
  rm -f "${OUTPUT_FILE}"
}

trap cleanup EXIT

echo "[1/6] Rendering Argo CD configuration..."

kubectl kustomize "${ARGOCD_DIR}" > "${OUTPUT_FILE}"

[[ -s "${OUTPUT_FILE}" ]] || {
  echo "ERROR: Argo CD manifest is empty."
  exit 1
}

echo "PASS: Argo CD configuration rendered."
echo

echo "[2/6] Validating Argo CD resources..."

PROJECT_COUNT="$(grep -c '^kind: AppProject$' "${OUTPUT_FILE}" || true)"
APPLICATION_COUNT="$(grep -c '^kind: Application$' "${OUTPUT_FILE}" || true)"

[[ "${PROJECT_COUNT}" -eq 1 ]] || {
  echo "ERROR: Expected 1 AppProject, found ${PROJECT_COUNT}."
  exit 1
}

[[ "${APPLICATION_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected 3 Applications, found ${APPLICATION_COUNT}."
  exit 1
}

echo "PASS: 1 AppProject and 3 Applications detected."
echo

echo "[3/6] Validating Git repository references..."

REPO_COUNT="$(
  grep -c 'repoURL: https://github.com/InnovAIte-Deakin/InnovAIte_FireFusion_Project.git' \
    "${OUTPUT_FILE}" || true
)"

[[ "${REPO_COUNT}" -eq 3 ]] || {
  echo "ERROR: Expected repository reference in all 3 Applications."
  exit 1
}

echo "PASS: All Applications use the FireFusion Git repository."
echo

echo "[4/6] Validating provider overlay paths..."

for provider in azure aws gcp
do
  if ! grep -q \
    "path: infrastructure/kubernetes/overlays/${provider}" \
    "${OUTPUT_FILE}"
  then
    echo "ERROR: Missing Argo CD path for ${provider}."
    exit 1
  fi

  if ! kubectl kustomize \
    "${REPO_ROOT}/infrastructure/kubernetes/overlays/${provider}" \
    >/dev/null
  then
    echo "ERROR: ${provider} Kubernetes overlay failed to render."
    exit 1
  fi

  echo "PASS: ${provider}"
done

echo
echo "[5/6] Validating automated reconciliation..."

SELF_HEAL_COUNT="$(grep -c 'selfHeal: true' "${OUTPUT_FILE}" || true)"
PRUNE_COUNT="$(grep -c 'prune: true' "${OUTPUT_FILE}" || true)"

[[ "${SELF_HEAL_COUNT}" -eq 3 ]] || {
  echo "ERROR: selfHeal is not enabled for all Applications."
  exit 1
}

[[ "${PRUNE_COUNT}" -eq 3 ]] || {
  echo "ERROR: prune is not enabled for all Applications."
  exit 1
}

echo "PASS: Automated prune and self-healing configured."
echo

echo "[6/6] Validating FireFusion destination..."

DESTINATION_COUNT="$(
  grep -c 'namespace: firefusion' "${OUTPUT_FILE}" || true
)"

if [[ "${DESTINATION_COUNT}" -lt 3 ]]; then
  echo "ERROR: FireFusion destination namespace is missing."
  exit 1
fi

echo "PASS: FireFusion destination configuration detected."

echo
echo "============================================================"
echo " GITOPS VALIDATION SUCCESSFUL"
echo "============================================================"
echo
echo "Validated:"
echo "  - Argo CD AppProject"
echo "  - Azure/AWS/GCP Applications"
echo "  - Git repository source"
echo "  - provider Kustomize overlays"
echo "  - automated pruning"
echo "  - self-healing"
echo
echo "No Argo CD resources were applied."
