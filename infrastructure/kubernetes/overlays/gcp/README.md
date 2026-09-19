# GCP Kubernetes Overlay

This overlay renders the portable FireFusion Kubernetes base for GCP/GKE.

The Google Secret Manager secret-provider template is stored under:

    secrets/

It is intentionally not included in the active overlay until:

- GKE is provisioned
- GKE Workload Identity is configured
- Google Secret Manager secrets exist
- Secrets Store CSI Driver and GCP provider are installed
- Real GCP identifiers are supplied

At deployment time, the GCP secret provider can be activated after replacing
template values with the approved environment configuration.
