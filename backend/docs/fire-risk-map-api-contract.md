# Fire Risk Map API Contract (Backend to Front-end)

**Status:** Draft for review — revision 3
**Author:** Arsh Dang
**Reviewer:** Viet Quang Nguyen
**Streams affected:** Back-end (producer), Front-end (consumer)
**Sprint 1 foundation:** Goals 2 and 3 — stable APIs for integration and one end-to-end integration.
**Sprint 2 alignment:** Improve Fire Risk Map integration reliability, failure handling and regression protection.
**Sprint 2 update:** Draft PR #238 proposes explicit cache-corruption and WebSocket delivery semantics.

## Scope

This document defines **only the Back-end to Front-end boundary** for the Fire Risk
Map: the single endpoint Front-end calls, and the shape of what it gets back.

It deliberately does **not** define the upstream flow. The Data Engineering to
Back-end to AI Modelling input contract (which Supabase tables feed the model, the
grid and timestamp mapping, and the `POST /predict/bushfire/forecast` request format)
is being worked through separately and tracked in PR #218.

The value of splitting them is that the Front-end boundary can be locked now, while
the upstream pipeline is still being resolved. Front-end builds against this document
and is unaffected by changes behind it.

---

## 1. Endpoint

```
GET /api/bushfire-forecast
```

Served by **firefusion-api** (port 8080). This is the only endpoint Front-end needs
for the Fire Risk Map. Front-end does not call model-api or aggregator-api directly.

No request parameters in Sprint 1. Filtering (by region or time window) is out of
scope and can be added later without breaking this contract.

### Optional live updates

```
WS /api/ws
```

The WebSocket pushes the same validated `FeatureCollection` payload after a new
prediction has been written successfully to Redis. Delivery is best effort: failure
to send to one client is logged, that stale client is removed, and delivery continues
to the remaining clients. A WebSocket delivery failure does not roll back the cached
prediction.

Front-end may use the WebSocket for live refresh, but the Fire Risk Map must continue
to work correctly using the REST endpoint alone.

---

## 2. Response schema

`200 OK`, `Content-Type: application/json`. The body is a GeoJSON
**FeatureCollection**; each feature is a polygon carrying a risk rating.

```jsonc
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[
          [142.1560, -37.5600],
          [142.3200, -37.7400],
          [142.5100, -37.6500],
          [142.3800, -37.5100],
          [142.1560, -37.5600]
        ]]
      },
      "properties": {
        "risk_factor": 2,
        "fire_probability": 0.78
      }
    }
  ]
}
```

### Field definitions

| Field | Type | Required | Notes |
|---|---|---|---|
| `type` | string | yes | Always `"FeatureCollection"` |
| `features` | array | yes | May be empty (`[]`) — see section 4 |
| `features[].type` | string | yes | Always `"Feature"` |
| `features[].geometry.type` | string | yes | `"Polygon"` in Sprint 1 |
| `features[].geometry.coordinates` | array | yes | GeoJSON polygon rings, `[longitude, latitude]` order, first and last position identical |
| `features[].properties.risk_factor` | integer | yes | `1`–`5`. **See the scale below — 1 is the most severe.** |
| `features[].properties.fire_probability` | number | optional | Model confidence/probability, `0.0`–`1.0`. Present when the model supplies it; Front-end must tolerate its absence. |

### `risk_factor` scale

Confirmed with AI Modelling. The Front-end value is the **inverse** of the model's
internal `risk_levels`, so **1 is the most severe**, not the least:

| AI internal `risk_levels` | Front-end `risk_factor` | Meaning |
|---|---|---|
| 4 | **1** | High / extreme |
| 3 | **2** | Medium-high |
| 2 | **3** | Medium |
| 1 | **4** | Medium-low |
| 0 | **5** | Low |

The backend serves the Front-end convention. Front-end does not need to know the
model's internal scale.

### Notes for Front-end

