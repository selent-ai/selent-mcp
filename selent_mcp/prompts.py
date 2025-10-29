"""Prompts to guide LLMs on using Selent MCP tools effectively."""

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register all prompts with the MCP server."""

    @mcp.prompt(
        description="IMPORTANT: Multi-key setup guide - Run discover_all_organizations() first!"
    )
    def multi_key_startup_guide() -> str:
        """
        CRITICAL startup guide for multi-key mode.

        When multiple API keys are detected, LLM should ALWAYS run
        discover_all_organizations() early in the conversation to enable
        automatic key selection by organization context.
        """
        return """# Multi-Key Mode Detected - Quick Start

## ⚠️ IMPORTANT: Run Discovery First

When you detect multiple API keys are configured (use `list_api_keys()` to check),
you MUST run organization discovery to enable intelligent key selection:

```
discover_all_organizations()
```

This command:
- Discovers all organizations for each API key
- Builds a map of organization ID → API key
- Enables automatic key selection when users mention organizations

## Why This Matters

Without discovery, when a user says "Get devices for Organization X", you won't know
which API key owns that organization. You'll get 404 errors or use the wrong key.

WITH discovery, the system automatically:
- Maps "Organization X" (org ID: 236620) → "key_id" key
- Selects the correct key when organizationId is provided
- Handles cross-customer queries seamlessly

## Recommended Startup Flow

When the conversation starts and you detect multi-key mode:

1. **List available keys:**
   ```
   list_api_keys()
   ```

2. **Discover all organizations:**
   ```
   discover_all_organizations()
   ```

3. **Now you can use organization context naturally:**
   ```
   execute_meraki_api_endpoint(
       section='organizations',
       method='getOrganizationDevices',
       organizationId='236620'  # Auto-selects 'key_id' key
   )
   ```

## User Intent Recognition

When users mention organization names or ask about specific customers:
- "Get devices in Organization X" → Look up org ID → Auto-select key
- "Show me Sebastian Inc. networks" → Look up org ID → Auto-select key
- "What devices does customer X have?" → Use their specific key

## Example Session

```
User: "Get all organizations"
Assistant: [runs list_api_keys() to see multi-key mode]
Assistant: [runs discover_all_organizations() to enable smart selection]
Assistant: [runs execute_meraki_api_endpoint with appropriate keys]

User: "Get all devices in Organization X"
Assistant: [knows org 236620 belongs to 'key_id' key from discovery]
Assistant: [executes with organizationId='236620', auto-selects key_id key]
```

## Key Points

- Discovery takes 5-10 seconds but only runs once
- After discovery, key selection is automatic and instant
- Without discovery, you must manually specify key_id on every call
- Discovery enables natural language organization references

ALWAYS discover organizations early when multiple keys are configured!
"""

    @mcp.prompt(description="Common parameter formats and examples for Meraki API")
    def parameter_examples_guide() -> str:
        """
        Provides format examples for common Meraki API parameters.

        Use this when you need to show users what format parameters should be in.
        """
        return """# Common Meraki API Parameter Examples

## Device Parameters

**serial** (string)
- Format: QXXX-XXXX-XXXX (Q followed by 3 blocks of 4 characters)
- Example: `Q2XX-ABCD-1234`
- Description: Unique device serial number
- Used in: Device operations, switch ports, camera settings

**portId** (string)
- Format: Number as string
- Examples: `"1"`, `"4"`, `"24"`
- Description: Physical port number on switch or appliance
- Used in: Switch port configuration, port status

## Network & Organization Parameters

**networkId** (string)
- Format: L_XXXXXXXXX (L followed by numbers)
- Example: `L_123456789`
- Description: Unique network identifier
- Used in: Network clients, firewall rules, SSIDs

**organizationId** (string)
- Format: Numeric string
- Example: `"123456"`
- Description: Organization identifier
- Used in: Organization-wide operations, inventory

## Filtering & Pagination Parameters

**timespan** (integer)
- Format: Seconds as integer
- Examples:
  - `3600` (1 hour)
  - `86400` (24 hours)
  - `604800` (7 days)
- Description: Time period for historical data
- Used in: Client history, traffic analytics

**perPage** (integer)
- Format: Number (1-1000)
- Example: `100`
- Description: Results per page (max 1000)
- Used in: Paginated list endpoints

