# Backend Integration & Resilience Validation

This folder contains **black-box integration tests** for the final merged FireFusion Backend.

The suite is designed to be prepared before the current Backend PRs are merged. It does not directly import the implementation from those branches. Instead, it tests the running services through HTTP, Redis and, where configured, WebSockets.

Some tests are therefore expected to **fail or skip on an older/pre-merge clone**. The intended use is to run them again after the relevant Backend work has been merged and reconciled.

## What this suite validates

The tests cover the combined behaviour expected from the recent Backend work:

- **Arsh PR #240 – Backend security hardening**
  - internal API-key protection
  - valid/invalid credential behaviour
  - public operational/liveness routes

- **Ashan – health/readiness commit**
  - `/health`
  - `/ready`
  - final endpoint availability after service startup

- **Zehong PR #238 – Fire Risk Map reliability**
  - malformed cache remains an explicit `503`
  - valid no-data remains a normal response
  - `risk_factor`
  - optional `fire_probability`
  - final REST/WebSocket contract behaviour

- **Arsh PR #250 – graceful degradation / freshness**
  - `live`
  - `stale`
  - `unavailable`
  - timestamp handling
  - freshness metadata

- **Previously reviewed Kubernetes deployment work**
  - the same final endpoints can later be exercised inside the Kind/Kubernetes deployment

## Files

### `conftest.py`

Provides shared pytest fixtures and helpers:

- service URLs
- API key
- HTTP client
- Redis client
- known valid forecast fixture
- forecast cache preservation/restoration
- controlled forecast seeding

### `test_health_readiness.py`

Checks that all three Backend APIs expose the expected liveness/readiness endpoints after startup.

### `test_security_contract.py`

Checks the final service-to-service API-key boundary:

- missing key rejected
- invalid key rejected
- valid key not rejected as unauthorised
- public liveness route remains public

### `test_forecast_contract.py`

Tests the most important merged Fire Risk Map behaviours:

| State | Expected result |
| --- | --- |
| Fresh valid forecast | `200`, polygons served, `meta.status=live` |
| Old valid forecast | `200`, polygons served, `meta.status=stale` |
| Valid forecast with missing/unknown age | `200`, polygons served, `meta.status=stale` |
| No forecast received | `200`, empty `FeatureCollection`, `meta.status=unavailable` |
| Corrupted cached forecast | `503` |
| Schema-invalid cached forecast | `503` |

It also verifies that `risk_factor`, optional `fire_probability`, and the new `meta` information can coexist after merge.

### `test_forecast_boundary.py`

Checks behaviour immediately inside and clearly outside the configured freshness window.

### `test_openapi_contract.py`

Checks that the final generated API contract still exposes:

- `FeatureCollection`
- `risk_factor`
- `fire_probability`
- `meta`
- `/health`
- `/ready`

This is intended to catch accidental model/router regression during merge conflict resolution.

### `test_websocket_contract.py`

Optionally compares one forecast delivered over WebSocket with the current REST response so both channels retain the same final payload contract.

### `test_failure_recovery.py`

Optional **destructive local test** that stops Redis, checks for the expected `503`, restarts Redis, and verifies the API becomes responsive again.

It is disabled unless `RUN_DESTRUCTIVE_INTEGRATION=1`.

### `fixtures/valid_forecast.json`

A known valid Fire Risk Map `FeatureCollection` used to put controlled forecast state into Redis.

---

# Expected final contract

The merged Backend should preserve these distinctions:

| Situation | Expected Backend behaviour |
| --- | --- |
| Fresh valid forecast | `200`, features served, `meta.status=live` |
| Old valid forecast | `200`, features served, `meta.status=stale` |
| Valid prediction with missing/unknown timestamp | `200`, features served, `meta.status=stale` |
| No prediction has been received | `200`, empty features, `meta.status=unavailable` |
| Malformed/corrupted cached prediction | `503 Service Unavailable` |
| Redis/cache unavailable | `503 Service Unavailable` |
| Missing/invalid internal API key | `401` or `403` |
| Healthy service | `/health` returns `200` |
| Ready service | `/ready` returns `200` |

