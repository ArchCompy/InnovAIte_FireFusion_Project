# ADR-005: Observability, Monitoring, Logging and Alerting Platform

## Status

Accepted

## Date

September 2026

## Context

FireFusion operates as a distributed backend composed of multiple services. Operating these services in Kubernetes requires visibility into application availability, HTTP behaviour, latency, errors, logs, and abnormal runtime conditions.

The observability solution should also remain portable across AKS, EKS, and GKE rather than making the application dependent on a single provider-specific monitoring platform.

## Decision

FireFusion will use a Kubernetes-native observability stack consisting of:

- Prometheus for metrics collection and alert-rule evaluation;
- Grafana for dashboards and operational visualisation;
- Loki for centralised log aggregation; and
- Grafana Alloy for Kubernetes log collection and forwarding.

The three FastAPI backend services expose Prometheus-compatible `/metrics` endpoints.

The high-level architecture is:

```text
FireFusion API --------+
Model API -------------+----> Prometheus ----> Alert Rules
Aggregator API --------+          |
                                  v
                               Grafana

Backend Pod Logs
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

## Application Metrics

Prometheus-compatible application metrics are exposed from:

- FireFusion API;
- Model API; and
- Aggregator API.

The FastAPI services use `prometheus-fastapi-instrumentator` to expose metrics through `/metrics`.

The metrics endpoint is excluded from its own instrumentation to prevent Prometheus scrape traffic from creating unnecessary monitoring noise.

## Prometheus

Prometheus performs Kubernetes service discovery and identifies the FireFusion backend services.

The configuration targets:

- `firefusion-api`;
- `model-api`; and
- `aggregator-api`.

Metrics are collected from `/metrics`.

Prometheus is configured using declarative Kubernetes manifests maintained in the repository.

## Grafana

Grafana provides the visualisation layer.

Datasource provisioning is maintained as code rather than requiring manual dashboard configuration.

The observability configuration provides Prometheus and Loki as Grafana datasources.

FireFusion dashboard configuration is also version-controlled so that dashboards can be reproduced consistently in a Kubernetes environment.

## Centralised Logging

Backend applications continue to emit logs through standard container stdout and stderr streams.

Grafana Alloy performs Kubernetes workload discovery and forwards selected FireFusion logs to Loki.

Loki provides centralised storage and querying of those logs.

Grafana then provides a common interface for both metrics and logs.

This design avoids requiring application containers to directly integrate with a provider-specific logging API.

## Alerting

Prometheus evaluates FireFusion-specific alert rules.

The initial alert policy contains four backend operational rules covering conditions such as:

- backend service unavailability;
- absence of expected backend targets;
- elevated HTTP server error behaviour; and
- elevated request latency.

Alert definitions are stored in Git alongside the observability infrastructure.

This ensures that monitoring policy changes are version-controlled and reviewable.

## Network Security

The FireFusion Kubernetes environment uses default-deny network controls.

A dedicated NetworkPolicy permits Prometheus in the monitoring namespace to reach the backend workloads on the metrics/application port.

The policy is scoped to the three FireFusion backend services rather than opening unrestricted ingress.

This preserves the default-deny security model while enabling required monitoring traffic.

## Workload Security

Observability workloads apply Kubernetes security controls including:

- non-root execution;
- prevention of privilege escalation;
- read-only root filesystems where applicable;
- dropped Linux capabilities; and
- RuntimeDefault seccomp configuration.

The implementation avoids privileged containers and hostPath-based node log collection.

Prometheus RBAC is limited to the permissions required for Kubernetes discovery.

## Cloud Portability

The observability baseline runs at the Kubernetes layer and is therefore reusable across:

- AKS;
- EKS; and
- GKE.

This does not prevent a future production environment from integrating provider-native monitoring services.

However, the Kubernetes-native baseline ensures that FireFusion retains a consistent operational capability if the selected cloud provider changes.

## Validation

The project includes automated observability validation.

The validation process checks:

1. complete observability-stack rendering;
2. Prometheus, Grafana, Loki, and Alloy workloads;
3. FireFusion Prometheus metrics collection configuration;
4. Prometheus and Loki Grafana datasources;
5. Alloy-to-Loki centralised logging;
6. FireFusion alert rules; and
7. observability workload security controls.

This validation can run before access to a live cloud Kubernetes cluster.

## DevSecOps Integration

Observability infrastructure is included in the wider infrastructure security process.

The implementation has been evaluated through the project's DevSecOps Security Validation workflow, including Trivy infrastructure configuration scanning.

Security findings identified during implementation are treated as configuration defects and remediated before the observability configuration is considered acceptable.

## Storage Considerations

The current observability implementation provides the project baseline required for development and controlled cloud validation.

For a longer-lived production deployment, metrics and log retention should use appropriately secured persistent storage or cloud object storage.

Retention periods, backup requirements, storage encryption, and cost controls should be determined from production operational requirements.

## Alternatives Considered

### Provider-Native Monitoring Only

Using Azure Monitor, Amazon CloudWatch, or Google Cloud Operations exclusively would provide deep provider integration but would increase coupling between application operations and the selected cloud.

### Application-Specific Logging Integration

Sending logs directly from application code to a remote logging provider would introduce logging-platform dependencies into each service.

Using standard container logs keeps the application layer simpler.

### No Centralised Observability

Relying only on individual container logs and Kubernetes status would not provide sufficient visibility for operating a distributed backend.

## Consequences

### Positive

- Common observability baseline across cloud providers.
- Centralised metrics and logs.
- Declarative dashboards and datasources.
- Version-controlled alerting.
- Reduced provider coupling.
- Integration with Kubernetes security controls.
- Repeatable validation before deployment.

### Trade-offs

- Additional platform components must be operated.
- Prometheus and Loki require storage planning for longer retention.
- Monitoring components consume cluster resources.
- Alert thresholds require tuning using real runtime behaviour.
- Production-scale high availability would require additional configuration.

## Implementation Evidence

Relevant repository paths include:

- `infrastructure/observability/prometheus/`
- `infrastructure/observability/grafana/`
- `infrastructure/observability/loki/`
- `infrastructure/observability/alloy/`
- `infrastructure/observability/alerts/`
- `infrastructure/scripts/observability-validate.sh`
- `infrastructure/kubernetes/base/network-policies/allow-prometheus.yaml`

Application instrumentation is implemented in the three backend FastAPI services.

The complete observability stack passes local Kustomize and automated observability validation.

The associated infrastructure changes also pass the DevSecOps Security Validation workflow.

Live Prometheus targets, Grafana dashboards, Loki logs, and alert-state evidence will be validated after deployment to the approved Kubernetes environment.

## Decision Review

Review this ADR if:

- FireFusion adopts a provider-native observability platform as the primary standard;
- monitoring volume requires a managed or highly available architecture;
- retention requirements change significantly; or
- application telemetry moves toward a broader OpenTelemetry architecture.