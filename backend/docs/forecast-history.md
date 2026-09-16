# Forecast History

**Status:** Implemented
**Streams affected:** Back-end (producer), Front-end (consumer)
**Related:** docs/fire-risk-map-graceful-degradation.md (the `meta` field this
capability reuses), docs/fire-risk-map-api-contract.md

## Why this exists

Every prediction used to be written to a single Redis key (`predictions`)
and overwritten by the next one. Nothing was persisted. The system had no
memory of what it had previously told anyone.

That matters for two reasons:

- **After-action review.** Once an incident is over, the first question is
  always what information responders actually had at a given moment.
  FireFusion could not answer "what did the dashboard show at 2:47pm" —
  that forecast was long gone by the time anyone asked.
- **Trend, not just snapshot.** Whether a risk area has been escalating or
  easing over the last few hours is often more operationally useful than the
  current reading alone. That needs more than one point in time.

## What was built

- Every prediction is now also written to a `forecast_history` table
  (`utilities/firefusion/forecast-history-init.sql`), in addition to the
  existing Redis cache and WebSocket broadcast — those are unchanged.
- `GET /api/bushfire-forecast/at?timestamp=<iso8601>` replays the forecast
  that was current at a past moment.
- `GET /api/bushfire-forecast/history?from=<iso>&to=<iso>&limit=<n>` returns
  forecasts across a window, newest first — the data source for a time
  slider over recent risk trend.
