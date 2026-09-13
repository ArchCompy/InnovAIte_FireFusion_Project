# FireFusion Cloud-Native Backend Architecture

## 1. Overview

FireFusion is a cloud-native backend platform composed of three FastAPI services:

- FireFusion API
- Model API
- Aggregator API

The platform is designed to support local development using Docker Compose and controlled cloud deployment using managed Kubernetes.

The cloud architecture has been designed with portability across:

- Google Cloud Platform / GKE
- Microsoft Azure / AKS
- Amazon Web Services / EKS

The cloud providers represent alternative deployment targets rather than simultaneous production environments.

The current university-supported deployment direction is Google Cloud Platform, subject to completion of the required university cloud approval process.

---

## 2. Architecture Goals

The architecture is designed to provide:

- reproducible Infrastructure as Code;
- portable Kubernetes deployments;
- secure cloud authentication;
- controlled secrets management;
- GitOps continuous delivery;
- workload health management;
- centralized metrics and logging;
- operational alerting;
- automated security validation;
- deterministic deployment and rollback;
- separation between local development and cloud operations.

---

## 3. High-Level Architecture

```text
                         Developers
                             |
                             v
                         GitHub Repo
                             |
                             v
                  +----------------------+
                  |    GitHub Actions    |
                  |----------------------|
                  | Tests                |
                  | Security Validation  |
                  | Container Build      |
                  | Terraform Validation |
                  +----------+-----------+
                             |
                             v
                     Container Registry
                             |
                             |
                    Immutable Image Tag
                             |
                             v
                      Git Desired State
                             |
                             v
                         Argo CD
                             |
                             v
                 Managed Kubernetes Cluster
                     GKE / AKS / EKS
                             |
             +---------------+---------------+
             |               |               |
             v               v               v
      FireFusion API     Model API      Aggregator API
             |               |               |
             +---------------+---------------+
                             |
                    Runtime Dependencies
                             |
              +--------------+-------------+
              |              |             |
           Database        Redis       Message Broker


                    Observability Layer

      Backend /metrics ----------------> Prometheus
                                           |
                                           v
                                        Grafana

      Backend Container Logs ----------> Alloy
                                           |
                                           v
                                          Loki
                                           |
                                           v
                                        Grafana
```

---

## 4. Backend Services

### FireFusion API

The FireFusion API provides the primary backend API interface.

The service exposes:

```text
/health
/ready
/metrics
```

These endpoints support Kubernetes health management and Prometheus monitoring.

### Model API

The Model API provides the machine-learning model service layer.

It exposes the same operational interfaces:

```text
/health
/ready
/metrics
```

### Aggregator API

The Aggregator API supports aggregation and event-processing functionality.

It also exposes:

```text
/health
/ready
/metrics
```

All three services are independently deployable Kubernetes workloads.

---

## 5. Local Development Architecture

Docker Compose remains the local development and integration environment.

The local development flow is:

```text
Developer
   |
   v
Docker Compose
   |
   +--> FireFusion API
   |
   +--> Model API
   |
   +--> Aggregator API
   |
   +--> PostgreSQL / External Database Configuration
   |
   +--> Redis
   |
   +--> RabbitMQ
```

Docker Compose is not intended to replace Kubernetes in the shared cloud environment.

---

## 6. Infrastructure as Code

Terraform is used to define cloud infrastructure.

The repository contains provider-specific environments for:

```text
infrastructure/terraform/environments/dev/
├── azure/
├── aws/
└── gcp/
```

Reusable Terraform modules are maintained under:

```text
infrastructure/terraform/modules/
├── azure/
├── aws/
└── gcp/
```

The managed Kubernetes mapping is:

| Cloud | Kubernetes Platform |
|---|---|
| Google Cloud | GKE |
| Microsoft Azure | AKS |
| AWS | EKS |

Terraform configurations are validated before any approved runtime deployment.

---

## 7. Kubernetes Architecture

Common Kubernetes workload configuration is stored under:

```text
infrastructure/kubernetes/base/
```

The base contains:

- namespace;
- Deployments;
- Services;
- ConfigMap;
- Secret references;
- ServiceAccount;
- RBAC;
- NetworkPolicies;
- health probes;
- readiness probes;
- resource controls;
- workload security contexts.

Provider-specific Kustomize overlays are located under:

```text
infrastructure/kubernetes/overlays/
├── azure/
├── aws/
└── gcp/
```

This allows the application deployment architecture to remain common while cloud-specific configuration remains isolated.

---

## 8. Application Health Management

Each backend service provides:

```text
/health
```

for Kubernetes liveness checks.

Each backend service also provides:

```text
/ready
```

for Kubernetes readiness checks.

A workload must not be considered ready for traffic until its initialization is complete.

This allows Kubernetes to distinguish between:

- a running process; and
- an application that is actually ready to serve traffic.

---

## 9. Container Security

Backend containers are configured to operate as non-root users.

Kubernetes security controls include:

