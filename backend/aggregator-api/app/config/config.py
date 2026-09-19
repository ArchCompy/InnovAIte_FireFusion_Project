from pydantic_settings import BaseSettings

# gets from environment variables (case-insensitive)
class Environment(BaseSettings):
    relational_db_url: str
    broker_url: str
    api_key: str

    # Distributed tracing. Off by default so local development is
    # unaffected unless explicitly enabled. See docs/distributed-tracing.md.
    otel_traces_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "tempo:4317"
    otel_service_name: str = "aggregator-api"

environment = Environment() # type: ignore