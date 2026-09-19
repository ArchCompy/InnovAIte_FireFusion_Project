import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import ValidationError

from .caching_service import cache_client
from .websocket_connection_manager import ws_manager
from ...config.config import environment
from ..models.geojson import FeatureCollection
from ..models.forecast_status import ForecastMeta, ForecastStatus
from ..repositories.forecast_history_repository import ForecastHistoryRepository
from shared.tracing import set_span_attributes, start_consumer_span

DEFAULT_HISTORY_LIMIT = 100
MAX_HISTORY_LIMIT = 1000

# Span attribute names for the forecast path. Values are always scalars
# (counts, status, booleans) - never the GeoJSON payload itself.
ATTR_FEATURE_COUNT = "forecast.feature_count"
ATTR_STATUS = "forecast.status"
ATTR_FROM_CACHE = "forecast.from_cache"


logger = logging.getLogger(__name__)

GENERATED_AT_KEY = "predictions:generated_at"


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


def _tag_and_return(feature_collection: dict, meta: ForecastMeta, *, from_cache: bool) -> dict:
    """Attach meta, then tag the current span with the same information.

    Never the GeoJSON payload itself - only counts and status, which is all
    a trace needs to show how the forecast path behaved.
    """
    result = _with_meta(feature_collection, meta)
    set_span_attributes({
        ATTR_FEATURE_COUNT: len(result.get("features", [])),
        ATTR_STATUS: meta.status.value,
        ATTR_FROM_CACHE: from_cache,
    })
    return result


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

    def __init__(self):
        self.history_repository = ForecastHistoryRepository()

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

        # Best-effort: recording history must never block live forecast
        # delivery. A responder needs the current risk picture regardless of
        # whether it could also be recorded for later review.
        try:
            await self.history_repository.insert(
                datetime.fromisoformat(generated_at), validated_payload
            )
        except Exception:
            logger.exception(
                "Failed to record forecast history; live delivery unaffected"
            )

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

        set_span_attributes({
            ATTR_FEATURE_COUNT: len(validated_payload.get("features", [])),
            ATTR_STATUS: ForecastStatus.LIVE.value,
            ATTR_FROM_CACHE: False,  # freshly written, not read back from cache
        })

        return validated_payload

    async def on_prediction_message(self, message):
        """
        Handle predictions received through the inherited RabbitMQ flow.
        """

        async with message.process():
            # Extracts model-api's trace context from the "predictions"
            # message headers, so this span (and store_prediction's work
            # inside it) is part of the same trace as the aggregator ->
            # model-api -> firefusion-api pipeline that produced it, rather
            # than starting a new, disconnected one.
            with start_consumer_span("predictions queue consume", message.headers):
                payload = json.loads(message.body)

                await self.store_prediction(payload)

    async def fetch_predictions(self):
        """Return the latest forecast as a GeoJSON FeatureCollection.

        A missing Redis value represents the normal no-prediction state and
        returns an empty FeatureCollection tagged unavailable. A present but
        unusable value is reported as cache corruption so the API does not
        disguise damaged prediction data as a normal no-data response.

        The last known good forecast keeps being served past its freshness
        window, tagged stale, rather than being dropped: during an incident a
        stale risk picture is more useful than a blank map. See
        docs/fire-risk-map-graceful-degradation.md.

        Redis dependency failures propagate to the router unchanged.
        """

        data = await cache_client.get("predictions")

        if data is None:
            logger.info(
                "No cached prediction available; "
                "returning empty FeatureCollection"
            )
            return _tag_and_return(_empty(), _unavailable_meta(), from_cache=True)

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
            feature_collection = FeatureCollection(**payload).model_dump(
                exclude_none=True
            )
        except ValidationError as exc:
            raise ForecastCacheCorruptionError(
                "Cached prediction did not match the GeoJSON schema"
            ) from exc

        generated_at_raw = await cache_client.get(GENERATED_AT_KEY)
        meta = _classify_freshness(generated_at_raw)

        if meta.status == ForecastStatus.STALE:
            logger.warning(
                "Serving stale forecast (age_seconds=%s)", meta.age_seconds
            )

        return _tag_and_return(feature_collection, meta, from_cache=True)

    async def get_forecast_at(self, timestamp: datetime) -> Optional[dict]:
        """Return the forecast that was current at the given moment.

        The most recent recorded forecast at or before timestamp, never a
        later one. None if nothing was recorded that early; the router turns
        that into a 404. Same FeatureCollection shape as fetch_predictions(),
        including meta, so Front-end can reuse its existing rendering.
        """
        record = await self.history_repository.get_at(timestamp)

        if record is None:
            set_span_attributes({ATTR_FEATURE_COUNT: 0, ATTR_FROM_CACHE: False})
            return None

        meta = _classify_freshness(record.generated_at.isoformat())
        return _tag_and_return(dict(record.payload), meta, from_cache=False)

    async def get_forecast_history(
        self,
        from_timestamp: datetime,
        to_timestamp: datetime,
        limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> list[dict]:
        """Return forecasts in [from_timestamp, to_timestamp], newest first.

        Drives a time slider over recent risk trend. limit is bounded so a
        wide window cannot return everything at once.
        """
        limit = max(1, min(limit, MAX_HISTORY_LIMIT))

        records = await self.history_repository.get_window(
            from_timestamp, to_timestamp, limit
        )

        results = []
        total_features = 0
        for record in records:
            meta = _classify_freshness(record.generated_at.isoformat())
            entry = _with_meta(dict(record.payload), meta)
            total_features += len(entry.get("features", []))
            results.append(entry)

        # One span covers many entries here, so feature_count/status are
        # aggregated (total across the window, entry count) rather than the
        # single-entry attributes _tag_and_return uses elsewhere.
        set_span_attributes({
            ATTR_FEATURE_COUNT: total_features,
            "forecast.entry_count": len(results),
            ATTR_FROM_CACHE: False,
        })
        return results

    async def prune_expired_history(self) -> int:
        """Delete forecast_history rows older than the configured retention window.

        No scheduler is built into this service; something outside it must
        call this periodically. See docs/forecast-history.md.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=environment.forecast_history_retention_days
        )
        deleted = await self.history_repository.prune_older_than(cutoff)
        logger.info(
            "Pruned %s forecast_history row(s) older than %s",
            deleted,
            cutoff.isoformat(),
        )
        return deleted
