import json
import logging

from pydantic import ValidationError

from .caching_service import cache_client
from .websocket_connection_manager import ws_manager
from ..models.geojson import FeatureCollection


logger = logging.getLogger(__name__)


class ForecastCacheCorruptionError(RuntimeError):
    """Raised when Redis contains unusable cached forecast data."""


def _empty():
    """Return a fresh empty FeatureCollection.

    A new dict each call so callers can never mutate a shared constant.
    """
    return {
        "type": "FeatureCollection",
        "features": []
    }


class ForecastService:

    async def store_prediction(self, payload: dict) -> dict:
        """
        Validate and store a prediction through the shared Backend path.

        This allows both the inherited RabbitMQ prediction flow and the
        newer REST-based AI Modelling integration to use the same
        validation, Redis caching and WebSocket broadcast behaviour.
        """

        geojson = FeatureCollection(**payload)

        # Exclude optional fields that were not supplied so the cached,
        # WebSocket and REST representations remain consistent.
        validated_payload = geojson.model_dump(exclude_none=True)

        await cache_client.set(
            "predictions",
            json.dumps(validated_payload)
        )

        await ws_manager.broadcast(validated_payload)

        return validated_payload

    async def on_prediction_message(self, message):
        """
        Handle predictions received through the inherited RabbitMQ flow.
        """

        async with message.process():
            payload = json.loads(message.body)

            await self.store_prediction(payload)

    async def fetch_predictions(self):
        """Return the latest forecast as a GeoJSON FeatureCollection.

        A missing Redis value represents the normal no-prediction state and
        returns an empty FeatureCollection. A present but unusable value is
        reported as cache corruption so the API does not disguise damaged
        prediction data as a normal no-data response.

        Redis dependency failures propagate to the router unchanged.
        """

        data = await cache_client.get("predictions")

        if data is None:
            logger.info(
                "No cached prediction available; "
                "returning empty FeatureCollection"
            )
            return _empty()

        try:
            payload = json.loads(data)
        except (TypeError, ValueError) as exc:
            raise ForecastCacheCorruptionError(
                "Cached prediction was not valid JSON"
            ) from exc

        if not isinstance(payload, dict):
            raise ForecastCacheCorruptionError(
                "Cached prediction decoded to "
                f"{type(payload).__name__}, not an object"
            )

        try:
            return FeatureCollection(**payload).model_dump(
                exclude_none=True
            )
        except ValidationError as exc:
            raise ForecastCacheCorruptionError(
                "Cached prediction did not match the GeoJSON schema"
            ) from exc

