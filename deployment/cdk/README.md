# CDK Infrastructure for MCP Server

AWS CDK templates for deploying MCP server infrastructure to support AgentCore Runtime deployments.

## Overview

This CDK application creates:
- 📦 S3 bucket for deployment packages
- 🐳 ECR repository for Docker images (optional)
- 🔐 IAM execution role with proper permissions
- 📊 CloudWatch log group
- 🔔 SNS topic for notifications
- ⚙️ SSM parameters for configuration
- 🚨 CloudWatch alarms for monitoring

## Prerequisites

1. **AWS CDK installed**:
   ```bash
   npm install -g aws-cdk
   ```

2. **Python CDK libraries**:
   ```bash
   pip install aws-cdk-lib constructs
   ```

3. **AWS CLI configured** with appropriate credentials

4. **Bootstrap CDK** (first time only):
   ```bash
   cdk bootstrap aws://ACCOUNT-ID/REGION
   ```

## Quick Start

### 1. Deploy Development Environment

```bash
cd deployment/cdk
cdk deploy --context environment=dev
```

### 2. View What Will Be Created

```bash
cdk diff --context environment=dev
```

### 3. Synthesize CloudFormation Template

```bash
cdk synth --context environment=dev > template.yaml
```

## Usage

### Deploy with Custom Parameters

```bash
# Custom project name
cdk deploy --context project=my-mcp-server --context environment=dev

# Production with Docker deployment
cdk deploy --context environment=prod --context deployment-method=docker

# Enable OAuth authentication
cdk deploy --context environment=prod --context enable-oauth=true
```

### Deploy Multiple Environments

```bash
# Development
cdk deploy --context environment=dev

# Staging
cdk deploy --context environment=staging

# Production
cdk deploy --context environment=prod
```

### Update Existing Stack

```bash
# Make changes to the code, then:
cdk deploy --context environment=dev
```

### Destroy Stack

```bash
cdk destroy --context environment=dev
```

## Context Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `project` | mcp-server | Project name for resource naming |
| `environment` | dev | Environment (dev, staging, prod) |
| `deployment-method` | s3 | Deployment method (s3 or docker) |
| `enable-oauth` | false | Enable OAuth authentication |

## Stack Outputs

After deployment, the stack provides these outputs:

| Output | Description | Example |
|--------|-------------|---------|
| `DeploymentBucketName` | S3 bucket name | mcp-server-dev-deployments-123456789012 |
| `ExecutionRoleArn` | IAM role ARN | arn:aws:iam::123456789012:role/... |
| `LogGroupName` | CloudWatch log group | /aws/bedrock-agentcore/mcp-server-dev |
| `NotificationTopicArn` | SNS topic ARN | arn:aws:sns:us-west-2:... |
| `ContainerRepositoryUri` | ECR repository (if Docker) | 123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-server-dev |
| `DeploymentCommand` | Example deploy command | python deployment/s3-direct/deploy_s3.py ... |

### Retrieve Outputs

```bash
# Get all outputs
aws cloudformation describe-stacks \
  --stack-name mcp-server-dev-stack \
  --query 'Stacks[0].Outputs'

# Get specific output
aws cloudformation describe-stacks \
  --stack-name mcp-server-dev-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`ExecutionRoleArn`].OutputValue' \
  --output text
```

## Project Structure

```
cdk/
├── app.py                        # CDK application entry point
├── mcp_infrastructure_stack.py   # Main stack definition
├── README.md                     # This file
├── cdk.json                      # CDK configuration
└── requirements.txt              # Python dependencies
```

## CDK Configuration

Create `cdk.json` in this directory:

```json
{
  "app": "python3 app.py",
  "context": {
    "@aws-cdk/core:newStyleStackSynthesis": true,
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:enableStackNameDuplicates": true,
    "@aws-cdk/core:stackRelativeExports": true
  }
}
```

## Resource Details

### S3 Bucket

- **Versioning**: Enabled
- **Encryption**: SSE-S3 (AES256)
- **Public Access**: Blocked
- **Lifecycle**:
  - Old versions deleted after 30 days
  - Deployments deleted after 90 days

### ECR Repository (Docker mode)

- **Image Scanning**: Enabled
- **Tag Mutability**: Mutable
- **Encryption**: AES256
- **Lifecycle**: Keep last 10 images

### IAM Role

Permissions:
- ✅ Read from deployment S3 bucket
- ✅ Pull from ECR repository
- ✅ Invoke Bedrock models
- ✅ Access Secrets Manager secrets
- ✅ Write to CloudWatch Logs

