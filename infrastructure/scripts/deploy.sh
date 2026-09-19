#!/usr/bin/env bash

set -euo pipefail

PROVIDER="${1:-}"
IMAGE_TAG="${2:-}"
ACTION="${3:-}"
NAMESPACE="firefusion"

if [[ -z "${PROVIDER}" || -z "${IMAGE_TAG}" ]]; then
  echo "Usage:"
  echo "  $0 <azure|aws|gcp> <image-tag> [--apply]"
  echo
  echo "Safe validation example:"
  echo "  DOCKERHUB_USERNAME=myuser $0 gcp abc1234"
  echo
  echo "Actual deployment example:"
  echo "  DOCKERHUB_USERNAME=myuser $0 gcp abc1234 --apply"
  exit 1
fi

case "${PROVIDER}" in
  azure|aws|gcp)
    ;;
  *)
    echo "ERROR: Unsupported provider '${PROVIDER}'."
    exit 1
    ;;
esac

if [[ -z "${DOCKERHUB_USERNAME:-}" ]]; then
  echo "ERROR: DOCKERHUB_USERNAME is required."
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
RENDER_SCRIPT="${REPO_ROOT}/infrastructure/scripts/render-deployment.sh"
MANIFEST="${REPO_ROOT}/infrastructure/rendered/firefusion-${PROVIDER}-${IMAGE_TAG}.yaml"

echo "============================================================"
echo " FireFusion Kubernetes Deployment"
echo "============================================================"
echo "Provider : ${PROVIDER}"
echo "Image tag: ${IMAGE_TAG}"
echo "Namespace: ${NAMESPACE}"
echo

echo "[1/5] Rendering and validating deployment manifest..."

"${RENDER_SCRIPT}" "${PROVIDER}" "${IMAGE_TAG}"

if [[ ! -f "${MANIFEST}" ]]; then
  echo "ERROR: Expected manifest was not generated:"
  echo "${MANIFEST}"
  exit 1
fi

echo
echo "PASS: Deployment manifest prepared."

echo
echo "[2/5] Checking deployment mode..."

if [[ "${ACTION}" != "--apply" ]]; then
  echo
  echo "SAFE MODE"
  echo "No Kubernetes resources will be changed."
  echo
  echo "Validated manifest:"
  echo "${MANIFEST}"
  echo
  echo "To deploy to a connected and approved cluster, run:"
  echo
  echo "  DOCKERHUB_USERNAME=${DOCKERHUB_USERNAME} \\"
  echo "  $0 ${PROVIDER} ${IMAGE_TAG} --apply"
  echo
  echo "============================================================"
  echo " DEPLOYMENT PREPARATION SUCCESSFUL"
  echo "============================================================"
  exit 0
fi

echo "APPLY MODE ENABLED."
echo

echo "[3/5] Verifying Kubernetes cluster connection..."

if ! kubectl cluster-info >/dev/null 2>&1; then
  echo "ERROR: No reachable Kubernetes cluster."
  echo "Deployment aborted."
  exit 1
fi

CURRENT_CONTEXT="$(kubectl config current-context)"

echo "Connected context: ${CURRENT_CONTEXT}"
echo

echo "WARNING: Kubernetes resources are about to be applied."
echo "Provider : ${PROVIDER}"
echo "Context  : ${CURRENT_CONTEXT}"
echo

read -r -p "Type DEPLOY to continue: " CONFIRMATION

if [[ "${CONFIRMATION}" != "DEPLOY" ]]; then
  echo "Deployment cancelled."
  exit 1
fi

echo
echo "[4/5] Applying Kubernetes manifest..."

kubectl apply -f "${MANIFEST}"

echo
echo "[5/5] Waiting for backend deployments..."

for deployment in \
  aggregator-api \
  firefusion-api \
  model-api
do
  echo
  echo "Waiting for deployment/${deployment}..."

  kubectl rollout status \
    "deployment/${deployment}" \
    -n "${NAMESPACE}" \
    --timeout=300s
done

echo
echo "============================================================"
echo " DEPLOYMENT SUCCESSFUL"
echo "============================================================"

kubectl get deployments,pods,services \
  -n "${NAMESPACE}" \
  -o wide

echo
echo "Provider : ${PROVIDER}"
echo "Image tag: ${IMAGE_TAG}"
echo "Context  : ${CURRENT_CONTEXT}"
