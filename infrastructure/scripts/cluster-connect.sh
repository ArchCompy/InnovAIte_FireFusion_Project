#!/usr/bin/env bash

set -euo pipefail

PROVIDER="${1:-}"

if [[ -z "${PROVIDER}" ]]; then
  echo "Usage:"
  echo "  $0 <azure|aws|gcp>"
  echo
  echo "Required environment variables:"
  echo
  echo "Azure:"
  echo "  AZURE_RESOURCE_GROUP"
  echo "  AZURE_CLUSTER_NAME"
  echo
  echo "AWS:"
  echo "  AWS_REGION"
  echo "  AWS_CLUSTER_NAME"
  echo
  echo "GCP:"
  echo "  GCP_PROJECT_ID"
  echo "  GCP_REGION"
  echo "  GCP_CLUSTER_NAME"
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

echo "============================================================"
echo " FireFusion Kubernetes Cluster Connection"
echo "============================================================"
echo "Provider: ${PROVIDER}"
echo

case "${PROVIDER}" in

  azure)
    : "${AZURE_RESOURCE_GROUP:?AZURE_RESOURCE_GROUP is required}"
    : "${AZURE_CLUSTER_NAME:?AZURE_CLUSTER_NAME is required}"

    if ! command -v az >/dev/null 2>&1; then
      echo "ERROR: Azure CLI (az) is not installed."
      exit 1
    fi

    echo "Connecting to AKS..."
    echo "Resource group: ${AZURE_RESOURCE_GROUP}"
    echo "Cluster       : ${AZURE_CLUSTER_NAME}"
    echo

    az aks get-credentials \
      --resource-group "${AZURE_RESOURCE_GROUP}" \
      --name "${AZURE_CLUSTER_NAME}" \
      --overwrite-existing
    ;;

  aws)
    : "${AWS_REGION:?AWS_REGION is required}"
    : "${AWS_CLUSTER_NAME:?AWS_CLUSTER_NAME is required}"

    if ! command -v aws >/dev/null 2>&1; then
      echo "ERROR: AWS CLI is not installed."
      exit 1
    fi

    echo "Connecting to EKS..."
    echo "Region : ${AWS_REGION}"
    echo "Cluster: ${AWS_CLUSTER_NAME}"
    echo

    aws eks update-kubeconfig \
      --region "${AWS_REGION}" \
      --name "${AWS_CLUSTER_NAME}"
    ;;

  gcp)
    : "${GCP_PROJECT_ID:?GCP_PROJECT_ID is required}"
    : "${GCP_REGION:?GCP_REGION is required}"
    : "${GCP_CLUSTER_NAME:?GCP_CLUSTER_NAME is required}"

    if ! command -v gcloud >/dev/null 2>&1; then
      echo "ERROR: Google Cloud CLI (gcloud) is not installed."
      exit 1
    fi

    echo "Connecting to GKE..."
    echo "Project : ${GCP_PROJECT_ID}"
    echo "Region  : ${GCP_REGION}"
    echo "Cluster : ${GCP_CLUSTER_NAME}"
    echo

    gcloud container clusters get-credentials \
      "${GCP_CLUSTER_NAME}" \
      --region "${GCP_REGION}" \
      --project "${GCP_PROJECT_ID}"
    ;;
esac

echo
echo "Verifying Kubernetes context..."

CURRENT_CONTEXT="$(kubectl config current-context)"

echo "Current context: ${CURRENT_CONTEXT}"
echo

if kubectl cluster-info >/dev/null 2>&1; then
  echo "PASS: Kubernetes API is reachable."
else
  echo "ERROR: kubeconfig was updated, but the Kubernetes API is not reachable."
  exit 1
fi

echo
echo "Cluster nodes:"
kubectl get nodes -o wide

echo
echo "============================================================"
echo " CLUSTER CONNECTION SUCCESSFUL"
echo "============================================================"
echo "Provider: ${PROVIDER}"
echo "Context : ${CURRENT_CONTEXT}"
