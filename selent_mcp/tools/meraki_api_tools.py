import asyncio
import inspect
import json
import logging
import re
import time
from typing import Dict, List, Optional, Tuple

from mcp.server.fastmcp import FastMCP

from selent_mcp.services.meraki_client import MerakiClient

logger = logging.getLogger(__name__)


class MerakiApiTools:
    """Dynamic tool class that can discover and execute any Meraki API endpoint"""

    def __init__(self, mcp: FastMCP, meraki_client: MerakiClient, enabled: bool):
        self.mcp = mcp
        self.meraki_client = meraki_client
        self._api_cache: Dict[str, List[str]] = {}
        self._device_cache: Dict[str, Dict] = {}
        self._response_cache: Dict[str, Dict] = {}
        self._cache_ttl = 300
        self._search_patterns: List[Dict] = []
        self._patterns_initialized = False
        self.enabled = enabled
        if self.enabled:
            self._register_tools()
        else:
            logger.info("MerakiApiTools not registered (MERAKI_API_KEY not set)")

    def _generate_keywords_from_method(self, section: str, method: str) -> List[str]:
        """Generate semantic keywords from section and method names"""
        keywords = []

        keywords.append(section.lower())
        if section == "organizations":
            keywords.extend(["org", "orgs", "organization"])
        elif section == "appliance":
            keywords.extend(["mx", "security", "firewall"])
        elif section == "switch":
            keywords.extend(["ms", "switching", "port", "ports"])
        elif section == "wireless":
            keywords.extend(["mr", "wifi", "wireless", "access"])
        elif section == "camera":
            keywords.extend(["mv", "cameras", "video"])
        elif section == "sensor":
            keywords.extend(["mt", "sensors", "environmental"])
        elif section == "networks":
            keywords.extend(["network", "net"])
        elif section == "devices":
            keywords.extend(["device", "hardware"])

        method_parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)", method)
        method_words = [part.lower() for part in method_parts]
        keywords.extend(method_words)

        if "get" in method_words:
            keywords.extend(["show", "list", "fetch", "retrieve"])
        elif "update" in method_words:
            keywords.extend(["modify", "change", "edit", "set"])
        elif "create" in method_words:
            keywords.extend(["add", "new", "make"])
        elif "delete" in method_words:
            keywords.extend(["remove", "destroy"])

        if any(word in method_words for word in ["firewall", "rules"]):
            keywords.extend(["security", "l3", "layer3", "policy"])
        if any(word in method_words for word in ["client", "clients"]):
            keywords.extend(["connected", "devices", "users"])
        if any(word in method_words for word in ["port", "ports"]):
            keywords.extend(["interface", "config", "configuration", "settings"])
        if any(word in method_words for word in ["vpn"]):
            keywords.extend(["tunnel", "connection", "site"])
        if any(word in method_words for word in ["ssid"]):
            keywords.extend(["network", "wifi", "wireless"])

        return list(set(keywords))

    def _calculate_method_weight(self, method: str) -> float:
        """Calculate priority weight for a method based on common usage patterns"""
        method_lower = method.lower()

        if method in ["getOrganizations", "getDevice", "getNetworkClients"]:
            return 1.0
        elif "organization" in method_lower and method.startswith("get"):
            return 0.9
        elif "network" in method_lower and method.startswith("get"):
            return 0.8
        elif method.startswith("get") and "device" in method_lower:
            return 0.8
        elif method.startswith("get"):
            return 0.7
        elif method.startswith("update"):
            return 0.6
        elif method.startswith("create"):
            return 0.5
        elif method.startswith("delete"):
            return 0.4
        else:
            return 0.3

    def _get_method_parameters(self, section: str, method: str) -> List[str]:
        """Get required parameters for a method using inspection"""
        try:
            dashboard = self.meraki_client.get_dashboard()
            section_obj = getattr(dashboard, section)
            method_obj = getattr(section_obj, method)

            sig = inspect.signature(method_obj)
            required_params = []

            for param_name, param in sig.parameters.items():
                if param.default == inspect.Parameter.empty and param_name != "kwargs":
                    required_params.append(param_name)

            return required_params
        except Exception:
            return []

    def _generate_dynamic_patterns(self) -> List[Dict]:
        """Generate semantic patterns for ALL available API endpoints"""
        api_structure = self._discover_api_structure()
        patterns = []

        for section, methods in api_structure.items():
            for method in methods:
                keywords = self._generate_keywords_from_method(section, method)
                weight = self._calculate_method_weight(method)
                required_params = self._get_method_parameters(section, method)

                method_parts = re.findall(
                    r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)", method
                )
                description = " ".join(method_parts).lower()

                pattern = {
                    "keywords": keywords,
                    "section": section,
                    "method": method,
                    "description": description,
                    "required_params": required_params,
                    "weight": weight,
                }
                patterns.append(pattern)

        return patterns

    def _initialize_search_patterns(self) -> List[Dict]:
        """Initialize semantic search patterns by generating them dynamically from API structure"""
        return self._generate_dynamic_patterns()

    def _calculate_semantic_score(self, query: str, pattern: Dict) -> float:
        """Calculate semantic similarity score between query and pattern"""
        query_words = set(re.findall(r"\b\w+\b", query.lower()))
        pattern_keywords = set(pattern["keywords"])

        intersection = len(query_words.intersection(pattern_keywords))
        union = len(query_words.union(pattern_keywords))

        if union == 0:
            return 0.0

        jaccard_score = intersection / union

        weighted_score = jaccard_score * pattern["weight"]

        exact_matches = sum(1 for word in query_words if word in pattern_keywords)
        exact_bonus = min(exact_matches * 0.1, 0.3)

        return min(weighted_score + exact_bonus, 1.0)

    def _ensure_patterns_initialized(self):
        """Ensure search patterns are initialized (lazy loading)"""
        if not self._patterns_initialized:
            logger.info(
                "Initializing semantic search patterns for all API endpoints..."
            )
            self._search_patterns = self._generate_dynamic_patterns()
            self._patterns_initialized = True
            logger.info(f"Initialized {len(self._search_patterns)} semantic patterns")

    def _find_best_pattern_match(self, query: str) -> Optional[Dict]:
        """Find the best matching pattern for the given query"""
        self._ensure_patterns_initialized()

        best_score = 0.0
        best_pattern = None

        for pattern in self._search_patterns:
            score = self._calculate_semantic_score(query, pattern)
            if score > best_score and score > 0.3:
                best_score = score
                best_pattern = pattern

        return best_pattern

    def _register_tools(self):
        """Register the dynamic tools with the MCP server"""
        self.mcp.tool()(self.search_meraki_api_endpoints)
        self.mcp.tool()(self.execute_meraki_api_endpoint)
        self.mcp.tool()(self.get_meraki_endpoint_parameters)

    def _discover_api_structure(self) -> Dict[str, List[str]]:
        """Discover all available API sections and their methods"""
        if self._api_cache:
            return self._api_cache

        try:
            dashboard = self.meraki_client.get_dashboard()
            api_structure = {}

            # Get all API sections
            sections = [
                attr
                for attr in dir(dashboard)
                if not attr.startswith("_")
                and hasattr(getattr(dashboard, attr), "__class__")
                and "api" in str(type(getattr(dashboard, attr))).lower()
            ]

            for section in sections:
                section_obj = getattr(dashboard, section)
                methods = [
                    method
                    for method in dir(section_obj)
                    if not method.startswith("_")
                    and callable(getattr(section_obj, method))
                ]
                api_structure[section] = methods

            self._api_cache = api_structure
            return api_structure

        except Exception as e:
            logger.error(f"Failed to discover API structure: {e}")
            return {}

    def _get_cache_key(self, section: str, method: str, **params) -> str:
        """Generate a cache key for API responses"""
        sorted_params = sorted(params.items())
        return f"{section}.{method}:{hash(str(sorted_params))}"

    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        return time.time() - cache_entry.get("timestamp", 0) < self._cache_ttl

    async def search_meraki_api_endpoints(self, query: str) -> str:
        """
        Search and discover Meraki API endpoints using semantic similarity and natural language.

        This tool uses intelligent pattern matching and semantic scoring to find the most relevant
        API endpoints. It analyzes query intent and matches against known patterns for instant results.

        SEMANTIC MATCHING:
        - Organizations: "get organizations", "list orgs", "show my organizations"
        - Device Status: "device info", "device details", "check device status"
        - Port Config: "device port config", "switch port", "port configuration"
        - Firewall Rules: "firewall rules", "security rules", "l3 firewall"
        - Network Clients: "network clients", "connected devices", "client list"

        Args:
            query (str): Natural language search term. Examples:
                - "get my organizations" → organizations.getOrganizations
                - "device Q123 port 4 config" → switch.getDeviceSwitchPort
                - "network clients" → networks.getNetworkClients
                - "firewall rules" → appliance.getNetworkApplianceFirewallL3FirewallRules

        Returns:
            JSON string containing:
            - query: The search term used
            - direct_match: Best semantic match with confidence score
            - matches: Fallback section matches if no direct match
            - usage: Instructions for next steps
        """
        # Try semantic pattern matching first
        best_pattern = self._find_best_pattern_match(query)

        direct_match = None
        if best_pattern:
            direct_match = {
                "section": best_pattern["section"],
                "method": best_pattern["method"],
                "description": best_pattern["description"],
                "required_params": best_pattern["required_params"],
                "confidence": self._calculate_semantic_score(query, best_pattern),
            }

        matches = {}

        # Fallback to traditional search if no semantic match found
        if not direct_match:
            api_structure = self._discover_api_structure()
            query_lower = query.lower()

            for section, methods in api_structure.items():
                section_matches = []

                # Section name matching
                if any(word in section.lower() for word in query_lower.split()):
                    section_matches.extend(methods[:8])

                # Method name matching
                for method in methods:
                    if any(word in method.lower() for word in query_lower.split()):
                        if method not in section_matches:
                            section_matches.append(method)

                if section_matches:
                    matches[section] = section_matches[:8]

        result = {
            "query": query,
            "direct_match": direct_match,
            "matches": matches,
            "usage": "Use execute_api_endpoint with section='<section>' and method='<method>' to call an endpoint",
        }

        return json.dumps(result, indent=2)

    async def get_meraki_endpoint_parameters(self, section: str, method: str) -> str:
        """
        Discover required and optional parameters for any Meraki API endpoint.

        This tool provides complete parameter documentation for API methods, including
        data types, required vs optional parameters, and default values. Use this after
        finding endpoints with search_api_endpoints and before calling execute_api_endpoint.

        WHEN TO USE:
        - Before making API calls to understand required parameters
        - To validate you have all necessary data before execution
        - To understand optional parameters for enhanced functionality
        - To check parameter data types for proper formatting

        Args:
            section (str): API section name from search results. Must be exact match. Examples:
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
              "usage_example": "execute_api_endpoint(section='devices', method='getDevice', serial='Q2XX-XXXX-XXXX')"
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
                param_info = {
                    "required": param.default == inspect.Parameter.empty,
                    "type": str(param.annotation)
                    if param.annotation != inspect.Parameter.empty
                    else "unknown",
                }
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = param.default

                parameters[param_name] = param_info

            result = {
                "section": section,
                "method": method,
                "parameters": parameters,
                "usage_example": f"execute_api_endpoint(section='{section}', method='{method}', ...)",
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
        serial: Optional[str] = None,
        portId: Optional[str] = None,
        networkId: Optional[str] = None,
        organizationId: Optional[str] = None,
        kwargs: str = "{}",
    ) -> str:
        """
        Execute any Meraki Dashboard API endpoint with dynamic parameter handling.

        This is the primary execution tool that calls the actual Meraki API. It handles
        authentication, rate limiting, error handling, and response formatting automatically.

        COMMON DIRECT USAGE:
        1. Get device port configuration:
           execute_api_endpoint(section="switch", method="getDeviceSwitchPort",
                              serial="Q2XX-XXXX-XXXX", portId="4")

        2. Get device status:
           execute_api_endpoint(section="devices", method="getDevice",
                              serial="Q2XX-XXXX-XXXX")

        3. Get network clients with additional parameters:
           execute_api_endpoint(section="networks", method="getNetworkClients",
                              networkId="N_12345", kwargs='{"timespan": 3600, "perPage": 50}')

        Args:
            section (str): API section name (e.g., "switch", "devices", "networks")
            method (str): API method name (e.g., "getDeviceSwitchPort", "getDevice")
            serial (str, optional): Device serial number
            portId (str, optional): Port identifier (e.g., "4", "1", "2")
            networkId (str, optional): Network identifier
            organizationId (str, optional): Organization identifier
            kwargs (str): JSON string containing any additional parameters
                Examples: '{"timespan": 3600}', '{"perPage": 50, "startingAfter": "2023-01-01"}'

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
                dashboard = self.meraki_client.get_dashboard()
                section_obj = getattr(dashboard, section)
                method_obj = getattr(section_obj, method)

                all_params = {
                    "serial": serial,
                    "portId": portId,
                    "networkId": networkId,
                    "organizationId": organizationId,
                }

                try:
                    if kwargs and kwargs.strip():
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
                "provided_params": [
                    k
                    for k, v in {
                        "serial": serial,
                        "portId": portId,
                        "networkId": networkId,
                        "organizationId": organizationId,
                    }.items()
                    if v is not None and v != ""
                ],
                "additional_params_provided": kwargs,
                "suggestion": "Use get_meraki_endpoint_parameters to see all required parameters",
            }
            return json.dumps(error_result, indent=2)

        except AttributeError:
            api_structure = self._discover_api_structure()
            available_sections = list(api_structure.keys())

            if section not in available_sections:
                error_result = {
                    "error": f"Section '{section}' not found",
                    "available_sections": available_sections[:10],
                    "suggestion": "Use search_meraki_api_endpoints to find the correct section",
                }
            else:
                available_methods = api_structure.get(section, [])
                error_result = {
                    "error": f"Method '{method}' not found in section '{section}'",
                    "available_methods": available_methods[:20],
                    "suggestion": "Use search_meraki_api_endpoints to find the correct method",
                }

            return json.dumps(error_result, indent=2)

        except Exception as e:
            logger.error(f"API call failed: {e}")

            error_result = {
                "error": f"API call failed: {str(e)}",
                "section": section,
                "method": method,
                "provided_params": [
                    k
                    for k, v in {
                        "serial": serial,
                        "portId": portId,
                        "networkId": networkId,
                        "organizationId": organizationId,
                    }.items()
                    if v is not None and v != ""
                ],
            }
            if kwargs:
                error_result["additional_params"] = kwargs
            return json.dumps(error_result, indent=2)