- Coordinate order is **`[longitude, latitude]`**, per the GeoJSON standard. Some map
  libraries (including Leaflet's raw `L.polygon`) expect `[lat, lng]` — check before
  rendering.
- Drive the colour ramp from `risk_factor`, remembering that **low numbers are high
  risk**. The backend does not send colours.
- `fire_probability` is available where the model provides it, for example as an
  opacity or a detail-panel value. Treat it as optional.

---

## 3. Data sources behind the endpoint

The response shape is identical regardless of source, so Front-end never needs to
know which is in use:

1. **Live prediction (target for Sprint 1).** A prediction is produced upstream, the
   backend caches it and serves it here.
2. **Fallback sample data (planned follow-up).** If no live prediction is available,
   the backend serves an agreed sample `FeatureCollection`. **Not implemented yet** —
   the agreed fallback dataset is still to be confirmed with AI Modelling, so today
   the no-data path returns an empty `FeatureCollection` (section 4). Tracked as a
   follow-up task rather than blocking this contract.

---

## 4. Behaviour when data is unavailable

A missing Redis prediction and a corrupted Redis prediction represent different
states. A missing value is a normal no-prediction condition. A present value that
cannot satisfy the API contract is an operational failure and must not be disguised
as normal empty data.

| Situation | Status | Body |
|---|---|---|
| Valid live prediction available | `200` | Valid `FeatureCollection` with features |
| No live prediction, fallback available (planned) | `200` | Valid sample `FeatureCollection` |
| No cached prediction exists | `200` | `{"type": "FeatureCollection", "features": []}` |
| Cached prediction contains malformed JSON | `503` | `{"detail": "Forecast data temporarily unavailable"}` |
| Cached prediction is not a JSON object | `503` | `{"detail": "Forecast data temporarily unavailable"}` |
| Cached prediction violates the GeoJSON schema | `503` | `{"detail": "Forecast data temporarily unavailable"}` |
| Redis is unavailable or times out | `503` | `{"detail": "Forecast data temporarily unavailable"}` |
| Unexpected application failure | `500` | Server error response |

Every successful `200` response contains a valid `FeatureCollection`. The empty
`FeatureCollection` is reserved for the normal condition where no prediction exists.
Corrupted cached data is reported explicitly so operational failures cannot appear to
Front-end as a valid no-risk or no-data result.

Front-end should handle three response states: features present, features empty, and
a non-`200` response.

---

## 5. Confirmed and open points

Confirmed cross-stream contract:

- **`risk_factor` is 1–5 with 1 most severe**, the inverse of the model's internal
  scale (AI Modelling).
- **`risk_factor` alone is sufficient for the Sprint 1 map**, served through
  `GET /api/bushfire-forecast` (Front-end).

Implemented Backend reliability behaviour in Draft PR #238:

- A missing cached prediction returns `200` with an empty `FeatureCollection`.
- A present but malformed or schema-invalid cached prediction returns `503`.
- Incoming predictions are validated before Redis or WebSocket side effects.
- A validated prediction is cached before WebSocket broadcast begins.
- WebSocket delivery is best effort; failed clients are logged and removed without
  rolling back the cached prediction or blocking healthy clients.

Still open:

| # | Question | Who decides |
|---|---|---|
| 1 | Will `fire_probability` be present on every feature, or only some? | AI Modelling |
| 2 | Which sample dataset becomes the agreed fallback | AI Modelling and Back-end |
| 3 | Does Front-end intend to use WebSocket live refresh, or REST only? | Front-end |

---

## 6. Acceptance criteria

- Every successful `GET /api/bushfire-forecast` response is a valid
  `FeatureCollection` matching this contract.
- A missing cached prediction returns `200` with an empty `FeatureCollection`.
- Malformed, non-object or schema-invalid cached predictions return `503`.
- Redis connection failures and timeouts return `503`.
- Unexpected application errors are not misreported as normal no-data or Redis
  failures.
- `risk_factor` values are strict integers in `1`–`5` using the Front-end convention.
- Predictions are validated before they are cached or broadcast.
- Redis cache writes complete before WebSocket broadcast begins.
- Failure to deliver to one WebSocket client is logged and does not prevent delivery
  to healthy clients.
- The endpoint publishes its `200` `FeatureCollection` response schema, and its `503` response is documented in Swagger/OpenAPI.
- Automated tests cover valid data, missing data, corrupted cache data, Redis
  failures, prediction ordering and WebSocket delivery resilience.
- Front-end rendering with live data remains a cross-stream integration validation
  requirement and is not established by Backend unit tests alone.

---

## 7. Related work

- **PR #218** (Tim Trevett) — the wider cross-stream integration: Data Engineering
  models and Aggregator routes, the AI Modelling REST client for
  `POST /predict/bushfire/forecast`, and a shared `store_prediction()` path so the
  RabbitMQ and REST flows share validation, caching and WebSocket broadcast. Changes
  to `forecast_service.py` need coordinating across both branches before merge.
- **Draft PR #238** (Zehong Li) — Sprint 2 Fire Risk Map Backend reliability work:
  strict GeoJSON validation, Redis configuration and timeout handling,
  corrupted-cache semantics, prediction validation and side-effect ordering,
  WebSocket delivery resilience, and automated regression coverage.
