# FireFusion GCP Deployment Checklist

## Purpose

This checklist provides a concise operational sequence for deploying the FireFusion backend to the approved Google Cloud Platform environment.

It complements the detailed migration strategy and rollback runbook.

The checklist must only be used after university cloud approval and access are confirmed.

---

## 1. Governance and Access

Confirm:

- [ ] University Cloud Service approval is complete.
- [ ] Approved GCP project ID is known.
- [ ] Approved GCP region is known.
- [ ] Billing and quota requirements are confirmed.
- [ ] Approved management network or CIDR is known.
- [ ] Required IAM permissions are approved.
- [ ] GKE control-plane access model is confirmed.
- [ ] Data/security requirements are confirmed.

Do not proceed until these items are complete.

---

## 2. Repository and Branch

Confirm the correct repository and deployment branch:

```bash
git status
git branch --show-current
git pull
```

Confirm there are no unexpected local changes:

```bash
git status --short
```

---

## 3. Validate Terraform

Navigate to:

```bash
cd infrastructure/terraform/environments/dev/gcp
```

Run:

```bash
terraform fmt -check -recursive
terraform init
terraform validate
```

Expected result:

- [ ] Terraform initialization succeeds.
- [ ] Terraform validation succeeds.
- [ ] No sensitive files are tracked in Git.

---

## 4. Review Terraform Plan

Create and review a plan:

```bash
terraform plan
```

Confirm:

- [ ] expected GCP resources only;
- [ ] approved region;
- [ ] approved network ranges;
- [ ] expected GKE configuration;
- [ ] no unexpected public exposure;
- [ ] no destructive changes.

Do not apply an unreviewed Terraform plan.

---

## 5. Provision Infrastructure

After plan approval:

```bash
terraform apply
```

Record:

- Terraform output;
- GKE cluster name;
- GCP region;
- project ID;
- any required service endpoints.

---

## 6. Connect to GKE

Example:

```bash
gcloud container clusters get-credentials <cluster-name> \
  --region <region> \
  --project <project-id>
```

Then:

```bash
kubectl config current-context
kubectl cluster-info
kubectl get nodes
```

Confirm:

- [ ] correct GKE context;
- [ ] API server is reachable;
- [ ] all expected nodes are Ready.

---

## 7. Configure Identity

Confirm CI/CD identity:

- [ ] GitHub OIDC / GCP Workload Identity Federation configured.
- [ ] No long-lived GCP service-account key is required.
- [ ] IAM permissions follow least privilege.

Confirm workload identity:

- [ ] Kubernetes ServiceAccount exists.
- [ ] GKE workload identity binding is configured if required.
- [ ] backend workloads have only required cloud permissions.

---

## 8. Configure Secrets

Confirm required sensitive configuration exists using the approved secret mechanism.

Examples include:

- [ ] broker credentials / URL;
- [ ] Redis/cache credentials / URL;
- [ ] database credentials / URL;
- [ ] application API keys;
- [ ] other backend runtime secrets.

Do not commit actual secret values to Git.

Confirm the Kubernetes runtime can resolve all required Secret references before deployment.

---

## 9. Validate External Dependencies

Confirm availability of:

- [ ] relational database;
- [ ] RabbitMQ or approved message broker;
- [ ] Redis or approved cache;
- [ ] required external APIs.

Confirm network paths and ports are known.

Add only the required Kubernetes egress policies.

Do not remove the default-deny NetworkPolicy.

---

## 10. Verify Container Images

Confirm the selected immutable image tag exists for:

```text
firefusion-api
model-api
aggregator-api
```

Example:

```text
docker.io/<registry-user>/firefusion-api:<validated-sha>
docker.io/<registry-user>/model-api:<validated-sha>
docker.io/<registry-user>/aggregator-api:<validated-sha>
```

Confirm:

- [ ] image tag was produced by successful CI;
- [ ] all three images exist;
- [ ] selected tag is immutable;
- [ ] `latest` is not used for controlled deployment.

---

## 11. Validate Kubernetes Configuration

From the repository root:

```bash
./infrastructure/scripts/validate.sh gcp
```

Confirm:

- [ ] 3 backend Deployments;
- [ ] 3 backend Services;
- [ ] namespace configuration;
- [ ] `/health` probes;
- [ ] `/ready` probes;
- [ ] resource limits/requests;
- [ ] container security controls;
- [ ] RBAC;
- [ ] 4 expected NetworkPolicies;
- [ ] GCP provider metadata;
- [ ] logical image references.

The validation must complete successfully before deployment.

---

## 12. Render Immutable Deployment

Set the registry username:

```bash
export DOCKERHUB_USERNAME="<registry-user>"
```

Render:

```bash
./infrastructure/scripts/render-deployment.sh \
  gcp \
  <validated-image-tag>
```

Review the rendered manifest.

Confirm:

- [ ] correct provider;
- [ ] correct registry;
- [ ] correct immutable image tag;
- [ ] all three backend images updated;
- [ ] no unexpected resources.

---

## 13. Initial Controlled Deployment

For the initial approved deployment:

```bash
./infrastructure/scripts/deploy.sh \
  gcp \
  <validated-image-tag> \
  --apply
```

Verify that the script shows the expected cluster context.

Only type the required deployment confirmation if the context is correct.

---

## 14. Check Kubernetes Rollout

Run:

