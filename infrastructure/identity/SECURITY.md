# FireFusion Identity and Credential Security

## Required Controls

FireFusion cloud automation must use federated identity wherever supported.

The following credential types must not be committed to Git:

- AWS access keys
- Azure client secrets
- GCP service-account JSON keys
- Kubernetes bearer tokens
- Database passwords
- RabbitMQ passwords
- Redis credentials
- Application API keys

## GitHub Actions

GitHub Actions should authenticate to the selected cloud provider using GitHub's
OIDC identity token.

Required GitHub Actions permissions:

    permissions:
      contents: read
      id-token: write

The federated cloud identity should be restricted to the FireFusion repository
and approved branches or GitHub environments.

Long-lived cloud credentials should not be stored in GitHub repository secrets
when workload identity federation is available.

## Kubernetes Workloads

Application Pods should use cloud-native workload identity only when access to
managed cloud services is required.

The portable Kubernetes base intentionally grants no Kubernetes API permissions
to application workloads.

The current backend ServiceAccount therefore uses least-privilege RBAC and
disables unnecessary automatic Kubernetes API token mounting.

## Secret Management

Runtime secrets must be supplied through an approved secret-management
mechanism rather than committed Kubernetes manifests.

Provider-specific options include:

- Azure Key Vault
- AWS Secrets Manager
- Google Secret Manager

Database connection strings, messaging credentials, cache credentials and
application API keys must never be stored as plaintext values in Git.

## Multi-Cloud Security Model

The FireFusion architecture separates CI/CD identity from application workload
identity.

GitHub Actions:

    GitHub Actions
          |
          | OIDC Federation
          v
      Cloud IAM
          |
          +-- Terraform provisioning
          +-- Deployment automation

Kubernetes workloads:

    FireFusion Pod
          |
          | Workload Identity
          v
      Cloud IAM
          |
          +-- Secret Manager
          +-- Approved managed cloud services

This separation reduces credential exposure and supports portable deployment
across Azure, AWS and GCP.
