import meraki
from loguru import logger

from selent_mcp.services.meraki_multi_client import MerakiMultiClient


class MerakiClient:
    """
    Meraki client wrapper that supports both single and multiple API keys.
    """

    def __init__(self, api_key: str):
        """
        Initialize Meraki client with single or multiple API keys.

        Args:
            api_key: Single API key or comma-separated multiple keys
                Examples:
                - "abc123"  (single key - backward compatible)
                - "key1,key2,key3"  (multiple keys)
                - "customer_a:key1,customer_b:key2"  (named keys)
        """
        self.api_key: str = api_key
        self._multi_client: MerakiMultiClient | None = None

        if api_key:
            try:
                self._multi_client = MerakiMultiClient(api_key)
            except Exception as e:
                logger.error(f"Failed to initialize MerakiMultiClient: {e}")
                raise

    def get_dashboard(
        self,
        key_id: str | None = None,
        organization_id: str | None = None,
    ) -> meraki.DashboardAPI:
        """
        Get or create dashboard API instance with connection reuse.

        Args:
            key_id: Optional key identifier for multi-key mode
            organization_id: Optional organization ID to auto-select key

        Returns:
            meraki.DashboardAPI instance

        Raises:
            ValueError: If no API key available or key not found
        """
        if self._multi_client is None:
            raise ValueError("No API key configured")

        try:
            return self._multi_client.get_dashboard(
                key_id=key_id, organization_id=organization_id
            )
        except Exception as e:
            logger.error(f"Failed to get dashboard: {e}")
            raise

    @property
    def multi_client(self) -> MerakiMultiClient:
        """Access to underlying multi-client for advanced operations"""
        if self._multi_client is None:
            raise ValueError("No API key configured")
        return self._multi_client

    def is_multi_key(self) -> bool:
        """Check if client is configured with multiple API keys"""
        if self._multi_client is None:
            return False
        return len(self._multi_client.keys) > 1
