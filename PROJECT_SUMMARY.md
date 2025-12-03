# MCP Server Template - Project Summary

## Overview

This is a comprehensive, production-ready template for rapidly developing MCP (Model Context Protocol) servers optimized for Amazon Bedrock AgentCore Runtime. The template implements the "undifferentiated heavy lifting" principle - all common infrastructure, boilerplate code, deployment configurations, and observability integrations are pre-built.

## Key Features

### Two Development Modes
1. **Direct Tool Definition**: Define tools as Python functions using FastMCP decorators
2. **OpenAPI Specification**: Import OpenAPI 3.x specs and auto-convert to MCP tools

### Production-Ready Infrastructure
- FastMCP server with stateless HTTP transport (0.0.0.0:8000/mcp)
- Docker support optimized for ARM64 (AgentCore requirement)
- AWS Distro for OpenTelemetry (ADOT) integration
- OAuth authentication support (Cognito and Auth0)
- IAM execution role with AWS best practices
- Comprehensive error handling and input validation

## Project Structure

```
mcp-template/
├── README.md                          # Main documentation
├── PROJECT_SUMMARY.md                 # This file
├── requirements.txt                   # Core dependencies
├── requirements-openapi.txt           # OpenAPI mode dependencies
├── Dockerfile                         # ARM64-optimized container
├── config.yaml                        # Template configuration
├── .dockerignore                      # Docker build optimization
│
├── src/
│   ├── __init__.py
│   ├── server.py                      # Main MCP server entry point
│   ├── config.py                      # Configuration management
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── direct_tools.py           # Direct tool definitions
│   │   └── openapi_tools.py          # OpenAPI conversion
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validation.py             # Input validation
│   │   ├── error_handling.py         # Error handling
│   │   └── observability.py          # ADOT integration
│   │
│   └── examples/
│       ├── __init__.py
│       ├── calculator_tools.py       # Example: Calculator
│       ├── openapi_petstore.py       # Example: OpenAPI
│       └── sample_openapi.yaml       # Example: OpenAPI spec
│
├── deployment/
│   ├── iam_policy.json               # IAM execution role policy
│   ├── cognito_setup.md              # Cognito authentication
│   └── auth0_setup.md                # Auth0 authentication
│
├── tests/
│   ├── __init__.py
│   ├── test_client_local.py          # Local testing
│   └── test_client_remote.py         # Remote testing
│
└── docs/
    ├── DEPLOYMENT.md                  # Deployment guide
    ├── BEST_PRACTICES.md              # Production best practices
    └── CUSTOMIZATION.md               # Customization guide
```

## Core Components

### 1. MCP Server (src/server.py)
- FastMCP initialization with AgentCore requirements
- Automatic tool loading (direct or OpenAPI)
- Health check endpoint (/ping)
- Error handlers and observability setup

### 2. Configuration (src/config.py)
- YAML-based configuration with environment overrides
- Support for development, staging, production environments
- Environment variable overrides

### 3. Tools (src/tools/)
- **direct_tools.py**: Python function decorators for tools
- **openapi_tools.py**: Automatic OpenAPI → MCP conversion

### 4. Utilities (src/utils/)
- **validation.py**: Input validation decorators and helpers
- **error_handling.py**: Structured error responses
- **observability.py**: ADOT integration for traces and metrics

### 5. Examples (src/examples/)
- **calculator_tools.py**: Direct mode example (7 tools)
- **openapi_petstore.py**: OpenAPI mode example
- **sample_openapi.yaml**: Sample OpenAPI specification

## Quick Start

### 1. Installation
```bash
git clone <your-repo>
cd mcp-template
pip install -r requirements.txt
```

### 2. Customize Tools
Choose your mode and add tools:
- Direct: Edit `src/tools/direct_tools.py`
- OpenAPI: Add spec to `src/examples/` and update `config.yaml`

### 3. Test Locally
```bash
python src/server.py
python tests/test_client_local.py
```

### 4. Deploy to AWS
```bash
agentcore configure -e src/server.py --protocol MCP
agentcore launch
```

## Configuration

### config.yaml
Main configuration file with:
- Server settings (host, port, mcp_path)
- Tool mode selection (direct, openapi, both)
- Observability settings
- Security settings
- Environment-specific overrides

### Environment Variables
Override configuration:
- `ENVIRONMENT`: development/production
- `MCP_LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR
- `MCP_SERVICE_NAME`: Service name for observability
- `MCP_OBSERVABILITY_ENABLED`: true/false

## Authentication

### Cognito Setup
1. Create Cognito User Pool
2. Configure OAuth 2.0
3. Get discovery URL
4. Use during deployment

See: `deployment/cognito_setup.md`

### Auth0 Setup
1. Create Auth0 application
2. Configure OAuth settings
3. Get discovery URL
4. Use during deployment

See: `deployment/auth0_setup.md`

## Observability

### ADOT Integration
- Automatic distributed tracing
- Custom metrics recording
- Session ID propagation
- CloudWatch integration

### Usage
```bash
# Run with observability
opentelemetry-instrument python src/server.py
```

### View Metrics
1. Enable CloudWatch Transaction Search
2. Deploy with ADOT
3. View in CloudWatch → GenAI Observability

## Testing

### Local Testing
```bash
# Start server
python src/server.py

