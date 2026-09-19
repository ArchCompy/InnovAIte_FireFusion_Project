# Distributed Tracing

**Status:** Implemented
**Streams affected:** Back-end (all three services), DevOps/observability
**Related:** docs/misinformation-api-reliability.md (the connection pool this
reuses), docs/forecast-history.md (the path most of the example trace covers)

## The problem

A prediction flows `aggregator-api` &rarr; RabbitMQ (`forecast` queue)
&rarr; `model-api` &rarr; RabbitMQ (`predictions` queue) &rarr;
`firefusion-api` &rarr; the WebSocket. Each of those four hops wrote to its
own logs, with no shared identifier connecting them. The observability
platform (Prometheus, Grafana, Loki, Alloy) in `infrastructure/observability/`
could show that a service was slow, but never where in that chain the time
actually went — a slow request in `firefusion-api` looked identical whether
the delay was its own database, model-api's inference, or the RabbitMQ hop
in between.

## What was built

- OpenTelemetry instrumentation in all three services, configured through
  one shared module (`backend/shared/tracing.py`) rather than each service
  wiring its own setup.
- Trace context is carried across both RabbitMQ hops explicitly (aio_pika
  has no reliable auto-instrumentation), using the W3C `traceparent` format,
  so a single trace connects all three services rather than three
  disconnected ones.
- Span attributes on the forecast path: feature count, freshness status,
  whether the response came from cache — never the GeoJSON payload itself.
- Grafana Tempo as the tracing backend, added to
  `infrastructure/observability/` following the existing `prometheus/` and
  `loki/` Kustomize conventions, wired into Grafana as a datasource.
- Trace IDs in application log output, and a Loki→Tempo `derivedFields`
  link in the Grafana datasource, so a log line in Loki can jump straight
  to its trace in Tempo.
- Off by default everywhere. Enabling it is one environment variable.

## Enabling it

**Locally (docker compose):**

```bash
OTEL_TRACES_ENABLED=true docker compose --profile default up -d
```

