# FireFusion Cloud Secret Management

FireFusion runtime secrets must be retrieved from the selected cloud provider's
managed secret-management service rather than stored as plaintext values in Git.

Supported provider patterns:

- Azure Key Vault
- AWS Secrets Manager
- Google Secret Manager

The Kubernetes base deployment references a Kubernetes Secret named:

    firefusion-runtime-secrets

The provider-specific secret integration is responsible for supplying the
following runtime values:

- BROKER_URL
- CACHE_URL
- DB_URL
- RELATIONAL_DB_URL
- API_KEY
- VALID_API_KEY

No production secret value is committed to this repository.

## Architecture

Application Pod
      |
      | Kubernetes Secret reference
      v
firefusion-runtime-secrets
      |
      | Cloud secret integration
      v
Cloud Secret Manager

The exact provider integration is activated only after the approved cloud
environment is available.
