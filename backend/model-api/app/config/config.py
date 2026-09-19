from pydantic_settings import BaseSettings

# gets from environment variables (case-insensitive)
class Environment(BaseSettings):
    broker_url: str

    # Shared internal API key. Service-to-service routes require this to be
    # supplied in the X-API-Key header.
    api_key: str

    # Distributed tracing. Off by default so local development is
    # unaffected unless explicitly enabled. See docs/distributed-tracing.md.
    otel_traces_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "tempo:4317"
    otel_service_name: str = "model-api"

environment = Environment() # type: ignore
