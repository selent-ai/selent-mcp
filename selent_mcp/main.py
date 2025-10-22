import argparse
import logging

from fastmcp import FastMCP

from selent_mcp.services.meraki_client import MerakiClient
from selent_mcp.services.selent_service_client import SelentServiceClient
from selent_mcp.settings import ApiSettings
from selent_mcp.tools.commonly_used_api_tools import CommonlyUsedMerakiApiTools
from selent_mcp.tools.meraki_api_tools import MerakiApiTools
from selent_mcp.tools.meraki_complex_api_tools import MerakiComplexApiTools
from selent_mcp.tools.selent_api_tools import SelentApiTools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env = ApiSettings()
mcp: FastMCP = FastMCP("Selent MCP")

meraki_client = MerakiClient(api_key=env.MERAKI_API_KEY)
selent_client = SelentServiceClient(
    base_url=env.SELENT_API_BASE_URL, api_key=env.SELENT_API_KEY
)

meraki_api_tools = MerakiApiTools(mcp, meraki_client, enabled=bool(env.MERAKI_API_KEY))
meraki_complex_api_tools = MerakiComplexApiTools(
    mcp, meraki_client, enabled=bool(env.MERAKI_API_KEY)
)
commonly_used_meraki_api_tools = CommonlyUsedMerakiApiTools(
    mcp, meraki_client, enabled=bool(env.MERAKI_API_KEY)
)

selent_api_tools = SelentApiTools(
    mcp=mcp, selent_client=selent_client, enabled=bool(env.SELENT_API_KEY)
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Selent MCP Server")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the server on"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to run the server on"
    )
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        help="Transport to use for the server. Can be 'stdio', 'http' or 'sse'",
    )
    args = parser.parse_args()

    mcp.run(transport=args.transport, host=args.host, port=args.port)
