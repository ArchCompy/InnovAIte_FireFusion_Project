#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

SUBSCRIPTION_ID="cfd11b14-72e9-4d19-8357-b7648abd8ac6"
TF_DIR="$ROOT_DIR/infrastructure/terraform/environments/dev/azure"

echo "=========================================="
echo " FireFusion Azure Demo - Destroy"
echo "=========================================="

az account set --subscription "$SUBSCRIPTION_ID"

cd "$TF_DIR"

echo ""
echo "Terraform directory:"
pwd

echo ""
echo "Terraform resources:"
terraform state list

echo ""
echo "Destroying FireFusion Azure environment..."

terraform destroy -auto-approve

echo ""
echo "Remaining FireFusion resource groups:"

az group list \
  --query "[?contains(name, 'firefusion')].[name,location]" \
  -o table

echo ""
echo "Destroy completed."