The important merge requirement is that **stale-but-valid data must not be confused with corrupted data**.

---

# How to Run

## 1. Start the Backend stack

Make sure Docker Desktop is running.

From the location containing the project Docker Compose configuration, start the Backend stack using the project's normal command, for example:

```bash
docker compose up -d --build
```

Check that the containers are running:

```bash
docker compose ps
```

The tests expect the FireFusion API, Model API, Aggregator API and Redis to be available.

## 2. Install test dependencies

Use the project's existing Python environment where possible.

If required:

```bash
pip install pytest pytest-asyncio httpx redis websockets
```

## 3. Configure environment variables

Defaults are already provided for local development:

```text
FIREFUSION_URL=http://localhost:8080
MODEL_URL=http://localhost:8081
AGGREGATOR_URL=http://localhost:8082
CACHE_URL=redis://localhost:6379/0
API_KEY=secret_key
FORECAST_STALE_AFTER_SECONDS=900
```

Override any value that differs in the final merged stack.

### PowerShell example

```powershell
$env:FIREFUSION_URL="http://localhost:8080"
$env:MODEL_URL="http://localhost:8081"
$env:AGGREGATOR_URL="http://localhost:8082"
$env:CACHE_URL="redis://localhost:6379/0"
$env:API_KEY="secret_key"
$env:FORECAST_STALE_AFTER_SECONDS="900"
```

## 4. Run the full suite

From the repository root:

```bash
python -m pytest backend/tests/integration -v
```

or use the supplied PowerShell runner:

```powershell
.\backend\utilities\run_backend_integration_tests.ps1
```

or Bash runner:

```bash
bash backend/utilities/run_backend_integration_tests.sh
```

## 5. Run one test file

Example:

```bash
python -m pytest backend/tests/integration/test_forecast_contract.py -v
```

Other useful files:

```bash
python -m pytest backend/tests/integration/test_health_readiness.py -v
python -m pytest backend/tests/integration/test_security_contract.py -v
python -m pytest backend/tests/integration/test_forecast_boundary.py -v
python -m pytest backend/tests/integration/test_openapi_contract.py -v
```

## 6. Optional WebSocket test

Once the final WebSocket route is confirmed, set:

```powershell
$env:FORECAST_WEBSOCKET_URL="ws://localhost:8080/<final-websocket-route>"
```

Then run:

```bash
python -m pytest backend/tests/integration/test_websocket_contract.py -v
```

Without this variable, the test skips rather than failing.

## 7. Optional destructive Redis recovery test

Only use this against your **local development stack**.

PowerShell:

```powershell
.\backend\utilities\run_backend_integration_tests.ps1 -Destructive
```

or:

```powershell
$env:RUN_DESTRUCTIVE_INTEGRATION="1"
python -m pytest backend/tests/integration/test_failure_recovery.py -v
```

The test assumes the Redis Docker Compose service is named `cache`. Change that value in `test_failure_recovery.py` if the final compose configuration uses a different name.

---

# Important notes before the PRs merge

On your current pre-merge branch:

- `/ready` may not exist yet;
- `meta` may not exist yet;
- `fire_probability` may not exist in the local response model;
- final malformed-cache behaviour may differ;
- the final WebSocket route may not yet be known.

Failures caused by those missing features are expected at this stage.

Do **not** weaken the tests simply to make them green before the corresponding features exist. The suite is intended to describe and validate the final merged behaviour.

After the PRs merge, update only assumptions that genuinely changed by team decision, such as:

- final ports
- final WebSocket route
- API key
- Redis service name
- agreed `FORECAST_STALE_AFTER_SECONDS`

---

# Main merge-sensitive areas this suite protects

The final implementation should preserve both:

- **PR #238**
  - malformed cache -> `503`
  - optional `fire_probability`
  - final GeoJSON validation/error semantics

and:

- **PR #250**
  - `live` / `stale` / `unavailable`
  - `meta`
  - timestamp handling
  - stale forecasts remain visible

Likewise, Arsh's security/router/CORS work must coexist with Ashan's health/readiness lifecycle changes in the final service entry points.

The purpose of this suite is to prove those independently developed changes still work together after they are merged.
