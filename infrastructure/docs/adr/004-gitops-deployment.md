# ADR-004: GitOps Continuous Delivery with Argo CD

## Status

Accepted

## Date

September 2026

## Context

FireFusion requires a controlled, repeatable, and auditable method for deploying Kubernetes application changes.

Allowing the CI pipeline to directly apply routine Kubernetes changes would make CI responsible for both producing software artifacts and mutating the runtime cluster.

This would also increase the level of cluster access required by the CI environment.

The project already maintains declarative Kubernetes configuration in Git and supports immutable image-based deployment promotion.

## Decision

FireFusion will use Argo CD as the Kubernetes continuous-delivery mechanism.

Git will act as the source of truth for desired Kubernetes state.

The delivery flow is:

```text
Source Change
     |
     v
GitHub Actions CI
     |
     +--> Application Testing
     |
     +--> Security Validation
     |
     +--> Container Build
     |
     v
Container Registry
     |
     v
Controlled Image Promotion
     |
     v
Git Desired-State Update
     |
     v
Argo CD
     |
     v
Managed Kubernetes
```

GitHub Actions is responsible for CI validation and controlled modification of the desired deployment state.

Argo CD is responsible for reconciling the approved state stored in Git with the Kubernetes cluster.

## Rationale

Separating CI from routine runtime cluster mutation provides a clearer operational and security boundary.

The GitOps model provides:

- auditable deployment history;
- declarative desired state;
- drift detection;
- automated reconciliation;
- self-healing;
- pruning of obsolete resources;
- Git-based rollback;
- visibility into desired versus actual state; and
- repeatable deployment behaviour.

Git commits also provide a clear relationship between application versions, infrastructure configuration, deployment state, and operational evidence.

## Argo CD Architecture

FireFusion defines an Argo CD AppProject that scopes the GitOps deployment environment.

Provider-specific Argo CD Applications are maintained for:

- Azure/AKS;
- AWS/EKS; and
- GCP/GKE.

Each application references the corresponding Kubernetes Kustomize overlay.

The provider-specific Applications represent alternative deployment targets.

They do not indicate that FireFusion will automatically deploy production workloads to all three cloud providers simultaneously.

## Automated Reconciliation

The Argo CD configuration enables automated synchronization controls including:

- pruning;
- self-healing; and
- creation of the required application namespace.

Self-healing allows Argo CD to detect and reconcile configuration drift between Git and the runtime Kubernetes environment.

Pruning allows resources removed from the approved desired state to be removed from the cluster in a controlled manner.

## Image Promotion

FireFusion uses controlled image promotion rather than manually editing runtime resources.

The image-promotion process updates the selected provider's desired-state configuration with an immutable image tag.

The intended flow is:

```text
Validated Container Image
          |
          v
Select Provider + Image Tag
          |
          v
Promotion Validation
          |
          v
Update Kustomize Desired State
          |
          v
Commit Change to Git
          |
          v
Argo CD Reconciliation
```

A manually triggered GitHub Actions workflow is used for controlled promotion.

This is intentionally separated from normal CI so that building an image does not automatically imply production deployment.

## Rollback Strategy

GitOps provides a deterministic rollback mechanism.

If a deployment introduces a fault, the desired state can be restored to a previously validated Git revision or immutable container-image tag.

The rollback flow is:

```text
Deployment Problem Detected
          |
          v
Identify Last Known Good Revision
          |
          v
Restore Previous Desired State
          |
          v
Commit / Revert in Git
          |
          v
Argo CD Detects Change
          |
          v
Reconcile Kubernetes
          |
          v
Validate /health and /ready
```

This approach avoids manually reconstructing Kubernetes resources during normal rollback operations.

Emergency manual Kubernetes operations may still be used when GitOps reconciliation itself is unavailable, but Git should subsequently be updated to restore desired-state consistency.

## Security Considerations

The GitOps model reduces the requirement for routine CI jobs to hold broad Kubernetes deployment permissions.

Repository access and promotion workflow permissions must still be controlled because a malicious or incorrect desired-state change could be reconciled automatically.

Cloud and cluster credentials should use short-lived identity federation rather than long-lived static credentials.

GitOps does not replace:

- CI security validation;
- Kubernetes RBAC;
- NetworkPolicy;
- workload identity;
- secrets management; or
- infrastructure security scanning.

Instead, it forms one layer of the wider FireFusion deployment security model.

## Alternatives Considered

### Direct kubectl from GitHub Actions

This approach is straightforward but gives CI direct runtime deployment responsibility and requires cluster-level connectivity and permissions.

It also makes Git less authoritative if runtime changes can occur independently of the desired-state configuration.

### Manual kubectl Deployment

Manual deployment is useful for troubleshooting and controlled emergency operations.

However, it is not suitable as the primary continuous-delivery mechanism because it is less repeatable, less auditable, and more susceptible to configuration drift.

### Automatic Deployment After Every Image Build

Automatically deploying every successful image build was not selected because successful artifact creation does not necessarily mean that the artifact has been approved for the active cloud environment.

Controlled promotion provides an explicit deployment boundary.

## Consequences

### Positive

- Git provides an auditable deployment history.
- Runtime drift can be detected and corrected.
- CI and CD responsibilities are separated.
- Rollback is based on version-controlled desired state.
- Deployment promotion is explicit.
- The same GitOps model can support AKS, EKS, or GKE.
- Direct routine cluster mutation from CI is reduced.

### Trade-offs

- Argo CD becomes an operational platform dependency.
- Git repository access requires strong permission control.
- Incorrect approved configuration can be automatically reconciled.
- Initial Argo CD bootstrap requires cluster administrative access.
- Emergency procedures are required if Argo CD itself becomes unavailable.

## Implementation Evidence

Relevant repository paths include:

- `infrastructure/argocd/projects/firefusion-project.yaml`
- `infrastructure/argocd/applications/firefusion-azure.yaml`
- `infrastructure/argocd/applications/firefusion-aws.yaml`
- `infrastructure/argocd/applications/firefusion-gcp.yaml`
- `infrastructure/argocd/kustomization.yaml`
- `infrastructure/scripts/gitops-validate.sh`
- `infrastructure/scripts/promote-image.sh`
- `.github/workflows/gitops-promote.yml`

The GitOps configuration has been rendered and validated locally.

The implementation includes:

- one scoped Argo CD AppProject;
- three provider-specific Application definitions;
- automated pruning;
- automated self-healing;
- provider-overlay validation;
- immutable image-promotion tooling; and
- a manually controlled GitHub Actions promotion workflow.

Live Argo CD synchronization and reconciliation evidence remains pending access to the approved university Kubernetes environment.

## Decision Review

This decision should be reviewed if:

- FireFusion moves away from Kubernetes;
- another GitOps controller becomes the project standard;
- deployment governance requires a different promotion mechanism; or
- Argo CD operational overhead becomes unsuitable for the project.