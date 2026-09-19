#!/usr/bin/env bash

set -euo pipefail

PROVIDER="${1:-}"
IMAGE_TAG="${2:-}"
DOCKERHUB_USERNAME="${DOCKERHUB_USERNAME:-}"

if [[ -z "${PROVIDER}" || -z "${IMAGE_TAG}" ]]; then
  echo "Usage:"
  echo "  DOCKERHUB_USERNAME=<username> $0 <azure|aws|gcp> <image-tag>"
  echo
  echo "Example:"
  echo "  DOCKERHUB_USERNAME=myuser $0 gcp abc1234"
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

if [[ -z "${DOCKERHUB_USERNAME}" ]]; then
  echo "ERROR: DOCKERHUB_USERNAME environment variable is required."
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
OVERLAY="${REPO_ROOT}/infrastructure/kubernetes/overlays/${PROVIDER}"

OUTPUT_DIR="${REPO_ROOT}/infrastructure/rendered"
OUTPUT_FILE="${OUTPUT_DIR}/firefusion-${PROVIDER}-${IMAGE_TAG}.yaml"

mkdir -p "${OUTPUT_DIR}"

echo "============================================================"
echo " FireFusion Deployment Manifest Renderer"
echo "============================================================"
echo "Provider        : ${PROVIDER}"
echo "Docker Hub user : ${DOCKERHUB_USERNAME}"
echo "Image tag       : ${IMAGE_TAG}"
echo "Overlay         : ${OVERLAY}"
echo "Output          : ${OUTPUT_FILE}"
echo

if ! command -v kubectl >/dev/null 2>&1; then
  echo "ERROR: kubectl is required but was not found."
  exit 1
fi

echo "[1/4] Validating Kubernetes overlay..."

"${REPO_ROOT}/infrastructure/scripts/validate.sh" "${PROVIDER}"

echo
echo "[2/4] Rendering provider overlay..."

kubectl kustomize "${OVERLAY}" > "${OUTPUT_FILE}"

echo "PASS: Base manifest rendered."
echo

echo "[3/4] Injecting immutable Docker Hub image references..."

python3 - "${OUTPUT_FILE}" "${DOCKERHUB_USERNAME}" "${IMAGE_TAG}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
username = sys.argv[2]
tag = sys.argv[3]

text = path.read_text()

replacements = {
    "firefusion/firefusion-api:latest":
        f"docker.io/{username}/firefusion-api:{tag}",
    "firefusion/model-api:latest":
        f"docker.io/{username}/model-api:{tag}",
    "firefusion/aggregator-api:latest":
        f"docker.io/{username}/aggregator-api:{tag}",
}

for old, new in replacements.items():
    if old not in text:
        print(f"ERROR: Expected image reference not found: {old}")
        sys.exit(1)

    text = text.replace(old, new)

path.write_text(text)

print("Injected:")
for new in replacements.values():
    print(f"  {new}")
PY

echo
echo "[4/4] Verifying rendered image references..."

EXPECTED_IMAGES=(
  "docker.io/${DOCKERHUB_USERNAME}/firefusion-api:${IMAGE_TAG}"
  "docker.io/${DOCKERHUB_USERNAME}/model-api:${IMAGE_TAG}"
  "docker.io/${DOCKERHUB_USERNAME}/aggregator-api:${IMAGE_TAG}"
)

for image in "${EXPECTED_IMAGES[@]}"
do
  if ! grep -q "image: ${image}" "${OUTPUT_FILE}"; then
    echo "ERROR: Image was not rendered correctly:"
    echo "${image}"
    exit 1
  fi

  echo "PASS: ${image}"
done

echo
echo "============================================================"
echo " DEPLOYMENT MANIFEST READY"
echo "============================================================"
echo "Provider : ${PROVIDER}"
echo "Tag      : ${IMAGE_TAG}"
echo "Manifest : ${OUTPUT_FILE}"
echo
echo "No Kubernetes resources were deployed."
