"""Selent MCP package for Meraki Dashboard API integration."""

if __name__ == "__main__":
    import argparse

    from loguru import logger

    from selent_mcp.mcp import mcp

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

    if args.transport == "stdio":
        logger.info("Running MCP server in stdio mode")
        mcp.run(show_banner=False)
    else:
        mcp.run(
            transport=args.transport, host=args.host, port=args.port, show_banner=False
        )
