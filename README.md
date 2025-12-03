# MCP Server Template for Amazon Bedrock AgentCore Runtime

A comprehensive template for rapidly developing MCP (Model Context Protocol) servers optimized for Amazon Bedrock AgentCore Runtime. This template handles all the undifferentiated heavy lifting - infrastructure setup, boilerplate code, deployment configurations, and observability integrations - so you can focus solely on defining your specific tools and business logic.

## Features

- **Two Development Modes:**
  - 🔧 **Direct Tool Definition:** Define tools as Python functions using FastMCP decorators
  - 📋 **OpenAPI Specification:** Import OpenAPI 3.x specs and auto-convert to MCP tools

- **Production-Ready Infrastructure:**
  - ✅ FastMCP server with stateless HTTP transport (0.0.0.0:8000/mcp)
  - ✅ Docker support optimized for ARM64 (AgentCore requirement)
  - ✅ AWS Distro for OpenTelemetry (ADOT) integration for traces and metrics
  - ✅ OAuth authentication support (Cognito and Auth0)
  - ✅ IAM execution role with AWS best practices
  - ✅ Comprehensive error handling and input validation

- **Developer Experience:**
  - 📚 Complete examples for both modes
  - 🧪 Local testing and remote invocation patterns
  - 📝 Configuration files ready for customization
  - 🚀 Quick start guide with step-by-step instructions

## Table of Contents

- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Usage Modes](#usage-modes)
  - [Direct Tool Definition Mode](#direct-tool-definition-mode)
  - [OpenAPI Specification Mode](#openapi-specification-mode)
- [Local Testing](#local-testing)
- [Deployment](#deployment)
- [Authentication Setup](#authentication-setup)
- [Observability](#observability)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Python 3.10 or higher
- Docker, Finch, or Podman (for deployment)
- AWS account with appropriate permissions
- AWS CLI configured with credentials

### Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd mcp-template
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Choose your development mode and customize the examples in `src/examples/`

4. Test locally:
```bash
python src/server.py
```

5. Deploy to AWS:
```bash
agentcore configure -e src/server.py --protocol MCP
agentcore launch
```

## Project Structure

```
mcp-template/
├── README.md                          # This file
├── requirements.txt                   # Core dependencies
├── requirements-openapi.txt           # Optional OpenAPI mode dependencies
├── Dockerfile                         # ARM64-optimized container
├── config.yaml                        # Template configuration
├── .dockerignore                      # Docker build optimization
├── src/
│   ├── __init__.py
│   ├── server.py                      # Main MCP server entry point
│   ├── config.py                      # Configuration management
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── direct_tools.py           # Example: Direct tool definitions
│   │   └── openapi_tools.py          # Example: OpenAPI-based tools
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validation.py             # Input validation utilities
│   │   ├── error_handling.py         # Error handling utilities
│   │   └── observability.py          # ADOT integration helpers
│   └── examples/
│       ├── __init__.py
│       ├── calculator_tools.py       # Example: Simple calculator
│       ├── openapi_petstore.py       # Example: OpenAPI conversion
│       └── sample_openapi.yaml       # Example: OpenAPI spec
├── deployment/
│   ├── iam_policy.json               # IAM execution role policy
│   ├── cognito_setup.md              # Cognito authentication guide
│   └── auth0_setup.md                # Auth0 authentication guide
├── tests/
│   ├── __init__.py
│   ├── test_client_local.py          # Local testing client
│   └── test_client_remote.py         # Remote testing client
└── docs/
    ├── DEPLOYMENT.md                  # Detailed deployment guide
    ├── BEST_PRACTICES.md              # Security and production best practices
    └── CUSTOMIZATION.md               # How to customize this template
```

## Usage Modes

### Direct Tool Definition Mode

The simplest way to create MCP tools - define Python functions and decorate them with `@mcp.tool()`.

**Example: Create a new tool**

1. Open `src/tools/direct_tools.py`
2. Add your function:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(host="0.0.0.0", stateless_http=True)

@mcp.tool()
def my_custom_tool(input_param: str) -> str:
    """
    Description of what your tool does.
    
    Args:
        input_param: Description of the parameter
    
    Returns:
        Description of the return value
    """
    # Your business logic here
    result = process_input(input_param)
    return result
```

3. Import your tool in `src/server.py`:
```python
from tools.direct_tools import my_custom_tool
```

4. Test locally and deploy

**See `src/examples/calculator_tools.py` for a complete example.**

### OpenAPI Specification Mode

Convert existing OpenAPI specifications to MCP tools automatically.

**Example: Import an OpenAPI spec**

1. Place your OpenAPI spec in `src/examples/` (YAML or JSON)
2. Use the conversion utility in `src/tools/openapi_tools.py`:

```python
from tools.openapi_tools import create_tools_from_openapi

# Load and convert your OpenAPI spec
tools = create_tools_from_openapi("src/examples/your_api_spec.yaml")
```

3. The converter will automatically:
   - Parse the OpenAPI specification
   - Generate MCP tool definitions
   - Create input validation schemas
   - Set up proper error handling

**See `src/examples/openapi_petstore.py` for a complete example.**

## Local Testing

### Start the MCP Server

```bash
# Standard mode
python src/server.py

# With observability (ADOT)
opentelemetry-instrument python src/server.py
```

The server will start on `http://localhost:8000/mcp`

### Test with MCP Client

Use the provided test client:

```bash
python tests/test_client_local.py
```

Or test manually with curl:

```bash
# List available tools
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
  }'

# Call a tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "add_numbers",
      "arguments": {"a": 5, "b": 3}
    },
    "id": 2
  }'
```

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

## Deployment

### Step 1: Configure Deployment

1. Set up authentication (see [Authentication Setup](#authentication-setup))

2. Configure the deployment:
```bash
agentcore configure -e src/server.py --protocol MCP
```

Follow the prompts to set:
- IAM execution role ARN
- ECR repository (auto-created if not specified)
- OAuth configuration (optional)

### Step 2: Deploy to AWS

```bash
agentcore launch
```

This will:
1. Build a Docker container (ARM64)
2. Push to Amazon ECR
3. Deploy to Amazon Bedrock AgentCore Runtime
4. Return your agent runtime ARN

### Step 3: Test Remote Deployment

```bash
# Set environment variables
export AGENT_ARN="your-agent-runtime-arn"
export BEARER_TOKEN="your-oauth-token"

# Run remote test
python tests/test_client_remote.py
```

## Authentication Setup

### Option 1: Amazon Cognito

Follow the detailed guide in `deployment/cognito_setup.md`

**Quick Setup:**

1. Create a Cognito User Pool
2. Configure OAuth 2.0 settings
3. Create an app client
4. Use the discovery URL during deployment:
   ```
   https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/openid-configuration
   ```

### Option 2: Auth0

Follow the detailed guide in `deployment/auth0_setup.md`

**Quick Setup:**

1. Create an Auth0 application
2. Configure application settings
3. Use your Auth0 domain's discovery URL:
   ```
   https://{your-domain}.auth0.com/.well-known/openid-configuration
   ```

## Observability

This template includes AWS Distro for OpenTelemetry (ADOT) integration for comprehensive observability.

### Enable Observability

1. **Enable CloudWatch Transaction Search** (one-time setup):
   - Open CloudWatch console
   - Navigate to Application Signals (APM) → Transaction search
   - Choose "Enable Transaction Search"

2. **Run with ADOT instrumentation**:
```bash
opentelemetry-instrument python src/server.py
```

3. **View metrics in CloudWatch**:
   - Open CloudWatch console
   - Navigate to GenAI Observability
   - Find your agent service
   - View traces, metrics, and logs

### Custom Instrumentation

The template includes helper utilities in `src/utils/observability.py`:

```python
from utils.observability import trace_tool_execution, record_metric

@mcp.tool()
@trace_tool_execution("my_tool")
def my_tool(input_data: str) -> str:
    record_metric("tool_invocation", 1, {"tool_name": "my_tool"})
    return process(input_data)
```

### Session ID Propagation

For session tracking:

```python
from opentelemetry import baggage, context

ctx = baggage.set_baggage("session.id", session_id)
context.attach(ctx)
```

## Best Practices

### Security

✅ **Never hardcode secrets** - Use AWS Secrets Manager or environment variables
✅ **Follow least privilege principle** - Use minimal IAM permissions
✅ **Validate all inputs** - Use the validation utilities in `src/utils/validation.py`
✅ **Enable OAuth authentication** - Protect your deployed MCP server
✅ **Regular updates** - Keep dependencies up to date

### Error Handling

✅ **Use structured error responses** - Follow MCP protocol standards
✅ **Log errors appropriately** - Include context but not sensitive data
✅ **Handle timeouts gracefully** - Set appropriate timeout values
✅ **Provide helpful error messages** - Guide users to resolution

### Performance

✅ **Keep tools stateless** - AgentCore provides session isolation
✅ **Optimize cold starts** - Minimize initialization code
✅ **Use async where appropriate** - For I/O-bound operations
✅ **Monitor metrics** - Use CloudWatch to track performance

### Development

✅ **Test locally first** - Use the provided test clients
✅ **Use version control** - Track changes to your tools
✅ **Document your tools** - Clear docstrings help AI agents use them
✅ **Separate concerns** - Keep business logic separate from MCP boilerplate

See `docs/BEST_PRACTICES.md` for comprehensive guidelines.

## Troubleshooting

### Common Issues

**Server won't start:**
- Check Python version (3.10+ required)
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check port 8000 is not in use: `lsof -i :8000`

**Deployment fails:**
- Verify AWS credentials: `aws sts get-caller-identity`
- Check IAM permissions match `deployment/iam_policy.json`
- Ensure Docker/Finch/Podman is running
- Verify execution role ARN is correct

**Authentication errors:**
- Verify OAuth token is valid and not expired
- Check discovery URL is accessible
- Confirm client ID matches your OAuth configuration
- Review authentication setup guides in `deployment/`

**Docker build fails:**
- Ensure Docker buildx is enabled: `docker buildx create --use`
- Verify ARM64 platform support
- Check network connectivity for downloading dependencies

**Tools not working:**
- Verify tool definitions follow MCP protocol
- Check input validation schemas
- Review CloudWatch logs for detailed errors
- Test locally before deploying

### Getting Help

- Review the detailed guides in `docs/`
- Check CloudWatch logs for your deployed agent
- Test with MCP Inspector for detailed debugging
- Review AWS AgentCore documentation: https://docs.aws.amazon.com/bedrock-agentcore/

## Additional Resources

- [Amazon Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [AWS Distro for OpenTelemetry](https://aws-otel.github.io/)
- [OpenAPI Specification](https://swagger.io/specification/)

## Contributing

Contributions are welcome! Please ensure:
- All examples work both locally and deployed
- Documentation is updated
- Code follows existing patterns
- Tests pass

## License

This template is provided as-is for use with Amazon Bedrock AgentCore Runtime.
