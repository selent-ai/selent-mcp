import asyncio
import inspect
import json
import time
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from loguru import logger
from qdrant_client import QdrantClient, models

from selent_mcp.services.meraki_client import MerakiClient


SDK_INTERNAL_PARAMS = {"total_pages", "direction", "suppress_logging"}

def extract_non_empty_params(**kwargs: Any) -> list[str]:
    """
    Extract parameter names that have non-null and non-empty values.

    Args:
        **kwargs: Arbitrary keyword arguments to filter

    Returns:
        List of parameter names whose values are not None and not empty strings

    Example:
        >>> extract_non_empty_params(serial="Q2XX", portId="", networkId=None)
        ['serial']
    """
    return [k for k, v in kwargs.items() if v is not None and v != ""]


class MerakiApiTools:
    """
    Dynamic tool class that uses semantic search to discover and execute
    Meraki API endpoints
    """

    def __init__(
        self,
        mcp: FastMCP,
        meraki_client: MerakiClient,
        enabled: bool,
        collection_path: str = "./data/meraki_api_collection",
        collection_name: str = "meraki_api_collection",
        model_name: str = "BAAI/bge-small-en-v1.5",
    ):
        self.mcp: FastMCP = mcp
        self.meraki_client: MerakiClient = meraki_client
        self.enabled: bool = enabled
        self.collection_path: str = collection_path
        self.collection_name: str = collection_name
        self.model_name: str = model_name

        # Response caching
        self._response_cache: dict[str, dict[str, Any]] = {}
        self._cache_ttl: int = 300

        # Qdrant client (lazy loaded)
        self._qdrant_client: QdrantClient | None = None

        if self.enabled:
            self._register_tools()
        else:
            logger.info("MerakiApiTools not registered (MERAKI_API_KEY not set)")

    def _get_qdrant_client(self) -> QdrantClient:
        """Lazy load Qdrant client"""
        if self._qdrant_client is None:
            Path(self.collection_path).mkdir(parents=True, exist_ok=True)
            self._qdrant_client = QdrantClient(path=self.collection_path)

        return self._qdrant_client

    def _register_tools(self):
        """Register the dynamic tools with the MCP server"""
        self.mcp.tool()(self.search_meraki_api_endpoints)
        self.mcp.tool()(self.execute_meraki_api_endpoint)
        self.mcp.tool()(self.get_meraki_endpoint_parameters)

    def _get_cache_key(self, section: str, method: str, **params: Any) -> str:
        """Generate a cache key for API responses"""
        sorted_params = sorted(params.items())
        return f"{section}.{method}:{hash(str(sorted_params))}"

    def _is_cache_valid(self, cache_entry: dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - cache_entry.get("timestamp", 0) < self._cache_ttl

    def search_meraki_api_endpoints(
        self, query: str, limit: int = 5, min_score: float = 0.5
    ) -> str:
        """
        Search and discover Meraki API endpoints using semantic similarity.

        This tool uses embeddings and vector similarity search to find the
        most relevant API endpoints based on your natural language query.

        Examples:
            - "get my organizations" → organizations.getOrganizations
            - "device port configuration" → switch.getDeviceSwitchPort
            - "network clients" → networks.getNetworkClients
            - "firewall rules" → getNetworkApplianceFirewallL3FirewallRules
            - "list all devices" → organizations.getOrganizationDevices

        Args:
            query (str): Natural language search term
            limit (int): Maximum number of results to return (default: 5)
            min_score (float): Minimum similarity score 0-1 (default: 0.5)

        Returns:
            JSON string containing:
            - query: The search term used
            - results: List of matching endpoints with scores
            - usage: Instructions for next steps
        """
        try:
            client = self._get_qdrant_client()

            # Search using Qdrant semantic search
            search_results = client.query_points(
                self.collection_name,
                query=models.Document(text=query, model=self.model_name),
                limit=limit,
            ).points

            results = []
            query_lower = query.lower()
            query_words = set(query_lower.split())

            for point in search_results:
                if point.score >= min_score:
                    payload = point.payload or {}
                    method_data = payload.get("method", {})
                    method_name = method_data.get("name", "")
                    section_name = payload.get("section", "")

                    # Calculate boosted score for exact matches
                    boosted_score = point.score
                    method_lower = method_name.lower()
                    section_lower = section_name.lower()

                    key_terms = query_words - {"get", "all", "list", "my", "the"}
                    for term in key_terms:
                        if len(term) > 3:
                            # Check if method name is a simple get + term pattern
                            simple_method = f"get{term}"
                            if method_lower == simple_method or method_lower == f"get{term}s":
                                boosted_score += 0.25  # Strong boost for simple getX methods

                    # Boost if query words appear in method name
                    for word in query_words:
                        if len(word) > 3:  # Only boost meaningful words
                            if word in method_lower:
                                boosted_score += 0.08
                            if word in section_lower:
                                boosted_score += 0.04

                    # Prioritize shorter method names (simpler methods are often more useful)
                    if len(method_name) < 25:
                        boosted_score += 0.03
                    elif len(method_name) > 40:
                        boosted_score -= 0.02 

                    results.append(
                        {
                            "section": section_name,
                            "method": method_name,
                            "description": method_data.get("description", "").split(
                                "\n", 1
                            )[0],
                            "score": round(point.score, 4),
                            "boosted_score": round(min(boosted_score, 1.0), 4),
                        }
                    )

            results.sort(key=lambda x: x["boosted_score"], reverse=True)

            result = {
                "query": query,
                "results": results,
                "usage": (
                    "Use get_meraki_endpoint_parameters(section, method) to "
                    "see detailed parameters, then "
                    "execute_meraki_api_endpoint(section, method, ...) to call"
                ),
            }

            return json.dumps(result, indent=2)

        except FileNotFoundError as e:
            error_result = {
                "error": str(e),
                "suggestion": (
                    "Run 'python selent_mcp/generate_collection.py <API_KEY>'"
                    " to generate the collection first"
                ),
            }
            return json.dumps(error_result, indent=2)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            error_result = {
                "error": f"Search failed: {str(e)}",
            }
            return json.dumps(error_result, indent=2)

    async def get_meraki_endpoint_parameters(self, section: str, method: str) -> str:
        """
        Discover required and optional parameters for any Meraki API endpoint.

        This tool provides complete parameter documentation for API methods, including
        data types, required vs optional parameters, and default values. Use this after
        finding endpoints with search_api_endpoints and before calling
        execute_api_endpoint.

        WHEN TO USE:
        - Before making API calls to understand required parameters
        - To validate you have all necessary data before execution
        - To understand optional parameters for enhanced functionality
        - To check parameter data types for proper formatting

        Args:
            section (str): API section name from search results. Must be exact match.
            Examples:
                - "organizations" - for organization management endpoints
                - "devices" - for device-specific operations
                - "networks" - for network management
                - "appliance" - for MX security appliance features
                - "wireless" - for wireless access point management
                - "switch" - for MS switch management
                - "camera" - for MV camera management
                - "sensor" - for MT sensor management

            method (str): Exact method name from search results. Examples:
                - "getOrganizations" - list all organizations
                - "getDevice" - get device details (requires serial parameter)
                - "getNetworkClients" - list network clients (requires networkId)
                - "updateNetworkSettings" - modify network settings
                - "getOrganizationDevices" - list organization devices

        Returns:
            JSON string containing complete parameter documentation:
            {
              "section": "devices",
              "method": "getDevice",
              "parameters": {
                "serial": {
                  "required": true,
                  "type": "<class 'str'>",
                  "description": "Device serial number"
                },
                "optional_param": {
                  "required": false,
                  "type": "<class 'str'>",
                  "default": "default_value"
                }
              },
              "usage_example": "execute_api_endpoint(
                    section='devices',
                    method='getDevice',
                    serial='Q2XX-XXXX-XXXX'
                )"
            }

        PARAMETER TYPES:
        - str: Text strings (device serials, network IDs, names)
        - int: Numbers (timespan, per_page limits)
        - bool: True/False values (enabled/disabled settings)
        - list: Arrays of values (multiple device serials, IP ranges)
        - dict: JSON objects (configuration settings, rule definitions)

        ERROR HANDLING:
        If endpoint not found, returns suggestions to use search_api_endpoints first.

        WORKFLOW TIP:
        1. search_api_endpoints("your query") → find available methods
        2. get_endpoint_parameters(section, method) → understand requirements
        3. execute_api_endpoint(section, method, param1=value1, ...) → make the call
        """
        try:
            dashboard = self.meraki_client.get_dashboard()
            section_obj = getattr(dashboard, section)
            method_obj = getattr(section_obj, method)

            sig = inspect.signature(method_obj)
            parameters = {}

            for param_name, param in sig.parameters.items():
                if param_name in SDK_INTERNAL_PARAMS:
                    continue

                param_type = "Any"
                if param.annotation != inspect.Parameter.empty:
                    if hasattr(param.annotation, "__name__"):
                        param_type = param.annotation.__name__
                    else:
                        param_type = str(param.annotation)
                elif param.default != inspect.Parameter.empty and param.default is not None:
                    param_type = type(param.default).__name__

                param_info = {
                    "required": param.default == inspect.Parameter.empty,
                    "type": param_type,
                }

                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default

                parameters[param_name] = param_info

            required_params = [k for k, v in parameters.items() if v["required"]]
            optional_params = [k for k, v in parameters.items() if not v["required"]]

            result = {
                "section": section,
                "method": method,
                "parameters": parameters,
                "usage_example": (
                    f"execute_api_endpoint(section='{section}', method='{method}', ...)"
                ),
            }

            # Add complexity warning for endpoints with 3+ required params
            if len(required_params) >= 3:
                result["complexity_warning"] = {
                    "message": f"This endpoint requires {len(required_params)} parameters",
                    "required_params": required_params,
                    "suggestion": (
                        "Consider using the 'parameters_guide' prompt for detailed "
                        "guidance on providing multiple parameters"
                    ),
                }

            # Add helpful summary
            result["summary"] = {
                "required_count": len(required_params),
                "optional_count": len(optional_params),
                "required_params": required_params,
            }

            return json.dumps(result, indent=2)

        except AttributeError:
            error_result = {
                "error": f"Endpoint not found: {section}.{method}",
                "suggestion": "Use search_api_endpoints to find available endpoints",
            }
            return json.dumps(error_result, indent=2)
        except Exception as e:
            logger.error(f"Failed to get endpoint parameters: {e}")
            error_result = {"error": f"Failed to get parameters: {str(e)}"}
            return json.dumps(error_result, indent=2)

    async def execute_meraki_api_endpoint(
        self,
        section: str,
        method: str,
        serial: str | None = None,
        portId: str | None = None,
        networkId: str | None = None,
        organizationId: str | None = None,
        key_id: str | None = None,
        kwargs: str | dict[str, Any] = "{}",
    ) -> str | dict[str, Any]:
        """
        Execute any Meraki Dashboard API endpoint with dynamic parameter handling.

        This is the primary execution tool that calls the actual Meraki API. It handles
        authentication, rate limiting, error handling, and response formatting
        automatically.

        COMMON DIRECT USAGE:
        1. Get device port configuration:
           execute_api_endpoint(section="switch", method="getDeviceSwitchPort",
                              serial="Q2XX-XXXX-XXXX", portId="4")

        2. Get device status:
           execute_api_endpoint(section="devices", method="getDevice",
                              serial="Q2XX-XXXX-XXXX")

        3. Get network clients with additional parameters:
           execute_api_endpoint(
                section="networks",
                method="getNetworkClients",
                networkId="N_12345",
                kwargs='{"timespan": 3600, "perPage": 50}'
            )

        MULTI-KEY USAGE (MSP Mode):
        4. Execute with specific API key:
           execute_api_endpoint(
                section="organizations",
                method="getOrganizations",
                key_id="customer_a"
            )

        5. Auto-select key by organization:
           execute_api_endpoint(
                section="networks",
                method="getOrganizationNetworks",
                organizationId="123456"  # System finds correct key
            )

        Args:
            section (str): API section name (e.g., "switch", "devices", "networks")
            method (str): API method name (e.g., "getDeviceSwitchPort", "getDevice")
            serial (str, optional): Device serial number
            portId (str, optional): Port identifier (e.g., "4", "1", "2")
            networkId (str, optional): Network identifier
            organizationId (str, optional): Organization identifier
            key_id (str, optional): API key identifier for multi-key mode
                Examples: "customer_a", "key_1", etc.
                If not specified, uses default key or auto-selects by organizationId
            kwargs (str): JSON string containing any additional parameters
                Examples:
                    '{"timespan": 3600}'
                    '{"perPage": 50, "startingAfter": "2023-01-01"}'

        Returns:
            JSON string containing API response or error details
        """
        try:
            cache_key = self._get_cache_key(
                section,
                method,
                serial=serial,
                portId=portId,
                networkId=networkId,
                organizationId=organizationId,
                kwargs=kwargs,
            )

            if method.startswith("get") and cache_key in self._response_cache:
                cache_entry = self._response_cache[cache_key]
                if self._is_cache_valid(cache_entry):
                    logger.info(f"Cache hit for {section}.{method}")
                    return cache_entry["response"]

            def _call_api():
                # Get dashboard with key selection support
                dashboard = self.meraki_client.get_dashboard(
                    key_id=key_id, organization_id=organizationId
                )
                section_obj = getattr(dashboard, section)
                method_obj = getattr(section_obj, method)

                all_params = {
                    "serial": serial,
                    "portId": portId,
                    "networkId": networkId,
                    "organizationId": organizationId,
                }

                try:
                    if kwargs and isinstance(kwargs, str) and kwargs.strip():
                        extra_params = json.loads(kwargs)
                        if isinstance(extra_params, dict):
                            all_params.update(extra_params)
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning(f"Invalid additional_params JSON: {e}")

                filtered_params = {
                    k: v for k, v in all_params.items() if v is not None and v != ""
                }

                sig = inspect.signature(method_obj)
                missing_params = []

                for param_name, param in sig.parameters.items():
                    if (
                        param.default == inspect.Parameter.empty
                        and param_name != "kwargs"
                    ):
                        if param_name not in filtered_params:
                            missing_params.append(param_name)

                if missing_params:
                    raise ValueError(
                        f"Missing required parameters: {', '.join(missing_params)}"
                    )

                return method_obj(**filtered_params)

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _call_api)

            response_json = json.dumps(result, indent=2, default=str)
            if method.startswith("get"):
                self._response_cache[cache_key] = {
                    "response": response_json,
                    "timestamp": time.time(),
                }

            return response_json

        except ValueError as ve:
            error_result = {
                "error": str(ve),
                "section": section,
                "method": method,
                "provided_params": extract_non_empty_params(
                    serial=serial,
                    portId=portId,
                    networkId=networkId,
                    organizationId=organizationId,
                ),
                "additional_params_provided": kwargs,
                "suggestion": (
                    "Use get_meraki_endpoint_parameters to see all required parameters"
                ),
            }
            return json.dumps(error_result, indent=2)

        except AttributeError:
            error_result = {
                "error": f"Endpoint '{section}.{method}' not found",
                "suggestion": (
                    "Use search_meraki_api_endpoints to find the correct endpoint"
                ),
            }
            return json.dumps(error_result, indent=2)

        except Exception as e:
            logger.error(f"API call failed: {e}")

            error_result: dict[str, Any] = {
                "error": f"API call failed: {str(e)}",
                "section": section,
                "method": method,
                "provided_params": extract_non_empty_params(
                    serial=serial,
                    portId=portId,
                    networkId=networkId,
                    organizationId=organizationId,
                ),
            }

            if kwargs:
                error_result["additional_params"] = kwargs

            return json.dumps(error_result, indent=2)
