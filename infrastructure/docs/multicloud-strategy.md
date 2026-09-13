# FireFusion Multi-Cloud Strategy

## 1. Purpose

The FireFusion multi-cloud strategy defines how the backend remains portable across Google Cloud Platform, Microsoft Azure, and Amazon Web Services without requiring simultaneous production deployment across all three providers.

The objective is portability, not active-active multi-cloud operation.

---

## 2. Supported Cloud Platforms

FireFusion currently maintains infrastructure foundations for:

| Provider | Managed Kubernetes |
|---|---|
| Google Cloud Platform | GKE |
| Microsoft Azure | AKS |
| Amazon Web Services | EKS |

Terraform defines provider-specific infrastructure.

Kubernetes provides the common application runtime.

---

## 3. Current Preferred Deployment Target

GCP is the current preferred initial target because university stakeholders have indicated support for proceeding with Google Cloud Platform.

Actual deployment remains subject to the university cloud-service approval process.

This does not make the backend permanently dependent on GCP.

---

## 4. Portability Model

FireFusion separates the platform into two layers.

### Provider-Specific Infrastructure Layer

Includes:

- virtual networking;
- managed Kubernetes;
- cloud IAM;
- managed secret services;
- private/public control-plane configuration;
- provider-specific resource configuration.

### Portable Application Platform Layer

Includes:

- Kubernetes Deployments;
- Kubernetes Services;
- ConfigMaps;
- Secret references;
- probes;
- RBAC;
- NetworkPolicies;
- Argo CD;
- Prometheus;
- Grafana;
- Loki;
- Grafana Alloy.

This separation reduces the amount of application configuration that changes between cloud providers.

---

## 5. Architecture

```text
                   FireFusion Source Code
                           |
                           v
                    Container Images
                           |
                           v
                  Kubernetes Base Layer
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
         GCP Overlay   Azure Overlay   AWS Overlay
             |             |             |
             v             v             v
            GKE           AKS           EKS
```

Only one provider is expected to act as the active project deployment environment unless future requirements change.

---

## 6. Terraform Strategy

Terraform configuration is separated into provider environments:

```text
infrastructure/terraform/environments/dev/
├── gcp/
├── azure/
└── aws/
```

Reusable provider modules are stored under:

```text
infrastructure/terraform/modules/
├── gcp/
├── azure/
└── aws/
```

This keeps cloud-specific infrastructure explicit rather than hiding significant provider differences behind excessive abstraction.

---

## 7. Kubernetes Strategy

Common Kubernetes resources are stored under:

```text
infrastructure/kubernetes/base/
```

Provider overlays are stored under:

```text
infrastructure/kubernetes/overlays/
├── gcp/
├── azure/
└── aws/
```

The base is reused across all providers.

This ensures that application behaviour remains consistent even when infrastructure implementation changes.

---

## 8. Container Registry Strategy

The current architecture uses a common Docker-compatible registry path for portable application images.

Using the same image artifact across cloud targets avoids rebuilding provider-specific versions of the application.

A future deployment may adopt:

- Google Artifact Registry;
- Azure Container Registry;
- Amazon ECR;

if operational or governance requirements justify provider-native registries.

The application architecture does not depend on a specific registry technology.

---

## 9. Identity Strategy

CI/CD uses short-lived identity federation.

Provider mappings are:

| Provider | CI/CD Identity |
|---|---|
| GCP | Workload Identity Federation |
| Azure | Microsoft Entra federation |
| AWS | IAM OIDC federation |

The goal is to avoid long-lived cloud credentials in GitHub.

---

## 10. Workload Identity Strategy

Provider-specific workload identity mechanisms can connect Kubernetes ServiceAccounts with cloud IAM.

Mapping:

| Provider | Kubernetes Workload Identity |
|---|---|
| GCP | GKE Workload Identity |
| Azure | AKS Workload Identity |
| AWS | EKS IAM workload identity mechanism |