# Test with client
python tests/test_client_local.py

# Test with MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8000/mcp
```

### Remote Testing
```bash
export AGENT_ARN="your-arn"
export BEARER_TOKEN="your-token"
python tests/test_client_remote.py
```

## Deployment

### Method 1: AgentCore Toolkit (Recommended)
```bash
agentcore configure -e src/server.py --protocol MCP
agentcore launch
```

### Method 2: Manual
1. Build Docker image (ARM64)
2. Push to ECR
3. Create AgentCore Runtime
4. Deploy

See: `docs/DEPLOYMENT.md`

## Best Practices

### Security
- Never hardcode secrets
- Use AWS Secrets Manager
- Enable OAuth authentication
- Follow least privilege (IAM)
- Validate all inputs

### Error Handling
- Use structured error responses
- Log with context
- Handle timeouts gracefully
- Provide helpful error messages

### Performance
- Keep tools stateless
- Optimize cold starts
- Use async for I/O
- Monitor metrics

See: `docs/BEST_PRACTICES.md`

## Customization

### Add New Tools
1. Create tool function
2. Add decorators (@mcp.tool(), @trace_tool_execution)
3. Import in server.py
4. Test and deploy

### Add OpenAPI Spec
1. Place spec in `src/examples/`
2. Update `config.yaml`
3. Restart server (auto-generated)

### Extend Utilities
- Add custom validation functions
- Create custom error types
- Add business metrics
- Implement middleware

See: `docs/CUSTOMIZATION.md`

## Technical Requirements

### AgentCore Requirements (DO NOT CHANGE)
- Host: 0.0.0.0
- Port: 8000
- Endpoint: /mcp
- Transport: stateless streamable-http
- Platform: ARM64 (Docker)

### Dependencies
- Python 3.10+
- mcp
- fastapi
- uvicorn
- pydantic
- boto3
- aws-opentelemetry-distro
- pyyaml

### Optional (OpenAPI Mode)
- openapi-spec-validator
- prance
- openapi-core

## Documentation

| Document | Description |
|----------|-------------|
| README.md | Main usage guide |
| docs/DEPLOYMENT.md | Detailed deployment instructions |
| docs/BEST_PRACTICES.md | Security and production best practices |
| docs/CUSTOMIZATION.md | How to customize the template |
| deployment/cognito_setup.md | Cognito authentication setup |
| deployment/auth0_setup.md | Auth0 authentication setup |
| deployment/iam_policy.json | IAM role permissions |

## Example Tools Included

### Calculator Tools (Direct Mode)
- add_numbers
- subtract_numbers
- multiply_numbers
- divide_numbers
- power
- calculate_average
- calculate_statistics

### Direct Tools (Utilities)
- process_text
- validate_data
- transform_json

### OpenAPI Tools (Auto-generated)
- Based on sample_openapi.yaml
- Demonstrates Pet Store API conversion

## Support and Resources

### Documentation
- Amazon Bedrock AgentCore: https://docs.aws.amazon.com/bedrock-agentcore/
- Model Context Protocol: https://modelcontextprotocol.io/
- FastMCP: https://github.com/jlowin/fastmcp

### CloudWatch
- Logs: `/aws/agentcore/your-server-name`
- Metrics: GenAI Observability section
- Traces: X-Ray integration

### Testing Tools
- MCP Inspector: `npx @modelcontextprotocol/inspector`
- Local client: `tests/test_client_local.py`
- Remote client: `tests/test_client_remote.py`

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Solution: `pip install -r requirements.txt`

2. **Docker Build Fails (ARM64)**
   - Solution: Enable buildx: `docker buildx create --use`

3. **Deployment Fails**
   - Check AWS credentials
   - Verify IAM permissions
   - Check CloudWatch logs

4. **Authentication Errors**
   - Verify OAuth discovery URL
   - Check token validity
   - Confirm client ID

See `docs/DEPLOYMENT.md` for detailed troubleshooting.

## Development Workflow

1. **Clone template**
2. **Customize tools** (src/tools/ or src/examples/)
3. **Update configuration** (config.yaml)
4. **Test locally** (python src/server.py)
5. **Configure deployment** (agentcore configure)
6. **Deploy** (agentcore launch)
7. **Test remotely** (tests/test_client_remote.py)
8. **Monitor** (CloudWatch)

## License

This template is provided for use with Amazon Bedrock AgentCore Runtime.

## Version

Template Version: 1.0.0
Compatible with: AgentCore Runtime 2024+
