# AgentCore Runtime Deployment Guide

Comprehensive guide for deploying MCP servers to Amazon Bedrock AgentCore Runtime with detailed instructions for both Docker-based and S3 direct file reference approaches.

## Table of Contents

- [Overview](#overview)
- [Deployment Approaches](#deployment-approaches)
- [Prerequisites](#prerequisites)
- [Approach 1: S3 Direct File Reference](#approach-1-s3-direct-file-reference)
- [Approach 2: Docker-Based Deployment](#approach-2-docker-based-deployment)
- [AgentCore Invocation Examples](#agentcore-invocation-examples)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Overview

Amazon Bedrock AgentCore Runtime provides a managed environment for running MCP (Model Context Protocol) servers. This guide covers two deployment methods, each with specific advantages and use cases.

### Deployment Comparison

| Feature | S3 Direct | Docker |
|---------|-----------|--------|
| **Setup Time** | 5 minutes | 15-30 minutes |
| **Build Time** | ~10 seconds | 2-5 minutes |
| **Update Speed** | Very fast | Moderate |
| **Complexity** | Low | Medium |
| **Dependencies** | Python only | Any system package |
| **Best For** | Development, simple projects | Production, complex dependencies |
| **Local Testing** | `python src/server.py` | Docker required |
| **Platform Issues** | None | ARM64 build required |

## Deployment Approaches

### S3 Direct File Reference ✨ Recommended for Getting Started

**How it works:**
1. Package Python code into ZIP file
2. Upload to S3
3. AgentCore runs code directly in managed Python runtime

**Advantages:**
- ✅ No Docker installation needed
- ✅ Fastest deployment cycle
- ✅ Easiest debugging
- ✅ Perfect for development

**Limitations:**
- ⚠️ Pure Python packages only
- ⚠️ 250 MB package limit
- ⚠️ AWS managed Python runtime

### Docker-Based Deployment 🐳 Recommended for Production

**How it works:**
1. Build Docker container (ARM64)
2. Push to Amazon ECR
3. AgentCore runs containerized application

**Advantages:**
- ✅ Any system dependencies
- ✅ Exact environment control
- ✅ Better for complex projects
- ✅ Production-grade isolation

**Limitations:**
- ⚠️ Requires Docker/Finch/Podman
- ⚠️ ARM64 platform required
- ⚠️ Slower build process

## Prerequisites

### Common Requirements

1. **AWS Account** with AgentCore access
2. **AWS CLI** configured:
   ```bash
   aws configure
   aws sts get-caller-identity  # Verify credentials
   ```

3. **Python 3.10+**:
   ```bash
   python --version  # Should be 3.10 or higher
   ```

4. **boto3** installed:
   ```bash
   pip install boto3
   ```

### Additional for Docker Deployment

5. **Docker, Finch, or Podman** with buildx support:
   ```bash
   docker --version
   docker buildx version
   ```

6. **Enable buildx** (if not already):
   ```bash
   docker buildx create --use
   ```

### IAM Permissions

Your IAM user/role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:CreateAgentRuntime",
        "bedrock-agentcore:UpdateAgentRuntime",
        "bedrock-agentcore:DeleteAgentRuntime",
        "bedrock-agentcore:InvokeAgentRuntime",
        "bedrock-agentcore:DescribeAgentRuntime",
        "s3:PutObject",
        "s3:GetObject",
        "s3:CreateBucket",
        "ecr:CreateRepository",
        "ecr:PutImage",
        "ecr:GetAuthorizationToken",
        "iam:PassRole",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

## Approach 1: S3 Direct File Reference

### Step 1: Deploy Infrastructure

Choose one method:

**Option A: Using CloudFormation**
```bash
cd deployment/cloudformation

aws cloudformation create-stack \
  --stack-name mcp-server-dev \
  --template-body file://mcp-infrastructure.yaml \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=mcp-server \
    ParameterKey=Environment,ParameterValue=dev \
    ParameterKey=DeploymentMethod,ParameterValue=s3 \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete --stack-name mcp-server-dev
```

**Option B: Using CDK**
```bash
cd deployment/cdk

# Install dependencies
pip install aws-cdk-lib constructs

# Deploy
cdk deploy --context environment=dev --context deployment-method=s3
```

**Option C: Manual Setup**
```bash
# Create S3 bucket
aws s3 mb s3://my-mcp-deployments-$AWS_ACCOUNT_ID --region us-west-2

# Create IAM role (use deployment/iam_policy.json)
aws iam create-role \
  --role-name AgentCoreExecutionRole \
  --assume-role-policy-document file://trust-policy.json

aws iam put-role-policy \
  --role-name AgentCoreExecutionRole \
  --policy-name AgentCorePolicy \
  --policy-document file://deployment/iam_policy.json
```

### Step 2: Deploy MCP Server to S3

```bash
cd /path/to/mcp-template

python deployment/s3-direct/deploy_s3.py \
  --bucket my-mcp-deployments-123456789012 \
  --role-arn arn:aws:iam::123456789012:role/AgentCoreExecutionRole \
  --runtime-name mcp-server-dev \
  --region us-west-2
```

**With OAuth authentication:**
```bash
python deployment/s3-direct/deploy_s3.py \
  --bucket my-mcp-deployments-123456789012 \
  --role-arn arn:aws:iam::123456789012:role/AgentCoreExecutionRole \
  --runtime-name mcp-server-dev \
  --oauth-discovery-url https://cognito-idp.us-west-2.amazonaws.com/us-west-2_xxxxx/.well-known/openid-configuration \
  --oauth-client-id your-client-id
```

### Step 3: Validate Deployment

```bash
# Get runtime ARN from deployment output
RUNTIME_ARN="arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-dev"

# Run validation
python deployment/validation/validate_deployment.py \
  --runtime-arn $RUNTIME_ARN \
  --region us-west-2
```

### Step 4: Update Deployment

When you make changes:

```bash
python deployment/s3-direct/deploy_s3.py \
  --bucket my-mcp-deployments-123456789012 \
  --role-arn arn:aws:iam::123456789012:role/AgentCoreExecutionRole \
  --update arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-dev
```

## Approach 2: Docker-Based Deployment

### Step 1: Deploy Infrastructure

Same as S3 approach, but use `deployment-method=docker`:

```bash
# CloudFormation
aws cloudformation create-stack \
  --stack-name mcp-server-prod \
  --template-body file://deployment/cloudformation/mcp-infrastructure.yaml \
  --parameters \
    ParameterKey=ProjectName,ParameterValue=mcp-server \
    ParameterKey=Environment,ParameterValue=prod \
    ParameterKey=DeploymentMethod,ParameterValue=docker \
  --capabilities CAPABILITY_NAMED_IAM

# Or CDK
cd deployment/cdk
cdk deploy --context environment=prod --context deployment-method=docker
```

### Step 2: Build Docker Image

```bash
cd /path/to/mcp-template

# Login to ECR
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-west-2"
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/mcp-server-prod"

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

# Build for ARM64 (AgentCore requirement)
docker buildx build \
  --platform linux/arm64 \
  -t $ECR_REPO:latest \
  --push \
  .
```

### Step 3: Deploy with AgentCore Starter Toolkit

```bash
# Install toolkit
pip install bedrock-agentcore-starter-toolkit

# Configure
agentcore configure --entrypoint src/server.py --protocol MCP

# Follow prompts:
# - IAM Role: arn:aws:iam::123456789012:role/AgentCoreExecutionRole
# - ECR Repository: <use the one from infrastructure stack>
# - OAuth: (optional)

# Deploy
agentcore launch
```

### Step 4: Alternative - Manual Deployment

```bash
# Create deployment script
cat > deploy_docker.py << 'EOF'
import boto3
import json

client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')

response = client.create_agent_runtime(
    agentRuntimeName='mcp-server-prod',
    agentRuntimeArtifact={
        'containerConfiguration': {
            'containerUri': '123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-server-prod:latest'
        }
    },
    networkConfiguration={'networkMode': 'PUBLIC'},
    roleArn='arn:aws:iam::123456789012:role/AgentCoreExecutionRole'
)

print(f"Runtime ARN: {response['agentRuntimeArn']}")
print(f"Status: {response['status']}")
EOF

python deploy_docker.py
```

### Step 5: Validate Deployment

```bash
RUNTIME_ARN="<from-deployment-output>"

python deployment/validation/validate_deployment.py \
  --runtime-arn $RUNTIME_ARN
```

## AgentCore Invocation Examples

### Example 1: List Available Tools

```python
#!/usr/bin/env python3
"""List all tools available in the MCP server."""

import boto3
import json

# Initialize client
client = boto3.client('bedrock-agentcore', region_name='us-west-2')

# Prepare request
runtime_arn = "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-dev"
session_id = "example-session-12345678901234567890123"  # Must be 33+ characters

payload = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
}

# Invoke runtime
response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps(payload),
    qualifier='DEFAULT'
)

# Parse response
result = json.loads(response['response'].read())
print(json.dumps(result, indent=2))

# Expected output:
# {
#   "jsonrpc": "2.0",
#   "result": {
#     "tools": [
#       {
#         "name": "add_numbers",
#         "description": "Add two numbers together",
#         "inputSchema": {
#           "type": "object",
#           "properties": {
#             "a": {"type": "number"},
#             "b": {"type": "number"}
#           },
#           "required": ["a", "b"]
#         }
#       }
#     ]
#   },
#   "id": 1
# }
```

### Example 2: Call a Tool

```python
#!/usr/bin/env python3
"""Call a specific tool in the MCP server."""

import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

runtime_arn = "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-dev"
session_id = "example-session-12345678901234567890123"

payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "add_numbers",
        "arguments": {
            "a": 42,
            "b": 58
        }
    },
    "id": 2
}

response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps(payload),
    qualifier='DEFAULT'
)

result = json.loads(response['response'].read())
print(json.dumps(result, indent=2))

# Expected output:
# {
#   "jsonrpc": "2.0",
#   "result": {
#     "content": [
#       {
#         "type": "text",
#         "text": "100"
#       }
#     ]
#   },
#   "id": 2
# }
```

### Example 3: With Authentication

```python
#!/usr/bin/env python3
"""Invoke MCP server with OAuth authentication."""

import boto3
import json
import requests

# Get OAuth token first
def get_oauth_token(client_id, client_secret, token_url):
    """Obtain OAuth token from provider."""
    response = requests.post(
        token_url,
        data={
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret
        }
    )
    response.raise_for_status()
    return response.json()['access_token']

# Get token
token = get_oauth_token(
    client_id="your-client-id",
    client_secret="your-client-secret",
    token_url="https://your-domain.auth0.com/oauth/token"
)

# Invoke with bearer token
client = boto3.client('bedrock-agentcore', region_name='us-west-2')

payload = {
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
}

response = client.invoke_agent_runtime(
    agentRuntimeArn="arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-prod",
    runtimeSessionId="auth-session-12345678901234567890123",
    payload=json.dumps(payload),
    qualifier='DEFAULT',
    bearerToken=token  # Add authentication token
)

result = json.loads(response['response'].read())
print(json.dumps(result, indent=2))
```

### Example 4: Error Handling

```python
#!/usr/bin/env python3
"""Proper error handling for AgentCore invocations."""

import boto3
import json
from botocore.exceptions import ClientError

def invoke_mcp_tool(runtime_arn, tool_name, arguments):
    """
    Invoke MCP tool with comprehensive error handling.
    
    Args:
        runtime_arn: AgentCore Runtime ARN
        tool_name: Name of the tool to call
        arguments: Dictionary of tool arguments
    
    Returns:
        Tool result or None if error
    """
    client = boto3.client('bedrock-agentcore', region_name='us-west-2')
    
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        },
        "id": 1
    }
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=f"session-{tool_name}-{''.join(str(hash(str(arguments))))}",
            payload=json.dumps(payload),
            qualifier='DEFAULT'
        )
        
        result = json.loads(response['response'].read())
        
        # Check for JSON-RPC error
        if 'error' in result:
            error = result['error']
            print(f"Tool error: {error.get('message', 'Unknown error')}")
            print(f"Error code: {error.get('code', 'unknown')}")
            return None
        
        # Extract result
        if 'result' in result:
            return result['result']
        else:
            print("Unexpected response format")
            return None
            
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'ResourceNotFoundException':
            print(f"Runtime not found: {runtime_arn}")
        elif error_code == 'ValidationException':
            print(f"Invalid request: {error_message}")
        elif error_code == 'AccessDeniedException':
            print(f"Access denied: {error_message}")
        elif error_code == 'ThrottlingException':
            print("Rate limited - please retry")
        else:
            print(f"AWS error: {error_code} - {error_message}")
        
        return None
    
    except json.JSONDecodeError as e:
        print(f"Invalid JSON response: {e}")
        return None
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


# Usage
result = invoke_mcp_tool(
    runtime_arn="arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-dev",
    tool_name="add_numbers",
    arguments={"a": 10, "b": 20}
)

if result:
    print("Success:", result)
else:
    print("Tool invocation failed")
```

### Example 5: Batch Operations

```python
#!/usr/bin/env python3
"""Execute multiple tool calls in sequence."""

import boto3
import json
import uuid

def batch_invoke_tools(runtime_arn, tool_calls):
    """
    Execute multiple tool calls.
    
    Args:
        runtime_arn: AgentCore Runtime ARN
        tool_calls: List of (tool_name, arguments) tuples
    
    Returns:
        List of results
    """
    client = boto3.client('bedrock-agentcore', region_name='us-west-2')
    results = []
    
    for idx, (tool_name, arguments) in enumerate(tool_calls, 1):
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": idx
        }
        
        session_id = f"batch-session-{uuid.uuid4().hex}"
        
        try:
            response = client.invoke_agent_runtime(
                agentRuntimeArn=runtime_arn,
                runtimeSessionId=session_id,
                payload=json.dumps(payload),
                qualifier='DEFAULT'
            )
            
            result = json.loads(response['response'].read())
            results.append({
                'tool': tool_name,
                'success': 'result' in result,
                'data': result
            })
            
        except Exception as e:
            results.append({
                'tool': tool_name,
                'success': False,
                'error': str(e)
            })
    
    return results


# Usage
runtime_arn = "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-dev"

tool_calls = [
    ("add_numbers", {"a": 5, "b": 3}),
    ("multiply_numbers", {"a": 4, "b": 7}),
    ("subtract_numbers", {"a": 10, "b": 2}),
]

results = batch_invoke_tools(runtime_arn, tool_calls)

for result in results:
    print(f"\nTool: {result['tool']}")
    print(f"Success: {result['success']}")
    if result['success']:
        print(f"Result: {result['data']['result']}")
    else:
        print(f"Error: {result.get('error', 'Unknown')}")
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Runtime Not Found

**Error:** `ResourceNotFoundException: Agent runtime not found`

**Solution:**
```bash
# Verify runtime exists
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id mcp-server-dev

# Check status
aws bedrock-agentcore-control list-agent-runtimes \
  --query 'agentRuntimes[?agentRuntimeName==`mcp-server-dev`]'
```

#### 2. Runtime Not Active

**Error:** Runtime status is CREATING, UPDATING, or FAILED

**Solution:**
```bash
# Check status
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id mcp-server-dev \
  --query 'status'

# If FAILED, check logs
aws logs tail /aws/bedrock-agentcore/mcp-server-dev --follow

# Wait for ACTIVE status
aws bedrock-agentcore-control wait agent-runtime-available \
  --agent-runtime-id mcp-server-dev
```

#### 3. Invalid Session ID

**Error:** `ValidationException: runtimeSessionId must be at least 33 characters`

**Solution:**
```python
# Correct: 33+ characters
session_id = f"my-session-{uuid.uuid4().hex}"  # Total: 43 characters

# Incorrect: Too short
session_id = "session-123"  # Only 11 characters
```

#### 4. Authentication Failure

**Error:** `AccessDeniedException: Unauthorized`

**Solution:**
```bash
# Verify OAuth token is valid
# Test token endpoint
curl -X POST https://your-domain.auth0.com/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "client_credentials",
    "client_id": "your-client-id",
    "client_secret": "your-client-secret"
  }'

# Use fresh token
# Tokens typically expire after 1 hour
```

#### 5. Tool Not Found

**Error:** `"error": {"code": -32601, "message": "Method not found"}`

**Solution:**
```python
# List available tools first
payload = {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
# Then call exact tool name from the list
```

#### 6. Invalid Parameters

**Error:** `"error": {"code": -32602, "message": "Invalid params"}`

**Solution:**
```python
# Check tool schema
response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1}),
    qualifier='DEFAULT'
)

# Match parameter names and types exactly
# Use the inputSchema from tools/list response
```

#### 7. S3 Deployment Package Import Error

**Error:** `ModuleNotFoundError: No module named 'xyz'`

**Solution:**
```bash
# Add missing package to requirements.txt
echo "xyz==1.0.0" >> requirements.txt

# Redeploy
python deployment/s3-direct/deploy_s3.py --update arn:...
```

#### 8. Docker Build Platform Error

**Error:** `exec format error` or `platform mismatch`

**Solution:**
```bash
# Always specify ARM64 platform
docker buildx build --platform linux/arm64 -t image:tag .

# Verify buildx is enabled
docker buildx ls
```

#### 9. ECR Push Permission Denied

**Error:** `denied: User ... is not authorized to perform: ecr:PutImage`

**Solution:**
```bash
# Add ECR permissions to IAM user/role
aws iam put-user-policy \
  --user-name your-user \
  --policy-name ECRAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:PutImage",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "*"
    }]
  }'