```bash
kubectl get deployments -n firefusion
kubectl get pods -n firefusion
kubectl get services -n firefusion
```

Then:

```bash
kubectl rollout status deployment/firefusion-api -n firefusion
kubectl rollout status deployment/model-api -n firefusion
kubectl rollout status deployment/aggregator-api -n firefusion
```

Confirm:

- [ ] all deployments are Available;
- [ ] all expected pods are Ready;
- [ ] no CrashLoopBackOff;
- [ ] no ImagePullBackOff;
- [ ] no failed readiness probes.

---

## 15. Run Backend Smoke Tests

Execute:

```bash
./infrastructure/scripts/smoke-test.sh
```

Confirm:

- [ ] cluster is reachable;
- [ ] all deployments are available;
- [ ] backend pods are Ready;
- [ ] `/health` returns successfully;
- [ ] `/ready` returns successfully.

Do not continue to GitOps enablement if smoke testing fails.

---

## 16. Validate Security

Confirm:

- [ ] workloads run as non-root;
- [ ] privilege escalation disabled;
- [ ] read-only root filesystem controls remain active;
- [ ] required NetworkPolicies exist;
- [ ] no real secrets appear in manifests;
- [ ] no long-lived cloud credentials committed;
- [ ] DevSecOps Security Validation workflow is green.

---

## 17. Bootstrap / Validate Argo CD

Before activating GitOps:

```bash
./infrastructure/scripts/gitops-validate.sh
```

Confirm:

- [ ] AppProject is valid;
- [ ] GCP Application is valid;
- [ ] repository reference is correct;
- [ ] GCP overlay renders;
- [ ] self-healing is configured;
- [ ] pruning is configured.

Install/bootstrap Argo CD only using the approved cluster process.

---

## 18. Verify GitOps State

After Argo CD is active, confirm the FireFusion GCP Application becomes:

```text
Synced
Healthy
```

Routine deployment changes should now occur through Git desired state rather than manual `kubectl apply`.

---

## 19. Deploy Observability

Validate first:

```bash
./infrastructure/scripts/observability-validate.sh
```

Confirm:

- [ ] Prometheus configuration;
- [ ] Grafana configuration;
- [ ] Loki configuration;
- [ ] Grafana Alloy configuration;
- [ ] alert rules;
- [ ] workload security controls.

Deploy using the approved GitOps/deployment mechanism.

---

## 20. Validate Prometheus

Confirm:

- [ ] Prometheus pod is Ready;
- [ ] FireFusion backend targets are discovered;
- [ ] all expected backend targets show `UP`;
- [ ] `/metrics` is successfully scraped.

Check for:

```text
firefusion-api
model-api
aggregator-api
```

---

## 21. Validate Grafana

Confirm:

- [ ] Grafana pod is Ready;
- [ ] Prometheus datasource works;
- [ ] Loki datasource works;
- [ ] FireFusion dashboard loads;
- [ ] metrics appear on dashboard panels.

---

## 22. Validate Loki and Alloy

Confirm:

- [ ] Loki pod is Ready;
- [ ] Alloy pod is Ready;
- [ ] FireFusion pod logs are collected;
- [ ] logs are queryable from Grafana;
- [ ] unrelated workloads are not unintentionally collected.

---

## 23. Validate Alert Rules

Confirm the four backend rules are loaded:

- [ ] backend service unavailable;
- [ ] no backend targets;
- [ ] high HTTP 5xx rate;
- [ ] high request latency.

Alert thresholds should later be tuned using actual runtime traffic.

---

## 24. Final Integration Validation

Verify:

- [ ] FireFusion API operational;
- [ ] Model API operational;
- [ ] Aggregator API operational;
- [ ] service-to-service communication works;
- [ ] database access works;
- [ ] broker communication works;
- [ ] Redis/cache access works;
- [ ] observability is operational;
- [ ] no unexpected security alerts;
- [ ] Argo CD reports expected state.

---

## 25. Evidence Capture

Capture evidence for assessment and operational records:

- [ ] Terraform validation/plan;
- [ ] GKE nodes Ready;
- [ ] backend Deployments and Pods;
- [ ] successful smoke test;
- [ ] Argo CD Synced/Healthy state;
- [ ] Prometheus targets;
- [ ] Grafana dashboard;
- [ ] Loki logs;
- [ ] alert rules;
- [ ] successful DevSecOps workflow.

Do not capture screenshots containing secret values.

---

## 26. Rollback Trigger Conditions

Rollback should be considered if:

- backend deployments fail to become Ready;
- smoke testing fails;
- critical integration fails;
- error rate increases significantly;
- severe latency regression occurs;
- security controls are unexpectedly disabled;
- GitOps reconciliation fails due to the new deployment.

Follow:

```text
infrastructure/docs/runbooks/rollback-recovery.md
```

---

## 27. Deployment Completion Criteria

The first GCP deployment is considered successfully validated only when:

- [ ] infrastructure is provisioned successfully;
- [ ] all GKE nodes are Ready;
- [ ] all three backend services are Ready;
- [ ] health/readiness tests pass;
- [ ] external dependencies are reachable;
- [ ] GitOps reconciliation is healthy;
- [ ] metrics are visible;
- [ ] logs are visible;
- [ ] alert rules are loaded;
- [ ] security validation passes;
- [ ] required evidence is captured.