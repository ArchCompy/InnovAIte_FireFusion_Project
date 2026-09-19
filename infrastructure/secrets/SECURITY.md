# Secret Management Security Requirements

The FireFusion secret-management templates are examples only.

They must not contain real secret values.

The cloud deployment must use least-privilege workload identity to access only
the secrets required by the backend workloads.

Required secrets:

- BROKER_URL
- CACHE_URL
- DB_URL
- RELATIONAL_DB_URL
- API_KEY
- VALID_API_KEY

Secret access should be scoped to the selected environment and should not grant
broad access to unrelated cloud resources.

The repository must not contain:

- database passwords
- RabbitMQ credentials
- Redis passwords
- cloud access keys
- client secrets
- API key values
