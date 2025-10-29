import json

from fastmcp import FastMCP
from loguru import logger

from selent_mcp.services.meraki_client import MerakiClient


class KeyManagementTools:
    """
    Provides MCP tools for managing multiple API keys in MSP mode.

    Only registered when multiple API keys are configured.
    """

    def __init__(self, mcp: FastMCP, meraki_client: MerakiClient):
        """
        Initialize key management tools.

        Args:
            mcp: FastMCP server instance
            meraki_client: MerakiClient with multi-key support
        """
        self.mcp: FastMCP = mcp
        self.meraki_client: MerakiClient = meraki_client

        if self.meraki_client.is_multi_key():
            self._register_tools()
            logger.info("KeyManagementTools registered (multi-key mode detected)")
        else:
            logger.info("KeyManagementTools not registered (single-key mode)")

    def _register_tools(self):
        """Register all key management tools with the MCP server"""
        self.mcp.tool()(self.list_api_keys)
        self.mcp.tool()(self.get_key_organizations)
        self.mcp.tool()(self.set_default_key)
        self.mcp.tool()(self.discover_all_organizations)
        self.mcp.tool()(self.find_organization_by_name)

    def list_api_keys(self) -> str:
        """
        List all configured API keys and their details.

        Returns information about each API key without exposing
        the actual key values. Shows which key is the default and
        whether organizations have been discovered.

        USE THIS WHEN:
        - User asks "what API keys are configured?"
        - User asks "list all customers"
        - Starting work with multiple customers
        - Need to know which key_id to use

        Returns:
            JSON string with list of API keys:
            {
                "count": 3,
                "keys": [
                    {
                        "key_id": "customer_a",
                        "name": "Customer A - Acme Corp",
                        "organization_count": 5,
                        "is_default": true,
                        "has_organizations_cached": true
                    },
                    ...
                ]
            }

        Example Usage:
            "Show me all configured API keys"
            "List all my customers"
            "What keys are available?"
        """
        try:
            multi_client = self.meraki_client.multi_client
            keys = multi_client.list_keys()

            result = {
                "count": len(keys),
                "keys": keys,
                "note": (
                    "Use get_key_organizations(key_id) to see "
                    "organizations for a specific key"
                ),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to list API keys: {e}")
            return json.dumps({"error": str(e)}, indent=2)

    def get_key_organizations(self, key_id: str) -> str:
        """
        Get organizations accessible by a specific API key.

        Discovers organizations if not already cached, then returns
        the list with full organization details.

        USE THIS WHEN:
        - User asks "what organizations does customer_a have?"
        - Need to find organization IDs for a specific customer
        - Verifying API key access before making calls

        Args:
            key_id: API key identifier (e.g., "customer_a", "key_1")
                Use list_api_keys() to see available key_ids

        Returns:
            JSON string with organizations for this key:
            {
                "key_id": "customer_a",
                "key_name": "Customer A - Acme Corp",
                "organization_count": 2,
                "organizations": [
                    {
                        "id": "123456",
                        "name": "Acme HQ",
                        "url": "https://...",
                        ...
                    },
                    ...
                ]
            }

        Example Usage:
            get_key_organizations(key_id="customer_a")
            get_key_organizations(key_id="key_1")
        """
        try:
            multi_client = self.meraki_client.multi_client
            key_info = multi_client.get_key_info(key_id)

            return json.dumps(key_info, indent=2)
        except ValueError as e:
            available_keys = self.meraki_client.multi_client.list_keys()
            return json.dumps(
                {
                    "error": str(e),
                    "available_keys": [k["key_id"] for k in available_keys],
                },
                indent=2,
            )
        except Exception as e:
            logger.error(f"Failed to get organizations for {key_id}: {e}")
            return json.dumps({"error": str(e)}, indent=2)

    def set_default_key(self, key_id: str) -> str:
        """
        Set the default API key for subsequent operations.

        Once set, all API calls without an explicit key_id will use
        this default key. Useful when working with a single customer
        for an extended period.

        USE THIS WHEN:
        - User says "work with customer_a for now"
        - Starting batch operations on one customer
        - Want to avoid specifying key_id on every call

        Args:
            key_id: API key identifier to set as default
                Use list_api_keys() to see available key_ids

        Returns:
            JSON string confirming the change:
            {
                "success": true,
                "message": "Default key set to: customer_a",
                "key_name": "Customer A - Acme Corp"
            }

        Example Usage:
            set_default_key(key_id="customer_a")

        NOTE: This change persists only for the current session
        """
        try:
            multi_client = self.meraki_client.multi_client
            multi_client.set_default_key(key_id)

            result = {
                "success": True,
                "message": f"Default key set to: {key_id}",
                "key_name": multi_client.key_names[key_id],
                "note": ("All subsequent API calls without key_id will use this key"),
            }

            return json.dumps(result, indent=2)

        except ValueError as e:
            available_keys = self.meraki_client.multi_client.list_keys()
            return json.dumps(
                {
                    "error": str(e),
                    "available_keys": [k["key_id"] for k in available_keys],
                },
                indent=2,
            )
        except Exception as e:
            logger.error(f"Failed to set default key: {e}")
            return json.dumps({"error": str(e)}, indent=2)

    def discover_all_organizations(self) -> str:
        """
        Discover and cache organizations for ALL configured API keys.

        This can take several seconds but is useful for:
        - Initial setup to populate cache
        - Enabling auto-selection by organization ID
        - Getting overview of all accessible organizations

        USE THIS WHEN:
        - User asks "show me all organizations across all customers"
        - Setting up for cross-customer queries
        - Want to enable auto-key-selection by org ID

        Returns:
            JSON string with discovery results:
            {
                "total_keys": 3,
                "total_organizations": 12,
                "results": {
                    "customer_a": {
                        "organization_count": 5,
                        "status": "success"
                    },
                    "customer_b": {
                        "organization_count": 7,
                        "status": "success"
                    }
                }
            }

        Example Usage:
            "Discover all organizations for all customers"
            "Show me everything I have access to"

        NOTE: This may take 5-10 seconds for many keys
        """
        try:
            multi_client = self.meraki_client.multi_client
            results = {}
            total_orgs = 0

            for key_id in multi_client.keys.keys():
                try:
                    orgs = multi_client.discover_organizations(key_id)
                    results[key_id] = {
                        "organization_count": len(orgs),
                        "status": "success",
                    }
                    total_orgs += len(orgs)
                except Exception as e:
                    results[key_id] = {
                        "organization_count": 0,
                        "status": "failed",
                        "error": str(e),
                    }

            result = {
                "total_keys": len(multi_client.keys),
                "total_organizations": total_orgs,
                "results": results,
                "note": (
                    "Organizations cached. You can now use organizationId "
                    "in execute_meraki_api_endpoint without specifying key_id"
                ),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to discover all organizations: {e}")
            return json.dumps({"error": str(e)}, indent=2)

    def find_organization_by_name(self, name: str, fuzzy: bool = True) -> str:
        """
        Find organization(s) by name across all API keys.

        This tool helps resolve organization names to IDs and keys, enabling
        natural language queries like "get devices for organization X"

        USE THIS WHEN:
        - User mentions an organization by name (not ID)
        - User asks "get devices in [org name]"
        - Need to find which API key owns an organization
        - Disambiguating between multiple organizations with similar names

        Args:
            name: Organization name or partial name to search for
                Examples: "Organization X", "Organization Y", "Organization Z"
            fuzzy: If True, performs case-insensitive partial matching.
                If False, requires exact match (default: True)

        Returns:
            JSON string with matching organizations:
            {
                "query": "Organization X",
                "matches": [
                    {
                        "id": "236620",
                        "name": "Organization X",
                        "key_id": "organization_x",
                        "key_name": "organization_x",
                        "url": "https://..."
                    }
                ],
                "usage": "Use organizationId='236620' in API calls for auto-selection"
            }

        Example Usage:
            # Find by exact name
            find_organization_by_name(name="Organization X")

            # Find by partial name
            find_organization_by_name(name="Organization X")

            # Case-insensitive search
            find_organization_by_name(name="organization x")

        WORKFLOW EXAMPLE:
            User: "Get devices for Organization X"

            Step 1: find_organization_by_name(name="Organization X")
            → Returns: org_id="236620", key_id="organization_x"

            Step 2: execute_meraki_api_endpoint(
                        section="organizations",
                        method="getOrganizationDevices",
                        organizationId="236620"  # Auto-selects organization_x key
                    )
        """
        try:
            multi_client = self.meraki_client.multi_client

            if not multi_client.org_to_key_map:
                logger.info("Organizations not cached, discovering...")
                multi_client.discover_all_organizations()

            matches = []
            search_name = name.lower() if fuzzy else name

            for key_id, orgs in multi_client.organizations_cache.items():
                for org in orgs:
                    org_name = org.get("name", "")

                    is_match = False
                    if fuzzy:
                        is_match = search_name in org_name.lower()
                    else:
                        is_match = search_name == org_name

                    if is_match:
                        matches.append(
                            {
                                "id": org.get("id"),
                                "name": org_name,
                                "key_id": key_id,
                                "key_name": multi_client.key_names[key_id],
                                "url": org.get("url"),
                            }
                        )

            result = {
                "query": name,
                "fuzzy_match": fuzzy,
                "match_count": len(matches),
                "matches": matches,
            }

            if len(matches) == 0:
                result["suggestion"] = (
                    "No organizations found. Try: "
                    "1) Run discover_all_organizations() first, "
                    "2) Check spelling, "
                    "3) Try fuzzy=True for partial matching"
                )
            elif len(matches) == 1:
                result["usage"] = (
                    f"Use organizationId='{matches[0]['id']}' in API calls. "
                    f"The system will auto-select key: {matches[0]['key_id']}"
                )
            else:
                result["note"] = (
                    f"Multiple matches found ({len(matches)}). "
                    "Use the specific organizationId for the one you want."
                )

            return json.dumps(result, indent=2)

        except Exception as e:
            logger.error(f"Failed to find organization by name: {e}")
            return json.dumps({"error": str(e)}, indent=2)
