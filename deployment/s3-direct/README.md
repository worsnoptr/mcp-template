# S3 Direct File Reference Deployment

Deploy your MCP server to AgentCore Runtime using S3 direct file references instead of Docker containers. This method is faster for development iterations and doesn't require Docker builds.

## Overview

This deployment method:
- ✅ Packages your Python code into a ZIP file
- ✅ Uploads directly to S3
- ✅ Configures AgentCore to run your code directly
- ✅ No Docker build required
- ✅ Faster deployment cycles
- ✅ Easier debugging and updates

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Python 3.10+** installed locally
3. **S3 bucket** created for deployment packages
4. **IAM execution role** with proper permissions (see `../iam_policy.json`)
5. **boto3** installed: `pip install boto3`

## Quick Start

### 1. Create S3 Bucket

```bash
aws s3 mb s3://my-mcp-deployments --region us-west-2
```

### 2. Deploy Your MCP Server

```bash
python deploy_s3.py \
  --bucket my-mcp-deployments \
  --role-arn arn:aws:iam::123456789012:role/AgentCoreExecutionRole \
  --runtime-name my-mcp-server
```

### 3. Validate Deployment

```bash
python ../validation/validate_deployment.py \
  --runtime-arn arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-mcp-server
```

## Detailed Usage

### Basic Deployment

```bash
python deploy_s3.py \
  --bucket your-bucket-name \
  --role-arn your-role-arn \
  --runtime-name your-runtime-name \
  --region us-west-2
```

### Deployment with OAuth

```bash
python deploy_s3.py \
  --bucket your-bucket-name \
  --role-arn your-role-arn \
  --runtime-name your-runtime-name \
  --oauth-discovery-url https://cognito-idp.us-west-2.amazonaws.com/us-west-2_xxxxx/.well-known/openid-configuration \
  --oauth-client-id your-client-id
```

### Update Existing Runtime

```bash
python deploy_s3.py \
  --bucket your-bucket-name \
  --role-arn your-role-arn \
  --update arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-mcp-server
```

### Custom Entry Point

```bash
python deploy_s3.py \
  --bucket your-bucket-name \
  --role-arn your-role-arn \
  --runtime-name your-runtime-name \
  --entry-point custom/path/server.py
```

## Command-Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--bucket` | Yes | - | S3 bucket for deployment packages |
| `--role-arn` | Yes | - | IAM execution role ARN |
| `--runtime-name` | No | mcp-server-s3 | Name for AgentCore Runtime |
| `--entry-point` | No | src/server.py | Python entry point |
| `--region` | No | us-west-2 | AWS region |
| `--update` | No | - | Update existing runtime ARN |
| `--oauth-discovery-url` | No | - | OAuth discovery URL |
| `--oauth-client-id` | No | - | OAuth client ID |

## What Gets Deployed

The deployment script packages:

```
mcp-server-deployment.zip
├── src/
│   ├── server.py
│   ├── config.py
│   ├── tools/
│   ├── utils/
│   └── examples/
├── requirements.txt
├── requirements-openapi.txt (if exists)
└── config.yaml (if exists)
```

## S3 Bucket Structure

After deployment, your S3 bucket will contain:

```
s3://my-mcp-deployments/
└── mcp-server/
    ├── 1702345678/
    │   └── mcp-server.zip
    ├── 1702456789/
    │   └── mcp-server.zip
    └── 1702567890/
        └── mcp-server.zip
```

Each deployment creates a new timestamped directory for easy rollback.

## Deployment Workflow

```
┌─────────────────┐
│  Local Files    │
│  (src/, *.txt)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ZIP Package    │
│  (in /tmp)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Upload to S3   │
│  (encrypted)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ AgentCore       │
│ Runtime         │
│ (S3 reference)  │
└─────────────────┘
```

## Comparison: S3 vs Docker Deployment

| Aspect | S3 Direct | Docker |
|--------|-----------|--------|
| **Build Time** | ~5 seconds | ~2-5 minutes |
| **Deployment Time** | ~10 seconds | ~30-60 seconds |
| **Update Speed** | Very fast | Moderate |
| **Local Testing** | Run `python src/server.py` | Requires Docker |
| **Debugging** | Easier (direct Python) | Container logs |
| **Dependencies** | Python packages only | Docker required |
| **Platform** | Any | ARM64 build required |
| **Best For** | Development, rapid iteration | Production, complex dependencies |

## Advantages