### CloudWatch Alarms

- **Error Alarm**: Triggers when >5 errors in 5 minutes
- **Action**: Sends SNS notification

### SSM Parameters

Configuration stored in Parameter Store:
- Runtime ARN
- Deployment bucket name
- Execution role ARN

## Integration with Deployment Scripts

After deploying this infrastructure, use the outputs with deployment scripts:

### S3 Direct Deployment

```bash
# Get outputs
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name mcp-server-dev-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`DeploymentBucketName`].OutputValue' \
  --output text)

ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name mcp-server-dev-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`ExecutionRoleArn`].OutputValue' \
  --output text)

# Deploy MCP server
python ../s3-direct/deploy_s3.py \
  --bucket $BUCKET \
  --role-arn $ROLE_ARN \
  --runtime-name mcp-server-dev
```

### Docker Deployment

```bash
# Get ECR URI
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name mcp-server-dev-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`ContainerRepositoryUri`].OutputValue' \
  --output text)

# Build and push
docker buildx build --platform linux/arm64 -t $ECR_URI:latest --push .

# Configure AgentCore
agentcore configure -e src/server.py --protocol MCP
agentcore launch
```

## Advanced Usage

### Custom Stack Properties

Modify `mcp_infrastructure_stack.py` to add custom resources:

```python
# Add custom policy
self.execution_role.add_to_policy(
    iam.PolicyStatement(
        effect=iam.Effect.ALLOW,
        actions=["dynamodb:GetItem"],
        resources=["arn:aws:dynamodb:*:*:table/my-table"]
    )
)

# Add custom alarm
custom_alarm = cloudwatch.Alarm(
    self,
    "CustomAlarm",
    metric=cloudwatch.Metric(
        namespace="Custom",
        metric_name="MyMetric",
        statistic="Average"
    ),
    threshold=100,
    evaluation_periods=1
)
```

### Multi-Region Deployment

Deploy to multiple regions:

```bash
# US West 2
AWS_REGION=us-west-2 cdk deploy --context environment=prod

# US East 1
AWS_REGION=us-east-1 cdk deploy --context environment=prod
```

### CI/CD Integration

Add to your CI/CD pipeline:

```yaml
# .github/workflows/deploy-infrastructure.yml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths:
      - 'deployment/cdk/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-west-2
      
      - name: Install CDK
        run: npm install -g aws-cdk
      
      - name: Install dependencies
        run: pip install -r deployment/cdk/requirements.txt
      
      - name: Deploy stack
        run: |
          cd deployment/cdk
          cdk deploy --context environment=prod --require-approval never
```

## Troubleshooting

### Error: "Stack already exists"

The stack name must be unique per region. Use different project names or environments:
```bash
cdk deploy --context project=my-project --context environment=dev
```

### Error: "Unable to resolve AWS account"

Ensure AWS credentials are configured:
```bash
aws sts get-caller-identity
```

### Error: "CDK bootstrap required"

Bootstrap CDK in your account/region:
```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### Error: "Resource already exists"

Some resources (like S3 buckets) have global uniqueness requirements. The stack includes account ID in bucket names to avoid conflicts.

## Cost Optimization

### Development Environment

- Use S3 deployment (no ECR costs)
- Shorter log retention (7 days)
- No redundancy

### Production Environment

- Use Docker deployment for better isolation
- Longer log retention (30+ days)
- Multi-region deployment
- Additional monitoring

## Best Practices

1. **Use separate stacks per environment**: Don't share resources between dev/prod
2. **Tag all resources**: Include Environment, Project, and ManagedBy tags
3. **Enable versioning**: On S3 buckets for rollback capability
4. **Set lifecycle policies**: To manage costs
5. **Use SSM Parameter Store**: For configuration management
6. **Enable monitoring**: CloudWatch alarms and SNS notifications
7. **Document custom changes**: If you modify the stack

## Migration from CloudFormation

If you have existing CloudFormation templates:

1. **Import existing resources**:
   ```bash
   cdk import --context environment=dev
   ```

2. **Or recreate with CDK** and update references

3. **Gradually migrate** one environment at a time

## Next Steps

After deploying infrastructure:

1. **Deploy your MCP server** using the deployment command from stack outputs
2. **Validate deployment** with the validation script
3. **Set up monitoring** by subscribing to SNS topic
4. **Configure CI/CD** for automated deployments

## Additional Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [CDK Best Practices](https://docs.aws.amazon.com/cdk/latest/guide/best-practices.html)
- [AgentCore Documentation](https://docs.aws.amazon.com/bedrock-agentcore/)
