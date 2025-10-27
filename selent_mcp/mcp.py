from fastmcp import FastMCP

from selent_mcp.prompts import register_prompts
from selent_mcp.services.meraki_client import MerakiClient
from selent_mcp.services.selent_service_client import SelentServiceClient
from selent_mcp.settings import ApiSettings
from selent_mcp.tools.commonly_used_api_tools import CommonlyUsedMerakiApiTools
from selent_mcp.tools.key_management_tools import KeyManagementTools
from selent_mcp.tools.meraki_api_tools import MerakiApiTools
from selent_mcp.tools.selent_api_tools import SelentApiTools

env = ApiSettings()
mcp: FastMCP = FastMCP("Selent MCP")

# Initialize Meraki client (supports single or multiple API keys)
meraki_client = MerakiClient(api_key=env.MERAKI_API_KEY)

selent_client = SelentServiceClient(
    base_url=env.SELENT_API_BASE_URL, api_key=env.SELENT_API_KEY
)

# Register Meraki API tools
meraki_api_tools = MerakiApiTools(mcp, meraki_client, enabled=bool(env.MERAKI_API_KEY))

commonly_used_meraki_api_tools = CommonlyUsedMerakiApiTools(
    mcp, meraki_client, enabled=bool(env.MERAKI_API_KEY)
)

# Register key management tools (only if multi-key mode detected)
key_management_tools = KeyManagementTools(mcp, meraki_client)

# Register Selent API tools
selent_api_tools = SelentApiTools(
    mcp=mcp, selent_client=selent_client, enabled=bool(env.SELENT_API_KEY)
)

# Register prompts
register_prompts(mcp)
