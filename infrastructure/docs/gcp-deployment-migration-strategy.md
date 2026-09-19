# FireFusion GCP Deployment and Migration Strategy

## 1. Purpose

This document defines the proposed deployment and migration approach for moving the FireFusion backend from the current local and validated Infrastructure-as-Code state into the university-approved Google Cloud Platform environment.

The current implementation already provides:

- Docker-based local development;
- multi-cloud Terraform foundations;
- Kubernetes base manifests;
- GCP/GKE Kustomize overlays;
- GitHub Actions CI and security validation;
- Argo CD GitOps configuration;
- Prometheus, Grafana, Loki, and Alloy observability;
- cloud identity and secret-management templates; and
- deployment and smoke-test automation.

The actual live GCP deployment remains dependent on university cloud approval and access.

## 2. Why GCP Is the Preferred Initial Target

GCP is currently the preferred initial deployment target because the university has indicated support for proceeding with Google Cloud Platform.

The design does not assume that GCP is permanently mandatory. FireFusion retains AKS and EKS infrastructure definitions so that the backend can migrate to another managed Kubernetes provider if required.

GCP therefore acts as the current deployment target while Kubernetes remains the portability layer.

## 3. Target Runtime Architecture

The proposed runtime architecture is:

```text
GitHub
  |
  | CI / Security Validation
  v
Container Registry
  |
  | Immutable Image Tag
  v
Git Desired State
  |
  v
Argo CD
  |
  v
Google Kubernetes Engine
  |
  +--> FireFusion API
  |
  +--> Model API
  |
  +--> Aggregator API
  |
  +--> Prometheus
  |
  +--> Grafana
  |
  +--> Loki
  |
  +--> Grafana Alloy
```

External managed dependencies such as database, messaging, cache, and secret-management services will be integrated once approved endpoints and credentials are available.

## 4. Migration Principles

The migration will follow these principles:

- no direct production deployment before infrastructure validation;
- no hard-coded credentials;
- no mutable `latest` image tag for controlled deployment;
- infrastructure changes must be reproducible;
- security validation must pass before deployment;
- Git must remain the source of truth for desired Kubernetes state;
- application health must be validated after deployment;
- rollback must remain possible at every deployment stage.

## 5. Phase 1 – Cloud Access and Governance

Before any resources are created:

1. confirm university Cloud Service approval;
2. confirm the approved GCP project;
3. confirm project billing and quota constraints;
4. confirm approved GCP region;
5. confirm allowed management CIDR or network path;
6. confirm service-account and IAM governance;
7. confirm whether public or private GKE control-plane access is permitted;
8. confirm data-residency and security requirements.

No infrastructure should be deployed until the required governance approval is complete.

## 6. Phase 2 – Terraform Configuration

The GCP Terraform environment is located under:

```text
infrastructure/terraform/environments/dev/gcp/
```

The reusable GCP modules are located under:

```text
infrastructure/terraform/modules/gcp/
```

Deployment-specific values should be provided using a local or protected Terraform variables file that is not committed to Git.

Before deployment:

```bash
terraform fmt -check
terraform init
terraform validate
terraform plan
```

The generated Terraform plan must be reviewed before apply.

No credentials, state files, plan files, or actual secret values should be committed to source control.

## 7. Phase 3 – Provision GKE Infrastructure

After approval of the Terraform plan:

```bash
terraform apply
```

The deployment should provision the approved GCP Kubernetes infrastructure.

Expected validation includes:

```bash
gcloud container clusters get-credentials <cluster-name> \
  --region <region> \
  --project <project-id>
```

Then:

```bash
kubectl cluster-info
kubectl get nodes
kubectl get namespaces
```

Deployment should stop if the cluster is unreachable or nodes are not Ready.

## 8. Phase 4 – Identity and Secrets

Before deploying backend workloads, cloud identity and secret-management integration must be activated.

The preferred direction is:

```text
GitHub Actions
      |
      v
GCP Workload Identity Federation
      |
      v
Short-Lived GCP Identity
```

For workloads:

```text
Kubernetes ServiceAccount
      |
      v
GKE Workload Identity
      |
      v
Approved Google Cloud Services
```

Sensitive values should be maintained in an approved managed secret service such as Google Secret Manager.

The existing repository secret templates contain placeholders only.

A real Kubernetes Secret or managed secret-sync integration must exist before backend workloads that depend on these values are started.

## 9. Phase 5 – External Dependencies

The FireFusion backend depends on runtime services including:

- relational database;
- RabbitMQ or equivalent message broker;
- Redis cache; and
- required application API keys.

The final managed services and network endpoints must be known before creating production egress NetworkPolicies.

The current default-deny network posture intentionally does not provide unrestricted access to unknown external endpoints.

Provider-specific egress rules should therefore be created only after the approved managed-service topology is confirmed.

## 10. Phase 6 – Container Image Availability

Before Kubernetes deployment, verify that the required immutable image tag exists for:

- `firefusion-api`;
- `model-api`; and
- `aggregator-api`.

The deployment must not assume that an arbitrary Git SHA is available in the container registry.

Only a tag produced by a successful image-build and publish workflow should be promoted.

Example:

```text
docker.io/<registry-user>/firefusion-api:<validated-sha>
docker.io/<registry-user>/model-api:<validated-sha>
docker.io/<registry-user>/aggregator-api:<validated-sha>
```

