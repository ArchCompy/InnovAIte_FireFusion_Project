# FireFusion Rollback and Recovery Runbook

## 1. Purpose

This runbook defines the operational procedure for recovering FireFusion from failed application deployments, GitOps configuration errors, infrastructure changes, and Kubernetes workload failures.

The objective is to restore the last known good state quickly while preserving an auditable deployment history.

## 2. Recovery Principles

During an incident:

1. stop further deployments;
2. identify the failing change;
3. determine the last known good state;
4. restore desired state through Git where possible;
5. validate Kubernetes rollout;
6. verify `/health` and `/ready`;
7. inspect metrics and logs;
8. document the cause and remediation.

Routine rollback should use GitOps rather than manually modifying cluster state.

## 3. Application Deployment Failure

Example symptoms:

- pods enter `CrashLoopBackOff`;
- readiness probes fail;
- application error rate increases;
- deployment rollout times out;
- new image fails integration tests.

### Step 1 – Inspect Deployment State

```bash
kubectl get deployments -n firefusion
kubectl get pods -n firefusion
```

Inspect the affected workload:

```bash
kubectl describe deployment <deployment-name> -n firefusion
```

Check pod logs:

```bash
kubectl logs <pod-name> -n firefusion
```

### Step 2 – Identify the Last Known Good Revision

Review the most recent Git desired-state changes.

Identify the previous known-good immutable image tag or Git commit.

### Step 3 – Revert Through Git

Preferred rollback:

```bash
git revert <deployment-change-commit>
```

Then:

```bash
git push
```

Argo CD should detect the restored desired state and reconcile the cluster.

### Step 4 – Validate Reconciliation

```bash
kubectl rollout status \
  deployment/firefusion-api \
  -n firefusion

kubectl rollout status \
  deployment/model-api \
  -n firefusion

kubectl rollout status \
  deployment/aggregator-api \
  -n firefusion
```

### Step 5 – Validate Application Health

Run the FireFusion smoke tests:

```bash
./infrastructure/scripts/smoke-test.sh
```

Confirm:

- `/health` succeeds;
- `/ready` succeeds;
- pods remain Ready;
- backend integration succeeds.

## 4. Argo CD Synchronization Failure

Example symptoms:

- Argo CD application becomes OutOfSync;
- sync operation fails;
- invalid Kubernetes desired state;
- resource reconciliation loops.

### Investigation

Check the affected Argo CD Application.

Determine whether the failure was introduced by:

- invalid manifest configuration;
- missing Kubernetes Secret;
- invalid container image;
- missing CRD;
- cluster permissions;
- networking dependency; or
- unavailable cloud resource.

### Recovery

If the current Git revision is invalid, revert to the previous known-good Git revision.

Do not repeatedly force-sync a configuration known to be invalid.

After restoring Git:

1. verify Argo CD sees the new revision;
2. perform or allow reconciliation;
3. confirm application status becomes Synced;
4. confirm application health becomes Healthy;
5. run backend smoke tests.

## 5. Failed Image Promotion

If an image promotion references a tag that does not exist:

1. stop the promotion;
2. verify registry image availability;
3. identify the last known good image;
4. restore the previous image tag in the provider overlay;
5. validate Kustomize rendering;
6. commit the corrected state;
7. allow Argo CD to reconcile.

Never replace a missing immutable image with `latest` merely to complete a deployment.

## 6. Kubernetes Readiness Failure

If a pod is Running but not Ready:

```bash
kubectl get pods -n firefusion
kubectl describe pod <pod-name> -n firefusion
kubectl logs <pod-name> -n firefusion
```

Check:

- required environment variables;
- Kubernetes Secret availability;
- RabbitMQ availability;
- Redis availability;
- database connectivity;
- readiness endpoint behaviour;
- NetworkPolicy restrictions.

Do not remove readiness probes to hide the failure.

Correct the dependency or configuration issue instead.

## 7. Kubernetes Liveness Failure

Repeated liveness failures can cause container restarts.

Inspect:

```bash
kubectl describe pod <pod-name> -n firefusion
kubectl logs <pod-name> -n firefusion --previous
```

Confirm `/health` behaviour and check whether the application process is failing.

If the new application version introduced the issue, revert to the previous image.

## 8. NetworkPolicy Failure

