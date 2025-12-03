# Customization Guide

This guide explains how to customize the MCP server template for your specific needs.

## Table of Contents

- [Adding New Tools](#adding-new-tools)
- [Configuring Server Settings](#configuring-server-settings)
- [Customizing Authentication](#customizing-authentication)
- [Extending Utilities](#extending-utilities)
- [Custom Middleware](#custom-middleware)
- [Docker Customization](#docker-customization)

## Adding New Tools

### Direct Tool Definition Mode

#### Option 1: Add to Existing Module

Edit `src/tools/direct_tools.py`:

```python
def register_direct_tools(mcp):
    """Register all direct tools."""
    
    # Your existing tools...
    
    # Add your new tool
    @mcp.tool()
    @trace_tool_execution("my_new_tool")
    @validate_required_fields(["input"])
    def my_new_tool(input: str, option: str = "default") -> dict:
        """
        Description of what your tool does.
        
        Args:
            input: Description of input parameter
            option: Description of optional parameter
        
        Returns:
            Description of return value
        """
        # Your logic here
        result = process_input(input, option)
        
        # Record metrics
        record_metric("tool.invocations", 1, {"tool": "my_new_tool"})
        
        return {
            "success": True,
            "data": result
        }
```

#### Option 2: Create New Module

Create `src/tools/my_tools.py`:

```python
"""My custom MCP tools."""

import logging
from utils.observability import trace_tool_execution, record_metric

logger = logging.getLogger(__name__)


def register_my_tools(mcp):
    """Register custom tools with MCP server."""
    
    @mcp.tool()
    @trace_tool_execution("custom_tool")
    def custom_tool(param: str) -> str:
        """Your custom tool implementation."""
        logger.info(f"Processing: {param}")
        record_metric("tool.invocations", 1, {"tool": "custom_tool"})
        return f"Processed: {param}"
    
    logger.info("✓ Custom tools registered")
```

Then import in `src/server.py`:

```python
# Add this import
from tools.my_tools import register_my_tools

# Add this in load_tools() function
def load_direct_tools():
    # Existing tools...
    
    # Your custom tools
    try:
        register_my_tools(mcp)
        logger.info("✓ Custom tools loaded")
    except Exception as e:
        logger.warning(f"Could not load custom tools: {e}")
```

### OpenAPI Specification Mode

#### Add New OpenAPI Spec

1. Place your OpenAPI spec file in `src/examples/`:
   ```
   src/examples/my_api_spec.yaml
   ```

2. Update `config.yaml`:
   ```yaml
   tools:
     mode: "openapi"  # or "both"
     openapi:
       specs:
         - "examples/sample_openapi.yaml"
         - "examples/my_api_spec.yaml"  # Add your spec
       base_url: "https://api.example.com"  # Optional override
       auth:
         type: "bearer"  # or "api_key", "basic"
         header: "Authorization"
   ```

3. Restart the server - tools will be auto-generated

#### Custom OpenAPI Processing

For advanced control, create a custom processor:

```python
# src/tools/my_openapi_processor.py

from tools.openapi_tools import load_openapi_spec, create_api_tool

def register_my_api_tools(mcp):
    """Custom OpenAPI processing."""
    
    # Load spec
    spec = load_openapi_spec("examples/my_api_spec.yaml")
    
    # Filter operations
    paths = spec.get("paths", {})
    for path, path_item in paths.items():
        # Only include GET operations
        if "get" in path_item:
            operation = path_item["get"]
            # Create tool with custom processing
            create_api_tool(
                mcp,
                tool_name=operation.get("operationId"),
                description=operation.get("summary"),
                base_url="https://api.example.com",
                path=path,
                method="GET",
                parameters=extract_parameters(operation, spec)
            )
```

## Configuring Server Settings

### Modify config.yaml

The main configuration file supports environment-specific overrides:

```yaml
server:
  host: "0.0.0.0"  # Don't change (AgentCore requirement)
  port: 8000       # Don't change (AgentCore requirement)
  mcp_path: "/mcp" # Don't change (AgentCore requirement)

mcp:
  server_name: "my-custom-server"  # Customize this
  server_version: "2.0.0"          # Customize this

tools:
  mode: "both"  # Use both direct and OpenAPI modes
  
  direct:
    modules:
      - "tools.direct_tools"
      - "tools.my_custom_tools"  # Add your module
  
  openapi:
    specs:
      - "examples/my_api.yaml"

observability:
  enabled: true
  service_name: "my-custom-service"
  sampling_rate: 1.0  # 0.0 to 1.0

logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

security:
  validate_inputs: true
  max_request_size: 2097152  # 2MB
  rate_limit: 100

# Environment-specific overrides
environments:
  development:
    logging:
      level: "DEBUG"
    security:
      rate_limit: 1000
  
  production:
    logging:
      level: "WARNING"
    security:
      rate_limit: 50
```

### Environment Variables

Override config with environment variables:

```bash
# In your deployment
export ENVIRONMENT="production"
export MCP_LOG_LEVEL="WARNING"
export MCP_SERVICE_NAME="my-service"
export MCP_OBSERVABILITY_ENABLED="true"
```

### Programmatic Configuration

For dynamic configuration:

```python
# src/config.py - Add custom configuration logic

class Config:
    def __init__(self, config_path: Optional[str] = None):
        # Load base configuration
        self._config = self._load_yaml(config_path)
        
        # Add custom logic
        self._apply_dynamic_config()
    
    def _apply_dynamic_config(self):
        """Apply dynamic configuration based on runtime conditions."""
        # Example: Adjust settings based on AWS region
        region = boto3.session.Session().region_name
        if region.startswith('us-'):
            self._config['observability']['sampling_rate'] = 1.0
        else:
            self._config['observability']['sampling_rate'] = 0.1
```

## Customizing Authentication

### Add Custom Auth Logic

Create `src/utils/auth.py`:

```python
"""Custom authentication logic."""

import logging
from typing import Optional
from starlette.requests import Request
from utils.error_handling import MCPError

logger = logging.getLogger(__name__)


async def validate_api_key(request: Request) -> Optional[str]:
    """
    Validate API key from request.
    
    Args:
        request: Starlette Request object
    
    Returns:
        User ID if valid, None otherwise
    
    Raises:
        MCPError: If authentication fails
    """
    # Get API key from header
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise MCPError(
            "Missing API key",
            code="missing_auth",
            details={"header": "X-API-Key"}
        )
    
    # Validate against your system
    user_id = await verify_api_key(api_key)
    
    if not user_id:
        raise MCPError(
            "Invalid API key",
            code="invalid_auth"
        )
    
    logger.info(f"Authenticated user: {user_id}")
    return user_id


def require_auth(func):
    """Decorator to require authentication for tools."""
    async def wrapper(*args, **kwargs):
        # Get request from context
        request = get_request_context()
        
        # Validate authentication
        user_id = await validate_api_key(request)
        
        # Add user_id to kwargs
        kwargs['authenticated_user'] = user_id
        
        return await func(*args, **kwargs)
    
    return wrapper
```

Use in tools:

```python
from utils.auth import require_auth

@mcp.tool()
@require_auth
async def protected_tool(data: dict, authenticated_user: str) -> dict:
    """Tool that requires authentication."""
    logger.info(f"User {authenticated_user} called protected_tool")
    return process_for_user(data, authenticated_user)
```

### Custom OAuth Provider

To add support for a custom OAuth provider:

1. Get the discovery URL from your provider
2. Use it during deployment:
   ```bash
   agentcore configure -e src/server.py --protocol MCP
   # Provide: https://your-provider.com/.well-known/openid-configuration
   ```

## Extending Utilities

### Add Custom Validation

Create `src/utils/custom_validation.py`:

```python
"""Custom validation utilities."""

from utils.validation import ValidationException


def validate_phone_number(phone: str) -> bool:
    """Validate phone number format."""
    import re
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, phone))


def validate_credit_card(card_number: str) -> bool:
    """Validate credit card using Luhn algorithm."""
    def luhn_checksum(card):
        def digits_of(n):
            return [int(d) for d in str(n)]
        
        digits = digits_of(card)
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(digits_of(d*2))
        return checksum % 10
    
    return luhn_checksum(card_number) == 0


def validate_custom_format(value: str, pattern: str) -> bool:
    """Validate against custom regex pattern."""
    import re
    return bool(re.match(pattern, value))
```

### Add Custom Error Types

Extend `src/utils/error_handling.py`:

```python
class PaymentError(MCPError):
    """Exception for payment processing errors."""
    
    def __init__(self, message: str, transaction_id: str = None):
        super().__init__(
            message=message,
            code="payment_error",
            details={"transaction_id": transaction_id}
        )


class RateLimitError(MCPError):
    """Exception for rate limit violations."""
    
    def __init__(self, retry_after: int):
        super().__init__(
            message="Rate limit exceeded",
            code="rate_limit",
            details={"retry_after_seconds": retry_after}
        )
```

### Custom Observability Metrics

Add to `src/utils/observability.py`:

```python
class CustomMetrics:
    """Helper for custom business metrics."""
    
    @staticmethod
    def record_payment_amount(amount: float, currency: str):
        """Record payment amount metric."""
        record_metric(
            "business.payment.amount",
            amount,
            {"currency": currency}
        )
    
    @staticmethod
    def record_user_action(action: str, user_id: str):
        """Record user action metric."""
        record_metric(
            "business.user.action",
            1,
            {"action": action, "user_id": user_id}
        )
```

## Custom Middleware

### Add Request/Response Middleware

Create `src/middleware/custom_middleware.py`:

```python
"""Custom middleware for request/response processing."""

import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request timing."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "duration_ms": duration * 1000,
                "status_code": response.status_code
            }
        )
        
        return response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        import uuid
        request_id = str(uuid.uuid4())
        
        # Add to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
```

Register in `src/server.py`:

```python
from middleware.custom_middleware import TimingMiddleware, RequestIDMiddleware

# After creating mcp instance
mcp.app.add_middleware(TimingMiddleware)
mcp.app.add_middleware(RequestIDMiddleware)
```

## Docker Customization

### Add System Dependencies

Edit `Dockerfile`:

```dockerfile
# After the base image
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    postgresql-client \    # Add PostgreSQL client
    imagemagick \          # Add image processing
    && rm -rf /var/lib/apt/lists/*
```

### Add Custom Files

```dockerfile
# Copy custom configuration
COPY config/ ./config/

# Copy custom scripts
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh
```

### Multi-Stage Build

For smaller images:

```dockerfile
# Stage 1: Builder
FROM --platform=linux/arm64 python:3.11-slim-bookworm AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM --platform=linux/arm64 python:3.11-slim-bookworm

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY src/ ./src/

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["opentelemetry-instrument", "python", "src/server.py"]
```

### Custom Environment Variables

```dockerfile
# Set custom environment variables
ENV APP_ENV="production"
ENV MAX_WORKERS="4"
ENV TIMEOUT="300"

# Use in your application
CMD ["opentelemetry-instrument", "python", "src/server.py", \
     "--workers", "${MAX_WORKERS}", \
     "--timeout", "${TIMEOUT}"]
```

## Testing Customizations

### Unit Tests

Create `tests/test_tools.py`:

```python
"""Unit tests for custom tools."""

import pytest
from src.tools.my_tools import register_my_tools


def test_custom_tool():
    """Test custom tool functionality."""
    # Mock MCP instance
    class MockMCP:
        def tool(self):
            def decorator(func):
                return func
            return decorator
    
    mcp = MockMCP()
    register_my_tools(mcp)
    
    # Test your tool
    result = custom_tool("test input")
    assert result == "Processed: test input"
```

### Integration Tests

Create `tests/test_integration.py`:

```python
"""Integration tests for MCP server."""

import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def test_full_workflow():
    """Test complete workflow."""
    mcp_url = "http://localhost:8000/mcp"
    
    async with streamablehttp_client(mcp_url, {}) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Test tool exists
            tools = await session.list_tools()
            assert "my_custom_tool" in [t.name for t in tools.tools]
            
            # Test tool execution
            result = await session.call_tool(
                "my_custom_tool",
                {"input": "test"}
            )
            assert result is not None


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
```

## Additional Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Starlette Documentation](https://www.starlette.io/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Python Best Practices](https://docs.python-guide.org/)
