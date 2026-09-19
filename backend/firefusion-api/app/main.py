from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.middleware.cors import CORSMiddleware

from app.routers import forecast, hello, misinformation_controller
from .internal.services.forecast_service import ForecastService
from .internal.services.messaging_service import MessagingService


@asynccontextmanager
async def init_lifespan_objects(app: FastAPI):
    # Kubernetes readiness must remain false until the application's
    # required startup dependencies have been successfully initialised.
    app.state.ready = False

    # Initialise the messaging connection and forecasting service used
    # by the FireFusion API during its application lifecycle.
    messaging_service = await MessagingService.create()
    forecast_service = ForecastService()

    try:
        # Start consuming model prediction messages before marking the
        # application as ready to receive Kubernetes-managed traffic.
        await messaging_service.consume_predictions(
            forecast_service.on_prediction_message
        )

        app.state.ready = True
        yield

    finally:
        # Remove the pod from ready service endpoints during shutdown
        # and cleanly close the messaging connection.
        app.state.ready = False
        await messaging_service.close()


app = FastAPI(
    title="FireFusion API",
    version="1.0.0",
    lifespan=init_lifespan_objects,
)

setup_tracing(
    app,
    environment.otel_service_name,
    enabled=environment.otel_traces_enabled,
    otlp_endpoint=environment.otel_exporter_otlp_endpoint,
    instrument_db=True,
    instrument_cache=True,
)

# Restricted to the configured dashboard origins. A wildcard origin combined
# with allow_credentials is rejected by browsers and is unsafe once deployed,
# so the permitted origins are configured per environment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=environment.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "service": "firefusion-api",
    }


# Kubernetes readiness probe endpoint.
# Traffic should only be routed to this instance after application
# startup dependencies have been successfully initialised.
@app.get("/ready", tags=["Operations"])
async def ready():
    if not getattr(app.state, "ready", False):
        raise HTTPException(
            status_code=503,
            detail="FireFusion API is not ready",
        )

    return {
        "status": "ready",
        "service": "firefusion-api",
    }


# Register the existing FireFusion application routers.
app.include_router(hello.router)
app.include_router(forecast.router)
app.include_router(misinformation_controller.router)