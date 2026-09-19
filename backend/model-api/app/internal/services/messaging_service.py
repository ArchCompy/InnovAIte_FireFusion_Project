import aio_pika
import json
from aio_pika.abc import AbstractRobustConnection, AbstractChannel
from ...config.config import environment
from shared.tracing import inject_trace_context

class MessagingService:

    def __init__(self, connection: AbstractRobustConnection, channel: AbstractChannel):
        self.connection: AbstractRobustConnection = connection
        self.channel: AbstractChannel = channel

    async def consume_data(self, callback): # from forecast queue
        queue = await self.channel.declare_queue("forecast", durable=True)
        await queue.consume(callback)

    async def publish_prediction(self, payload):
        # aio_pika has no auto-instrumentation, so the current trace context
        # (the consumer span ModelService.consume_data_publish_prediction
        # opened for the "forecast" message) is carried across the RabbitMQ
        # boundary explicitly, as W3C traceparent message headers.
        await self.channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload.model_dump()).encode("utf-8"),
                content_type="application/json",
                headers=inject_trace_context(),
            ),
            routing_key="predictions",
        )

    async def close(self):
        # invoke after use
        await self.connection.close()

    @classmethod
    async def create(cls):
        connection: AbstractRobustConnection =  await aio_pika.connect_robust(environment.broker_url)
        channel: AbstractChannel = await connection.channel()
        await channel.declare_queue("predictions", durable=True)
        await channel.declare_queue("forecast", durable=True)
        return cls(connection, channel)