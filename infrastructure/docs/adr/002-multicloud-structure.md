# ADR-002: Multi-Cloud Infrastructure Structure

## Status

Accepted

## Date

September 2026

## Context

FireFusion requires a cloud deployment architecture that can be developed and validated before final university-managed cloud access is confirmed.

The backend consists of multiple containerised services and should remain portable across major cloud providers without requiring a redesign of the application deployment model.

The project therefore requires a clear distinction between supporting multiple cloud deployment targets and operating production workloads simultaneously across multiple providers.

## Decision

FireFusion will maintain Infrastructure-as-Code foundations for Microsoft Azure, Amazon Web Services, and Google Cloud Platform.

The repository provides Terraform environments and reusable modules for:

- Azure Kubernetes Service (AKS)
- Amazon Elastic Kubernetes Service (EKS)
- Google Kubernetes Engine (GKE)

The three cloud implementations represent alternative deployment targets.

They do not represent an active-active production deployment across all three providers.

The current university-supported deployment direction is GCP, subject to completion and approval of the university cloud-service process.

## Rationale

Maintaining a common multi-cloud structure allows the team to:

- validate infrastructure patterns before final cloud access is available;
- reduce dependency on a single cloud provider;
- compare provider-specific networking, identity, and Kubernetes services;
- reuse the same Kubernetes workload architecture across cloud targets; and
- change the final hosting provider without redesigning the backend services.

Terraform provides a consistent Infrastructure-as-Code workflow while still allowing provider-specific resources to remain isolated within their respective modules.

The application deployment layer is further standardised through Kubernetes and Kustomize, allowing the majority of backend configuration to remain independent of the selected cloud provider.

## Repository Structure

The Terraform implementation is organised under:

```text
infrastructure/
└── terraform/
    ├── environments/
    │   └── dev/
    │       ├── azure/
    │       ├── aws/
    │       └── gcp/
    └── modules/
        ├── azure/
        ├── aws/
        └── gcp/
```

Kubernetes provider overlays are maintained separately under:

```text
infrastructure/kubernetes/overlays/
├── azure/
├── aws/
└── gcp/
```

This structure separates reusable application configuration from cloud-specific infrastructure and deployment configuration.

## Cloud Provider Mapping

| Capability | Azure | AWS | GCP |
|---|---|---|---|
| Managed Kubernetes | AKS | EKS | GKE |
| Infrastructure as Code | Terraform | Terraform | Terraform |
| Cloud Identity | Microsoft Entra ID / Workload Identity | IAM / EKS workload identity mechanisms | IAM / Workload Identity Federation |
| Managed Secrets | Azure Key Vault | AWS Secrets Manager | Google Secret Manager |
| Kubernetes Deployment | Kustomize | Kustomize | Kustomize |
| GitOps | Argo CD | Argo CD | Argo CD |
| Observability Baseline | Prometheus/Grafana/Loki/Alloy | Prometheus/Grafana/Loki/Alloy | Prometheus/Grafana/Loki/Alloy |

The common Kubernetes, GitOps, and observability layers reduce provider-specific differences at the application operations layer.

## Alternatives Considered

### Single-Cloud Infrastructure Only

A single-cloud implementation would be simpler to maintain. However, selecting one provider before university cloud access was confirmed would increase dependency on an early platform decision and reduce portability if the available cloud environment changed.

### Simultaneous Multi-Cloud Production

Running FireFusion production workloads simultaneously across Azure, AWS, and GCP was not selected.

This would introduce unnecessary complexity in:

- networking;
- identity management;
- data consistency;
- secrets management;
- observability;
- deployment coordination;
- cost management; and
- incident response.

The current requirement is portability between providers rather than active-active multi-cloud operation.

## Consequences

### Positive

- The final cloud provider can change without redesigning the backend.
- Terraform patterns are reusable.
- Kubernetes workload configuration remains largely common.
- Provider-specific differences remain clearly isolated.
- Infrastructure can be validated before final cloud access.
- The architecture supports future comparative cost and operational analysis.

### Trade-offs

- Additional Terraform modules must be maintained.
- Provider-specific IAM and networking knowledge is still required.
- Multi-cloud validation increases engineering effort.
- Cloud portability does not make all managed cloud services directly interchangeable.
- Operational procedures must identify which provider is the active deployment target.

## Implementation Evidence

Relevant repository paths include:

- `infrastructure/terraform/environments/dev/azure/`
- `infrastructure/terraform/environments/dev/aws/`
- `infrastructure/terraform/environments/dev/gcp/`
- `infrastructure/terraform/modules/azure/`
- `infrastructure/terraform/modules/aws/`
- `infrastructure/terraform/modules/gcp/`
- `infrastructure/kubernetes/overlays/azure/`
- `infrastructure/kubernetes/overlays/aws/`
- `infrastructure/kubernetes/overlays/gcp/`
- `infrastructure/identity/`
- `infrastructure/secrets/`

Terraform and Kubernetes configurations have been validated locally and through CI/security validation.

Actual runtime deployment remains dependent on approved university cloud access.

## Decision Review

This decision should be reviewed if:

- the university confirms a permanent single-cloud platform;
- FireFusion requires active-active multi-cloud operation;
- provider-specific managed services become mandatory; or
- maintaining multiple infrastructure implementations creates disproportionate operational overhead.