```

#### 10. Slow Cold Starts

**Symptom:** First invocation takes 10+ seconds

**Solution:**
```python
# Optimize imports - use lazy loading
def my_tool(input_data: str):
    import heavy_library  # Import only when needed
    return heavy_library.process(input_data)

# Reduce package size
# Remove unused dependencies from requirements.txt

# Use Docker deployment for better cold start performance
```

### Debugging Tips

#### View Runtime Logs

```bash
# Tail logs in real-time
aws logs tail /aws/bedrock-agentcore/mcp-server-dev --follow

# Get recent logs
aws logs tail /aws/bedrock-agentcore/mcp-server-dev --since 1h

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/mcp-server-dev \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000
```

#### Test Locally First

```bash
# Always test locally before deploying
python src/server.py

# In another terminal
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

#### Enable Debug Logging

```python
# In src/config.py
logging:
  level: "DEBUG"  # Change from INFO to DEBUG

# Or set environment variable
export MCP_LOG_LEVEL="DEBUG"
```

#### Use Validation Script

```bash
# Comprehensive validation
python deployment/validation/validate_deployment.py \
  --runtime-arn arn:... \
  --output-report validation-report.json

# Review report
cat validation-report.json | jq '.'
```

## Best Practices

### 1. Development Workflow

```bash
# Local development
python src/server.py
# Test with client
python tests/test_client_local.py

# Deploy to dev (S3 for speed)
python deployment/s3-direct/deploy_s3.py --bucket ... --runtime-name mcp-server-dev

# Validate
python deployment/validation/validate_deployment.py --runtime-arn ...

# Once stable, deploy to prod (Docker for isolation)
docker buildx build --platform linux/arm64 -t ... --push .
agentcore launch
```

