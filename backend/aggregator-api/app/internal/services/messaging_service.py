import aio_pika
import json
from aio_pika.abc import AbstractRobustConnection
from aio_pika.abc import AbstractChannel
from ...config.config import environment
from shared.tracing import inject_trace_context

class MessagingService:

    def __init__(self, connection: AbstractRobustConnection, channel: AbstractChannel):
        self.connection: AbstractRobustConnection = connection
        self.channel: AbstractChannel = channel

    async def publish_to_forecast_model(self, payload):
        # aio_pika has no auto-instrumentation, so the current trace context
        # (see AggregatorService.handle_events_update) is carried across the
        # RabbitMQ boundary explicitly, as W3C traceparent message headers.
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode("utf-8"),
                content_type="application/json",
                headers=inject_trace_context(),
            ),
            routing_key="forecast",
        )

    async def close(self):
        # invoke after use
        await self.connection.close()

    @classmethod
    async def create(cls):
        connection: AbstractRobustConnection =  await aio_pika.connect_robust(environment.broker_url)
        channel: AbstractChannel = await connection.channel()
        await channel.declare_queue("forecast", durable=True)
        return cls(connection, channel)
