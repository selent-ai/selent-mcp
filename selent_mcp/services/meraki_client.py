import logging

import meraki

logger = logging.getLogger(__name__)


class MerakiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._dashboard = None

    def get_dashboard(self) -> meraki.DashboardAPI:
        """Get or create dashboard API instance with connection reuse"""
        if self._dashboard is None:
            try:
                self._dashboard = meraki.DashboardAPI(
                    api_key=self.api_key,
                    suppress_logging=True,
                    maximum_retries=3,
                    wait_on_rate_limit=True,
                )
                logger.info("Meraki Dashboard API client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Meraki Dashboard API: {e}")
                raise
        return self._dashboard
