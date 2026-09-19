"""Shared OpenTelemetry setup for FireFusion's three FastAPI services.

Keeps tracing configuration identical across firefusion-api, aggregator-api
and model-api rather than each service wiring its own. See
docs/distributed-tracing.md.

Tracing is off by default (OTEL_TRACES_ENABLED unset/false) so local
development is unaffected unless explicitly enabled, and it must never break
the request path: span export runs on BatchSpanProcessor's background
thread, so a collector that is unreachable is retried and dropped there, not
raised into request handling. setup_tracing() additionally catches any
unexpected setup failure itself, logs it, and leaves the service running
untraced rather than failing to start.

aio_pika has no reliable auto-instrumentation, so trace context is carried
across the RabbitMQ boundary explicitly: inject_trace_context() on publish,
start_consumer_span() on consume, using the W3C traceparent format.
"""
import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import SpanKind

logger = logging.getLogger(__name__)


def setup_tracing(
    app: FastAPI,
    service_name: str,
    *,
    enabled: bool,
    otlp_endpoint: str,
    instrument_db: bool = False,
    instrument_cache: bool = False,
) -> None:
    """Configure OpenTelemetry tracing for one service, if enabled.

    Safe to call unconditionally regardless of environment: a no-op when
    enabled is False, and any failure while setting up degrades to
    untraced rather than raising, so a tracing misconfiguration can never
    stop a service from starting.
    """
    if not enabled:
        return

    try:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.propagate import set_global_textmap
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

        resource = Resource.create({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)
        # insecure=True: Tempo's OTLP receiver in this stack has no TLS,
        # matching Loki/Prometheus, which are also plain HTTP internally.
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Explicit rather than relying on the SDK default, since the
        # RabbitMQ propagation below depends on this exact format.
        set_global_textmap(TraceContextTextMapPropagator())

        FastAPIInstrumentor.instrument_app(app)

        # Injects trace_id/span_id into every log record's format string,
        # so a Loki log line can be linked to its trace in Tempo.
        LoggingInstrumentor().instrument(set_logging_format=True)

        if instrument_db:
            from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
            PsycopgInstrumentor().instrument()

        if instrument_cache:
            from opentelemetry.instrumentation.redis import RedisInstrumentor
            RedisInstrumentor().instrument()

        logger.info(
            "OpenTelemetry tracing enabled for %s, exporting to %s",
            service_name,
            otlp_endpoint,
        )
    except Exception:
        logger.exception(
            "Failed to set up OpenTelemetry tracing for %s; continuing untraced",
            service_name,
        )


def inject_trace_context(headers: dict | None = None) -> dict:
    """W3C traceparent header(s) for an outgoing aio_pika message.

    Safe to call whether or not tracing is enabled: with no tracer
    configured this is a no-op and the headers are returned unchanged.
    """
    headers = dict(headers or {})
    inject(headers)
    return headers


def start_consumer_span(name: str, headers: dict | None, **attributes):
    """Start a span for an incoming aio_pika message.

    Extracts the producer's W3C traceparent from the message headers so the
    new span is a child of the producer's span, in the same trace, rather
    than starting a disconnected one. Returns a context manager; safe to use
    whether or not tracing is enabled (a no-op span with no tracer
    configured).
    """
    ctx = extract(headers or {})
    tracer = trace.get_tracer(__name__)
    return tracer.start_as_current_span(
        name, context=ctx, kind=SpanKind.CONSUMER, attributes=attributes
    )


def set_span_attributes(attributes: dict) -> None:
    """Attach attributes to the current span.

    Takes a dict (rather than **kwargs) since span attribute names are
    dotted (e.g. "forecast.feature_count") and so aren't valid Python
    identifiers. Never pass the GeoJSON payload itself, only scalars that
    describe it (feature count, status, whether it came from cache).
    """
    span = trace.get_current_span()
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)
