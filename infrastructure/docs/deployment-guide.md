# FireFusion Deployment Guide

## 1. Purpose

This guide describes the supported deployment workflow for the FireFusion backend.

It covers validation and deployment preparation for Azure, AWS, and GCP Kubernetes targets.

The current proposed university deployment target is GCP, subject to approved university cloud access.

---

## 2. Deployment Stages

The FireFusion delivery process is:

```text
Application Change
      |
      v
CI Testing
      |
      v
Security Validation
      |
      v
Container Build
      |
      v
Registry
      |
      v
Kubernetes Validation
      |
      v
Controlled Deployment
      |
      v
Smoke Testing
      |
      v
GitOps
      |
      v
Observability Validation
```

---

## 3. Supported Providers

Supported Kubernetes deployment targets are:

```text
azure
aws
gcp
```

These represent deployment alternatives rather than simultaneous production environments.

---

## 4. Prerequisites

Before a live cloud deployment, ensure:

- cloud access is approved;
- Terraform CLI is installed;
- `kubectl` is installed;
- provider CLI is installed;
- Docker registry access is available;
- required cloud permissions exist;
- runtime dependencies are configured;
- secrets are available through an approved mechanism.

Provider CLIs include:

```text
Azure -> az
AWS   -> aws
GCP   -> gcloud
```

---

## 5. Validate Terraform

Navigate to the required provider environment.

Example for GCP:

```bash
cd infrastructure/terraform/environments/dev/gcp
```

Run:

```bash
terraform fmt -check
terraform init
terraform validate
terraform plan
```

Review the plan before any apply.

---

## 6. Connect to the Cluster

The repository provides:

```bash
./infrastructure/scripts/cluster-connect.sh
```

Provider-specific cloud values must be configured before using the script.

After connection:

```bash
kubectl config current-context
kubectl cluster-info
kubectl get nodes
```

Verify the current context carefully before performing any live deployment.

---

## 7. Validate Kubernetes Configuration

From the repository root:

```bash
./infrastructure/scripts/validate.sh gcp
```

Replace `gcp` with:

```text
azure
aws
```

when validating another provider.

The validation checks include:

- Deployments;
- Services;
- namespace;
- health probes;
- readiness probes;
- security controls;
- RBAC;
- NetworkPolicies;
- provider labels;
- container image references.

---

## 8. Select an Immutable Image

Use only a container image tag that has actually been published by CI.

Example:

```text
docker.io/<registry-user>/firefusion-api:<sha>
docker.io/<registry-user>/model-api:<sha>
docker.io/<registry-user>/aggregator-api:<sha>
```

Do not assume that every Git commit has a corresponding container image.

For controlled deployment, prefer immutable SHA-based tags instead of `latest`.

---

## 9. Render Deployment

Set the registry username:

```bash
export DOCKERHUB_USERNAME="<registry-user>"
```

Then:

```bash
./infrastructure/scripts/render-deployment.sh \
  gcp \
  <image-tag>
```

The rendered output is stored outside the Git-tracked desired-state configuration.

Review the manifest before applying it.

---

## 10. Confirm Required Secrets

Before deploying backend workloads, confirm required Secret references are available.

Required configuration may include:

- broker URL;
- cache URL;
- database URL;
- relational database URL;
- API keys.

Never commit production secrets to the repository.

---

## 11. Confirm External Connectivity

The Kubernetes environment uses default-deny networking.

Before cloud deployment, define required connectivity to:

- database services;
- Redis;
- RabbitMQ;
- external APIs.

Do not remove default-deny networking as a shortcut.

Create targeted provider/environment-specific egress rules.

---

## 12. Controlled Initial Deployment

The deployment script defaults to safe behaviour.

For an approved live deployment:

```bash
./infrastructure/scripts/deploy.sh \
  gcp \
  <image-tag> \
  --apply
```

The script requires explicit confirmation before modifying the cluster.

Verify the displayed Kubernetes context before proceeding.

---

## 13. Check Deployment State

Run:

```bash
kubectl get deployments -n firefusion
kubectl get pods -n firefusion
kubectl get services -n firefusion
```

Check rollout:

```bash
kubectl rollout status deployment/firefusion-api -n firefusion
kubectl rollout status deployment/model-api -n firefusion
kubectl rollout status deployment/aggregator-api -n firefusion
```

All expected workloads should reach Ready state.

---

## 14. Run Integration Smoke Tests

Run:

```bash
./infrastructure/scripts/smoke-test.sh
```

The script validates:

- cluster access;
- deployments;
- pod readiness;
- backend Services;
- `/health`;
- `/ready`.

A failed smoke test should block further promotion.

---

## 15. Validate Security

Confirm:

- containers run as non-root;
- privilege escalation is disabled;
- expected NetworkPolicies exist;
- secret values are not present in ConfigMaps;
- cloud credentials are not committed;
- the DevSecOps security workflow is successful.

---

## 16. GitOps Validation

Validate the Argo CD configuration:

```bash
./infrastructure/scripts/gitops-validate.sh
```

The configuration includes provider-specific Applications for:

```text
gcp
azure
aws
```

Only the selected deployment target should be activated.

---

## 17. Image Promotion

After the container image is validated, use controlled promotion rather than manual runtime edits.

The repository provides:

```bash
./infrastructure/scripts/promote-image.sh
```

A GitHub Actions workflow also supports manually controlled image promotion.

Promotion modifies Git desired state.

Argo CD then reconciles the cluster.

---

## 18. GitOps Steady-State Deployment

After Argo CD is bootstrapped:

```text
Build Image
    |
    v
Validate Image
    |
    v
Promote Image Tag
    |
    v
Commit Desired State
    |
    v
Argo CD
    |
    v
Kubernetes
```

Routine deployments should occur through this mechanism.

---

## 19. Observability Validation

Run:

```bash
./infrastructure/scripts/observability-validate.sh
```

The validation checks:

- Prometheus;
- Grafana;
- Loki;
- Grafana Alloy;
- metrics configuration;
- logging configuration;
- alert rules;
- workload security.

---

## 20. Runtime Observability Checks

After live deployment confirm:

### Prometheus

- FireFusion targets are discovered.
- All expected targets are UP.
- `/metrics` can be scraped.

### Grafana

- Prometheus datasource works.
- Loki datasource works.
- dashboards receive data.

### Loki

- backend logs are available.

### Alloy

- FireFusion Kubernetes workloads are discovered;
- logs are forwarded to Loki.

### Alerts

Verify backend alert rules are loaded.

---

## 21. Rollback

If deployment validation fails, follow:

```text
infrastructure/docs/runbooks/rollback-recovery.md
```

Preferred application rollback uses a previous Git desired-state revision or known-good immutable image.

Do not switch to uncontrolled `latest` tags as a rollback mechanism.

---

## 22. GCP Deployment Checklist

For the first approved GCP deployment use:

```text
infrastructure/docs/runbooks/gcp-deployment-checklist.md
```

This provides the full operational checklist and evidence requirements.

---

## 23. Current Deployment Status

The deployment architecture and supporting tooling have been implemented and locally/CI validated.

Live cloud deployment remains pending approved university cloud access.