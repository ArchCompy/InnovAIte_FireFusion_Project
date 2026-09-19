import httpx

from ...config.config import environment
from ..models.ai_forecast import AIForecastRequest


class AIModellingClient:
    """
    Handles REST communication between FireFusion Backend
    and the AI Modelling FastAPI service.
    """

    def __init__(self):
        self.base_url = environment.ai_modelling_url

    async def forecast_bushfire(
        self,
        payload: dict
    ) -> dict:
        """
        Validate and send a forecast request to AI Modelling.

        The returned GeoJSON includes the prediction polygons and
        Frontend-compatible risk_factor values.
        """

        # Validate the request against the confirmed AI payload structure
        # before sending it to the AI service.
        request = AIForecastRequest(**payload)

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0
        ) as client:

            response = await client.post(
                "/predict/bushfire/forecast",
                json=request.model_dump(mode="json")
            )

            response.raise_for_status()

            return response.json()

    async def health(self) -> dict:
        """
        Simple connectivity check for the AI Modelling service.
        """

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=5.0
        ) as client:

            response = await client.get("/health")

            response.raise_for_status()

            return response.json()