# Backend Security Configuration

Implements findings F1 and F2 from the Backend Audit Summary.

## What was wrong

- **Authentication was applied to one route out of sixteen.** Only
  `aggregator-api /hello/` enforced the API key. The `/internal/data/*` routes,
  which expose Data Engineering source data, were reachable without any
  credential. `model-api` contained a working API key check in
  `internal/services/security.py` that was never applied to a route.
- **The API key was hardcoded in a committed Dockerfile**
  (`ENV API_KEY=secret_key`), so the credential was in version control and
  identical in every environment.
- **CORS allowed all origins.** `firefusion-api` used `allow_origins=["*"]`
  together with `allow_credentials=True`, a combination browsers reject
  outright, so the configuration was both unsafe and non-functional.

## What is enforced now

### Internal service-to-service routes require the shared API key

Supplied in the `X-API-Key` header. Rejected requests return `401`.

| Service | Route | Access |
|---|---|---|
| aggregator-api | `/internal/data/fire-incidents` | API key |
| aggregator-api | `/internal/data/fire-risk-inputs` | API key |
| aggregator-api | `/hello/` | API key |
| model-api | `/model/geojson` | API key |
| model-api | `/model/hello` | Public (liveness probe) |
| firefusion-api | `/api/bushfire-forecast`, `/api/ws`, `/api/misinformation/*` | Public |

The `firefusion-api` routes remain public deliberately: they are consumed by
the dashboard, which has no credential handling yet. Adding user
authentication there is a separate decision for the team and the Product
Owner, and is recorded as a follow-up rather than assumed here.

### The key comes from the environment

The hardcoded value is removed from the Dockerfile. Both services that require
it read `API_KEY` from the environment, supplied through Docker Compose:

```yaml
API_KEY: ${API_KEY:-local-development-key}
```

Local development works with no setup. Any deployed environment must set
`API_KEY` to a real secret, ideally from a secrets manager rather than an
environment file.

### CORS is restricted per environment

`firefusion-api` reads `CORS_ALLOWED_ORIGINS`, a comma separated list,
defaulting to local dashboard origins. Methods are limited to `GET`, which is
all the dashboard needs today.

```yaml
CORS_ALLOWED_ORIGINS: https://dashboard.example.com
```

## Running locally

No change to the normal workflow:

```bash
docker compose --profile default up --build -d
pytest tests
```

Calling a protected route by hand:

```bash
curl -H "X-API-Key: local-development-key" localhost:8082/internal/data/fire-incidents
```

## Tests

`tests/test_security.py` covers the behaviour: protected routes reject a
missing and an invalid key, accept a valid one, the liveness probe stays
public, the dashboard endpoint stays reachable, an unknown browser origin is
not permitted, and the configured dashboard origin is.

## For the cloud deployment work

Two things the deployment workstream needs from this:

1. `API_KEY` and `CORS_ALLOWED_ORIGINS` must be set per environment. Neither
   should use the local default outside local development.
2. `API_KEY` is a secret and belongs in a secrets manager (Key Vault, Secrets
   Manager or the equivalent), not in a manifest or an environment file.

## Follow-ups not covered here

- Whether the dashboard-facing endpoints need user authentication, and if so
  which mechanism. This needs a decision from the team and the Product Owner.
- Rotating the previously committed `secret_key` value if it was ever used
  outside local development.

## Known issue found while testing this (unrelated to security)

`GET /internal/data/fire-incidents` returns `500` even with a valid API key.
The route's key check works correctly (confirmed by the `401` tests passing);
the failure is downstream. `RECENT_FIRE_INCIDENTS_V2_SQL` in
`aggregator_repository.py`, and the `FireIncidentV2` model it feeds, expect a
NASA FIRMS hotspot shape (`record_type`, `source`, `satellite`,
`brightness_ti4`/`ti5`, `frp`, `daynight`, ...), but `Fire_Incident_Record` in
`utilities/v2/aggregator-init.sql` only has `incident_id`, `location_id`,
`time_id`, `original_latitude`, `original_longitude`, `confidence_score`,
`source_system`. The model's own comments mark the FIRMS fields as "still a
cross-stream decision" with AI Modelling, so the table was evidently never
migrated to match. Needs a decision from Data Engineering / AI Modelling on
the actual contract before either the table or the query is changed.

Two smaller, unrelated bugs were found and fixed alongside the security work
while getting the stack running locally:
- `docker-compose.yaml` never mounted `utilities/v2/aggregator-init.sql` or
  `utilities/v2/seed-aggregator.sql` for `relational-db`, so the v2 tables
  never existed locally. Added as `05-schema.sql`/`06-seed.sql`, alongside the
  existing v1 and misinformation mounts.
- `utilities/v2/seed-aggregator.sql` seeded `Time_Registry` with `time_id`
  101-110 but referenced `time_id` 1-10 in `Fire_Incident_Record`, violating
  the foreign key. Corrected to match.