These integrations remain provider-specific while application workloads use a common Kubernetes ServiceAccount model.

---

## 11. Secrets Strategy

Provider mappings include:

| Provider | Managed Secret Service |
|---|---|
| GCP | Google Secret Manager |
| Azure | Azure Key Vault |
| AWS | AWS Secrets Manager |

FireFusion Kubernetes workloads reference secrets through a provider-neutral application interface where possible.

Real secret values are not committed to Git.

---

## 12. GitOps Strategy

Argo CD Applications exist for:

```text
GCP
Azure
AWS
```

These are alternative desired-state targets.

The project does not intend to synchronize the production application to all three providers simultaneously.

The active Argo CD Application should correspond to the approved cloud platform.

---

## 13. Observability Strategy

The Kubernetes-level observability stack is intentionally cloud-neutral:

```text
Prometheus
Grafana
Loki
Grafana Alloy
```

This provides a common baseline regardless of cloud provider.

Provider-native observability services may later complement the common monitoring platform.

---

## 14. Security Strategy

A common minimum security baseline applies across providers:

- non-root containers;
- read-only root filesystems;
- dropped Linux capabilities;
- no privilege escalation;
- Kubernetes RBAC;
- NetworkPolicies;
- short-lived cloud identity;
- managed secret integration;
- automated infrastructure security scanning.

Provider-specific security controls are added where required.

---

## 15. Provider Differences

Multi-cloud portability does not imply that all cloud resources are identical.

Differences include:

- IAM models;
- networking;
- load balancers;
- private cluster configuration;
- storage;
- secret-management integration;
- managed database products;
- monitoring integrations;
- pricing.

These differences remain explicit in provider-specific Terraform and identity configuration.

---

## 16. Why Not Active-Active Multi-Cloud

Running FireFusion simultaneously across GCP, Azure, and AWS would require additional solutions for:

- cross-cloud networking;
- global traffic routing;
- database replication;
- consistency;
- distributed secrets;
- multi-cluster observability;
- incident response;
- cost management.

This complexity is not justified by the current project requirements.

---

## 17. Migration Between Providers

A future migration follows:

```text
Validate Target Terraform
        |
        v
Provision Target Kubernetes
        |
        v
Configure Identity
        |
        v
Configure Secrets
        |
        v
Configure Dependencies
        |
        v
Deploy Existing Kubernetes Base
        |
        v
Apply Target Overlay
        |
        v
Run Smoke Tests
        |
        v
Enable GitOps
        |
        v
Enable Observability
        |
        v
Validate
        |
        v
Cut Over
```

Data migration and provider-managed services must be handled separately where required.

---

## 18. GCP-First Migration

The current proposed migration path is documented in:

```text
infrastructure/docs/gcp-deployment-migration-strategy.md
```

This covers:

- governance;
- Terraform provisioning;
- GKE deployment;
- identity;
- secrets;
- runtime dependencies;
- GitOps;
- observability;
- migration validation;
- rollback.

---

## 19. Multi-Cloud Validation

The project validates provider configurations before live deployment.

Current validation includes:

- Terraform validation;
- Kustomize rendering;
- Kubernetes architecture checks;
- security scanning;
- GitOps validation;
- observability validation.

This demonstrates portability at the infrastructure and application-platform layers without claiming three live production environments.

---

## 20. Current State

The Azure, AWS, and GCP infrastructure foundations have been implemented and validated.

The Kubernetes deployment architecture supports all three provider overlays.

No claim is made that FireFusion is currently operating production workloads across these providers.

GCP remains the proposed first live university cloud deployment target, subject to approval.

---

## 21. Related Decisions

See:

```text
infrastructure/docs/adr/002-multicloud-structure.md
infrastructure/docs/adr/003-managed-kubernetes.md
infrastructure/docs/adr/004-gitops-deployment.md
infrastructure/docs/adr/006-security-identity.md
```