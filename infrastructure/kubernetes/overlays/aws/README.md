# AWS Kubernetes Overlay

This overlay renders the portable FireFusion Kubernetes base for AWS/EKS.

The AWS Secrets Manager secret-provider template is stored under:

    secrets/

It is intentionally not included in the active overlay until:

- EKS is provisioned
- EKS workload identity is configured
- AWS Secrets Manager secrets exist
- Secrets Store CSI Driver and AWS provider are installed
- Real AWS identifiers are supplied

At deployment time, the AWS secret provider can be activated after replacing
template values with the approved environment configuration.