**startingAfter** (string)
- Format: ISO 8601 timestamp
- Example: `"2023-01-01T00:00:00Z"`
- Description: Start timestamp for date range
- Used in: Historical queries

**endingBefore** (string)
- Format: ISO 8601 timestamp
- Example: `"2023-12-31T23:59:59Z"`
- Description: End timestamp for date range
- Used in: Historical queries

## Special Parameters

**kwargs** (JSON string)
- Format: JSON object as string
- Examples:
  - `'{"timespan": 3600}'`
  - `'{"perPage": 100, "startingAfter": "2023-01-01T00:00:00Z"}'`
  - `'{"enabled": true, "vlan": 10}'`
- Description: Additional parameters passed as JSON
- Used in: When parameters aren't directly supported as function args
- **Important**: Must be valid JSON string with double quotes

## How to Use These Examples

When calling `execute_meraki_api_endpoint`:

### Simple Parameters (Direct)
```python
execute_meraki_api_endpoint(
    section='devices',
    method='getDevice',
    serial='Q2XX-ABCD-1234'
)
```

### Multiple Required Parameters
```python
execute_meraki_api_endpoint(
    section='switch',
    method='getDeviceSwitchPort',
    serial='Q2XX-ABCD-1234',
    portId='4'
)
```

### With Additional Parameters (via kwargs)
```python
execute_meraki_api_endpoint(
    section='networks',
    method='getNetworkClients',
    networkId='L_123456789',
    kwargs='{"timespan": 3600, "perPage": 50}'
)
```

## Tips

1. **Always use correct ID format**: Check the prefix (Q for devices, L for networks)
2. **JSON in kwargs**: Use double quotes, not single quotes inside the JSON
3. **Port numbers**: Always strings, not integers ("4" not 4)
4. **Timestamps**: Use ISO 8601 format with timezone (Z for UTC)
5. **Boolean values**: Use true/false (lowercase) in JSON

"""

    @mcp.prompt(
        description="Guide for discovering and using Meraki API endpoints through semantic search"
    )
    def meraki_api_workflow(task: str) -> list[str]:
        """
        Provides step-by-step guidance for working with Meraki API endpoints.

        Use this prompt when you need to help a user interact with the Meraki Dashboard API
        but don't know which specific endpoint to use.

        Args:
            task: The user's goal (e.g., "get device configuration", "list organizations")
        """
        return [
            f"# Meraki API Workflow for: {task}",
            "",
            "I'll help you accomplish this task using the Meraki API. Here's the recommended workflow:",
            "",
            "## Step 1: Search for Relevant Endpoints",
            "",
            f"First, I'll search for API endpoints related to '{task}':",
            "",
            "```",
            f'search_meraki_api_endpoints(query="{task}", limit=5)',
            "```",
            "",
            "This will return the most relevant API methods with their:",
            "- Section (e.g., 'devices', 'networks', 'organizations')",
            "- Method name (e.g., 'getDevice', 'getNetworkClients')",
            "- Description (what the endpoint does)",
            "- Relevance score (how well it matches your query)",
            "",
            "## Step 2: Get Parameter Details",
            "",
            "Once I identify the right endpoint, I'll get its parameter requirements:",
            "",
            "```",
            "get_meraki_endpoint_parameters(section='<section>', method='<method>')",
            "```",
            "",
            "This shows:",
            "- Required parameters (must be provided)",
            "- Optional parameters (can be omitted)",
            "- Parameter types (str, int, bool, list, dict)",
            "- Default values for optional parameters",
            "",
            "## Step 3: Execute the API Call",
            "",
            "Finally, I'll execute the endpoint with the appropriate parameters:",
            "",
            "```",
            "execute_meraki_api_endpoint(",
            "    section='<section>',",
            "    method='<method>',",
            "    serial='...',  # if needed",
            "    networkId='...',  # if needed",
            "    organizationId='...',  # if needed",
            '    kwargs=\'{"additional": "parameters"}\'  # for other params',
            ")",
            "```",
            "",
            "## Common Patterns",
            "",
            "**For device-specific operations:**",
            "- Provide `serial` parameter (e.g., 'Q2XX-XXXX-XXXX')",
            "- May also need `portId` for switch ports",
            "",
            "**For network-level operations:**",
            "- Provide `networkId` parameter (e.g., 'L_123456789')",
            "",
            "**For organization-wide operations:**",
            "- Provide `organizationId` parameter",
            "- Or first get organizations with 'getOrganizations'",
            "",
            "**For additional parameters:**",
            "- Use the `kwargs` field with JSON string",
            '- Example: kwargs=\'{"timespan": 3600, "perPage": 50}\'',
            "",
            "## Tips for Better Results",
            "",
            "1. **Use natural language in searches:**",
            '   - "get device status" works better than just "device"',
            '   - "switch port configuration" is clearer than "port"',
            "",
            "2. **Check parameter requirements carefully:**",
            "   - Missing required parameters will cause errors",
            "   - Use get_meraki_endpoint_parameters() to verify",
            "",
            "3. **Handle IDs properly:**",
            "   - If user doesn't provide IDs, get them first",
            "   - Example: Get organizationId before querying org resources",
            "",
            "Let me now proceed with these steps to help you accomplish your task.",
        ]

    @mcp.prompt(
        description="Quick reference for searching Meraki API endpoints with examples"
    )
    def search_endpoints_guide() -> str:
        """
        Provides quick examples of effective semantic searches for Meraki API endpoints.

        Use this when you need inspiration for search queries or want to show
        users how to effectively search for API methods.
        """
        return """# Searching Meraki API Endpoints

