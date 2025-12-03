"""
Main MCP Server Entry Point

This is the core MCP server implementation optimized for Amazon Bedrock AgentCore Runtime.
It supports both direct tool definition and OpenAPI specification modes.

Requirements for AgentCore:
- Host: 0.0.0.0
- Port: 8000
- Endpoint: /mcp
- Transport: stateless streamable-http
- Platform: ARM64 (for Docker deployment)
"""

import logging
import sys
from typing import List

from mcp.server.fastmcp import FastMCP
from starlette.responses import JSONResponse

# Import configuration
from config import config

# Import utilities
from utils.error_handling import setup_error_handlers
from utils.observability import setup_observability

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.get("logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger = logging.getLogger(__name__)

# Initialize MCP server with AgentCore-required configuration
mcp = FastMCP(
    name=config.get("mcp.server_name", "mcp-server"),
    host=config.server_host,  # 0.0.0.0 required by AgentCore
    port=config.server_port,  # 8000 required by AgentCore
    stateless_http=config.stateless_http  # True required by AgentCore
)

logger.info(f"Initializing MCP server: {mcp.name}")
logger.info(f"Configuration: host={config.server_host}, port={config.server_port}, stateless_http={config.stateless_http}")


# ==============================================================================
# TOOL LOADING
# ==============================================================================

def load_direct_tools():
    """Load tools defined directly as Python functions."""
    logger.info("Loading direct tool definitions...")
    
    # Import example tools
    try:
        from examples.calculator_tools import register_calculator_tools
        register_calculator_tools(mcp)
        logger.info("✓ Calculator tools loaded")
    except Exception as e:
        logger.warning(f"Could not load calculator tools: {e}")
    
    # Import custom direct tools
    try:
        from tools.direct_tools import register_direct_tools
        register_direct_tools(mcp)
        logger.info("✓ Direct tools loaded")
    except Exception as e:
        logger.warning(f"Could not load direct tools: {e}")


def load_openapi_tools():
    """Load tools from OpenAPI specifications."""
    logger.info("Loading OpenAPI specifications...")
    
    try:
        from tools.openapi_tools import register_openapi_tools
        
        # Get OpenAPI specs from configuration
        specs = config.get("tools.openapi.specs", [])
        
        if not specs:
            logger.warning("No OpenAPI specs configured")
            return
        
        for spec_path in specs:
            try:
                register_openapi_tools(mcp, spec_path)
                logger.info(f"✓ OpenAPI spec loaded: {spec_path}")
            except Exception as e:
                logger.error(f"Failed to load OpenAPI spec {spec_path}: {e}")
    
    except ImportError:
        logger.warning("OpenAPI support not available. Install with: pip install -r requirements-openapi.txt")
    except Exception as e:
        logger.error(f"Error loading OpenAPI tools: {e}")


def load_tools():
    """Load tools based on configuration mode."""
    mode = config.get("tools.mode", "direct").lower()
    
    logger.info(f"Loading tools in '{mode}' mode")
    
    if mode == "direct":
        load_direct_tools()
    elif mode == "openapi":
        load_openapi_tools()
    elif mode == "both":
        load_direct_tools()
        load_openapi_tools()
    else:
        logger.error(f"Unknown tools mode: {mode}. Using 'direct' mode.")
        load_direct_tools()


# Load all tools
load_tools()


# ==============================================================================
# HEALTH CHECK ENDPOINT
# ==============================================================================

@mcp.get("/ping")
async def health_check():
    """
    Health check endpoint for AgentCore Runtime.
    
    Returns:
        JSON response with server status
    """
    return JSONResponse({
        "status": "healthy",
        "server": mcp.name,
        "version": config.get("mcp.server_version", "1.0.0")
    })


# ==============================================================================
# ERROR HANDLERS AND OBSERVABILITY
# ==============================================================================

# Setup error handlers
setup_error_handlers(mcp)

# Setup observability (ADOT integration)
if config.observability_enabled:
    logger.info("Observability enabled - ADOT instrumentation active")
    setup_observability(config.service_name)
else:
    logger.info("Observability disabled")


# ==============================================================================
# SERVER STARTUP
# ==============================================================================

def main():
    """Main entry point for the MCP server."""
    try:
        logger.info("=" * 80)
        logger.info("Starting MCP Server for Amazon Bedrock AgentCore Runtime")
        logger.info("=" * 80)
        logger.info(f"Server Name: {mcp.name}")
        logger.info(f"Endpoint: http://{config.server_host}:{config.server_port}{config.mcp_path}")
        logger.info(f"Stateless HTTP: {config.stateless_http}")
        logger.info(f"Observability: {'Enabled' if config.observability_enabled else 'Disabled'}")
        logger.info("=" * 80)
        
        # Run the server with streamable-http transport (required by AgentCore)
        mcp.run(transport="streamable-http")
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
