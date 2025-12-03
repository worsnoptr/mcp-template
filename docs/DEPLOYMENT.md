# Deployment Guide

Detailed guide for deploying your MCP server to Amazon Bedrock AgentCore Runtime.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Methods](#deployment-methods)
- [Step-by-Step Deployment](#step-by-step-deployment)
- [Configuration Options](#configuration-options)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- **AWS Account**: With appropriate permissions
- **Python 3.10+**: Installed locally
- **AWS CLI**: Configured with credentials
- **AgentCore Starter Toolkit**: `pip install bedrock-agentcore-starter-toolkit`

### Optional (for local testing)

- **Docker, Finch, or Podman**: For building and testing containers locally

### AWS Permissions

Your IAM user/role needs these permissions:

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
        "ecr:CreateRepository",
        "ecr:PutImage",
        "ecr:GetAuthorizationToken",
        "iam:PassRole"
      ],
      "Resource": "*"
    }
  ]
}
```

## Deployment Methods

### Method 1: AgentCore Starter Toolkit (Recommended)

**Pros:**
- Automated deployment process
- Handles containerization automatically
- Easy updates and rollbacks

**Best for:** Quick prototyping and most production use cases

### Method 2: Manual Deployment with boto3

**Pros:**
- Full control over deployment
- Custom CI/CD integration
- Advanced configuration options

**Best for:** Enterprise deployments with existing CI/CD pipelines

## Step-by-Step Deployment

### Method 1: Using AgentCore Starter Toolkit

#### 1. Install the Toolkit

```bash
pip install bedrock-agentcore-starter-toolkit
```

#### 2. Prepare Your Project

Ensure your project structure matches:

```
your-mcp-server/
├── src/
│   ├── server.py        # Main entry point
│   ├── config.py        # Configuration
│   ├── tools/           # Your tools
│   └── utils/           # Utilities
├── requirements.txt     # Dependencies
└── __init__.py          # Makes it a package
```

#### 3. Configure Deployment

```bash
agentcore configure --entrypoint src/server.py --protocol MCP
```

This will prompt you for:

**a. IAM Execution Role:**
- Choose existing role or create new one
- Must have permissions from `deployment/iam_policy.json`

Example ARN:
```
arn:aws:iam::123456789012:role/AgentCoreExecutionRole
```

**b. ECR Repository:**
- Press Enter to auto-create
- Or provide existing repository URL:
```
123456789012.dkr.ecr.us-west-2.amazonaws.com/my-mcp-server
```

**c. Dependencies:**
- Automatically detected from requirements.txt
- Confirm or modify as needed

**d. OAuth Configuration (Optional but Recommended):**
- Type "yes" if you want OAuth authentication
- Provide discovery URL (see [Cognito Setup](../deployment/cognito_setup.md) or [Auth0 Setup](../deployment/auth0_setup.md))
- Provide client ID

#### 4. Local Testing (Optional)

Test your container locally before deploying:

```bash
agentcore launch --local
```

This requires Docker, Finch, or Podman.

Test with:
```bash
curl http://localhost:8000/ping
```

#### 5. Deploy to AWS

```bash
agentcore launch
```

This will:
1. Build your Docker container (ARM64)
2. Push to Amazon ECR
3. Create AgentCore Runtime
4. Deploy your MCP server

Expected output:
```
Building container...
Pushing to ECR...
Creating AgentCore Runtime...
✓ Deployment successful!

Agent Runtime ARN: arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-mcp-server-xyz123
Endpoint: https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/...
Status: ACTIVE
```

#### 6. Test Your Deployment

```bash
# Set environment variables
export AGENT_ARN="your-agent-runtime-arn"
export BEARER_TOKEN="your-oauth-token"  # If using OAuth

# Run remote test
python tests/test_client_remote.py
```

### Method 2: Manual Deployment

#### 1. Build Docker Container

```bash
# Ensure Docker buildx is set up
docker buildx create --use

# Build for ARM64 (AgentCore requirement)
docker buildx build \
  --platform linux/arm64 \
  -t my-mcp-server:latest \
  --load \
  .
```

#### 2. Test Locally (Optional)

```bash
docker run --platform linux/arm64 \
  -p 8000:8000 \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_SESSION_TOKEN="$AWS_SESSION_TOKEN" \
  my-mcp-server:latest
```

Test:
```bash
curl http://localhost:8000/ping
```

#### 3. Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name my-mcp-server \
  --region us-west-2
```

Note the repositoryUri from output.

#### 4. Push to ECR

```bash
# Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-west-2"
REPO_NAME="my-mcp-server"

# Login to ECR
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Tag image
docker tag my-mcp-server:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest

# Push to ECR
docker buildx build \
  --platform linux/arm64 \
  -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest \
  --push \
  .
```

#### 5. Create AgentCore Runtime

Create `deploy.py`:

```python
import boto3

client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')

response = client.create_agent_runtime(
    agentRuntimeName='my-mcp-server',
    agentRuntimeArtifact={
        'containerConfiguration': {
            'containerUri': '123456789012.dkr.ecr.us-west-2.amazonaws.com/my-mcp-server:latest'
        }
    },
    networkConfiguration={'networkMode': 'PUBLIC'},
    roleArn='arn:aws:iam::123456789012:role/AgentCoreExecutionRole'
)

print(f"Agent Runtime ARN: {response['agentRuntimeArn']}")
print(f"Status: {response['status']}")
```

