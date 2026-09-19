from pydantic_settings import BaseSettings


# Reads service configuration from environment variables.
# Pydantic environment variable matching is case-insensitive.
class Environment(BaseSettings):
    db_url: str
    broker_url: str
    cache_url: str

    # Internal Backend service used to retrieve prepared DE records.
    aggregator_url: str = "http://aggregator-api:8080"

    # AI Modelling service address.
    #
    # host.docker.internal allows the Docker-based Backend to reach an
    # AI Modelling FastAPI process running directly on the developer's host.
    # This can later be replaced by a container/service URL without changing
    # the client implementation.
    ai_modelling_url: str = "http://host.docker.internal:8090"

    # Comma separated list of browser origins permitted to call this service.
    # Defaults to local development origins. Set CORS_ALLOWED_ORIGINS in any
    # deployed environment to the dashboard's real origin.
    cors_allowed_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    @property
    def allowed_origins(self) -> list[str]:
        """Parse the configured origins into a list."""
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


environment = Environment()  # type: ignore