# MCP Server Best Practices

This document outlines best practices for developing, deploying, and maintaining MCP servers for Amazon Bedrock AgentCore Runtime.

## Table of Contents

- [Security](#security)
- [Error Handling](#error-handling)
- [Performance](#performance)
- [Observability](#observability)
- [Development Workflow](#development-workflow)
- [Production Readiness](#production-readiness)

## Security

### Never Hardcode Secrets

❌ **Don't:**
```python
API_KEY = "sk-1234567890abcdef"  # Never do this!

def call_api():
    headers = {"Authorization": f"Bearer {API_KEY}"}
```

✅ **Do:**
```python
import os
import boto3

def get_api_key():
    """Get API key from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='agentcore/api-key')
    return response['SecretString']

def call_api():
    api_key = os.getenv('API_KEY') or get_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
```

### Input Validation

Always validate and sanitize inputs:

```python
from utils.validation import validate_required_fields, sanitize_string

@mcp.tool()
@validate_required_fields(["user_input"])
def process_user_input(user_input: str) -> str:
    # Sanitize to prevent injection attacks
    clean_input = sanitize_string(user_input, max_length=1000)
    
    # Additional validation
    if not clean_input:
        raise ValidationException("Input cannot be empty")
    
    return process(clean_input)
```

### Follow Least Privilege Principle

Configure IAM roles with minimum required permissions:

```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject"
  ],
  "Resource": [
    "arn:aws:s3:::specific-bucket/specific-prefix/*"
  ]
}
```

Not:
```json
{
  "Effect": "Allow",
  "Action": "s3:*",
  "Resource": "*"
}
```

### OAuth Authentication

Always enable OAuth for production deployments:

```bash
agentcore configure -e src/server.py --protocol MCP
# When prompted, provide OAuth discovery URL and client ID
```

### Regular Security Updates

```bash
# Check for security vulnerabilities
pip install safety
safety check

# Update dependencies regularly
pip list --outdated
pip install --upgrade <package>
```

## Error Handling

### Structured Error Responses

✅ **Good:**
```python
from utils.error_handling import MCPError

@mcp.tool()
def my_tool(data: dict) -> dict:
    if "required_field" not in data:
        raise MCPError(
            message="Missing required field",
            code="missing_field",
            details={"required_fields": ["required_field"]}
        )
    
    try:
        result = process(data)
        return result
    except Exception as e:
        raise MCPError(
            message="Processing failed",
            code="processing_error",
            details={"error": str(e)}
        )
```

❌ **Avoid:**
```python
@mcp.tool()
def my_tool(data: dict) -> dict:
    # This returns 500 with cryptic message
    return process(data["required_field"])
```

### Log Errors Appropriately

```python
import logging

logger = logging.getLogger(__name__)

@mcp.tool()
def my_tool(data: dict) -> dict:
    try:
        result = process(data)
        logger.info(f"Successfully processed data for: {data.get('id')}")
        return result
    except Exception as e:
        # Log error with context, but not sensitive data
        logger.error(
            f"Failed to process data",
            extra={
                "error": str(e),
                "data_id": data.get('id'),  # Safe to log
                # Don't log: passwords, tokens, PII
            },
            exc_info=True
        )
        raise
```

### Handle Timeouts Gracefully

```python
import httpx
from utils.error_handling import MCPError

@mcp.tool()
async def call_external_api(url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
    
    except httpx.TimeoutException:
        raise MCPError(
            message="API request timed out",
            code="timeout",
            details={"url": url, "timeout_seconds": 30}
        )
    
    except httpx.HTTPError as e:
        raise MCPError(
            message="API request failed",
            code="api_error",
            details={"url": url, "error": str(e)}
        )
```

## Performance

### Keep Tools Stateless

AgentCore provides session isolation, so design stateless tools:

✅ **Good:**
```python
@mcp.tool()
def calculate(a: int, b: int, operation: str) -> int:
    # No state maintained between calls
    operations = {"add": lambda x, y: x + y}
    return operations[operation](a, b)
```

❌ **Avoid:**
```python
# Global state can cause issues across sessions
calculation_history = []

@mcp.tool()
def calculate(a: int, b: int) -> int:
    result = a + b
    calculation_history.append(result)  # Don't do this!
    return result
```

### Optimize Cold Starts

Minimize initialization code:

✅ **Good:**
```python
# Import only what's needed
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# Lazy load heavy dependencies
@mcp.tool()
def ml_inference(data: dict) -> dict:
    import tensorflow as tf  # Load only when needed
    return model.predict(data)
```

❌ **Avoid:**
```python
# Loading everything at startup
import tensorflow as tf
import torch
import pandas as pd
import numpy as np
# ... lots of heavy imports

# Complex initialization
model = load_giant_model()  # Slow cold starts!
```

### Use Async for I/O Operations

```python
import httpx

@mcp.tool()
async def fetch_multiple_urls(urls: list) -> list:
    """Fetch multiple URLs concurrently."""
    async with httpx.AsyncClient() as client:
        tasks = [client.get(url) for url in urls]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]
```

### Cache When Appropriate

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_config(config_key: str) -> dict:
    """Cache configuration lookups."""
    return load_config_from_s3(config_key)

@mcp.tool()
def process_with_config(data: dict, config_key: str) -> dict:
    config = get_config(config_key)  # Cached
    return process(data, config)
```

## Observability

### Use Tracing Decorators

```python
from utils.observability import trace_tool_execution

@mcp.tool()
@trace_tool_execution("my_important_tool")
def my_important_tool(data: dict) -> dict:
    # Automatically traced with spans
    result = process(data)
    return result
```

### Record Custom Metrics

```python
from utils.observability import record_metric

@mcp.tool()
def process_data(data: dict) -> dict:
    start_time = time.time()
    
    record_metric("tool.invocations", 1, {"tool": "process_data"})
    
    result = process(data)
    
    duration = time.time() - start_time
    record_metric("tool.duration_ms", duration * 1000, {"tool": "process_data"})
    
    return result
```

### Add Context to Logs

```python
import logging

logger = logging.getLogger(__name__)

@mcp.tool()
def process_order(order_id: str, user_id: str) -> dict:
    logger.info(
        "Processing order",
        extra={
            "order_id": order_id,
            "user_id": user_id,
            "tool": "process_order"
        }
    )
    
    result = process(order_id)
    
    logger.info(
        "Order processed successfully",
        extra={
            "order_id": order_id,
            "status": result["status"]
        }
    )
    
    return result
```

### Session ID Propagation

```python
from utils.observability import set_session_id

def handle_request(request_data: dict):
    session_id = request_data.get("session_id")
    if session_id:
        set_session_id(session_id)
    
    # Session ID now propagated through traces
    return process_request(request_data)
```

## Development Workflow

### Test Locally First

```bash
# 1. Start server
python src/server.py

# 2. Test with client
python tests/test_client_local.py

# 3. Test with MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

### Use Version Control

```bash
# .gitignore
__pycache__/
*.pyc
.env
.env.local
*.log
venv/
.vscode/
```

### Document Your Tools

✅ **Good documentation:**
```python
@mcp.tool()
def calculate_shipping(
    weight_kg: float,
    destination: str,
    service_level: str = "standard"
) -> dict:
    """
    Calculate shipping cost and estimated delivery time.
    
    This tool integrates with multiple shipping providers to calculate
    the cost and delivery time based on package weight, destination,
    and selected service level.
    
    Args:
        weight_kg: Package weight in kilograms (0.1 to 50.0)
        destination: ISO country code (e.g., "US", "GB", "JP")
        service_level: Shipping speed ("economy", "standard", "express")
    
    Returns:
        Dictionary with:
        - cost_usd: Shipping cost in USD
        - delivery_days: Estimated delivery time in business days
        - provider: Shipping provider name
        - tracking_available: Whether tracking is available
    
    Raises:
        ValidationException: If weight or destination is invalid
        MCPError: If shipping calculation fails
    
    Example:
        >>> calculate_shipping(2.5, "US", "express")
        {
            "cost_usd": 45.99,
            "delivery_days": 2,
            "provider": "FedEx",
            "tracking_available": true
        }
    """
    # Implementation...
```

### Separate Concerns

```
src/
├── tools/
│   ├── shipping.py      # Shipping-related tools
│   ├── inventory.py     # Inventory-related tools
│   └── payments.py      # Payment-related tools
├── utils/
│   ├── validation.py    # Shared validation logic
│   └── external_apis.py # External API clients
└── server.py            # MCP server setup only
```

## Production Readiness

### Environment-Specific Configuration

```yaml
# config.yaml
environments:
  development:
    logging:
      level: "DEBUG"
    error_handling:
      include_stack_trace: true
  
  production:
    logging:
      level: "WARNING"
    error_handling:
      include_stack_trace: false
    security:
      rate_limit: 100
```

### Health Monitoring

```python
@mcp.get("/ping")
async def health_check():
    """Comprehensive health check."""
    checks = {
        "server": "healthy",
        "database": check_database(),
        "external_api": check_external_api(),
        "memory_usage": get_memory_usage()
    }
    
    status = "healthy" if all(
        v == "healthy" for v in checks.values()
    ) else "unhealthy"
    
    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Rate Limiting

```python
from functools import wraps
from time import time

rate_limit_storage = {}

def rate_limit(max_calls: int, time_window: int):
    """Rate limit decorator."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = func.__name__
            now = time()
            
            if key not in rate_limit_storage:
                rate_limit_storage[key] = []
            
            # Clean old entries
            rate_limit_storage[key] = [
                t for t in rate_limit_storage[key]
                if now - t < time_window
            ]
            
            if len(rate_limit_storage[key]) >= max_calls:
                raise MCPError(
                    "Rate limit exceeded",
                    code="rate_limit",
                    details={
                        "max_calls": max_calls,
                        "time_window": time_window
                    }
                )
            
            rate_limit_storage[key].append(now)
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

@mcp.tool()
@rate_limit(max_calls=10, time_window=60)
def expensive_operation(data: dict) -> dict:
    """Limited to 10 calls per minute."""
    return process(data)
```

### Graceful Degradation

```python
@mcp.tool()
def get_recommendation(user_id: str) -> dict:
    """Get personalized recommendations with fallback."""
    try:
        # Try ML-based recommendations
        return ml_recommendations(user_id)
    
    except Exception as e:
        logger.warning(f"ML recommendations failed: {e}")
        
        # Fall back to popularity-based
        try:
            return popular_items()
        
        except Exception as e:
            logger.error(f"Fallback failed: {e}")
            
            # Final fallback
            return {"items": [], "fallback": True}
```

### Deployment Checklist

- [ ] All tests pass locally
- [ ] Security review completed
- [ ] IAM permissions follow least privilege
- [ ] OAuth authentication configured
- [ ] CloudWatch logging enabled
- [ ] Observability (ADOT) configured
- [ ] Error handling tested
- [ ] Rate limiting configured
- [ ] Health checks working
- [ ] Documentation updated
- [ ] Secrets in Secrets Manager, not code
- [ ] Docker image built for ARM64
- [ ] Tested with remote test client

### Monitoring and Alerts

Set up CloudWatch alarms for:

1. **Error Rate**: Alert if error rate > 5%
2. **Latency**: Alert if p99 latency > 5 seconds
3. **Availability**: Alert if health check fails
4. **Rate Limiting**: Alert on excessive rate limit hits

```bash
# Example CloudWatch alarm
aws cloudwatch put-metric-alarm \
    --alarm-name mcp-server-high-error-rate \
    --alarm-description "Alert on high error rate" \
    --metric-name ErrorCount \
    --namespace AWS/BedrockAgentCore \
    --statistic Sum \
    --period 300 \
    --evaluation-periods 2 \
    --threshold 10 \
    --comparison-operator GreaterThanThreshold
```

## Additional Resources

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Python Best Practices](https://docs.python-guide.org/)
- [MCP Specification](https://modelcontextprotocol.io/)
