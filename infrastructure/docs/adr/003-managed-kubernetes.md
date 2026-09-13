# ADR-003: Managed Kubernetes as the Backend Runtime

## Status

Accepted

## Date

September 2026

## Context

FireFusion consists of independently deployable backend services including:

- FireFusion API;
- Model API; and
- Aggregator API.

The services require a shared runtime capable of providing health management, service discovery, configuration management, workload isolation, security controls, controlled deployment, and observability.

Docker Compose already supports local development and integration testing. However, a shared cloud environment requires additional orchestration, security, deployment, and operational capabilities.

The project also requires a runtime model that can remain consistent across the supported cloud providers.

## Decision

FireFusion will use managed Kubernetes as the shared cloud runtime for the backend services.

The corresponding managed Kubernetes services are:

- Azure Kubernetes Service (AKS);
- Amazon Elastic Kubernetes Service (EKS); and
- Google Kubernetes Engine (GKE).

Reusable Kubernetes base manifests define the common FireFusion backend workload configuration.

Kustomize overlays provide provider-specific deployment metadata while avoiding duplication of the common application configuration.

The available university cloud environment will determine which provider-specific overlay becomes the active deployment target.

## Rationale

Kubernetes provides a consistent application runtime across the supported cloud providers.

The platform supports:

- declarative application deployments;
- service discovery;
- liveness probes;
- readiness probes;
- CPU and memory requests and limits;
- workload self-healing;
- controlled rolling updates;
- Kubernetes NetworkPolicy;
- RBAC;
- workload identity integration;
- configuration and Secret references;
- GitOps continuous delivery; and
- common monitoring and logging patterns.

Using managed Kubernetes also removes the requirement for the FireFusion team to operate the Kubernetes control plane itself.

## Local Development and Cloud Runtime

Docker Compose remains appropriate for local development and integration testing.

The intended delivery progression is:

```text
Developer Workstation
        |
        v
Docker Compose
        |
        v
CI and Security Validation
        |
        v
Container Registry
        |
        v
Managed Kubernetes
        |
        v
GitOps + Observability
```

Docker Compose and Kubernetes therefore serve different purposes rather than replacing one another.

Docker Compose provides a lightweight local development environment, while Kubernetes provides the target cloud orchestration and operational platform.

## Kubernetes Architecture

The FireFusion Kubernetes base contains:

- a dedicated FireFusion namespace;
- Deployments for all three backend services;
- ClusterIP Services;
- ConfigMap-based non-sensitive configuration;
- Secret references for sensitive configuration;
- liveness probes using `/health`;
- readiness probes using `/ready`;
- CPU and memory resource requests and limits;
- ServiceAccount configuration;
- least-privilege RBAC;
- pod and container security contexts; and
- NetworkPolicies.

The three backend applications expose health and readiness endpoints to support Kubernetes workload lifecycle management.

The services also expose Prometheus-compatible `/metrics` endpoints for the observability platform.

## Security Model

The Kubernetes workload configuration applies security controls including:

- non-root execution;
- prevention of privilege escalation;
- dropped Linux capabilities;
- read-only root filesystems;
- RuntimeDefault seccomp profiles;
- scoped ServiceAccounts;
- least-privilege RBAC; and
- default-deny network controls.

Additional NetworkPolicies explicitly allow required traffic, including controlled Prometheus metrics collection.

Sensitive runtime values are not stored directly in ConfigMaps or committed Kubernetes manifests.

Provider-specific workload identity and managed secret integrations can be activated once the final cloud environment is available.

## Provider Portability

The common Kubernetes base is reused by the following overlays:

```text
infrastructure/kubernetes/overlays/
├── azure/
├── aws/
└── gcp/
```

This provides a common workload architecture while allowing provider-specific configuration to be introduced without duplicating the complete application manifests.

The three overlays represent alternative targets, not three simultaneous production clusters.

## Alternatives Considered

### Virtual Machines

Virtual machines provide greater host-level control but would require additional manual management for:

- application deployment;
- scaling;
- service discovery;
- workload recovery;
- network isolation; and
- operational consistency.

### Docker Compose in the Cloud

Docker Compose remains useful for development but does not provide the orchestration, RBAC, NetworkPolicy, GitOps, and self-healing capabilities required by the target shared cloud environment.

### Provider-Specific Container Platforms

Provider-specific container services could reduce initial platform complexity but would increase provider coupling and weaken the common multi-cloud runtime architecture.

## Consequences

### Positive

- Common deployment model across cloud providers.
- Better workload isolation.
- Declarative configuration.
- Automated health management.
- Integration with Argo CD.
- Integration with Prometheus, Grafana, Loki, and Alloy.
- Consistent security controls.
- Easier migration between supported managed Kubernetes platforms.

### Trade-offs

- Kubernetes introduces operational complexity.
- Engineers require Kubernetes expertise.
- Provider-specific networking and identity configuration remain necessary.
- Persistent storage and managed service integrations remain provider-aware.
- Cluster-level platform components must also be secured and maintained.

## Implementation Evidence

Relevant repository paths include:

- `infrastructure/kubernetes/base/`
- `infrastructure/kubernetes/base/network-policies/`
- `infrastructure/kubernetes/overlays/azure/`
- `infrastructure/kubernetes/overlays/aws/`
- `infrastructure/kubernetes/overlays/gcp/`
- `infrastructure/scripts/validate.sh`
- `infrastructure/scripts/render-deployment.sh`
- `infrastructure/scripts/deploy.sh`
- `infrastructure/scripts/smoke-test.sh`

The Kubernetes deployment architecture has been rendered and validated across Azure, AWS, and GCP overlays.

The validation process checks core resources, probes, security controls, RBAC, NetworkPolicies, provider metadata, and container image references.

Live rollout and integration testing will be completed when the approved university Kubernetes environment becomes available.

## Decision Review

This decision should be reviewed if:

- Kubernetes operational overhead becomes disproportionate to project requirements;
- the backend moves to a serverless architecture;
- the university mandates a different application runtime; or
- application characteristics no longer justify container orchestration.