- A configurable retention period, and a script to enforce it (no scheduler
  is built into the app — see [Retention](#retention) below).

## The `forecast_history` table

```sql
CREATE TABLE forecast_history (
    id BIGSERIAL PRIMARY KEY,
    generated_at TIMESTAMPTZ NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX forecast_history_generated_at_idx ON forecast_history (generated_at DESC);
```

`generated_at` is the same timestamp already written to the
`predictions:generated_at` Redis key by `store_prediction()` — this is not a
second, independent notion of when a forecast was produced. `payload` is the
`type`/`features` FeatureCollection body exactly as served; `meta` (the
freshness metadata described in
docs/fire-risk-map-graceful-degradation.md) is **not** stored. It's computed
fresh at read time against the row's `generated_at`, using the same
classification `fetch_predictions()` uses for the live endpoint — so a
history entry's staleness is always correct relative to when you're actually
looking at it, not frozen at write time.

## Writing to history

`ForecastService.store_prediction()` inserts into `forecast_history`
immediately after writing the Redis cache and the generated-at timestamp,
before the WebSocket broadcast. This is **best-effort**: the insert is
wrapped in its own `try`/`except`, logged with `logger.exception` on failure,
and never re-raised. Serving the current risk picture matters more than
recording it — a database hiccup on the history path must never stop a live
forecast from being cached, broadcast, or served. This mirrors the same
principle applied to the misinformation database fixes in
docs/misinformation-api-reliability.md: a dependency problem must be visible
(logged), but must not degrade what it doesn't need to.

## Endpoints

### `GET /api/bushfire-forecast/at`

Returns the forecast that was current at the given moment: the most recent
recording **at or before** `timestamp`, never a later one.

```
GET /api/bushfire-forecast/at?timestamp=2026-01-21T14:47:00Z
```

```jsonc
{
  "type": "FeatureCollection",
  "features": [
    { "type": "Feature", "geometry": { "...": "..." }, "properties": { "risk_factor": 2 } }
  ],
  "meta": {
    "status": "stale",
    "generated_at": "2026-01-21T14:31:02+00:00",
    "age_seconds": 8452,
    "stale_after_seconds": 900,
    "message": "This forecast is 8452s old and the prediction source has stopped updating. The map still shows the last known risk picture."
  }
}
```

`404` if nothing was recorded that early:

```json
{"detail": "No forecast was recorded at or before 2020-01-01T00:00:00+00:00"}
```

Same `FeatureCollection` shape as `GET /api/bushfire-forecast` — Front-end
reuses its existing rendering unmodified. `meta.status` will almost always
be `stale` for anything genuinely historical (correct: it's being compared
against the same freshness window as a live forecast), but a very recent
timestamp can legitimately come back `live`.

### `GET /api/bushfire-forecast/history`

Returns forecasts recorded in `[from, to]`, newest first.

```
GET /api/bushfire-forecast/history?from=2026-01-21T12:00:00Z&to=2026-01-21T18:00:00Z&limit=50
```

```jsonc
[
  { "type": "FeatureCollection", "features": [ /* ... */ ], "meta": { "status": "stale", "...": "..." } },
  { "type": "FeatureCollection", "features": [ /* ... */ ], "meta": { "status": "stale", "...": "..." } }
]
```

| Parameter | Required | Default | Notes |
|---|---|---|---|
| `from` | yes | — | ISO 8601 |
| `to` | yes | — | ISO 8601 |
| `limit` | no | `100` | max `1000`; a request above the max is rejected with `422`, not silently truncated |

This is what would drive a time slider on the map: fetch the window once,
scrub locally.

## Retention

`forecast_history_retention_days` in `firefusion-api/app/config/config.py`
(default `30`) controls how long rows are kept. Set via the
`FORECAST_HISTORY_RETENTION_DAYS` environment variable.

**No scheduler is built into this service.** Enforcement is a script:

```bash
docker compose exec firefusion-api python -m app.internal.scripts.prune_forecast_history
```

It opens the connection pool, deletes rows with `generated_at` older than
`now() - forecast_history_retention_days`, logs how many were removed, and
closes the pool. Run it periodically from outside the app — host cron or a
Kubernetes CronJob are both fine. Example host cron entry, daily at 03:00:

```cron
0 3 * * * cd /path/to/backend && docker compose exec -T firefusion-api python -m app.internal.scripts.prune_forecast_history >> /var/log/firefusion-prune.log 2>&1
```

Deletion is strict (`generated_at < cutoff`): a row exactly at the cutoff is
kept, not deleted.

## Using the connection pool

`forecast_history_repository.py` uses the shared
`psycopg_pool.AsyncConnectionPool` from `app/internal/repositories/database.py`
(`get_pool()`) — the same pool the misinformation reliability fix
introduced (docs/misinformation-api-reliability.md). No new connections are
opened per query, and nothing here uses synchronous psycopg: a blocking call
inside an `async def` handler stalls the event loop for every other request
the process is handling, which is exactly the defect that pool exists to
avoid repeating.

## Demonstrating it locally

With the stack up (`docker compose --profile default up --build -d` from
`backend/`):

```bash
# Store a prediction through the real pipeline (same path AI Modelling uses)
docker compose exec firefusion-api python3 -c "
import asyncio
from app.internal.services.forecast_service import ForecastService

async def main():
    svc = ForecastService()
    await svc.store_prediction({
        'type': 'FeatureCollection',
        'features': [{'type': 'Feature', 'geometry': {'type': 'Polygon',
            'coordinates': [[[142.156,-37.56],[142.32,-37.74],[142.51,-37.65],[142.38,-37.51],[142.156,-37.56]]]},
            'properties': {'risk_factor': 2}}]
    })

asyncio.run(main())
"

# Note the timestamp, wait, store a different one
sleep 3
docker compose exec firefusion-api python3 -c "... risk_factor: 5 ..."

# Replay the moment before the second one landed
curl -s "localhost:8080/api/bushfire-forecast/at?timestamp=<the noted timestamp>" | python3 -m json.tool

# See the full window
curl -s "localhost:8080/api/bushfire-forecast/history?from=<start>&to=<now>" | python3 -m json.tool
```

## Tests

`tests/test_forecast_history.py` covers: a stored prediction is recorded in
history; a history write failure does not break `store_prediction()`
(verified against real cache/broadcast calls still happening, and the
failure logged at `ERROR`); `/at` returns the forecast current at that
moment rather than the nearest later one (the SQL semantics — `<=` ordered
`DESC` — are locked in with a source-text check, since a mocked repository
can't prove SQL correctness); a timestamp before any recorded forecast
returns `404`; the history window respects `from`, `to` and `limit`, with an
excessive `limit` rejected rather than silently truncated; the response
shape matches the live endpoint's contract (validated by parsing the result
back through the same `FeatureCollection` model); and retention pruning is
strictly-older-than the cutoff, not inclusive.

One `@pytest.mark.integration` test drives the real pipeline end to end
against the running stack: it publishes two predictions through the actual
RabbitMQ `predictions` queue (the same path `MessagingService` consumes in
`main.py`'s lifespan — not a shortcut around it), then confirms `/at` at the
boundary between them replays the first one, not the second, and `/history`
returns both, newest first.
