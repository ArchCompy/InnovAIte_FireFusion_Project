#!/usr/bin/env bash

set -euo pipefail

PROVIDER="${1:-}"
IMAGE_TAG="${2:-}"
DOCKERHUB_USERNAME="${DOCKERHUB_USERNAME:-}"

if [[ -z "${PROVIDER}" || -z "${IMAGE_TAG}" ]]; then
  echo "Usage:"
  echo "  DOCKERHUB_USERNAME=<username> $0 <azure|aws|gcp> <image-tag>"
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

if [[ -z "${DOCKERHUB_USERNAME}" ]]; then
  echo "ERROR: DOCKERHUB_USERNAME is required."
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
KUSTOMIZATION="${REPO_ROOT}/infrastructure/kubernetes/overlays/${PROVIDER}/kustomization.yaml"

echo "============================================================"
echo " FireFusion GitOps Image Promotion"
echo "============================================================"
echo "Provider : ${PROVIDER}"
echo "Tag      : ${IMAGE_TAG}"
echo "Registry : docker.io/${DOCKERHUB_USERNAME}"
echo

python3 - "${KUSTOMIZATION}" "${DOCKERHUB_USERNAME}" "${IMAGE_TAG}" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
username = sys.argv[2]
tag = sys.argv[3]

text = path.read_text()

marker = "\nimages:\n"

image_block = f"""
images:
  - name: firefusion/firefusion-api
    newName: docker.io/{username}/firefusion-api
    newTag: {tag}
  - name: firefusion/model-api
    newName: docker.io/{username}/model-api
    newTag: {tag}
  - name: firefusion/aggregator-api
    newName: docker.io/{username}/aggregator-api
    newTag: {tag}
"""

if marker in text:
    text = text.split(marker, 1)[0].rstrip() + "\n" + image_block
else:
    text = text.rstrip() + "\n" + image_block

path.write_text(text)

print(f"Updated {path}")
PY

echo
echo "Validating promoted overlay..."

kubectl kustomize \
  "${REPO_ROOT}/infrastructure/kubernetes/overlays/${PROVIDER}" \
  > "/tmp/firefusion-${PROVIDER}-gitops.yaml"

for image in \
  "docker.io/${DOCKERHUB_USERNAME}/firefusion-api:${IMAGE_TAG}" \
  "docker.io/${DOCKERHUB_USERNAME}/model-api:${IMAGE_TAG}" \
  "docker.io/${DOCKERHUB_USERNAME}/aggregator-api:${IMAGE_TAG}"
do
  if ! grep -q "image: ${image}" "/tmp/firefusion-${PROVIDER}-gitops.yaml"; then
    echo "ERROR: Expected promoted image missing: ${image}"
    exit 1
  fi

  echo "PASS: ${image}"
done

echo
echo "============================================================"
echo " IMAGE PROMOTION READY FOR GIT"
echo "============================================================"
echo
echo "The ${PROVIDER} overlay now declares immutable image tag:"
echo "  ${IMAGE_TAG}"
echo
echo "Review the Git diff and commit the overlay when promotion"
echo "to this environment is approved."
echo
echo "No Kubernetes resources were applied."
