# Fire Risk Map: Graceful Degradation

**Status:** Implemented
**Streams affected:** Back-end (producer), Front-end (consumer)
**Related:** docs/fire-risk-map-api-contract.md

## The problem

FireFusion is a decision support tool for emergency services during an active
bushfire. `GET /api/bushfire-forecast` depends on the AI Modelling prediction
flow, which depends on the Data Engineering pipeline. If either stops
producing new predictions, the endpoint previously kept serving whatever was
last cached until the cache entry itself expired or was cleared, at which
point it fell back to an empty `FeatureCollection` — the dashboard map goes
blank.

During an incident, a blank map is worse than an old one: it removes the
responder's last known risk picture entirely. But silently serving old data
is also unsafe, because nobody looking at the map can tell a five minute old
forecast from a five hour old one.

The fix is to keep serving the last known good forecast when the prediction
source stops updating, and say how old it is, so the map can render the risk
picture and warn the user in the same view.

## Behaviour

| Situation | `meta.status` | `features` | Notes |
|---|---|---|---|
| Forecast within the freshness window | `live` | served | normal |
| Forecast older than the window | `stale` | still served | data is never dropped for being old |
| No forecast ever received | `unavailable` | empty | nothing to fall back to |
| Forecast age unknown | `stale` | served | never reported as `live` |
| Cache itself unavailable | — | — | raises, router returns `503` |

The last row matters most: **overstating freshness is the dangerous error**
for an emergency tool. If the age of a forecast cannot be determined — the
timestamp key is missing, unreadable, or absent — it is always reported
`stale`, never `live`. A cache failure is different in kind from a stale
forecast: there is no last-known-good response to serve, so it is not
degraded — it raises, and the router turns it into a `503` as before.

A cached value that is present but unusable (not valid JSON, not an object,
or not matching the GeoJSON schema) is **not** degraded to `unavailable`. That
would show a blank map as if there were simply nothing to report, when in fact
the stored forecast is damaged. `fetch_predictions()` raises
`ForecastCacheCorruptionError` and the router returns `503`, the same as a
cache outage. Only a genuinely *missing* key means "no forecast yet", and
that is the one case that returns `unavailable`.

## Response shape

`meta` is additive and optional. It is included whenever `fetch_predictions()`
or the WebSocket broadcast produce a response; a client that only reads
`type` and `features` is unaffected either way.

```jsonc
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Polygon", "coordinates": [ /* ... */ ] },
      "properties": { "risk_factor": 2, "fire_probability": 0.78 }
    }
  ],
  "meta": {
    "status": "stale",
    "generated_at": "2026-09-13T02:10:04.512983+00:00",
    "age_seconds": 1834,
    "stale_after_seconds": 900,
    "message": "This forecast is 1834s old and the prediction source has stopped updating. The map still shows the last known risk picture."
  }
}
```

| Field | Type | Present when | Notes |
|---|---|---|---|
| `meta.status` | string | always, when `meta` is present | `"live"`, `"stale"`, or `"unavailable"` |
| `meta.generated_at` | string (ISO 8601 UTC) | forecast age is known | when to stop trusting it is left to `age_seconds` / `stale_after_seconds`, not to comparing this against wall clock time on the client |
| `meta.age_seconds` | integer | forecast age is known | omitted (not `null`, not `0`) when unknown |
| `meta.stale_after_seconds` | integer | always, when `meta` is present | the freshness window this forecast was classified against |
| `meta.message` | string | `stale` or `unavailable` | written to be shown to the user as-is |

Fields that don't apply to the current status are omitted entirely rather
than sent as `null` — this is `model_dump(exclude_none=True)` on
`ForecastMeta`, the same pattern already used for the rest of the response.

### What Front-end should do with `meta.status`

- **`live`** — render normally. No warning needed.
- **`stale`** — render the polygons as usual; the risk picture is still the
  best available. Show `meta.message` (or a banner built from `age_seconds`)
  so the responder knows they're looking at data that stopped updating,
  rather than assuming it's current.
- **`unavailable`** — `features` will be empty; there's nothing to render.
  `meta.message` explains why.
- A response with no `meta` key at all (older cached client, or a payload
  that predates this change) should be treated the same as `live` — this is
  the additive/back-compat guarantee.

The WebSocket channel (`WS /api/ws`) pushes the identical shape: a freshly
stored prediction is broadcast with `meta.status = "live"` and
`meta.age_seconds = 0`, so Front-end does not need separate handling for the
push and REST paths.

## Configuration

`forecast_stale_after_seconds` in `firefusion-api/app/config/config.py`
(default `900`, i.e. 15 minutes) is the freshness window a served forecast is
classified against. Set via the `FORECAST_STALE_AFTER_SECONDS` environment
variable in any environment where the default doesn't fit. It should be set
to match the AI Modelling prediction cadence once that cadence is confirmed —
900s is a placeholder in the meantime, not a value confirmed with AI
Modelling.

## How this is implemented

- `ForecastStatus` (`live` / `stale` / `unavailable`) and `ForecastMeta` live
  in `firefusion-api/app/internal/models/forecast_status.py`.
- `FeatureCollection` (`internal/models/geojson.py`) carries an optional
  `meta: ForecastMeta | None = None`.
- `ForecastService.store_prediction()` (`internal/services/forecast_service.py`)
  writes the prediction to the `predictions` cache key as before, and now
  also writes the current UTC timestamp to `predictions:generated_at`. The
  WebSocket broadcast carries `meta` with `status="live"`, `age_seconds=0`.
- `ForecastService.fetch_predictions()` reads both keys, classifies freshness
  against `forecast_stale_after_seconds`, and attaches `meta` to the response.
  A cache exception is not caught here, so it still propagates to the router's
  existing `503` handling.

## Demonstrating it locally

With the stack up (`docker compose --profile default up --build -d` from
`backend/`) and at least one prediction already stored:

```bash
# confirm it's live
curl -s localhost:8080/api/bushfire-forecast | python3 -m json.tool

# delete the timestamp key only — the forecast itself is untouched
docker compose exec cache redis-cli DEL predictions:generated_at

# the same polygons are still served, now tagged stale
curl -s localhost:8080/api/bushfire-forecast | python3 -m json.tool
```

The second call's `features` array is unchanged; `meta.status` changes from
`"live"` to `"stale"`, `meta.age_seconds` is absent, and `meta.message`
explains why. This is the "age unknown" row of the behaviour table: the
forecast itself was never lost, only its freshness became unknowable, and the
map keeps showing it rather than going blank.

## Tests

`tests/test_graceful_degradation.py` covers every row of the behaviour table
against the real `ForecastService` with `cache_client` and `ws_manager`
mocked: a fresh forecast is `live`; a forecast past the window is `stale` and
still carries its features; no forecast ever received is `unavailable` with
empty features; a missing or unparsable timestamp is `stale`, never `live`;
a cache failure still raises rather than degrading. It also asserts
`store_prediction()` writes `predictions:generated_at`, that the broadcast
payload carries the same `meta` shape as the REST response, and that
`meta` is omitted entirely (not sent as `null`) when unset.
