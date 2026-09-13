import json
import logging
from datetime import datetime, timezone

from .caching_service import cache_client
from .websocket_connection_manager import ws_manager
from ...config.config import environment
from ..models.geojson import FeatureCollection
from ..models.forecast_status import ForecastMeta, ForecastStatus


logger = logging.getLogger(__name__)

GENERATED_AT_KEY = "predictions:generated_at"


def _empty():
    """Return a fresh empty FeatureCollection.

    A new dict each call so callers can never mutate a shared constant.
    """
    return {
        "type": "FeatureCollection",
        "features": []
    }


def _now_iso() -> str:
    """Current UTC time as an ISO 8601 string, e.g. 2026-01-01T12:00:00+00:00."""
    return datetime.now(timezone.utc).isoformat()


def _with_meta(feature_collection: dict, meta: ForecastMeta) -> dict:
    """Attach freshness metadata to a FeatureCollection dict.

    exclude_none so a field the Front-end can't act on (an unknown
    generated_at or age) is omitted rather than sent as null.
    """
    feature_collection["meta"] = meta.model_dump(exclude_none=True)
    return feature_collection


def _unavailable_meta() -> ForecastMeta:
    return ForecastMeta(
        status=ForecastStatus.UNAVAILABLE,
        stale_after_seconds=environment.forecast_stale_after_seconds,
        message="No forecast is available yet.",
    )


def _classify_freshness(generated_at_raw) -> ForecastMeta:
    """Classify a stored forecast's freshness against the configured window.

    Overstating freshness is the dangerous error for an emergency tool, so
    any timestamp we cannot trust (missing, or unparsable) is reported as
    stale rather than live. Age is never guessed: unknown means unknown.
    """
    stale_after = environment.forecast_stale_after_seconds

    if not generated_at_raw:
        return ForecastMeta(
            status=ForecastStatus.STALE,
            stale_after_seconds=stale_after,
            message=(
                "Forecast age is unknown, so it is being treated as stale. "
                "The map still shows the last known risk picture."
            ),
        )

    # redis-py returns bytes unless decode_responses is set on the client
    # (it isn't, see caching_service.py), while json.loads tolerates bytes
    # transparently. datetime.fromisoformat does not, so decode explicitly.
    if isinstance(generated_at_raw, bytes):
        generated_at_raw = generated_at_raw.decode()

    try:
        generated_at = datetime.fromisoformat(generated_at_raw)
    except ValueError:
        logger.warning(
            "predictions:generated_at was not a valid ISO timestamp: %r",
            generated_at_raw,
        )
        return ForecastMeta(
            status=ForecastStatus.STALE,
            stale_after_seconds=stale_after,
            message=(
                "Forecast age is unknown, so it is being treated as stale. "
                "The map still shows the last known risk picture."
            ),
        )

    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)

    age_seconds = max(0, int((datetime.now(timezone.utc) - generated_at).total_seconds()))

    if age_seconds <= stale_after:
        return ForecastMeta(
            status=ForecastStatus.LIVE,
            generated_at=generated_at_raw,
            age_seconds=age_seconds,
            stale_after_seconds=stale_after,
        )

    return ForecastMeta(
        status=ForecastStatus.STALE,
        generated_at=generated_at_raw,
        age_seconds=age_seconds,
        stale_after_seconds=stale_after,
        message=(
            f"This forecast is {age_seconds}s old and the prediction source "
            "has stopped updating. The map still shows the last known risk picture."
        ),
    )


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

        generated_at = _now_iso()

        await cache_client.set(
            "predictions",
            json.dumps(validated_payload)
        )
        await cache_client.set(GENERATED_AT_KEY, generated_at)

        # A freshly stored prediction is live by definition, age 0. Attaching
        # the same meta shape here means the WebSocket push and the REST
        # response in fetch_predictions are never structurally different.
        broadcast_payload = _with_meta(
            dict(validated_payload),
            ForecastMeta(
                status=ForecastStatus.LIVE,
                generated_at=generated_at,
                age_seconds=0,
                stale_after_seconds=environment.forecast_stale_after_seconds,
            ),
        )
        await ws_manager.broadcast(broadcast_payload)

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

        Per the Fire Risk Map API contract, this always returns a valid
        FeatureCollection so map clients never receive a null or malformed body.
        The last known good forecast keeps being served past its freshness
        window, tagged stale, rather than being dropped: during an incident a
        stale risk picture is more useful than a blank map. See
        docs/fire-risk-map-graceful-degradation.md.

        Dependency failures propagate, and the router translates them to a 503.
        """

        data = await cache_client.get("predictions")

        if data is None:
            logger.info(
                "No cached prediction available; "
                "returning empty FeatureCollection"
            )
            return _with_meta(_empty(), _unavailable_meta())

        try:
            payload = json.loads(data)
        except (TypeError, ValueError):
            logger.warning(
                "Cached prediction was not valid JSON; "
                "returning empty FeatureCollection"
            )
            return _with_meta(_empty(), _unavailable_meta())

        # json.loads("null") returns None, and other JSON scalars decode
        # to non-dict types. None of these can be a FeatureCollection.
        if not isinstance(payload, dict):
            logger.warning(
                "Cached prediction decoded to %s, not an object; "
                "returning empty FeatureCollection",
                type(payload).__name__,
            )
            return _with_meta(_empty(), _unavailable_meta())

        try:
            feature_collection = FeatureCollection(**payload).model_dump(
                exclude_none=True
            )
        except Exception:
            logger.warning(
                "Cached prediction did not match the GeoJSON schema; "
                "returning empty FeatureCollection"
            )
            return _with_meta(_empty(), _unavailable_meta())

        generated_at_raw = await cache_client.get(GENERATED_AT_KEY)
        meta = _classify_freshness(generated_at_raw)

        if meta.status == ForecastStatus.STALE:
            logger.warning(
                "Serving stale forecast (age_seconds=%s)", meta.age_seconds
            )

        return _with_meta(feature_collection, meta)
