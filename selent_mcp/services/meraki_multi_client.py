from typing import Any

import meraki
from loguru import logger


class MerakiMultiClient:
    """
    Manages multiple Meraki API keys and provides context-aware dashboard access.

    Supports three configuration formats:
    1. Single key: "abc123..."
    2. Multiple keys: "key1,key2,key3"
    3. Named keys: "customer_a:key1,customer_b:key2"
    """

    def __init__(self, api_keys_string: str):
        """
        Initialize multi-client manager from comma-separated API keys.

        Args:
            api_keys_string: Comma-separated API keys, optionally with names
                Examples:
                - "abc123"  (single key)
                - "key1,key2,key3"  (multiple keys)
                - "customer_a:key1,customer_b:key2"  (named keys)

        Raises:
            ValueError: If api_keys_string is empty
        """
        if not api_keys_string or not api_keys_string.strip():
            raise ValueError("API keys string cannot be empty")

        # Parse API keys
        self.keys: dict[str, str] = {}  # key_id -> api_key
        self.key_names: dict[str, str] = {}  # key_id -> friendly name
        self.dashboards: dict[str, meraki.DashboardAPI] = {}  # key_id -> dashboard
        self.organizations_cache: dict[str, list[dict[str, Any]]] = {}  # key_id -> orgs
        self.org_to_key_map: dict[str, str] = {}  # org_id -> key_id
        self.default_key_id: str | None = None

        self._parse_api_keys(api_keys_string.strip())

        # Set default to first key
        if self.keys:
            self.default_key_id = list(self.keys.keys())[0]

        logger.info(
            f"Initialized MerakiMultiClient with {len(self.keys)} API key(s)"
        )

    def _parse_api_keys(self, api_keys_string: str):
        """
        Parse comma-separated API keys string.

        Supports formats:
        - "key1,key2,key3"
        - "name1:key1,name2:key2"
        - Mixed: "name1:key1,key2,name3:key3"
        """
        key_parts = [part.strip() for part in api_keys_string.split(",")]

        for idx, part in enumerate(key_parts):
            if ":" in part:
                # Named format: "customer_a:key123"
                name, api_key = part.split(":", 1)
                key_id = name.strip()
                api_key = api_key.strip()
                self.key_names[key_id] = name.strip()
            else:
                # Unnamed format: "key123"
                api_key = part.strip()
                key_id = f"key_{idx + 1}"
                self.key_names[key_id] = f"API Key {idx + 1}"

            if api_key:
                self.keys[key_id] = api_key
                logger.debug(f"Registered key: {key_id} ({self.key_names[key_id]})")

    def get_dashboard(
        self,
            key_id: str | None = None,
        organization_id: str | None = None,
    ) -> meraki.DashboardAPI:
        """
        Get dashboard instance for specified key or organization.

        Resolution order:
        1. If key_id provided, use that key
        2. If organization_id provided, find key that has access to it
        3. Use default key

        Args:
            key_id: Explicit key identifier (e.g., "customer_a", "key_1")
            organization_id: Organization ID to find matching key

        Returns:
            meraki.DashboardAPI instance

        Raises:
            ValueError: If key not found or no keys available
        """
        selected_key_id = self._resolve_key_id(key_id, organization_id)

        # Lazy load dashboard
        if selected_key_id not in self.dashboards:
            api_key = self.keys[selected_key_id]
            self.dashboards[selected_key_id] = meraki.DashboardAPI(
                api_key=api_key,
                suppress_logging=True,
                maximum_retries=3,
                caller="SelentMCP/1.0 SelentAI",
                wait_on_rate_limit=True,
            )
            logger.info(
                f"Created dashboard for: {selected_key_id} "
                f"({self.key_names[selected_key_id]})"
            )

        return self.dashboards[selected_key_id]

    def _resolve_key_id(
        self,
        key_id: str | None,
        organization_id: str | None,
    ) -> str:
        """
        Resolve which key to use based on context.

        Priority:
        1. Explicit key_id
        2. Find key by organization_id (if cached)
        3. Default key

        Args:
            key_id: Explicit key identifier
            organization_id: Organization ID to match

        Returns:
            Resolved key_id

        Raises:
            ValueError: If key cannot be resolved
        """
        # Priority 1: Explicit key_id
        if key_id:
            if key_id not in self.keys:
                available_keys = ", ".join(self.keys.keys())
                raise ValueError(
                    f"API key '{key_id}' not found. "
                    f"Available keys: {available_keys}"
                )
            return key_id

        # Priority 2: Find by organization_id
        if organization_id:
            if organization_id in self.org_to_key_map:
                return self.org_to_key_map[organization_id]

            # Try to discover organizations for all keys
            logger.info(
                f"Organization '{organization_id}' not in cache, "
                "discovering organizations..."
            )
            self.discover_all_organizations()

            if organization_id in self.org_to_key_map:
                return self.org_to_key_map[organization_id]

            raise ValueError(
                f"No API key found with access to organization: {organization_id}"
            )

        # Priority 3: Default key
        if self.default_key_id:
            return self.default_key_id

        raise ValueError("No API keys available")

    def discover_organizations(self, key_id: str) -> list[dict[str, Any]]:
        """
        Discover and cache organizations for a specific API key.

        Args:
            key_id: Key identifier to discover organizations for

        Returns:
            List of organization dictionaries

        Raises:
            ValueError: If key_id not found
        """
        if key_id not in self.keys:
            raise ValueError(f"API key not found: {key_id}")

        if key_id in self.organizations_cache:
            logger.debug(f"Using cached organizations for: {key_id}")
            return self.organizations_cache[key_id]

        try:
            dashboard = self.get_dashboard(key_id=key_id)
            orgs = dashboard.organizations.getOrganizations()
            self.organizations_cache[key_id] = orgs

            # Update org -> key mapping
            for org in orgs:
                org_id = org.get("id")
                if org_id:
                    self.org_to_key_map[org_id] = key_id

            logger.info(
                f"Discovered {len(orgs)} organizations for: {key_id} "
                f"({self.key_names[key_id]})"
            )
            return orgs

        except Exception as e:
            logger.error(f"Failed to discover organizations for {key_id}: {e}")
            raise

    def discover_all_organizations(self):
        """
        Discover organizations for all configured API keys.

        Useful for populating cache on startup or when user needs
        to query across multiple customers.
        """
        for key_id in self.keys.keys():
            try:
                self.discover_organizations(key_id)
            except Exception as e:
                logger.warning(
                    f"Failed to discover organizations for {key_id}: {e}"
                )

    def list_keys(self) -> list[dict[str, Any]]:
        """
        Get list of configured API keys (without exposing actual keys).

        Returns:
            List of dictionaries with key information:
            - key_id: Key identifier
            - name: Friendly name
            - organization_count: Number of orgs (if discovered)
            - is_default: Whether this is the default key
        """
        result: list[dict[str, Any]] = []  # pyright: ignore[reportUnknownReturnType]
        for key_id, api_key in self.keys.items():
            result.append(
                {
                    "key_id": key_id,
                    "name": self.key_names[key_id],
                    "organization_count": len(
                        self.organizations_cache.get(key_id, [])
                    ),
                    "is_default": key_id == self.default_key_id,
                    "has_organizations_cached": key_id in self.organizations_cache,
                }
            )
        return result

    def set_default_key(self, key_id: str):
        """
        Set the default API key for subsequent operations.

        Args:
            key_id: Key identifier to set as default

        Raises:
            ValueError: If key_id not found
        """
        if key_id not in self.keys:
            available_keys = ", ".join(self.keys.keys())
            raise ValueError(
                f"API key '{key_id}' not found. Available keys: {available_keys}"
            )

        old_default = self.default_key_id
        self.default_key_id = key_id

        logger.info(
            f"Default key changed from '{old_default}' to '{key_id}' "
            f"({self.key_names[key_id]})"
        )

    def get_key_info(self, key_id: str) -> dict[str, Any]:
        """
        Get detailed information about a specific API key.

        Args:
            key_id: Key identifier

        Returns:
            Dictionary with key information including organizations

        Raises:
            ValueError: If key_id not found
        """
        if key_id not in self.keys:
            raise ValueError(f"API key not found: {key_id}")

        # Discover organizations if not cached
        if key_id not in self.organizations_cache:
            self.discover_organizations(key_id)

        return {
            "key_id": key_id,
            "name": self.key_names[key_id],
            "is_default": key_id == self.default_key_id,
            "organization_count": len(self.organizations_cache.get(key_id, [])),
            "organizations": self.organizations_cache.get(key_id, []),
        }
