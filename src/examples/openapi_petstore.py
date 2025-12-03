"""
Example: OpenAPI Pet Store

This example demonstrates the OpenAPI Specification mode.
It shows how to convert an OpenAPI spec to MCP tools automatically.

To use this example:
1. Ensure requirements-openapi.txt is installed: pip install -r requirements-openapi.txt
2. Update config.yaml to use "openapi" mode
3. The sample_openapi.yaml spec will be loaded automatically
"""

import logging

logger = logging.getLogger(__name__)


def demo_openapi_usage():
    """
    Demonstration of how OpenAPI mode works.
    
    This is a documentation function showing the process.
    The actual loading happens in src/server.py via tools/openapi_tools.py
    """
    
    # Step 1: Place your OpenAPI spec in src/examples/
    # Example: sample_openapi.yaml (already provided)
    
    # Step 2: Configure in config.yaml
    # tools:
    #   mode: "openapi"
    #   openapi:
    #     specs:
    #       - "examples/sample_openapi.yaml"
    
    # Step 3: The server automatically generates tools:
    # - getPetById(petId: int) -> dict
    # - addPet(name: str, category: dict, status: str) -> dict
    # - getInventory() -> dict
    
    # Step 4: Test locally:
    # python src/server.py
    
    # Step 5: The tools can now be called via MCP:
    # {
    #   "jsonrpc": "2.0",
    #   "method": "tools/call",
    #   "params": {
    #     "name": "getPetById",
    #     "arguments": {"petId": 123}
    #   },
    #   "id": 1
    # }
    
    logger.info("OpenAPI mode automatically converts API specs to MCP tools")


# ==============================================================================
# CUSTOMIZATION OPTIONS
# ==============================================================================

def custom_openapi_processing_example():
    """
    Example of custom OpenAPI processing if you need more control.
    
    For most use cases, the automatic conversion in openapi_tools.py is sufficient.
    Use this approach only if you need custom preprocessing or filtering.
    """
    
    from tools.openapi_tools import load_openapi_spec, get_operation_list
    
    # Load your spec
    spec = load_openapi_spec("examples/sample_openapi.yaml")
    
    # Get all operations
    operations = get_operation_list(spec)
    
    # Filter or customize operations as needed
    for op in operations:
        print(f"Found operation: {op['method']} {op['path']} - {op['summary']}")
    
    # Then use register_openapi_tools with your customized spec
    # This is advanced usage - most users won't need this


# ==============================================================================
# BEST PRACTICES FOR OPENAPI MODE
# ==============================================================================

"""
BEST PRACTICES FOR OPENAPI MODE:

1. API Specification Quality:
   - Use clear operationId for each operation
   - Provide detailed descriptions for operations and parameters
   - Include response schemas for better type safety
   - Validate your spec before using it

2. Authentication:
   - Configure authentication in config.yaml under tools.openapi.auth
   - Supported types: bearer, api_key, basic
   - Example:
     tools:
       openapi:
         auth:
           type: "bearer"
           header: "Authorization"

3. Base URL Override:
   - If your API endpoint differs from the spec, override in config.yaml:
     tools:
       openapi:
         base_url: "https://your-actual-api.com"

4. Error Handling:
   - The generated tools automatically handle HTTP errors
   - Check CloudWatch logs for API call failures
   - Consider implementing retry logic for production

5. Rate Limiting:
   - Be aware of API rate limits
   - The server respects the rate_limit setting in config.yaml
   - Consider implementing caching for frequently accessed data

6. Security:
   - Never hardcode API keys in OpenAPI specs
   - Use environment variables or AWS Secrets Manager
   - Validate all inputs even though OpenAPI provides schemas

7. Testing:
   - Test each generated tool locally before deploying
   - Use MCP Inspector for interactive testing
   - Verify API responses match expected schemas

8. Documentation:
   - Keep your OpenAPI spec up-to-date with API changes
   - Version your specs (e.g., api-v1.yaml, api-v2.yaml)
   - Document any custom preprocessing or transformations
"""
