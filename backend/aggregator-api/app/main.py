from fastapi import FastAPI
from contextlib import asynccontextmanager
# fire_data exposes the new internal Data Engineering v2 access endpoint.
from app.routers import hello, fire_data
from .internal.services.sql_event_listener import sql_event_listener
from .internal.services.aggregator_service import AggregatorService
from .internal.services.messaging_service import MessagingService
from .config.config import environment
from shared.tracing import setup_tracing
import asyncio

# handling specific object lifecycles
# similar to @Bean from Spring Boot
@asynccontextmanager
async def init_lifespan_objects(app: FastAPI):
    messaging_service = await MessagingService.create()
    aggregator_service = AggregatorService(messaging_service)

    aggregator_task = asyncio.create_task(sql_event_listener(aggregator_service))

    yield

    aggregator_task.cancel()
    await messaging_service.close()

app = FastAPI(lifespan=init_lifespan_objects)

setup_tracing(
    app,
    environment.otel_service_name,
    enabled=environment.otel_traces_enabled,
    otlp_endpoint=environment.otel_exporter_otlp_endpoint,
    instrument_db=True,
)

# Existing route.
app.include_router(hello.router)
# New internal REST endpoint used by firefusion-api to retrieve
# prepared Data Engineering fire incident data.
app.include_router(fire_data.router)