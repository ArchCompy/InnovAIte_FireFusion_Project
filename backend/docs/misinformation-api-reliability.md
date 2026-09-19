# Misinformation API Reliability

**Status:** Implemented
**Streams affected:** Back-end
**Related:** docs/fire-risk-map-graceful-degradation.md (same principle applied
to a different failure mode: don't let a dependency problem look like normal
operation)

## The problems

### Defect 1: blocking the event loop

The routers in `app/routers/misinformation_controller.py` are `async def`,
but `app/internal/services/misinformation_service.py` and
`app/internal/repositories/misinformation_repository.py` were fully
synchronous and called `psycopg.connect()` directly.

FastAPI runs an `async def` handler's body on the event loop. A blocking
call inside it — a synchronous `psycopg.connect()` and query — runs
in-line and never yields, so it doesn't just block that one request: it
stalls the single-threaded event loop for every other request the process
is handling at the same time, including `GET /api/bushfire-forecast` and
the `/api/ws` WebSocket. A burst of misinformation traffic during an
incident degraded the fire risk map at the exact moment responders needed
it most.

The repository also opened a new connection per query — seven separate
`psycopg.connect()` call sites, each paying a TCP connect and an auth
handshake, on every single request.

### Defect 2: an outage looks like an empty result

Every service method did:

```python
except Exception as e:
    print(e)
    return []
```

A database outage and a genuine "nothing to report" both produced the same
`200 []` (or `None`/`404` for a single record). During an incident, a
backend that can't reach the database would show "no misinformation
detected" on the dashboard — indistinguishable from an actually quiet
narrative landscape. `print()` also bypasses logging entirely, so the
failure wasn't even visible in the service's logs.

## Behaviour

| Situation | Before | After |
|---|---|---|
| Misinformation query running | Blocks the event loop; forecast/WebSocket stall too | Runs on the pool via `async`; other requests are unaffected |
| Seven queries, seven requests | Seven separate `psycopg.connect()` handshakes | Reused connections from one shared pool |
| Database unreachable, list endpoint | `200 []` — looks like no misinformation | `503`, `MisinformationUnavailableError`, logged at `ERROR` |
| Database unreachable, single-record endpoint | `404` — looks like the record doesn't exist | `503` |
| Table genuinely empty | `200 []` | `200 []` — unchanged |
| Record genuinely missing | `404` | `404` — unchanged |
| Failure detail | `print(e)`, not logged | `logger.exception(...)`, `ERROR` level, full traceback |

The two behaviours that must not change — a genuine empty list, and a
genuine missing record — are unchanged. Only the outage case changed, from
looking identical to "nothing to report" to being reported as what it is.

## Configuration

Added to `firefusion-api/app/config/config.py`:

| Variable | Default | Notes |
|---|---|---|
| `DB_POOL_MIN_SIZE` | `2` | Connections the pool keeps open even when idle |
| `DB_POOL_MAX_SIZE` | `10` | Ceiling on connections this service instance holds |
| `DB_POOL_TIMEOUT_SECONDS` | `10.0` | How long a request waits for a pool connection before raising, which the service turns into a `503` |

**`DB_POOL_MAX_SIZE` times the number of running replicas of this service
must stay under PostgreSQL's `max_connections`.** Each replica opens its own
pool; a deployment that scales this service to, say, 5 replicas at the
default `max_size=10` can hold up to 50 connections against the database
from this service alone, before counting `aggregator-api` or any other
consumer. Size `max_connections` (or lower `DB_POOL_MAX_SIZE`) accordingly
before scaling replicas.

## How this is implemented

- `app/internal/repositories/database.py` owns a single shared
  `psycopg_pool.AsyncConnectionPool`: `open_pool()`, `close_pool()`,
  `get_pool()`. `get_pool()` raises a clear `RuntimeError` if called before
  `open_pool()` has run, rather than silently opening a fresh pool.
  `open_pool()` opens non-blocking (`wait=False`, the default): a database
  outage at boot does not stop the rest of the service — forecast, WebSocket
  — from starting.
- `app/main.py`'s lifespan opens the pool before the messaging service
  starts, and closes it after the messaging service closes.
- `misinformation_repository.py` is now `async`, using
  `async with pool.connection()` and
  `conn.cursor(row_factory=class_row(...))`. The repeated fetch-all and
  fetch-one logic (previously copy-pasted seven times) is factored into two
  module-level helpers, `_fetch_all` and `_fetch_one`.
- `misinformation_service.py` methods are `async` and `await` the
  repository. A `MisinformationUnavailableError` is raised on failure,
  logged with `logger.exception` (full traceback, `ERROR` level) at the
  point the original exception is caught.
- `misinformation_controller.py` awaits the service and translates
  `MisinformationUnavailableError` into `HTTPException(503, ...)`. The
  existing `404` behaviour for a missing single record is unchanged.
- The aggregator service already used `psycopg.AsyncConnection` per call
  (not a pool, but already async); this change makes the misinformation
  path consistent with that precedent rather than the outlier.

## Reproduction

With the stack up (`docker compose --profile default up --build -d` from
`backend/`):

```bash
# Baseline: idle forecast latency
for i in 1 2 3 4 5; do curl -s -o /dev/null -w '%{time_total}\n' localhost:8080/api/bushfire-forecast; done

# Fire 20 concurrent misinformation requests, then immediately hit forecast
for i in $(seq 1 20); do curl -s -o /dev/null localhost:8080/api/misinformation/posts & done
curl -s -o /dev/null -w '%{time_total}\n' localhost:8080/api/bushfire-forecast
wait
```

Before the fix, the forecast call issued while the 20 misinformation
requests are in flight measurably stalls, because it queues behind them on
the event loop. After the fix, it should complete close to the idle
baseline regardless of concurrent misinformation load.

To reproduce the outage-visibility defect, point `DB_URL` at an unreachable
host (or stop `relational-db`) and call any misinformation endpoint: before
the fix this returned `200 []`; after, it returns `503` with a body naming
the outage, and the failure appears in the service logs at `ERROR`.

**Recovery after a database restart:** when `relational-db` is restarted
(rather than left unreachable), every connection already held by the pool is
poisoned at once. The pool detects each bad connection as it's next used,
logs `discarding closed connection`, and opens a replacement — this took
roughly 5-10s to fully stabilize in local testing (a handful of `503`
responses, then back to `200`). This is standard connection-pool recovery
behaviour, not specific to this fix; a request that lands in that window
still gets a correct `503` rather than a wrong answer.

## Tests

`tests/test_misinformation_reliability.py` covers:

- every public `MisinformationService` and `MisinformationRepository` method
  is a coroutine function
- the repository source no longer contains `psycopg.connect(` and does read
  from the shared pool
- a repository failure raises `MisinformationUnavailableError`, for every
  method, rather than returning `[]`/`None`
- a genuine empty table still returns `[]`, and a genuine missing record
  still returns `None`
- a failure is logged at `ERROR` level and never printed to stdout
- `@pytest.mark.integration`: fires 20 concurrent `/api/misinformation/posts`
  requests against the running stack and asserts `/api/bushfire-forecast`
  latency during that window stays close to its idle baseline