## How It Works

The `search_meraki_api_endpoints` tool uses semantic search to find relevant API methods
based on natural language queries. It searches through 816 Meraki API endpoints and
returns the most relevant matches.

## Effective Search Examples

### Device Operations
- "get device status" → finds getDevice, getDeviceUplink, etc.
- "configure switch port" → finds updateDeviceSwitchPort
- "device port configuration" → finds getDeviceSwitchPort
- "wireless access point settings" → finds wireless device configs

### Network Management
- "list network clients" → finds getNetworkClients
- "network firewall rules" → finds getNetworkApplianceFirewallL3FirewallRules
- "create new network" → finds createOrganizationNetwork
- "network topology" → finds getNetworkTopologyLinkLayer

### Organization Level
- "get my organizations" → finds getOrganizations
- "list all devices in organization" → finds getOrganizationDevices
- "organization inventory" → finds getOrganizationInventoryDevices
- "organization configuration templates" → finds config template methods

### Security & Compliance
- "security appliance settings" → finds MX appliance endpoints
- "content filtering" → finds getNetworkApplianceContentFiltering
- "VPN configuration" → finds VPN-related endpoints
- "port forwarding rules" → finds port forwarding endpoints

### Monitoring & Analytics
- "client traffic" → finds traffic analysis endpoints
- "device uplink information" → finds getDeviceUplink
- "wireless client connectivity" → finds wireless client methods
- "network events" → finds getNetworkEvents

## Search Parameters

**query** (required): Natural language description of what you're looking for

**limit** (optional, default: 5): Number of results to return (1-10 recommended)

**min_score** (optional, default: 0.5): Minimum similarity score (0.0-1.0)
  - Higher values = more strict matching
  - Lower values = more permissive matching

## Example Usage

```
# Basic search
search_meraki_api_endpoints(query="get organizations", limit=3)

# More results
search_meraki_api_endpoints(query="firewall rules", limit=10)

# Stricter matching
search_meraki_api_endpoints(query="device status", limit=5, min_score=0.7)
```

## Interpreting Results

Each result includes:
- **score**: Relevance (0.0-1.0, higher is better)
- **section**: API section (e.g., "devices", "networks")
- **method**: Exact method name to use
- **description**: What the endpoint does

Scores above 0.7 are usually very relevant.
Scores between 0.5-0.7 may be partially relevant.
Scores below 0.5 are likely not what you're looking for.

## Next Steps

After finding endpoints:
1. Use `get_meraki_endpoint_parameters()` to see required parameters
2. Use `execute_meraki_api_endpoint()` to call the API
"""

    @mcp.prompt(
        description="Guide for understanding API endpoint parameters and requirements"
    )
    def parameters_guide(section: str, method: str) -> str:
        """
        Explains how to interpret parameter requirements for a specific endpoint.

        Args:
            section: The API section (e.g., 'devices', 'networks')
            method: The method name (e.g., 'getDevice', 'getNetworkClients')
        """
        return f"""# Understanding Parameters for {section}.{method}

## How to Get Parameter Details

Use this command to see all parameters:

