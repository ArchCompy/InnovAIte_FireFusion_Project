# Azure Kubernetes Overlay

This overlay renders the portable FireFusion Kubernetes base for Azure/AKS.

The Azure Key Vault secret-provider template is stored under:

    secrets/

It is intentionally not included in the active overlay until:

- AKS is provisioned
- Azure Workload Identity is configured
- Key Vault is available
- Secrets Store CSI Driver and Azure provider are installed
- Real Azure identifiers are supplied

At deployment time, the Azure secret provider can be activated after replacing
template values with the approved environment configuration.
