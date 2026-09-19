"""API key authentication for model-api.

Matches the implementation used by aggregator-api so the services enforce
authentication the same way. Applied to the model-api routes in
app/routers/model_router.py.
"""
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

from ...config.config import environment

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Reject the request unless a valid X-API-Key header is present."""
    if not api_key or api_key != environment.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True
