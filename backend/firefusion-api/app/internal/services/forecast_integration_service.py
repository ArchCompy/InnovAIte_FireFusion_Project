from ..clients.aggregator_client import AggregatorClient
from ..clients.ai_modelling_client import AIModellingClient
from ..models.ai_contract import (
    AI_FEATURE_NAMES,
    AI_INPUT_STEPS,
    DE_TO_AI_FEATURE_MAPPING,
)

from .ai_request_builder import AIRequestBuilder
from .forecast_normaliser import ForecastNormaliser
from .forecast_service import ForecastService


class ForecastIntegrationService:

    def __init__(self):
        self.aggregator = AggregatorClient()
        self.ai = AIModellingClient()

        self.request_builder = AIRequestBuilder()
        self.normaliser = ForecastNormaliser()

        self.forecast_service = ForecastService()

    async def generate_and_store_forecast(self) -> dict:
        """
        Execute the complete Backend integration pipeline:

        Data Engineering
            -> Aggregator API
            -> AI Modelling
            -> Backend normalisation
            -> Redis/WebSocket
        """

        source_records = (
            await self.aggregator.get_fire_risk_inputs(
                hours=720
            )
        )

        ai_request = self.request_builder.build(
            source_records=source_records,
            feature_names=AI_FEATURE_NAMES,
            feature_mapping=DE_TO_AI_FEATURE_MAPPING,
            input_steps=AI_INPUT_STEPS
        )

        ai_response = await self.ai.forecast_bushfire(
            ai_request
        )

        frontend_payload = self.normaliser.normalise(
            ai_response
        )

        return await self.forecast_service.store_prediction(
            frontend_payload
        )