```
get_meraki_endpoint_parameters(section="{section}", method="{method}")
```

## Understanding the Response

The response will show each parameter with:

### Required Parameters
These MUST be provided or the API call will fail.
```json
{{
  "serial": {{
    "required": true,
    "type": "<class 'str'>",
    "description": "Device serial number"
  }}
}}
```

### Optional Parameters
These can be omitted - they have default values.
```json
{{
  "perPage": {{
    "required": false,
    "type": "<class 'int'>",
    "default": 100
  }}
}}
```

## Common Parameter Types

**str (string)**: Text values
- Device serials: "Q2XX-XXXX-XXXX"
- Network IDs: "L_123456789"
- Organization IDs: "123456"
- Names and descriptions: "My Device"

**int (integer)**: Numeric values
- Timespan: 3600 (seconds)
- Port numbers: 8080
- Page size: 50

**bool (boolean)**: True/False values
- enabled: true
- disableRemoteStatusPage: false

**list**: Arrays of values
- tags: ["tag1", "tag2"]
- allowedUrls: ["https://example.com"]

**dict**: JSON objects
- settings: {{"vlan": 10, "enabled": true}}

## How to Provide Parameters

### Direct Parameters (Most Common)
For frequently used parameters, pass them directly:

```python
execute_meraki_api_endpoint(
    section="{section}",
    method="{method}",
    serial="Q2XX-XXXX-XXXX",          # if needed
    networkId="L_123456789",          # if needed
    organizationId="123456",          # if needed
    portId="4"                        # if needed (for switch ports)
)
```

### Additional Parameters (Via kwargs)
For other parameters, use the kwargs field with JSON:

```python
execute_meraki_api_endpoint(
    section="{section}",
    method="{method}",
    networkId="L_123456789",
    kwargs='{{"timespan": 3600, "perPage": 50, "startingAfter": "2023-01-01"}}'
)
```

## Common Patterns

**For GET operations (retrieving data):**
- Usually only require ID parameters (serial, networkId, etc.)
- May have optional filtering parameters (timespan, perPage)

**For UPDATE operations (modifying settings):**
- Require ID parameter to identify the resource
- Require configuration parameters in kwargs
- Example: Update switch port settings

**For CREATE operations (creating new resources):**
- Usually require parent ID (organizationId, networkId)
- Require configuration for the new resource in kwargs

## Tips

1. Always check which parameters are required vs optional
2. For complex objects, construct the JSON carefully in kwargs
3. String values in JSON must be quoted: "value"
4. Numbers and booleans should NOT be quoted: 100, true
5. If unsure about format, start with required params only

Would you like me to execute this endpoint now? Please provide the required parameters.
"""

    @mcp.prompt(description="Troubleshooting guide for common API execution errors")
    def troubleshooting_guide() -> str:
        """
        Provides solutions for common errors when executing Meraki API endpoints.

        Use this when an API call fails or returns an error.
        """
        return """# Troubleshooting Meraki API Calls

## Common Errors and Solutions

### 1. Missing Required Parameters

**Error:**
```json
{
  "error": "Missing required parameters: networkId",
  "suggestion": "Use get_meraki_endpoint_parameters to see all required parameters"
}
```

**Solution:**
- Run `get_meraki_endpoint_parameters(section, method)` first
- Check which parameters have `"required": true`
- Provide all required parameters in the execute call

### 2. Endpoint Not Found

**Error:**
```json
{
  "error": "Endpoint 'devices.getDeviceStatus' not found",
  "suggestion": "Use search_meraki_api_endpoints to find the correct endpoint"
}
```

**Solution:**
- The method name might be wrong
- Use `search_meraki_api_endpoints(query="your search")` to find correct name
- Copy the exact section and method from search results

### 3. Invalid Parameter Format

**Error:**
```json
{
  "error": "API call failed: Invalid parameter format"
}
```

**Solution:**
- Check parameter types with `get_meraki_endpoint_parameters()`
- Ensure JSON in kwargs is properly formatted
- Common issues:
  - Missing quotes around strings: "value" not value
  - Extra/missing commas in JSON
  - Incorrect nesting of objects

### 4. Authentication Errors

**Error:**
```
{
  "error": "401 Unauthorized"
}
```

**Solution:**
- API key might be invalid or expired
- Check MERAKI_API_KEY environment variable
- Verify API key has necessary permissions for this operation

