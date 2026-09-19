import httpx

from ...config.config import environment


class AggregatorClient:

    def __init__(self):
        self.base_url = environment.aggregator_url

    async def get_recent_fire_incidents(
        self,
        days: int = 14
    ) -> list[dict]:

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=15.0
        ) as client:

            response = await client.get(
                "/internal/data/fire-incidents",
                params={"days": days}
            )

            response.raise_for_status()

            return response.json()

    async def get_fire_risk_inputs(
        self,
        hours: int = 720
    ) -> list[dict]:
        """
        Retrieve the environmental/time-series source data prepared
        by Data Engineering for Fire Risk Map integration.
        """

        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0
        ) as client:

            response = await client.get(
                "/internal/data/fire-risk-inputs",
                params={"hours": hours}
            )

            response.raise_for_status()

            return response.json()