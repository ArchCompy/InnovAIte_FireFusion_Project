import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import hello
from .internal.services.sql_event_listener import sql_event_listener
from .internal.services.aggregator_service import AggregatorService
from .internal.services.messaging_service import MessagingService


# Manage application-level resources that must be created during startup
# and cleaned up during shutdown.
@asynccontextmanager
async def init_lifespan_objects(app: FastAPI):
    # Keep Kubernetes readiness false until the Aggregator API has
    # successfully initialised its required runtime components.
    app.state.ready = False

    # Establish the messaging connection used by the Aggregator API.
    messaging_service = await MessagingService.create()

    # Initialise the aggregation service with the active messaging service.
    aggregator_service = AggregatorService(messaging_service)

    # Start the SQL event listener as a background task so the application
    # can process database-driven events while continuing to serve requests.
    aggregator_task = asyncio.create_task(
        sql_event_listener(aggregator_service)
    )

    try:
        # Application startup has completed successfully and Kubernetes
        # can now consider this pod ready to receive traffic.
        app.state.ready = True
        yield

    finally:
        # Mark the application as unavailable before shutdown so Kubernetes
        # stops routing new traffic to the terminating pod.
        app.state.ready = False

        # Stop the SQL event listener background task gracefully.
        aggregator_task.cancel()

        try:
            await aggregator_task
        except asyncio.CancelledError:
            pass

        # Cleanly close the messaging connection during shutdown.
        await messaging_service.close()


app = FastAPI(
    title="Aggregator API",
    version="1.0.0",
    lifespan=init_lifespan_objects,
)

# Expose Prometheus-compatible HTTP metrics for platform monitoring.
# The metrics endpoint is intentionally excluded from API documentation
# and from its own request instrumentation to avoid scrape-generated noise.
Instrumentator(
    excluded_handlers=["/metrics"],
).instrument(app).expose(
    app,
    endpoint="/metrics",
    include_in_schema=False,
)

# Kubernetes liveness probe endpoint.
# A successful response confirms that the FastAPI process is running.
@app.get("/health", tags=["Operations"])
async def health():
    return {
        "status": "healthy",
        "service": "aggregator-api",
    }


# Kubernetes readiness probe endpoint.
# Traffic should only be routed to this pod after the Aggregator API
# startup components have been successfully initialised.
@app.get("/ready", tags=["Operations"])
async def ready():
    if not getattr(app.state, "ready", False):
        raise HTTPException(
            status_code=503,
            detail="Aggregator API is not ready",
        )

    return {
        "status": "ready",
        "service": "aggregator-api",
    }


# Register the existing Aggregator API application routes.
app.include_router(hello.router)
