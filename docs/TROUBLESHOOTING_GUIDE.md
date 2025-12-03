# Deployment and Invocation Troubleshooting Guide

Comprehensive troubleshooting guide for AgentCore Runtime deployment and MCP server invocation issues.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Deployment Issues](#deployment-issues)
- [Invocation Issues](#invocation-issues)
- [Runtime Issues](#runtime-issues)
- [Authentication Issues](#authentication-issues)
- [Performance Issues](#performance-issues)
- [Tool-Specific Issues](#tool-specific-issues)
- [Debug Checklist](#debug-checklist)

## Quick Diagnostics

### Run Validation Script First

```bash
python deployment/validation/validate_deployment.py \
  --runtime-arn arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server \
  --region us-west-2 \
  --output-report validation-report.json
```

This will identify most common issues automatically.

### Check Runtime Status

```bash
# Get runtime status
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id mcp-server-dev \
  --region us-west-2

# Expected: status = "ACTIVE"
```

### View Recent Logs

```bash
# Tail logs in real-time
aws logs tail /aws/bedrock-agentcore/mcp-server-dev --follow

# Get last hour of logs
aws logs tail /aws/bedrock-agentcore/mcp-server-dev --since 1h
```

## Deployment Issues

### Issue: S3 Upload Permission Denied

**Error:**
```
❌ Failed to upload to S3: An error occurred (AccessDenied) when calling the PutObject operation
```

**Diagnosis:**
```bash
# Check S3 bucket permissions
aws s3api get-bucket-policy --bucket my-deployment-bucket

# Test write access
echo "test" > /tmp/test.txt
aws s3 cp /tmp/test.txt s3://my-deployment-bucket/test.txt
```

**Solution:**
Add S3 permissions to your IAM user/role:
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::my-deployment-bucket/*",
    "arn:aws:s3:::my-deployment-bucket"
  ]
}
```

### Issue: Runtime Creation Fails

**Error:**
```
❌ Failed to create AgentCore Runtime: An error occurred (ValidationException) when calling the CreateAgentRuntime operation
```

**Diagnosis:**
```bash
# Check if runtime name already exists
aws bedrock-agentcore-control list-agent-runtimes \
  --query 'agentRuntimes[?agentRuntimeName==`mcp-server-dev`]'

# Verify role exists and is assumable
aws iam get-role --role-name AgentCoreExecutionRole
```

**Solutions:**

1. **Runtime name conflict:**
   ```bash
   # Use unique name
   python deploy_s3.py --runtime-name mcp-server-dev-v2 ...
   
   # Or delete existing
   aws bedrock-agentcore-control delete-agent-runtime \
     --agent-runtime-id existing-id
   ```

2. **Invalid role ARN:**
   ```bash
   # Verify role ARN format
   arn:aws:iam::123456789012:role/AgentCoreExecutionRole
   
   # Check trust policy allows AgentCore to assume role
   ```

### Issue: Docker Build Fails - Platform Error

**Error:**
```
exec /bin/sh: exec format error
```

**Diagnosis:**
```bash
# Check if ARM64 is specified
docker buildx ls
docker inspect your-image-name | jq '.[0].Architecture'
```

**Solution:**
```bash
# Always build for ARM64 platform
docker buildx build --platform linux/arm64 -t image:tag .

# If buildx not available, create builder
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap
```

### Issue: ECR Push Authentication Failed

**Error:**
```
denied: Your authorization token has expired. Reauthenticate and try again.
```

**Solution:**
```bash
# Re-authenticate with ECR
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION="us-west-2"

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Verify login successful
docker info | grep Registry
```

### Issue: Module Import Error in S3 Deployment

**Error from CloudWatch:**
```
ModuleNotFoundError: No module named 'requests'
```

**Diagnosis:**
```bash
# Check what's in your requirements.txt
cat requirements.txt

# Verify package exists
pip show requests
```

**Solution:**
```bash
# Add missing dependency
echo "requests==2.31.0" >> requirements.txt

# Redeploy
python deployment/s3-direct/deploy_s3.py \
  --update arn:aws:bedrock-agentcore:...
```

## Invocation Issues

### Issue: Runtime Not Found

**Error:**
```python
botocore.exceptions.ClientError: An error occurred (ResourceNotFoundException) when calling the InvokeAgentRuntime operation: Agent runtime not found
```

**Diagnosis:**
```bash
# List all runtimes
aws bedrock-agentcore-control list-agent-runtimes

# Check exact ARN
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id mcp-server-dev
```

**Solution:**
```python
# Use correct ARN format
runtime_arn = "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-dev"

# Not this:
# runtime_arn = "mcp-server-dev"  # ❌ Wrong
```

### Issue: Invalid Session ID

**Error:**
```
ValidationException: runtimeSessionId must be at least 33 characters
```

**Solution:**
```python
import uuid

# Correct: Generate long enough session ID
session_id = f"my-app-session-{uuid.uuid4().hex}"
# Length: 16 + 1 + 32 = 49 characters ✓

# Wrong: Too short
session_id = "session-123"  # Only 11 characters ❌
```

### Issue: JSON-RPC Method Not Found

**Error:**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32601,
    "message": "Method not found"
  }
}
```

**Diagnosis:**
```bash
# List available methods/tools
python -c "
import boto3, json
client = boto3.client('bedrock-agentcore')
response = client.invoke_agent_runtime(
    agentRuntimeArn='YOUR_ARN',
    runtimeSessionId='diagnostic-session-12345678901234567890123',
    payload=json.dumps({'jsonrpc':'2.0','method':'tools/list','id':1}),
    qualifier='DEFAULT'
)
print(response['response'].read())
"
```

**Solution:**
```python
# Use exact tool name from tools/list
payload = {
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "add_numbers",  # Must match exactly
        "arguments": {"a": 1, "b": 2}
    },
    "id": 1
}
```

### Issue: Invalid Parameters

**Error:**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params: missing required parameter 'a'"
  }
}
```

**Diagnosis:**
```python
# Check tool schema
response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    }),
    qualifier='DEFAULT'
)

result = json.loads(response['response'].read())
for tool in result['result']['tools']:
    if tool['name'] == 'your_tool_name':
        print(json.dumps(tool['inputSchema'], indent=2))
```

**Solution:**
```python
# Match parameter names and types exactly
# If schema says:
# {"type": "object", "properties": {"a": {"type": "number"}}, "required": ["a"]}

# Then use:
arguments = {"a": 42}  # ✓ Correct

# Not:
arguments = {"A": 42}  # ❌ Wrong case
arguments = {"a": "42"}  # ❌ Wrong type (string instead of number)
```

## Runtime Issues

### Issue: Runtime Stuck in CREATING Status

**Diagnosis:**
```bash
# Check status
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id mcp-server-dev \
  --query 'status'

# Check for failures in events
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id mcp-server-dev \
  --query 'failureReason'
```

**Solution:**
```bash
# If stuck for >5 minutes, delete and recreate
aws bedrock-agentcore-control delete-agent-runtime \
  --agent-runtime-id mcp-server-dev

# Wait for deletion
sleep 30

# Redeploy
python deployment/s3-direct/deploy_s3.py ...
```

### Issue: Runtime Status is FAILED

**Diagnosis:**
```bash
# Get failure reason
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id mcp-server-dev \
  --query 'failureReason' \
  --output text

# Check recent logs
aws logs tail /aws/bedrock-agentcore/mcp-server-dev --since 1h
```

**Common Failures and Solutions:**

1. **"Failed to download from S3"**
   - Check S3 bucket permissions
   - Verify S3 URI is correct
   - Ensure IAM role has s3:GetObject permission

2. **"Failed to pull Docker image"**
   - Verify ECR repository exists
   - Check image tag is correct
   - Ensure IAM role has ecr:GetDownloadUrlForLayer permission

3. **"Container failed health check"**
   - Check /ping endpoint exists
   - Verify server starts on port 8000
   - Review application logs in CloudWatch

### Issue: Container Exits Immediately

**Diagnosis:**
```bash
# Get container logs
aws logs tail /aws/bedrock-agentcore/mcp-server-dev --since 5m

# Common issues to look for:
# - "ModuleNotFoundError"
# - "SyntaxError"
# - "Port already in use"
# - "Permission denied"
```

**Solutions:**

1. **Module not found:**
   ```bash
   # Add to requirements.txt and redeploy
   echo "missing-module==1.0.0" >> requirements.txt
   ```

2. **Syntax error:**
   ```bash
   # Test locally first
   python src/server.py
   
   # Fix errors, then redeploy
   ```

3. **Port configuration:**
   ```python
   # Must use port 8000
   mcp = FastMCP(host="0.0.0.0", port=8000)
   ```

## Authentication Issues

### Issue: OAuth Token Expired

**Error:**
```
AccessDeniedException: The provided token is expired
```

**Solution:**
```python
import requests

def get_fresh_token(client_id, client_secret, token_url):
    """Get new OAuth token."""
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

# Use fresh token for each invocation
token = get_fresh_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL)

response = client.invoke_agent_runtime(
    agentRuntimeArn=runtime_arn,
    runtimeSessionId=session_id,
    payload=payload,
    bearerToken=token  # Fresh token
)
```

### Issue: OAuth Discovery URL Not Accessible

**Error:**
```
ValidationException: Unable to fetch OAuth configuration from discovery URL
```

**Diagnosis:**
```bash
# Test discovery URL
curl https://cognito-idp.us-west-2.amazonaws.com/us-west-2_xxxxx/.well-known/openid-configuration

# Should return JSON with issuer, token_endpoint, etc.
```

**Solution:**
```bash
# Verify URL format is correct
# Cognito: https://cognito-idp.{region}.amazonaws.com/{userPoolId}/.well-known/openid-configuration
# Auth0: https://{domain}.auth0.com/.well-known/openid-configuration

# Ensure URL is publicly accessible
# Check security group rules if using custom domain
```

### Issue: Unauthorized Access

**Error:**
```
AccessDeniedException: User is not authorized to perform: bedrock-agentcore:InvokeAgentRuntime
```

**Solution:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeAgentRuntime"
      ],
      "Resource": "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-server-dev"
    }
  ]
}
```

## Performance Issues

### Issue: High Latency (>2 seconds)

**Diagnosis:**
```python
import time

start = time.time()
response = client.invoke_agent_runtime(...)
end = time.time()

print(f"Latency: {(end - start) * 1000:.0f}ms")
```

**Solutions:**

1. **Optimize imports:**
   ```python
   # Bad: Import at module level
   import heavy_library
   
   def my_tool():
       return heavy_library.process()
   
   # Good: Lazy import
   def my_tool():
       import heavy_library
       return heavy_library.process()
   ```

2. **Use async for I/O:**
   ```python
   import asyncio
   import aiohttp
   
   async def fetch_data():
       async with aiohttp.ClientSession() as session:
           async with session.get(url) as response:
               return await response.json()
   ```

3. **Cache results:**
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=100)
   def expensive_computation(input_data):
       # This will be cached
       return process(input_data)
   ```

### Issue: Cold Start Takes >10 Seconds

**Solutions:**

1. **Minimize package size:**
   ```bash
   # Remove unused dependencies
   pip-autoremove unused-package
   
   # Use lighter alternatives
   # Instead of: pandas
   # Consider: built-in csv module
   ```

2. **Pre-compile Python files:**
   ```python
   # Add to Dockerfile
   RUN python -m compileall src/
   ```

3. **Use Docker deployment:**
   - Docker containers have faster cold starts
   - Better caching of dependencies

## Tool-Specific Issues

### Issue: Tool Returns Empty Result

**Diagnosis:**
```python
# Add debugging to your tool
@mcp.tool()
def my_tool(input_data: str) -> str:
    print(f"DEBUG: Received input: {input_data}")
    result = process(input_data)
    print(f"DEBUG: Generated result: {result}")
    return result
```

**Check CloudWatch logs for debug output:**
```bash
aws logs tail /aws/bedrock-agentcore/mcp-server-dev --follow
```

### Issue: Tool Timeout

**Error in CloudWatch:**
```
Task timed out after 30.00 seconds
```

**Solutions:**

1. **Optimize tool logic:**
   ```python
   # Set timeout for external calls
   import requests
   
   response = requests.get(url, timeout=5)  # 5 second timeout
   ```

2. **Use async operations:**
   ```python
   import asyncio
   
   @mcp.tool()
   async def my_tool(input_data: str) -> str:
       result = await async_process(input_data)
       return result
   ```

3. **Break down long operations:**
   ```python
   # Instead of one long tool
   @mcp.tool()
   def long_operation(data):
       # Process everything (60 seconds)
       return result
   
   # Use multiple tools
   @mcp.tool()
   def start_operation(data):
       job_id = initiate(data)
       return job_id
   
   @mcp.tool()
   def check_operation(job_id):
       return get_status(job_id)
   ```

## Debug Checklist

### Before Deployment
- [ ] Code runs locally: `python src/server.py`
- [ ] All tests pass: `pytest tests/`
- [ ] Requirements.txt is complete
- [ ] No hardcoded secrets in code
- [ ] Docker builds successfully (if using Docker)

### After Deployment
- [ ] Runtime status is ACTIVE
- [ ] Validation script passes all tests
- [ ] Can list tools successfully
- [ ] Can invoke at least one tool
- [ ] Logs show no errors in CloudWatch
- [ ] Response time is acceptable

### For Production
- [ ] OAuth authentication enabled
- [ ] IAM roles follow least privilege
- [ ] CloudWatch alarms configured
- [ ] Monitoring dashboard created
- [ ] Runbook for common issues
- [ ] Rollback procedure documented

## Getting Additional Help

### 1. Collect Diagnostic Information

```bash
# Run this script to collect all diagnostic info
cat > collect_diagnostics.sh << 'EOF'
#!/bin/bash
RUNTIME_ARN="$1"
RUNTIME_ID=$(echo $RUNTIME_ARN | rev | cut -d'/' -f1 | rev)

echo "=== Runtime Status ==="
aws bedrock-agentcore-control describe-agent-runtime \
  --agent-runtime-id $RUNTIME_ID

echo -e "\n=== Recent Logs ==="
aws logs tail /aws/bedrock-agentcore/$RUNTIME_ID --since 1h

echo -e "\n=== CloudWatch Metrics ==="
aws cloudwatch get-metric-statistics \
  --namespace AWS/BedrockAgentCore \
  --metric-name Invocations \
  --dimensions Name=RuntimeName,Value=$RUNTIME_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

echo -e "\n=== Validation Report ==="
python deployment/validation/validate_deployment.py \
  --runtime-arn $RUNTIME_ARN \
  --output-report /tmp/validation.json
cat /tmp/validation.json
EOF

chmod +x collect_diagnostics.sh
./collect_diagnostics.sh your-runtime-arn > diagnostics.txt
```

### 2. Enable Debug Logging

```python
# In src/config.py or environment
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export MCP_LOG_LEVEL=DEBUG
```

### 3. Contact Support

When contacting AWS Support, provide:
- Runtime ARN
- Deployment method (S3 or Docker)
- Error messages from CloudWatch
- Validation report output
- Diagnostic information (from above script)

## Related Documentation

- [AgentCore Deployment Guide](./AGENTCORE_DEPLOYMENT_GUIDE.md)
- [S3 Deployment README](../deployment/s3-direct/README.md)
- [Validation Script](../deployment/validation/validate_deployment.py)
- [AWS AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