### 2. Environment Management

```
dev     -> S3 deployment, fast iterations
staging -> Docker deployment, pre-production testing
prod    -> Docker deployment, strict controls
```

### 3. Version Control

```bash
# Tag deployments
python deployment/s3-direct/deploy_s3.py \
  --bucket my-bucket \
  --runtime-name mcp-server-dev-v1.2.0

# Or use git tags
git tag -a v1.2.0 -m "Release 1.2.0"
git push origin v1.2.0
```

### 4. Monitoring

```bash
# Set up CloudWatch dashboard
# Enable ADOT observability
# Configure SNS notifications
# Review logs regularly
```

### 5. Security

- ✅ Always use OAuth in production
- ✅ Rotate credentials regularly
- ✅ Use Secrets Manager for sensitive data
- ✅ Enable encryption at rest (S3, ECR)
- ✅ Restrict IAM roles to minimum permissions
- ✅ Review CloudTrail logs

### 6. Cost Optimization

- Use S3 deployment for dev (cheaper)
- Set lifecycle policies on S3 and ECR
- Delete unused runtimes
- Monitor CloudWatch costs
- Use appropriate log retention

## Next Steps

1. **Choose deployment method** based on your needs
2. **Deploy infrastructure** using CloudFormation or CDK
3. **Deploy MCP server** with chosen approach
4. **Validate deployment** with validation script
5. **Test invocations** with example scripts
6. **Set up monitoring** and alerts
7. **Document** your specific configuration

## Additional Resources

- [Main README](../README.md)
- [S3 Deployment Guide](../deployment/s3-direct/README.md)
- [CloudFormation Templates](../deployment/cloudformation/)
- [CDK Templates](../deployment/cdk/)
- [Validation Scripts](../deployment/validation/)
- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [MCP Specification](https://modelcontextprotocol.io/)
