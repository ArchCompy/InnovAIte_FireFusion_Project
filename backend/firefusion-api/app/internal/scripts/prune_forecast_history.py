"""Delete forecast_history rows older than the configured retention window.

No scheduler is built into this service. Run this periodically from outside
it: host cron, a Kubernetes CronJob, or equivalent. See
docs/forecast-history.md for the exact command and an example schedule.

Usage:
    python -m app.internal.scripts.prune_forecast_history
"""
import asyncio
import logging

from ..repositories.database import close_pool, open_pool
from ..services.forecast_service import ForecastService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    await open_pool()
    try:
        await ForecastService().prune_expired_history()
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