A local Tempo instance (`utilities/tempo/tempo.yaml`) is part of the compose
stack for this purpose — see [Viewing a trace locally](#viewing-a-trace-locally)
below. It is not part of the deployed platform (that's
`infrastructure/observability/tempo/`); it exists so tracing can be
demonstrated and debugged without a Kubernetes cluster.

**Deployed:** set `OTEL_TRACES_ENABLED=true` and
`OTEL_EXPORTER_OTLP_ENDPOINT=tempo.monitoring.svc.cluster.local:4317` (or
your Tempo Service's DNS name) on each service's deployment.

## Configuration

Each service's `app/config/config.py` carries the same three fields
(defaults are identical everywhere; `OTEL_SERVICE_NAME` is set per service
in `docker-compose.yaml` and should be set per deployment the same way):

| Variable | Default | Notes |
|---|---|---|
| `OTEL_TRACES_ENABLED` | `false` | Off by default so local development is unaffected unless explicitly enabled |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `tempo:4317` | OTLP gRPC endpoint. Configurable per environment |
| `OTEL_SERVICE_NAME` | `firefusion-api` / `aggregator-api` / `model-api` | Identifies the service in Tempo/Grafana |

## Never breaks the request path

- **Disabled is a true no-op.** `setup_tracing()` returns before importing
  or touching anything OpenTelemetry-related when `OTEL_TRACES_ENABLED` is
  false. No OTLP endpoint needs to exist.
- **Setup failures degrade, they don't crash.** The body of `setup_tracing()`
  is wrapped in its own `try`/`except`: a misconfiguration is logged and the
  service starts up untraced, rather than failing to start.
- **Export is asynchronous.** Spans are sent via `BatchSpanProcessor` on a
  background thread. A collector that is unreachable is retried and
  eventually dropped there — it is never raised into request handling.
  `tests/test_tracing.py` proves this directly: it points a fully-enabled
  tracer at `127.0.0.1:1` (nothing is listening there) and asserts the
  request still returns `200`.
- **The RabbitMQ helpers are always safe to call.** `inject_trace_context()`
  and `start_consumer_span()` use only `opentelemetry-api` (always
  installed, always safe without an SDK configured) — every publish/consume
  call site uses them unconditionally, whether or not tracing is enabled.

## Span attributes on the forecast path

Set via `set_span_attributes()` in `forecast_service.py`, on
`fetch_predictions()`, `get_forecast_at()`, `get_forecast_history()` and
`store_prediction()`:

| Attribute | Meaning |
|---|---|
| `forecast.feature_count` | Number of GeoJSON features in the response (or the total across a `/history` window) |
| `forecast.status` | `live` / `stale` / `unavailable` — the same value as the response's `meta.status` |
| `forecast.from_cache` | `true` for the live endpoint (Redis-backed), `false` for `/at` and `/history` (Postgres-backed) |
| `forecast.entry_count` | `/history` only — number of entries returned |

Only scalars. The GeoJSON payload itself is never attached to a span.

## Propagating trace context across RabbitMQ

aio_pika has no reliable auto-instrumentation, so this is explicit at every
publish and consume site, using `shared/tracing.py`:

- `inject_trace_context()` — called when publishing, returns a headers dict
  carrying the current span's context as a W3C `traceparent`.
- `start_consumer_span(name, headers)` — called when consuming, extracts
  that `traceparent` from the incoming message's headers and starts a new
  span as its child, so the trace continues rather than starting over.

Applied at both hops:

- `aggregator-api`: `AggregatorService.handle_events_update()` opens the
  trace's root span (`kind=PRODUCER`) — this is where a prediction's trace
  actually begins, since it's triggered by a Postgres `NOTIFY`, not an HTTP
  request, so there is no ambient span to attach to otherwise.
  `MessagingService.publish_to_forecast_model()` injects it into the
  `forecast` queue message headers.
- `model-api`: `ModelService.consume_data_publish_prediction()` extracts
  that context and opens a consumer span around the whole handler,
  including the `predictions` queue message it goes on to publish — so
  `MessagingService.publish_prediction()`'s injection picks up *this* span
  as its parent, carrying the chain forward.
- `firefusion-api`: `ForecastService.on_prediction_message()` extracts the
  `predictions` queue message's context and opens a consumer span around
  `store_prediction()`.

The result: one trace, `aggregator.handle_events_update` as its root, with
`forecast queue consume` (model-api) and `predictions queue consume`
(firefusion-api) nested underneath, in the order the work actually happened.

## Viewing a trace locally

With the stack up and tracing enabled:

```bash
OTEL_TRACES_ENABLED=true docker compose --profile default up -d
```

Trigger a prediction through the real pipeline — the same Postgres
`LISTEN`/`NOTIFY` `sql_event_listener` in aggregator-api already listens
for:

```bash
docker compose exec relational-db psql -U postgres -d postgres \
  -c "NOTIFY fire_events_channel, 'demo';"
```

Find the trace (Tempo's HTTP API is exposed on `localhost:3200` in the local
compose stack):

```bash
curl -s "localhost:3200/api/search?tags=service.name%3Daggregator-api&limit=5" | python3 -m json.tool
curl -s "localhost:3200/api/traces/<traceID>" | python3 -m json.tool
```

In a deployed environment with Grafana, open the Tempo datasource (or
follow a `TraceID` link from a Loki log line) and search the same way from
the UI.

## Following one prediction end to end

Triggering the `NOTIFY` above and fetching the resulting trace produces
exactly this span tree:

```
[aggregator-api]  aggregator.handle_events_update            38.2ms
  [aggregator-api]  SELECT (fire_events_full)                12.9ms
  [model-api]       forecast queue consume                    6.3ms
    [firefusion-api]  predictions queue consume               16.0ms
                         forecast.feature_count=1
                         forecast.status=live
                         forecast.from_cache=false
      [firefusion-api]  SET (Redis: predictions)                8.1ms
      [firefusion-api]  SET (Redis: predictions:generated_at)   0.2ms
      [firefusion-api]  INSERT (forecast_history)                3.1ms
```

Reading this: aggregator-api's Postgres query and RabbitMQ hand-off to
model-api account for most of the visible time; firefusion-api's own work
(cache writes, `forecast_history` insert) is fast. The `forecast.*`
attributes on `predictions queue consume` show, without opening the
payload, that this was a one-feature forecast served live. Before this,
none of these five operations were visibly connected — each was a separate
log line in a separate service.

**Log correlation:** the same request also produced this log line in
firefusion-api (from a `predictions:generated_at` deleted just before, to
force the stale path):

```
2026-09-16 07:37:17,274 WARNING [app.internal.services.forecast_service] [forecast_service.py:278] [trace_id=aae115337958799ccc3f98567e0ac4c0 span_id=91a9b9e3b005e361 ...] - Serving stale forecast (age_seconds=None)
```

`trace_id=aae115337958799ccc3f98567e0ac4c0` is directly queryable in Tempo
(`GET /api/traces/aae115337958799ccc3f98567e0ac4c0`) and resolves to the
`GET /api/bushfire-forecast` request that produced it — in Grafana, this is
the same jump the Loki `derivedFields` link makes automatically from the
log line itself.

## Infrastructure

`infrastructure/observability/tempo/` (`configmap.yaml`, `deployment.yaml`,
`service.yaml`, `kustomization.yaml`) follows the same structure as
`prometheus/` and `loki/`: single-binary Tempo, local filesystem storage,
`monitoring` namespace, `app.kubernetes.io/part-of: firefusion-platform`
labels. Added to the top-level `infrastructure/observability/kustomization.yaml`.

`infrastructure/observability/grafana/datasource.yaml` gained a `Tempo`
datasource (`http://tempo.monitoring.svc.cluster.local:3200`) and a
`derivedFields` entry on the `Loki` datasource matching `trace_id=(\w+)` in
log lines and linking to it.

## Tests

`tests/test_tracing.py` covers: tracing is off by default and a request
works normally with no OTLP endpoint configured; the `inject`/
`start_consumer_span`/`set_span_attributes` helpers are safe to call with no
tracer configured (every publish/consume site calls them unconditionally);
and — in the one test that actually enables tracing, since OpenTelemetry's
global `TracerProvider` can only be installed once per process — a request
produces a span, an unreachable collector does not break the request, and
trace context survives a round trip through simulated `aio_pika` message
headers so the consumer span is a genuine child of the producer's rather
than a new, disconnected trace.