- `runAsNonRoot`;
- explicit user/group IDs;
- `allowPrivilegeEscalation: false`;
- `readOnlyRootFilesystem: true`;
- dropped Linux capabilities;
- RuntimeDefault seccomp profiles.

These controls reduce the privileges available to application workloads.

---

## 10. Kubernetes Access Control

The backend uses a dedicated Kubernetes ServiceAccount.

RBAC follows a least-privilege model.

The application workloads are not granted unnecessary Kubernetes API permissions.

This prevents backend containers from obtaining cluster privileges simply because they are running inside Kubernetes.

---

## 11. Network Security

The Kubernetes architecture uses a default-deny NetworkPolicy model.

Explicit policies permit required traffic including:

- DNS;
- backend service communication;
- Prometheus metrics collection.

Provider-specific egress rules for services such as:

- databases;
- Redis;
- RabbitMQ;
- managed cloud APIs;

will be added when the approved runtime endpoints and network design are available.

---

## 12. Identity Architecture

The intended CI/CD identity architecture is:

```text
GitHub Actions
      |
      | OIDC
      v
Cloud Identity Federation
      |
      v
Short-Lived Cloud Identity
```

Provider mappings include:

- Microsoft Entra federated identity for Azure;
- IAM OIDC federation for AWS;
- Workload Identity Federation for GCP.

Long-lived cloud credentials should not be committed to source control.

---

## 13. Workload Identity

The intended workload identity model is:

```text
Kubernetes ServiceAccount
        |
        v
Cloud Workload Identity
        |
        v
Approved Managed Cloud Services
```

Provider-specific implementations can be activated once the target cloud environment is available.

---

## 14. Secrets Architecture

Sensitive values are separated from non-sensitive configuration.

### Non-Sensitive

Stored using ConfigMaps where appropriate.

### Sensitive

Examples include:

- database credentials;
- broker credentials;
- Redis credentials;
- API keys;
- external service secrets.

Provider-managed secret systems include:

| Cloud | Secret Platform |
|---|---|
| Azure | Azure Key Vault |
| AWS | AWS Secrets Manager |
| GCP | Google Secret Manager |

Only example secret manifests and provider templates are stored in Git.

---

## 15. CI/CD Architecture

GitHub Actions provides:

- application validation;
- backend tests;
- container build workflows;
- Terraform validation;
- infrastructure security checks;
- credential checks;
- container security checks;
- Kubernetes security checks;
- controlled GitOps image promotion.

Application images are intended to be promoted using immutable image tags.

---

## 16. GitOps Architecture

Argo CD provides Kubernetes continuous delivery.

The intended delivery flow is:

```text
Code Change
    |
    v
CI
    |
    v
Container Image
    |
    v
Controlled Promotion
    |
    v
Git Desired State
    |
    v
Argo CD
    |
    v
Kubernetes
```

Routine deployments should not require direct `kubectl apply` from CI.

Provider-specific Argo CD Applications exist for:

- GCP;
- Azure;
- AWS.

Only the approved provider should become the active deployment target.

---

## 17. Observability Architecture

The FireFusion observability stack contains:

- Prometheus;
- Grafana;
- Loki;
- Grafana Alloy.

### Metrics

```text
FastAPI Services
      |
      | /metrics
      v
Prometheus
      |
      v
Grafana
```

### Logs

```text
Backend Pod stdout/stderr
          |
          v
     Grafana Alloy
          |
          v
         Loki
          |
          v
       Grafana
```

---

## 18. Alerting

The initial monitoring configuration includes alerts for:

- unavailable backend services;
- missing backend targets;
- elevated HTTP 5xx rates;
- elevated request latency.

Alert thresholds should be tuned using real runtime traffic after cloud deployment.

---

## 19. Deployment Validation

The repository includes reusable validation and deployment tooling:

```text
infrastructure/scripts/
├── validate.sh
├── render-deployment.sh
├── deploy.sh
├── smoke-test.sh
├── cluster-connect.sh
├── gitops-validate.sh
├── promote-image.sh
└── observability-validate.sh
```

These scripts provide repeatable validation rather than relying on undocumented manual deployment steps.

---

## 20. Security Validation

The GitHub Actions security workflow validates:

- exposed credentials;
- backend container security;
- Kubernetes security controls;
- Terraform and Kubernetes infrastructure configuration using Trivy.

Infrastructure findings discovered during development are remediated before the corresponding implementation is treated as complete.

---

## 21. Deployment State

The architecture, Terraform environments, Kubernetes configuration, security controls, GitOps definitions, and observability components have been implemented and validated without claiming a live production deployment.

Actual cloud deployment remains dependent on approved university cloud access.

The current proposed initial target is GCP/GKE.

---

## 22. Related Documentation

Detailed architecture decisions:

```text
infrastructure/docs/adr/
```

GCP deployment and migration:

```text
infrastructure/docs/gcp-deployment-migration-strategy.md
```

Rollback and recovery:

```text
infrastructure/docs/runbooks/rollback-recovery.md
```

GCP deployment checklist:

```text
infrastructure/docs/runbooks/gcp-deployment-checklist.md
```