### ✅ Faster Deployments
- No Docker build step (saves 2-5 minutes)
- Direct ZIP upload (faster than container push)
- Ideal for rapid development cycles

### ✅ Simpler Workflow
- No Docker installation required
- No platform architecture concerns
- Standard Python development

### ✅ Easier Updates
- Change code, redeploy immediately
- No image building or pushing
- Quick rollback to previous versions

### ✅ Better for Development
- Test locally with `python src/server.py`
- Debug with standard Python tools
- Faster iteration cycles

## Disadvantages

### ⚠️ Limitations

- **System Dependencies**: Can only use pure Python packages or AWS Lambda-compatible binary packages
- **Complex Installations**: Tools requiring system libraries may not work
- **File Size**: ZIP package limited to 250 MB
- **Runtime Environment**: Uses AWS managed Python runtime

### When to Use Docker Instead

Use Docker deployment if you need:
- System-level dependencies (e.g., custom C libraries)
- Non-Python tools or binaries
- Complex build processes
- Exact environment replication
- Production deployments with strict requirements

## Troubleshooting

### Error: "S3 bucket does not exist"

```bash
# Create the bucket
aws s3 mb s3://your-bucket-name --region us-west-2
```

### Error: "Access Denied" when uploading to S3

Ensure your IAM user/role has these permissions:
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:PutObject",
    "s3:GetObject",
    "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::your-bucket-name/*",
    "arn:aws:s3:::your-bucket-name"
  ]
}
```

### Error: "Unable to import module"

This means a dependency is missing. Ensure it's in `requirements.txt`:
```bash
# Add missing package
echo "missing-package==1.0.0" >> requirements.txt

# Redeploy
python deploy_s3.py --bucket ... --update arn:...
```

### Error: "No module named 'src'"

Check your entry point:
```bash
# Correct entry point
--entry-point src/server.py

# NOT this
--entry-point server.py
```

### Runtime Errors

View CloudWatch logs:
```bash
aws logs tail /aws/bedrock-agentcore/my-mcp-server --follow
```

## Best Practices

### 1. Use Versioned Deployments

Keep track of deployment timestamps for rollback:
```bash
# Deploy
python deploy_s3.py --bucket my-bucket --role-arn arn:...

# Note the S3 URI from output
# s3://my-bucket/mcp-server/1702345678/mcp-server.zip

# To rollback, update runtime with old URI
```

### 2. Enable S3 Versioning

```bash
aws s3api put-bucket-versioning \
  --bucket my-bucket \
  --versioning-configuration Status=Enabled
```

### 3. Use Separate Buckets per Environment

```
my-mcp-dev-deployments
my-mcp-staging-deployments
my-mcp-prod-deployments
```

### 4. Tag Your Resources

```python
# In deploy_s3.py, add tags when creating runtime
runtime_config['tags'] = {
    'Environment': 'dev',
    'Project': 'mcp-server',
    'ManagedBy': 's3-direct-deploy'
}
```

### 5. Automate with CI/CD

Add to your CI/CD pipeline:
```yaml
# .github/workflows/deploy.yml
- name: Deploy to Dev
  run: |
    python deployment/s3-direct/deploy_s3.py \
      --bucket ${{ secrets.S3_BUCKET }} \
      --role-arn ${{ secrets.ROLE_ARN }} \
      --runtime-name mcp-server-dev \
      --update ${{ secrets.RUNTIME_ARN_DEV }}
```

## Migration Path

### From Starter Toolkit to S3 Direct

1. **Extract your code** from the toolkit structure
2. **Ensure** `requirements.txt` is complete
3. **Deploy** using this script
4. **Test** with validation script
5. **Switch** traffic once validated

### From S3 Direct to Docker

When you need Docker (for production):

1. **Use the provided Dockerfile** (already configured)
2. **Build and test locally** 
3. **Deploy** via `agentcore launch`
4. **Validate** functionality matches S3 version

## Next Steps

After successful deployment:

1. **Validate**: Run `validate_deployment.py`
2. **Test**: Use test client to invoke tools
3. **Monitor**: Check CloudWatch logs and metrics
4. **Iterate**: Make changes and update runtime

## Additional Resources

- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
- [S3 Best Practices](https://docs.aws.amazon.com/AmazonS3/latest/userguide/best-practices.html)
- [IAM Roles for AgentCore](../iam_policy.json)
- [Deployment Validation](../validation/README.md)
