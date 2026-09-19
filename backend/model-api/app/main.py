from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from .routers.model_router import router as model_router
from .internal.services.messaging_service import MessagingService
from .internal.services.model_service import ModelService
from .config.config import environment
from shared.tracing import setup_tracing


@asynccontextmanager
async def init_lifespan_object(app: FastAPI):
    # Kubernetes readiness remains false while the Model API is
    # initialising its messaging and model-processing components.
    app.state.ready = False

    # Establish the RabbitMQ messaging connection required by the
    # Model API for receiving data and publishing predictions.
    messaging_service = await MessagingService.create()

    try:
        # Initialise the model service with the active messaging service.
        model_service = ModelService(messaging_service)

        # Start consuming incoming data so that predictions can be
        # generated and published through the messaging layer.
        await messaging_service.consume_data(
            model_service.consume_data_publish_prediction
        )

        # Startup dependencies have been initialised successfully.
        # Kubernetes can now consider this application instance ready.
        app.state.ready = True
        yield

    finally:
        # Mark the application as unavailable before shutting down so
        # Kubernetes does not route new traffic to a terminating pod.
        app.state.ready = False

        # Cleanly close the messaging connection during application shutdown.
        await messaging_service.close()


app = FastAPI(
    title="Model API",
    version="1.0.0",
    lifespan=init_lifespan_object,
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
# A successful response confirms that the FastAPI process is operational.
@app.get("/health", tags=["Operations"])
async def health():
    return {
        "status": "healthy",
        "service": "model-api",
    }


# Kubernetes readiness probe endpoint.
# The pod should receive traffic only after the Model API startup
# dependencies have been successfully initialised.
@app.get("/ready", tags=["Operations"])
async def ready():
    if not getattr(app.state, "ready", False):
        raise HTTPException(
            status_code=503,
            detail="Model API is not ready",
        )

    return {
        "status": "ready",
        "service": "model-api",
    }


# Register the existing Model API application routes.
app.include_router(model_router)