Run:
```bash
python deploy.py
```

#### 6. Invoke Your Server

Create `invoke.py`:

```python
import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='us-west-2')

payload = json.dumps({
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
})

response = client.invoke_agent_runtime(
    agentRuntimeArn='your-agent-runtime-arn',
    runtimeSessionId='test-session-12345678901234567890123',  # 33+ chars
    payload=payload,
    qualifier='DEFAULT'
)

response_body = response['response'].read()
print(json.loads(response_body))
```

Run:
```bash
python invoke.py
```

## Configuration Options

### Environment Variables

Set these in your deployment environment:

```bash
# Required for AWS access
export AWS_REGION="us-west-2"
export AWS_ACCOUNT_ID="123456789012"

# Optional configuration overrides
export MCP_SERVER_HOST="0.0.0.0"
export MCP_SERVER_PORT="8000"
export MCP_LOG_LEVEL="INFO"
export MCP_SERVICE_NAME="my-mcp-server"
export MCP_OBSERVABILITY_ENABLED="true"

# Authentication (if using OAuth)
export OAUTH_DISCOVERY_URL="https://..."
export OAUTH_CLIENT_ID="..."
```

### config.yaml Customization

Edit `config.yaml` for environment-specific settings:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

tools:
  mode: "direct"  # or "openapi" or "both"

observability:
  enabled: true
  service_name: "my-mcp-server"

logging:
  level: "INFO"
```

### Dockerfile Customization

For special requirements, modify the Dockerfile:

```dockerfile
# Add custom system dependencies
RUN apt-get update && apt-get install -y \
    your-custom-package \
    && rm -rf /var/lib/apt/lists/*

# Set custom environment variables
ENV MY_CUSTOM_VAR="value"

# Copy additional files
COPY custom-config/ ./config/
```

## Updates and Rollbacks

### Update Deployment

Using Toolkit:
```bash
# Make your changes
# Then redeploy
agentcore launch
```

Using Manual Method:
```bash
# Rebuild and push new image
docker buildx build --platform linux/arm64 \
  -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:latest \
  --push .

# Update runtime
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id your-runtime-id \
  --agent-runtime-artifact containerConfiguration={containerUri="..."}
```

### Rollback

Tag your images with versions:

```bash
# Deploy with version tag
docker buildx build --platform linux/arm64 \
  -t $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO_NAME:v1.0.0 \
  --push .

# To rollback, update to previous version
aws bedrock-agentcore-control update-agent-runtime \
  --agent-runtime-id your-runtime-id \
  --agent-runtime-artifact containerConfiguration={containerUri="...:v0.9.0"}
```

## Troubleshooting

### Deployment Failures

#### Error: "No such file or directory: requirements.txt"

**Solution:** Ensure requirements.txt is in project root:
```bash
ls -la requirements.txt
```

#### Error: "exec format error"

**Solution:** Ensure ARM64 platform:
```bash
docker buildx build --platform linux/arm64 ...
```

#### Error: "Unable to locate credentials"

**Solution:** Configure AWS CLI:
```bash
aws configure
# Or set environment variables
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
```

#### Error: "Access Denied" when pushing to ECR

**Solution:** Check IAM permissions:
```bash
aws ecr get-login-password --region us-west-2
```

### Runtime Failures

#### Container exits immediately

**Solution:** Check CloudWatch logs:
```bash
aws logs tail /aws/agentcore/my-mcp-server --follow
```

Common issues:
- Missing dependencies in requirements.txt
- Syntax errors in Python code
- Port 8000 not exposed
- MCP endpoint not at /mcp

#### Health check fails

**Solution:** Verify /ping endpoint:
```bash
# In your server.py
@mcp.get("/ping")
async def health_check():
    return {"status": "healthy"}
```

#### OAuth authentication fails

**Solution:** Verify:
1. Discovery URL is accessible
2. Client ID is correct
3. Token is valid and not expired

### Performance Issues

#### Cold starts are slow

**Solution:**
- Reduce Docker image size
- Minimize import statements
- Use lazy loading for heavy dependencies

#### High latency

**Solution:**
- Enable CloudWatch metrics
- Check observability traces
- Optimize tool execution
- Consider caching

### Getting Help

1. **Check CloudWatch Logs:**
   ```bash
   aws logs tail /aws/agentcore/my-mcp-server --follow
   ```

2. **View AgentCore Runtime Status:**
   ```bash
   aws bedrock-agentcore-control describe-agent-runtime \
     --agent-runtime-id your-runtime-id
   ```

3. **Test Locally First:**
   ```bash
   python src/server.py
   python tests/test_client_local.py
   ```

4. **AWS Support:**
   - [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
   - AWS Support Console

## Additional Resources

- [AgentCore Runtime Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/)
- [Docker Multi-Platform Builds](https://docs.docker.com/build/building/multi-platform/)
- [Amazon ECR User Guide](https://docs.aws.amazon.com/ecr/)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