Symptoms may include:

- service-to-service requests fail;
- metrics are not scraped;
- database connection fails;
- Redis or RabbitMQ becomes unreachable.

Inspect NetworkPolicies:

```bash
kubectl get networkpolicy -n firefusion
```

Do not disable the default-deny policy as the first response.

Instead:

1. identify the required traffic path;
2. determine source and destination;
3. determine required protocol and port;
4. add the narrowest required allow policy;
5. validate connectivity;
6. commit the policy through Git.

## 9. Secret or Configuration Failure

If workloads fail because required configuration is missing:

```bash
kubectl describe pod <pod-name> -n firefusion
```

Check for:

- missing Secret;
- incorrect Secret key;
- missing ConfigMap;
- incorrect workload identity;
- unavailable managed secret provider.

Never place the real secret value directly into a Git-tracked manifest as an emergency fix.

Use the approved secret-management mechanism.

## 10. Observability Failure

### Prometheus Failure

Check:

```bash
kubectl get pods -n monitoring
kubectl logs deployment/prometheus -n monitoring
```

Confirm:

- configuration is valid;
- service discovery is working;
- NetworkPolicy permits metrics scraping.

### Grafana Failure

Check:

```bash
kubectl logs deployment/grafana -n monitoring
```

Confirm:

- `grafana-admin` Secret exists;
- Prometheus datasource is reachable;
- Loki datasource is reachable.

### Loki Failure

Check:

```bash
kubectl logs deployment/loki -n monitoring
```

Confirm writable data volumes and Loki configuration.

### Alloy Failure

Check:

```bash
kubectl logs deployment/alloy -n monitoring
```

Confirm:

- Kubernetes RBAC is valid;
- FireFusion pods can be discovered;
- Loki ingestion endpoint is reachable.

## 11. Terraform Infrastructure Failure

If `terraform apply` fails:

1. do not immediately re-run repeatedly;
2. review the error;
3. inspect current Terraform state;
4. run:

```bash
terraform plan
```

5. determine whether resources were partially created;
6. correct configuration;
7. produce a new plan;
8. review before applying again.

Do not manually delete Terraform-managed resources unless recovery requires it and the state implications are understood.

## 12. Bad Infrastructure Change

If a Terraform change causes a cluster or networking problem:

1. stop further changes;
2. identify the last known good Terraform commit;
3. compare the failing configuration;
4. revert the configuration in Git;
5. run:

```bash
terraform fmt -check
terraform validate
terraform plan
```

6. verify that the plan safely restores the previous design;
7. apply only after review.

## 13. Emergency Manual Kubernetes Changes

Manual cluster changes should be reserved for incident containment when GitOps cannot safely perform the recovery.

If emergency `kubectl` changes are made:

1. document the command;
2. record why GitOps could not be used;
3. restore service;
4. update Git to reflect the intended final configuration;
5. allow Argo CD to reconcile;
6. confirm no unmanaged configuration drift remains.

## 14. Recovery Validation

After any rollback or recovery:

```bash
kubectl get deployments -n firefusion
kubectl get pods -n firefusion
kubectl get services -n firefusion
```

Then:

```bash
./infrastructure/scripts/smoke-test.sh
```

Validate observability:

- Prometheus targets are UP;
- backend error rate is normal;
- request latency is acceptable;
- logs are visible in Loki;
- no unexpected alerts remain active.

## 15. Recovery Success Criteria

Recovery is complete only when:

- expected deployments are Ready;
- `/health` succeeds;
- `/ready` succeeds;
- backend service integration is operational;
- no critical monitoring alerts remain;
- Git and runtime desired state match;
- security controls remain enabled;
- incident actions are documented.

## 16. Post-Incident Actions

After recovery:

1. document the root cause;
2. identify whether CI should have detected the failure earlier;
3. add or improve automated tests where appropriate;
4. update alert thresholds if required;
5. update this runbook if the recovery process was incomplete;
6. record evidence for the project operational history.

## 17. Important Safety Rules

Do not:

- disable security controls simply to restore service;
- commit credentials;
- replace immutable deployment tags with uncontrolled `latest`;
- delete Terraform state;
- disable readiness/liveness probes to conceal a failing workload;
- permanently bypass GitOps without documenting and reconciling the change.