### 5. Resource Not Found

**Error:**
```
{
  "error": "404 Not Found"
}
```

**Solution:**
- The ID you provided doesn't exist
- Verify serial numbers, network IDs, organization IDs
- Use list/get operations to find valid IDs first

### 6. Rate Limiting

**Error:**
```
{
  "error": "429 Too Many Requests"
}
```

**Solution:**
- You've hit Meraki's API rate limit
- Wait a moment before retrying
- The MCP server has built-in rate limit handling

### 7. Insufficient Permissions

**Error:**
```
{
  "error": "403 Forbidden"
}
```

**Solution:**
- Your API key doesn't have permission for this operation
- Check if you have the right access level in the Meraki Dashboard
- Some operations require full organization admin access

## Debugging Workflow

1. **Verify the endpoint exists:**
   ```
   search_meraki_api_endpoints(query="your query")
   ```

2. **Check parameter requirements:**
   ```
   get_meraki_endpoint_parameters(section="...", method="...")
   ```

3. **Start with minimal parameters:**
   - Provide only required parameters first
   - Add optional parameters one at a time

4. **Validate IDs:**
   - Ensure serial numbers, network IDs are correct
   - Use getOrganizations, getNetworks, etc. to get valid IDs

5. **Check JSON formatting:**
   - Use a JSON validator for complex kwargs
   - Test with simple parameters first

## Getting Help

If you continue having issues:
1. Share the exact error message
2. Show the full command you're trying to run
3. Confirm which parameters you're providing

I'll help you diagnose and fix the issue!
"""

    @mcp.prompt(
        description="Guide for using Selent MCP with multiple API keys (MSP Mode)"
    )
    def multi_key_workflow() -> str:
        """
        Provides workflow guidance for MSPs managing multiple customer organizations.

        Use this when the MCP server is configured with multiple API keys.
        """
        return """# Multi-API Key Workflow for Managed Service Providers

## Overview

Selent MCP supports managing multiple Meraki organizations through multiple API keys.
This is ideal for Managed Service Providers (MSPs) handling multiple customers.

## Configuration

### Single Key (Backward Compatible)
```bash
MERAKI_API_KEY="abc123..."
```

### Multiple Keys (Comma-Separated)
```bash
# Simple format
MERAKI_API_KEY="key1,key2,key3"

# Named format (recommended)
MERAKI_API_KEY="customer_a:key1,customer_b:key2,customer_c:key3"
```

## Step 1: Discover Available Keys

First, see what API keys are configured:

```
list_api_keys()
```

**Returns:**
```json
{
  "count": 3,
  "keys": [
    {
      "key_id": "customer_a",
      "name": "Customer A - Acme Corp",
      "organization_count": 5,
      "is_default": true
    },
    {
      "key_id": "customer_b",
      "name": "Customer B - Beta Industries",
      "organization_count": 3,
      "is_default": false
    }
  ]
}
```

## Step 2: Get Organizations for a Customer

To see what organizations a specific customer has access to:

```
get_key_organizations(key_id="customer_a")
```

**Or discover all at once:**
```
discover_all_organizations()
```

This populates the cache and enables auto-selection by organization ID.

## Step 3: Execute API Calls

### Option A: Specify key_id Explicitly

```
execute_meraki_api_endpoint(
    section='organizations',
    method='getOrganizations',
    key_id='customer_a'
)
```

### Option B: Auto-Select by Organization ID

After discovering organizations, the system can auto-select the right key:

```
execute_meraki_api_endpoint(
    section='networks',
    method='getOrganizationNetworks',
    organizationId='123456'  # System finds the right key
)
```

### Option C: Set Default Key for Session

When working with one customer for multiple operations:

```
set_default_key(key_id='customer_a')

# Now all calls without key_id use customer_a
execute_meraki_api_endpoint(
    section='organizations',
    method='getOrganizations'
)

execute_meraki_api_endpoint(
    section='devices',
    method='getOrganizationDevices',
    organizationId='123456'
)
```

## Key Selection Priority

The system resolves which API key to use in this order:

1. **Explicit key_id** - If you provide `key_id` parameter
2. **Organization ID** - If you provide `organizationId` and orgs are cached
3. **Default key** - The default key set via `set_default_key()`
4. **First key** - The first key in the configuration
"""
