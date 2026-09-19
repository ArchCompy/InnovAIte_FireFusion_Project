# FireFusion Cloud Identity Architecture

FireFusion uses short-lived federated identities instead of long-lived cloud credentials.

Two identity paths are kept separate:

1. GitHub Actions -> Cloud Provider
   Used for Terraform provisioning and deployment automation.

2. Kubernetes Workloads -> Cloud Provider
   Used by application workloads when access to managed cloud services is required.

## GitHub Actions Federation

| Cloud | Federation Mechanism |
|---|---|
| Azure | Microsoft Entra workload identity federation |
| AWS | IAM OIDC provider and IAM role |
| GCP | Workload Identity Federation |

## Kubernetes Workload Identity

| Cloud | Mechanism |
|---|---|
| Azure | AKS Workload Identity |
| AWS | EKS Pod Identity / IRSA |
| GCP | GKE Workload Identity |

No long-lived cloud access keys, service-account JSON keys, or client secrets
should be committed to the repository.

Actual cloud account, subscription, project, tenant, role, or service-account
identifiers are supplied only after the target university cloud environment has
been approved.
