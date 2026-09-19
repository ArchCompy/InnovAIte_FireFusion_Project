"""Tests for distributed tracing (shared/tracing.py).

Exercises the real shared tracing module used identically by all three
services. See docs/distributed-tracing.md.

Skip if OpenTelemetry dependencies are not installed locally. CI installs
them via requirements-test.txt, so these run there.
"""
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "firefusion-api"


@pytest.fixture
def tracing_module():
    """Import the real shared.tracing module (used identically by all three services)."""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    try:
        from shared import tracing
    except Exception as exc:
        pytest.skip(f"opentelemetry dependencies unavailable locally: {exc}")
    return tracing


@pytest.fixture
def config_module(monkeypatch):
    """Import firefusion-api's config module; its Environment requires these."""
    if str(APP_DIR) not in sys.path:
        sys.path.insert(0, str(APP_DIR))
    monkeypatch.setenv("CACHE_URL", "redis://localhost:6379")
    monkeypatch.setenv("DB_URL", "postgresql://localhost/unused")
    monkeypatch.setenv("BROKER_URL", "amqp://localhost/unused")
    try:
        from app.config import config
    except Exception as exc:
        pytest.skip(f"config dependencies unavailable locally: {exc}")
    return config


# --- tracing is off by default ---

def test_tracing_disabled_by_default(config_module):
    assert config_module.Environment().otel_traces_enabled is False


def test_otel_traces_enabled_env_var_turns_it_on(config_module, monkeypatch):
    monkeypatch.setenv("OTEL_TRACES_ENABLED", "true")
    assert config_module.Environment().otel_traces_enabled is True


# --- the app works normally without an OTLP endpoint when disabled ---

def test_setup_tracing_is_a_noop_when_disabled(tracing_module):
    """No OTLP endpoint needed, and the app must work unaffected."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    # A deliberately bogus endpoint: must not matter, since tracing is
    # disabled and setup_tracing must return before ever touching it.
    tracing_module.setup_tracing(
        app, "test-service", enabled=False, otlp_endpoint="unreachable:4317"
    )

    with TestClient(app) as client:
        response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_helpers_are_safe_with_no_tracer_configured(tracing_module):
    """inject/start_consumer_span/set_span_attributes must never raise,
    whether or not a real TracerProvider has been installed - every
    service calls these unconditionally regardless of OTEL_TRACES_ENABLED.
    """
    headers = tracing_module.inject_trace_context({"existing": "header"})
    assert headers["existing"] == "header"

    with tracing_module.start_consumer_span("noop consume", None):
        pass

    tracing_module.set_span_attributes({"forecast.feature_count": 3})


# --- when enabled: a request produces a span, and trace context survives a
# round trip through simulated RabbitMQ message headers. One test: OTel's
# global TracerProvider can only be installed once per process, so
# setup_tracing(enabled=True) can only run once across this whole session. ---

def test_enabled_tracing_produces_spans_and_survives_rabbitmq_round_trip(tracing_module):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from opentelemetry import trace
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    # Port 1: guaranteed nothing is listening. Proves the collector-
    # unreachable constraint too - tracing enabled, endpoint unreachable,
    # the request must still succeed.
    tracing_module.setup_tracing(
        app, "test-service", enabled=True, otlp_endpoint="127.0.0.1:1"
    )

    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))

    # --- a request produces a span ---
    with TestClient(app) as client:
        response = client.get("/ping")

    assert response.status_code == 200, (
        "an unreachable OTLP collector must not break the request path"
    )

    request_spans = exporter.get_finished_spans()
    assert len(request_spans) >= 1, "FastAPI instrumentation must produce a span for a request"

    exporter.clear()

    # --- trace context survives a round trip through RabbitMQ message headers ---
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("producer.publish") as producer_span:
        producer_ctx = producer_span.get_span_context()
        headers = tracing_module.inject_trace_context()

    assert "traceparent" in headers, "a W3C traceparent header must be injected"
    assert headers["traceparent"].startswith("00-"), "must be the W3C traceparent format"
    assert f"{producer_ctx.trace_id:032x}" in headers["traceparent"]

    with tracing_module.start_consumer_span("consumer.consume", headers) as consumer_span:
        consumer_ctx = consumer_span.get_span_context()

    assert consumer_ctx.trace_id == producer_ctx.trace_id, (
        "the consumer span must join the producer's trace, not start a new, "
        "disconnected one"
    )

    finished = exporter.get_finished_spans()
    consumer_finished = next(s for s in finished if s.name == "consumer.consume")
    assert consumer_finished.parent is not None
    assert consumer_finished.parent.span_id == producer_ctx.span_id, (
        "the consumer span must be a direct child of the producer's span"
    )
