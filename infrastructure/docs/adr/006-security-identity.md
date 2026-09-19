# ADR-006: Cloud Security, Identity and Secrets Management

## Status

Accepted

## Date

September 2026

## Context

FireFusion requires secure access between CI/CD, cloud infrastructure, Kubernetes workloads, and external services.

A multi-cloud architecture introduces different identity and secret-management mechanisms across Azure, AWS, and GCP.

The project requires a security architecture that avoids committing credentials to source control, reduces the use of long-lived credentials, applies least privilege, and remains adaptable to the final approved cloud provider.

## Decision

FireFusion will use a layered cloud-native security model based on:

- short-lived federated cloud identity;
- Kubernetes workload identity;
- managed cloud secret stores;
- least-privilege Kubernetes RBAC;
- Kubernetes NetworkPolicy;
- hardened container security contexts;
- separation of sensitive and non-sensitive configuration; and
- automated DevSecOps validation.

No long-lived cloud credentials should be stored in the repository.

## CI/CD Cloud Identity

GitHub Actions should authenticate to the selected cloud provider using OpenID Connect federation rather than stored long-lived cloud access keys.

The conceptual flow is:

```text
GitHub Actions
      |
      | OIDC token
      v
Cloud Identity Federation
      |
      v
Short-Lived Cloud Identity
      |
      v
Approved Cloud Resources
```

Provider mappings are:

| Provider | CI/CD Identity Approach |
|---|---|
| Azure | Microsoft Entra federated identity |
| AWS | IAM OIDC federation |
| GCP | Workload Identity Federation |

This reduces the requirement to maintain reusable cloud credentials as GitHub secrets.

## Kubernetes Workload Identity

Backend workloads should use workload identity when accessing supported cloud services.

The intended provider mappings are:

| Provider | Workload Identity |
|---|---|
| Azure / AKS | AKS Workload Identity |
| AWS / EKS | EKS workload identity / IAM role integration |
| GCP / GKE | GKE Workload Identity |

The base Kubernetes architecture provides a dedicated backend ServiceAccount.

Provider-specific identity configuration can be activated through the selected cloud overlay when the final cloud environment and IAM resources are available.

## Secrets Management

Sensitive values must not be stored directly in ConfigMaps or committed deployment manifests.

Non-sensitive configuration is maintained using Kubernetes ConfigMaps.

Sensitive configuration is referenced through Kubernetes Secrets and provider-specific managed secret services.

Provider mappings are:

| Provider | Managed Secret Service |
|---|---|
| Azure | Azure Key Vault |
| AWS | AWS Secrets Manager |
| GCP | Google Secret Manager |

The repository contains example secret-provider configuration without storing real secret values.

Actual provider secret synchronization will be activated after the approved cloud environment is available.

## Kubernetes RBAC

FireFusion uses a dedicated Kubernetes ServiceAccount for backend workloads.

RBAC follows a least-privilege approach.

The backend Role intentionally provides no unnecessary Kubernetes API permissions.

A RoleBinding scopes the workload identity to the FireFusion namespace.

This prevents application workloads from receiving broad Kubernetes permissions by default.

## Network Security

The Kubernetes architecture applies default-deny NetworkPolicies.

Explicit policies permit only required traffic patterns such as:

- Kubernetes DNS;
- communication between approved FireFusion backend services; and
- Prometheus metrics collection.

Provider/environment-specific egress access to managed dependencies such as databases, Redis, RabbitMQ, or other external services must be added only when the approved endpoints and network design are known.

This avoids creating broad unrestricted egress rules before the deployment environment is confirmed.

## Container Security

Backend and platform workloads use hardened security settings where applicable.

Controls include:

- non-root execution;
- explicit runtime user/group identities;
- `allowPrivilegeEscalation: false`;
- read-only root filesystems;
- dropped Linux capabilities; and
- RuntimeDefault seccomp profiles.

Backend container images use a non-root application user.

These controls reduce the privileges available if an application or container is compromised.

## Configuration Separation

FireFusion separates configuration into two categories.

### Non-Sensitive Configuration