## 11. Phase 7 – Render and Validate the GCP Deployment

Before applying manifests:

```bash
./infrastructure/scripts/validate.sh gcp
```

Then render the selected immutable image tag:

```bash
export DOCKERHUB_USERNAME="<registry-user>"

./infrastructure/scripts/render-deployment.sh \
  gcp \
  <validated-image-tag>
```

The rendered manifests must be reviewed before cluster deployment.

Validation checks include:

- three backend Deployments;
- three Services;
- namespace configuration;
- health and readiness probes;
- resource controls;
- container security controls;
- RBAC;
- NetworkPolicies;
- provider labels; and
- immutable image references.

## 12. Phase 8 – Initial Controlled Deployment

The initial cluster deployment may use the controlled deployment script:

```bash
./infrastructure/scripts/deploy.sh \
  gcp \
  <validated-image-tag> \
  --apply
```

The script requires explicit confirmation before modifying a live Kubernetes cluster.

After deployment:

```bash
kubectl get deployments -n firefusion
kubectl get pods -n firefusion
kubectl get services -n firefusion
```

All backend deployments must reach their expected Ready state.

## 13. Phase 9 – Smoke and Integration Validation

Run:

```bash
./infrastructure/scripts/smoke-test.sh
```

The smoke test validates:

- Kubernetes connectivity;
- deployment rollout state;
- Ready backend pods;
- backend Services;
- `/health` endpoints; and
- `/ready` endpoints.

The deployment must not be promoted further if these checks fail.

## 14. Phase 10 – Bootstrap GitOps

After the initial cluster is stable, Argo CD can be installed and configured.

The FireFusion GCP Application definition is already maintained under:

```text
infrastructure/argocd/applications/firefusion-gcp.yaml
```

Before activation:

```bash
./infrastructure/scripts/gitops-validate.sh
```

The intended steady-state model is:

```text
Git Desired State
      |
      v
Argo CD
      |
      v
GKE
```

After GitOps activation, routine Kubernetes changes should be made through Git rather than direct `kubectl apply`.

## 15. Phase 11 – Observability Deployment

Deploy the observability stack after application networking and required secrets are available.

Validate locally first:

```bash
./infrastructure/scripts/observability-validate.sh
```

Expected components include:

- Prometheus;
- Grafana;
- Loki;
- Grafana Alloy; and
- backend alert rules.

Runtime validation should confirm:

- all Prometheus FireFusion targets are UP;
- Grafana can query Prometheus;
- Grafana can query Loki;
- FireFusion pod logs appear in Loki;
- backend dashboards display runtime data; and
- alert rules are loaded.

## 16. Phase 12 – Security Validation

Before considering the cloud migration successful, confirm:

- no long-lived cloud credentials are committed;
- workload containers run as non-root;
- read-only root filesystem controls are effective;
- privilege escalation is disabled;
- NetworkPolicies are active;
- secret values are not stored in ConfigMaps;
- GCP IAM follows least privilege;
- GitHub OIDC federation works as intended; and
- the DevSecOps pipeline remains green.

## 17. Migration Cutover Criteria

The GCP deployment can be considered operational only when all of the following are true:

- Terraform infrastructure is successfully provisioned;
- GKE nodes are Ready;
- required secrets and managed dependencies are available;
- all three backend services are deployed;
- `/health` succeeds;
- `/ready` succeeds;
- service-to-service integration is validated;
- Prometheus targets are UP;
- Grafana dashboards receive data;
- Loki receives backend logs;
- security checks pass;
- GitOps reconciliation succeeds.

## 18. Rollback Strategy

If migration validation fails before production cutover, the existing local/development workflow remains the fallback environment.

For application failures after Kubernetes deployment:

1. identify the last known good image tag;
2. revert the Git desired-state change;
3. allow Argo CD to reconcile the previous revision;
4. confirm deployment rollout;
5. run health and readiness tests;
6. verify logs and monitoring.

For infrastructure failures:

1. stop further Terraform changes;
2. review the Terraform plan/state;
3. revert the infrastructure change where safe;
4. restore the last known good configuration;
5. re-run Terraform validation and planning;
6. verify cluster and application health.

Detailed recovery procedures are maintained separately in the rollback runbook.

## 19. Migration to Another Cloud Provider

The GCP-first deployment does not prevent a future migration to Azure or AWS.

The general provider migration process would be:

```text
Current Provider
      |
      v
Validate Target Terraform
      |
      v
Provision Target Managed Kubernetes
      |
      v
Activate Target Identity + Secrets
      |
      v
Deploy Same Kubernetes Base
      |
      v
Use Target Kustomize Overlay
      |
      v
Run Smoke Tests
      |
      v
Activate GitOps + Observability
      |
      v
Cut Over
```

Provider-specific managed dependencies and networking would still need migration planning.

## 20. Current Status

The infrastructure, deployment tooling, security controls, GitOps configuration, and observability configuration have been implemented and validated without modifying a live university cloud environment.

The following remain pending approved cloud access:

- Terraform apply against the approved GCP project;
- GKE runtime deployment;
- workload identity activation;
- managed secret integration;
- final external dependency networking;
- live Argo CD synchronization;
- live Prometheus/Grafana/Loki evidence; and
- runtime alert testing.