from pydantic_settings import BaseSettings

# gets from environment variables (case-insensitive)
class Environment(BaseSettings):
    broker_url: str

    # Shared internal API key. Service-to-service routes require this to be
    # supplied in the X-API-Key header.
    api_key: str

environment = Environment() # type: ignore