Stored in ConfigMaps where appropriate.

Examples include runtime behaviour that does not contain credentials or secret values.

### Sensitive Configuration

Stored outside source-controlled ConfigMaps.

Examples include:

- database connection information;
- broker credentials;
- API keys;
- cache credentials; and
- other service authentication material.

Example Secret manifests contain placeholders only and must never contain production values.

## DevSecOps Validation

Security controls are validated continuously through GitHub Actions.

The DevSecOps Security Validation pipeline includes:

- secret and credential validation;
- backend container security validation;
- Kubernetes security validation; and
- Trivy infrastructure configuration scanning.

Infrastructure security findings are treated as build failures where they violate the configured severity policy.

During implementation, security scanning identified configuration issues that were remediated before the security pipeline was returned to a successful state.

This demonstrates a shift-left security model rather than relying only on post-deployment review.

## Multi-Cloud Infrastructure Security

Provider-specific infrastructure applies additional controls.

Examples include:

- private Kubernetes API access where configured;
- explicit cluster RBAC;
- restricted management-network access;
- encrypted Kubernetes secret storage where supported;
- private worker networking; and
- provider-native IAM.

Exact runtime controls remain subject to the networking and access model approved for the university cloud environment.

## Authentication Boundary

Infrastructure identity and application-user authentication are separate concerns.

This ADR defines infrastructure, workload, and CI/CD identity.

Application authentication should use the authentication mechanism approved for the final FireFusion environment.

No existing Auth0 deployment is assumed by this architecture.

If Azure is selected, Microsoft Entra-based application authentication may be evaluated. Equivalent approaches may be considered for the approved platform.

## Alternatives Considered

### Long-Lived Cloud Credentials in GitHub Secrets

This approach is easier to configure initially but increases credential lifecycle and compromise risk.

OIDC federation is preferred because it supports short-lived cloud authentication.

### Kubernetes Secrets as the Final Secret Store

Kubernetes Secrets are required as a runtime interface for some workloads, but relying on them as the only secret-management system would not provide the lifecycle and provider integration available from managed secret services.

### Broad Kubernetes Permissions

Granting workloads broad Kubernetes API permissions would simplify some operational tasks but violates least-privilege principles.

Application workloads should receive only the permissions they actually require.

### Unrestricted Network Access

Allowing unrestricted ingress and egress would simplify initial deployment but weaken workload isolation.

The selected architecture starts from default-deny and adds required traffic explicitly.

## Consequences

### Positive

- Reduced reliance on long-lived credentials.
- Clear separation of sensitive configuration.
- Least-privilege Kubernetes access.
- Stronger workload isolation.
- Security controls are version-controlled.
- Automated scanning detects infrastructure regressions.
- Security model maps across Azure, AWS, and GCP.

### Trade-offs

- Workload identity configuration is provider-specific.
- Managed secret integration requires additional platform setup.
- Default-deny networking requires explicit dependency rules.
- Private cluster networking affects CI/CD connectivity.
- Security configuration requires continued validation as the runtime environment evolves.

## Implementation Evidence

Relevant repository areas include:

- `infrastructure/identity/`
- `infrastructure/secrets/`
- `infrastructure/kubernetes/base/serviceaccount.yaml`
- `infrastructure/kubernetes/base/rbac.yaml`
- `infrastructure/kubernetes/base/network-policies/`
- `infrastructure/kubernetes/base/secret.example.yaml`
- `.github/workflows/security-ci.yml`
- `.github/workflows/oidc-azure.yml`
- `.github/workflows/oidc-aws.yml`
- `.github/workflows/oidc-gcp.yml`

The project has successfully executed its DevSecOps Security Validation workflow after remediation of identified infrastructure findings.

Provider-specific workload identity and managed secret integrations remain intentionally inactive until the approved cloud provider and runtime environment are available.

## Decision Review

Review this ADR when:

- the final university cloud provider is confirmed;
- workload identity is activated in the live cluster;
- the application authentication architecture is finalised;
- production secrets and rotation requirements are defined; or
- the threat model identifies additional controls.