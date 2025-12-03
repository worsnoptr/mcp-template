"""
OpenAPI-based tool generation.

This module provides utilities to convert OpenAPI specifications to MCP tools.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


def register_openapi_tools(mcp, spec_path: str, base_url: Optional[str] = None):
    """
    Register tools from an OpenAPI specification.
    
    Args:
        mcp: FastMCP server instance
        spec_path: Path to OpenAPI specification file (YAML or JSON)
        base_url: Base URL for API calls (overrides spec if provided)
    """
    logger.info(f"Loading OpenAPI spec from: {spec_path}")
    
    try:
        # Import OpenAPI dependencies
        import yaml
        from openapi_spec_validator import validate_spec
        
        # Load specification
        spec_file = Path(spec_path)
        if not spec_file.exists():
            logger.error(f"OpenAPI spec not found: {spec_path}")
            return
        
        # Parse spec based on file extension
        with open(spec_file, 'r') as f:
            if spec_file.suffix in ['.yaml', '.yml']:
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)
        
        # Validate spec
        try:
            validate_spec(spec)
            logger.info("✓ OpenAPI spec validation passed")
        except Exception as e:
            logger.warning(f"OpenAPI spec validation warning: {e}")
        
        # Extract base URL from spec if not provided
        if base_url is None:
            base_url = extract_base_url(spec)
        
        logger.info(f"Base URL: {base_url}")
        
        # Generate tools from operations
        tools_count = generate_tools_from_spec(mcp, spec, base_url)
        
        logger.info(f"✓ Registered {tools_count} tools from OpenAPI spec")
    
    except ImportError:
        logger.error("OpenAPI dependencies not installed. Run: pip install -r requirements-openapi.txt")
    except Exception as e:
        logger.error(f"Failed to load OpenAPI spec: {e}", exc_info=True)


def extract_base_url(spec: Dict) -> str:
    """
    Extract base URL from OpenAPI specification.
    
    Args:
        spec: OpenAPI specification dict
    
    Returns:
        Base URL for API calls
    """
    # OpenAPI 3.x
    if "servers" in spec and spec["servers"]:
        return spec["servers"][0]["url"]
    
    # OpenAPI 2.x (Swagger)
    if "host" in spec:
        scheme = spec.get("schemes", ["https"])[0]
        base_path = spec.get("basePath", "")
        return f"{scheme}://{spec['host']}{base_path}"
    
    # Fallback
    return "http://localhost:8080"


def generate_tools_from_spec(mcp, spec: Dict, base_url: str) -> int:
    """
    Generate MCP tools from OpenAPI paths.
    
    Args:
        mcp: FastMCP server instance
        spec: OpenAPI specification dict
        base_url: Base URL for API calls
    
    Returns:
        Number of tools generated
    """
    tools_count = 0
    paths = spec.get("paths", {})
    
    for path, path_item in paths.items():
        for method in ["get", "post", "put", "patch", "delete"]:
            if method not in path_item:
                continue
            
            operation = path_item[method]
            
            # Generate tool name from operationId or path
            tool_name = operation.get(
                "operationId",
                f"{method}_{path.replace('/', '_').replace('{', '').replace('}', '')}"
            ).replace("-", "_")
            
            # Get operation details
            summary = operation.get("summary", f"{method.upper()} {path}")
            description = operation.get("description", summary)
            
            # Extract parameters
            parameters = extract_parameters(operation, spec)
            
            # Create tool function
            create_api_tool(
                mcp,
                tool_name,
                description,
                base_url,
                path,
                method.upper(),
                parameters
            )
            
            tools_count += 1
    
    return tools_count


def extract_parameters(operation: Dict, spec: Dict) -> List[Dict]:
    """
    Extract parameters from operation definition.
    
    Args:
        operation: OpenAPI operation object
        spec: Full OpenAPI spec (for resolving references)
    
    Returns:
        List of parameter definitions
    """
    parameters = []
    
    # Path and query parameters
    for param in operation.get("parameters", []):
        # Resolve $ref if present
        if "$ref" in param:
            # Simple ref resolution (full resolution would need recursive handling)
            ref_path = param["$ref"].split("/")[-1]
            if "components" in spec and "parameters" in spec["components"]:
                param = spec["components"]["parameters"].get(ref_path, param)
        
        parameters.append({
            "name": param.get("name"),
            "location": param.get("in"),  # path, query, header, cookie
            "required": param.get("required", False),
            "type": param.get("schema", {}).get("type", "string"),
            "description": param.get("description", "")
        })
    
    # Request body parameters (for POST/PUT/PATCH)
    if "requestBody" in operation:
        request_body = operation["requestBody"]
        content = request_body.get("content", {})
        
        # Get JSON schema if available
        if "application/json" in content:
            schema = content["application/json"].get("schema", {})
            
            # Extract properties
            for prop_name, prop_schema in schema.get("properties", {}).items():
                parameters.append({
                    "name": prop_name,
                    "location": "body",
                    "required": prop_name in schema.get("required", []),
                    "type": prop_schema.get("type", "string"),
                    "description": prop_schema.get("description", "")
                })
    
    return parameters


def create_api_tool(
    mcp,
    tool_name: str,
    description: str,
    base_url: str,
    path: str,
    method: str,
    parameters: List[Dict]
):
    """
    Create an MCP tool that calls an API endpoint.
    
    Args:
        mcp: FastMCP server instance
        tool_name: Name of the tool
        description: Tool description
        base_url: API base URL
        path: API path
        method: HTTP method
        parameters: List of parameter definitions
    """
    
    async def api_tool_function(**kwargs) -> Dict[str, Any]:
        """
        Dynamically generated API tool.
        
        This function is created for each API operation in the OpenAPI spec.
        """
        try:
            # Build URL with path parameters
            url = base_url + path
            for param in parameters:
                if param["location"] == "path" and param["name"] in kwargs:
                    url = url.replace(f"{{{param['name']}}}", str(kwargs[param["name"]]))
            
            # Build query parameters
            query_params = {}
            for param in parameters:
                if param["location"] == "query" and param["name"] in kwargs:
                    query_params[param["name"]] = kwargs[param["name"]]
            
            # Build request body
            body_data = {}
            for param in parameters:
                if param["location"] == "body" and param["name"] in kwargs:
                    body_data[param["name"]] = kwargs[param["name"]]
            
            # Make API call
            async with httpx.AsyncClient() as client:
                if method in ["GET", "DELETE"]:
                    response = await client.request(
                        method,
                        url,
                        params=query_params,
                        timeout=30.0
                    )
                else:
                    response = await client.request(
                        method,
                        url,
                        params=query_params,
                        json=body_data if body_data else None,
                        timeout=30.0
                    )
                
                response.raise_for_status()
                
                # Try to parse JSON response
                try:
                    return response.json()
                except:
                    return {"response": response.text, "status_code": response.status_code}
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error in {tool_name}: {e}")
            return {"error": str(e), "tool": tool_name}
        except Exception as e:
            logger.error(f"Error in {tool_name}: {e}")
            return {"error": str(e), "tool": tool_name}
    
    # Build docstring from parameters
    param_docs = "\n        ".join([
        f"{p['name']}: {p['description'] or p['type']}"
        for p in parameters
    ])
    
    api_tool_function.__doc__ = f"""
    {description}
    
    Parameters:
        {param_docs if param_docs else 'No parameters'}
    
    Returns:
        API response as dictionary
    """
    
    api_tool_function.__name__ = tool_name
    
    # Register the tool
    mcp.tool()(api_tool_function)
    
    logger.debug(f"Created tool: {tool_name} -> {method} {path}")


# ==============================================================================
# HELPER FUNCTIONS FOR CUSTOM OPENAPI PROCESSING
# ==============================================================================

def load_openapi_spec(spec_path: str) -> Dict:
    """
    Load and validate an OpenAPI specification.
    
    Args:
        spec_path: Path to OpenAPI spec file
    
    Returns:
        Parsed OpenAPI specification
    """
    import yaml
    from openapi_spec_validator import validate_spec
    
    spec_file = Path(spec_path)
    
    with open(spec_file, 'r') as f:
        if spec_file.suffix in ['.yaml', '.yml']:
            spec = yaml.safe_load(f)
        else:
            spec = json.load(f)
    
    validate_spec(spec)
    
    return spec


def get_operation_list(spec: Dict) -> List[Dict[str, Any]]:
    """
    Get list of all operations from an OpenAPI spec.
    
    Args:
        spec: OpenAPI specification
    
    Returns:
        List of operations with metadata
    """
    operations = []
    
    for path, path_item in spec.get("paths", {}).items():
        for method in ["get", "post", "put", "patch", "delete", "options", "head"]:
            if method in path_item:
                operation = path_item[method]
                operations.append({
                    "path": path,
                    "method": method.upper(),
                    "operationId": operation.get("operationId"),
                    "summary": operation.get("summary"),
                    "description": operation.get("description"),
                    "tags": operation.get("tags", [])
                })
    
    return operations
