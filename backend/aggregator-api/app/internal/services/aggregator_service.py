from opentelemetry import trace

from .messaging_service import MessagingService
from ..repositories.aggregator_repository import AggregatorRepository
from ..models.fire_event import FireEvent

tracer = trace.get_tracer(__name__)

class AggregatorService:
    def __init__(self, messaging: MessagingService):
        self.repository = AggregatorRepository()
        self.messaging = messaging

    async def handle_events_update(self):
        # This is where a prediction's trace begins: triggered by a Postgres
        # NOTIFY, not an HTTP request, so there is no ambient span to attach
        # to otherwise. This span becomes the root that publish_to_forecast_model
        # carries across the RabbitMQ boundary to model-api.
        with tracer.start_as_current_span(
            "aggregator.handle_events_update", kind=trace.SpanKind.PRODUCER
        ):
            # get data from database
            data: list[FireEvent] = await self.repository.get_recent_events(365)

            for d in data:
                print(d.event_id)

            # encode the model into a JSON
            broker_message = [event.model_dump(mode="json") for event in data]

            await self.messaging.publish_to_forecast_model(broker_message)