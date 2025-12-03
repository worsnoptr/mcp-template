# Enterprise CI/CD Deployment Guide

Guide for transitioning from the starter kit to production-grade CI/CD pipelines for MCP server deployment.

## Table of Contents

- [Overview](#overview)
- [CI/CD Pipeline Architecture](#cicd-pipeline-architecture)
- [GitHub Actions](#github-actions)
- [GitLab CI/CD](#gitlab-cicd)
- [AWS CodePipeline](#aws-codepipeline)
- [Multi-Environment Strategy](#multi-environment-strategy)
- [Security Best Practices](#security-best-practices)
- [Monitoring and Rollback](#monitoring-and-rollback)

## Overview

This guide helps you transition from manual deployments with the AgentCore starter kit to automated, production-grade CI/CD pipelines.

### Transition Path

```
Stage 1: Manual → Use starter toolkit for development
Stage 2: Basic CI → Automated builds and tests
Stage 3: Multi-env → Dev, staging, production pipelines
Stage 4: Advanced → Blue/green, canary, automated rollback
```

### CI/CD Benefits

- ✅ Consistent deployments
- ✅ Automated testing
- ✅ Faster iterations
- ✅ Reduced human error
- ✅ Audit trail
- ✅ Easy rollbacks

## CI/CD Pipeline Architecture

### Basic Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Code      │────▶│   Build     │────▶│   Test      │────▶│   Deploy    │
│   Push      │     │   (Docker)  │     │   (Validate)│     │   (S3/ECR)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Enterprise Pipeline

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Code    │──▶│  Build   │──▶│   Test   │──▶│  Deploy  │──▶│ Validate │
│  Commit  │   │  & Scan  │   │  & Lint  │   │   Dev    │   │  Health  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
                                                    │
                                                    ▼
                                              ┌──────────┐
                                              │ Approval │
                                              │  Gate    │
                                              └──────────┘
                                                    │
                                                    ▼
                                              ┌──────────┐   ┌──────────┐
                                              │  Deploy  │──▶│ Validate │
                                              │ Staging  │   │  Health  │
                                              └──────────┘   └──────────┘
                                                    │
                                                    ▼
                                              ┌──────────┐
                                              │ Approval │
                                              │  Gate    │
                                              └──────────┘
                                                    │
                                                    ▼
                                              ┌──────────┐   ┌──────────┐
                                              │  Deploy  │──▶│ Validate │
                                              │   Prod   │   │  Health  │
                                              └──────────┘   └──────────┘
```

## GitHub Actions

### Complete Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy MCP Server

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  AWS_REGION: us-west-2
  PROJECT_NAME: mcp-server

jobs:
  # Job 1: Build and Test
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run linting
        run: |
          pylint src/
          flake8 src/

      - name: Run tests
        run: |
          pytest tests/ --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  # Job 2: Security Scanning
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'

  # Job 3: Deploy to Dev
  deploy-dev:
    needs: [build-and-test, security-scan]
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: development
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install boto3
        run: pip install boto3

      - name: Deploy to Dev (S3)
        run: |
          python deployment/s3-direct/deploy_s3.py \
            --bucket ${{ secrets.DEV_DEPLOYMENT_BUCKET }} \
            --role-arn ${{ secrets.DEV_EXECUTION_ROLE_ARN }} \
            --runtime-name ${PROJECT_NAME}-dev \
            --region ${{ env.AWS_REGION }} \
            --update ${{ secrets.DEV_RUNTIME_ARN }}

      - name: Validate deployment
        run: |
          python deployment/validation/validate_deployment.py \
            --runtime-arn ${{ secrets.DEV_RUNTIME_ARN }} \
            --region ${{ env.AWS_REGION }}

      - name: Run smoke tests
        run: |
          python tests/test_client_remote.py \
            --runtime-arn ${{ secrets.DEV_RUNTIME_ARN }}

  # Job 4: Deploy to Staging
  deploy-staging:
    needs: [build-and-test, security-scan]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: ${{ env.PROJECT_NAME }}-staging
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker buildx build \
            --platform linux/arm64 \
            -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG \
            -t $ECR_REGISTRY/$ECR_REPOSITORY:latest \
            --push \
            .

      - name: Deploy to AgentCore Staging
        env:
          IMAGE_URI: ${{ steps.login-ecr.outputs.registry }}/${{ env.PROJECT_NAME }}-staging:${{ github.sha }}
        run: |
          python deployment/docker/deploy_docker.py \
            --image-uri $IMAGE_URI \
            --role-arn ${{ secrets.STAGING_EXECUTION_ROLE_ARN }} \
            --runtime-name ${PROJECT_NAME}-staging \
            --update ${{ secrets.STAGING_RUNTIME_ARN }}

      - name: Validate deployment
        run: |
          python deployment/validation/validate_deployment.py \
            --runtime-arn ${{ secrets.STAGING_RUNTIME_ARN }} \
            --bearer-token ${{ secrets.STAGING_OAUTH_TOKEN }}

      - name: Run integration tests
        run: |
          pytest tests/integration/ \
            --runtime-arn ${{ secrets.STAGING_RUNTIME_ARN }}

  # Job 5: Deploy to Production
  deploy-prod:
    needs: [deploy-staging]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Copy image from staging to prod
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          STAGING_REPO: ${{ env.PROJECT_NAME }}-staging
          PROD_REPO: ${{ env.PROJECT_NAME }}-prod
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker pull $ECR_REGISTRY/$STAGING_REPO:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$STAGING_REPO:$IMAGE_TAG $ECR_REGISTRY/$PROD_REPO:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$STAGING_REPO:$IMAGE_TAG $ECR_REGISTRY/$PROD_REPO:latest
          docker push $ECR_REGISTRY/$PROD_REPO:$IMAGE_TAG
          docker push $ECR_REGISTRY/$PROD_REPO:latest

      - name: Deploy to AgentCore Production
        env:
          IMAGE_URI: ${{ steps.login-ecr.outputs.registry }}/${{ env.PROJECT_NAME }}-prod:${{ github.sha }}
        run: |
          python deployment/docker/deploy_docker.py \
            --image-uri $IMAGE_URI \
            --role-arn ${{ secrets.PROD_EXECUTION_ROLE_ARN }} \
            --runtime-name ${PROJECT_NAME}-prod \
            --update ${{ secrets.PROD_RUNTIME_ARN }}

      - name: Validate deployment
        run: |
          python deployment/validation/validate_deployment.py \
            --runtime-arn ${{ secrets.PROD_RUNTIME_ARN }} \
            --bearer-token ${{ secrets.PROD_OAUTH_TOKEN }}

      - name: Smoke tests
        run: |
          python tests/smoke/ \
            --runtime-arn ${{ secrets.PROD_RUNTIME_ARN }}

      - name: Create release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: v${{ github.run_number }}
          release_name: Release ${{ github.run_number }}
          body: |
            Automated production deployment
            Commit: ${{ github.sha }}
          draft: false
          prerelease: false

      - name: Notify success
        if: success()
        run: |
          aws sns publish \
            --topic-arn ${{ secrets.NOTIFICATION_TOPIC_ARN }} \
            --subject "MCP Server Production Deployment Success" \
            --message "Successfully deployed version ${{ github.sha }} to production"

      - name: Notify failure
        if: failure()
        run: |
          aws sns publish \
            --topic-arn ${{ secrets.NOTIFICATION_TOPIC_ARN }} \
            --subject "MCP Server Production Deployment FAILED" \
            --message "Deployment of version ${{ github.sha }} to production FAILED"
```

### Required Secrets

Configure these in GitHub Settings → Secrets:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY

# Development
DEV_DEPLOYMENT_BUCKET
DEV_EXECUTION_ROLE_ARN
DEV_RUNTIME_ARN

# Staging
STAGING_EXECUTION_ROLE_ARN
STAGING_RUNTIME_ARN
STAGING_OAUTH_TOKEN

# Production
PROD_EXECUTION_ROLE_ARN
PROD_RUNTIME_ARN
PROD_OAUTH_TOKEN

# Notifications
NOTIFICATION_TOPIC_ARN
```

## GitLab CI/CD

Create `.gitlab-ci.yml`:

```yaml
image: python:3.11

variables:
  AWS_REGION: us-west-2
  PROJECT_NAME: mcp-server

stages:
  - build
  - test
  - deploy-dev
  - deploy-staging
  - deploy-prod

before_script:
  - pip install boto3

# Build stage
build:
  stage: build
  script:
    - pip install -r requirements.txt
    - python -m py_compile src/**/*.py
  artifacts:
    paths:
      - src/
    expire_in: 1 hour

# Test stage
test:lint:
  stage: test
  script:
    - pip install pylint flake8
    - pylint src/
    - flake8 src/

test:unit:
  stage: test
  script:
    - pip install -r requirements.txt pytest pytest-cov
    - pytest tests/unit/ --cov=src

test:security:
  stage: test
  image: aquasec/trivy:latest
  script:
    - trivy fs --exit-code 0 --severity HIGH,CRITICAL .

# Deploy to Dev
deploy:dev:
  stage: deploy-dev
  environment:
    name: development
  only:
    - develop
  script:
    - python deployment/s3-direct/deploy_s3.py
        --bucket $DEV_DEPLOYMENT_BUCKET
        --role-arn $DEV_EXECUTION_ROLE_ARN
        --runtime-name ${PROJECT_NAME}-dev
        --update $DEV_RUNTIME_ARN
    - python deployment/validation/validate_deployment.py
        --runtime-arn $DEV_RUNTIME_ARN

# Deploy to Staging
deploy:staging:
  stage: deploy-staging
  environment:
    name: staging
  only:
    - main
  script:
    - apt-get update && apt-get install -y docker.io
    - docker buildx build --platform linux/arm64 -t staging:latest --load .
    # Push to ECR and deploy
    - python deployment/docker/deploy_docker.py
        --runtime-name ${PROJECT_NAME}-staging
        --update $STAGING_RUNTIME_ARN
    - python deployment/validation/validate_deployment.py
        --runtime-arn $STAGING_RUNTIME_ARN

# Deploy to Production
deploy:prod:
  stage: deploy-prod
  environment:
    name: production
  when: manual
  only:
    - main
  script:
    - python deployment/docker/deploy_docker.py
        --runtime-name ${PROJECT_NAME}-prod
        --update $PROD_RUNTIME_ARN
    - python deployment/validation/validate_deployment.py
        --runtime-arn $PROD_RUNTIME_ARN
        --bearer-token $PROD_OAUTH_TOKEN
```

## AWS CodePipeline

### Pipeline with CDK

Create `cicd_pipeline_stack.py`:

```python
from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as actions,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct

class McpCicdPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)
        
        # S3 bucket for artifacts
        artifact_bucket = s3.Bucket(self, "ArtifactBucket")
        
        # Source stage
        source_output = codepipeline.Artifact("SourceOutput")
        source_action = actions.GitHubSourceAction(
            action_name="GitHub_Source",
            owner="your-github-username",
            repo="mcp-template",
            oauth_token=SecretValue.secrets_manager("github-token"),
            output=source_output,
            branch="main"
        )
        
        # Build stage
        build_project = codebuild.PipelineProject(
            self, "BuildProject",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "install": {
                        "runtime-versions": {"python": "3.11"},
                        "commands": ["pip install -r requirements.txt"]
                    },
                    "build": {
                        "commands": [
                            "python -m pytest tests/",
                            "python deployment/s3-direct/deploy_s3.py --bucket $BUCKET --role-arn $ROLE_ARN --runtime-name mcp-server-dev"
                        ]
                    }
                }
            }),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0
            )
        )
        
        build_output = codepipeline.Artifact("BuildOutput")
        build_action = actions.CodeBuildAction(
            action_name="Build",
            project=build_project,
            input=source_output,
            outputs=[build_output]
        )
        
        # Create pipeline
        pipeline = codepipeline.Pipeline(
            self, "McpPipeline",
            artifact_bucket=artifact_bucket,
            stages=[
                codepipeline.StageProps(
                    stage_name="Source",
                    actions=[source_action]
                ),
                codepipeline.StageProps(
                    stage_name="Build",
                    actions=[build_action]
                )
            ]
        )
```

## Multi-Environment Strategy

### Environment Configuration

Create `environments.yaml`:

```yaml
development:
  deployment_method: s3
  bucket: mcp-dev-deployments-123456789012
  role_arn: arn:aws:iam::123456789012:role/AgentCore-Dev
  runtime_arn: arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-dev
  oauth_enabled: false
  log_retention_days: 7
  auto_deploy: true

staging:
  deployment_method: docker
  ecr_repository: 123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-staging
  role_arn: arn:aws:iam::123456789012:role/AgentCore-Staging
  runtime_arn: arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-staging
  oauth_enabled: true
  oauth_discovery_url: https://cognito-idp.us-west-2.amazonaws.com/...
  log_retention_days: 30
  auto_deploy: true
  requires_approval: false

production:
  deployment_method: docker
  ecr_repository: 123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp-prod
  role_arn: arn:aws:iam::123456789012:role/AgentCore-Prod
  runtime_arn: arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/mcp-prod
  oauth_enabled: true
  oauth_discovery_url: https://cognito-idp.us-west-2.amazonaws.com/...
  log_retention_days: 90
  auto_deploy: false
  requires_approval: true
  canary_deployment: true
  rollback_on_alarm: true
```

### Environment-Specific Deployment Script

```python
#!/usr/bin/env python3
import yaml
import sys

def deploy_to_environment(env_name):
    with open('environments.yaml', 'r') as f:
        config = yaml.safe_load(f)[env_name]
    
    if config['deployment_method'] == 's3':
        # S3 deployment
        cmd = f"""
        python deployment/s3-direct/deploy_s3.py \\
          --bucket {config['bucket']} \\
          --role-arn {config['role_arn']} \\
          --runtime-name mcp-{env_name} \\
          --update {config['runtime_arn']}
        """
    else:
        # Docker deployment
        cmd = f"""
        docker buildx build --platform linux/arm64 \\
          -t {config['ecr_repository']}:latest --push . &&
        python deployment/docker/deploy_docker.py \\
          --image-uri {config['ecr_repository']}:latest \\
          --role-arn {config['role_arn']} \\
          --update {config['runtime_arn']}
        """
    
    os.system(cmd)

if __name__ == "__main__":
    deploy_to_environment(sys.argv[1])
```

## Security Best Practices

### 1. Secrets Management

**Never commit secrets to repository!**

Use AWS Secrets Manager:

```python
import boto3

def get_secret(secret_name):
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

# Usage in deployment
oauth_client_secret = get_secret('mcp-server/prod/oauth-secret')
```

### 2. IAM Least Privilege

Create deployment-specific roles:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:UpdateAgentRuntime",
        "s3:PutObject",
        "ecr:PutImage"
      ],
      "Resource": [
        "arn:aws:bedrock-agentcore:*:*:runtime/mcp-*",
        "arn:aws:s3:::mcp-*-deployments/*",
        "arn:aws:ecr:*:*:repository/mcp-*"
      ]
    }
  ]
}
```

### 3. Code Signing

Sign Docker images:

```bash
# Enable Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# Build and push (automatically signed)
docker buildx build --platform linux/arm64 -t $ECR_URI:latest --push .
```

### 4. Vulnerability Scanning

Add to pipeline:

```yaml
- name: Run Trivy
  run: |
    trivy image --exit-code 1 --severity CRITICAL $ECR_URI:latest
```

## Monitoring and Rollback

### Automated Rollback

```python
#!/usr/bin/env python3
"""Automated rollback on deployment failure."""

import boto3
import time

def deploy_with_rollback(runtime_arn, new_version, previous_version):
    client = boto3.client('bedrock-agentcore-control')
    
    # Deploy new version
    update_runtime(runtime_arn, new_version)
    
    # Wait and monitor
    time.sleep(60)
    
    # Check health
    if not check_health(runtime_arn):
        print("❌ Health check failed - rolling back")
        update_runtime(runtime_arn, previous_version)
        return False
    
    print("✅ Deployment successful")
    return True

def check_health(runtime_arn):
    """Check runtime health via validation script."""
    result = subprocess.run([
        'python', 'deployment/validation/validate_deployment.py',
        '--runtime-arn', runtime_arn
    ], capture_output=True)
    
    return result.returncode == 0
```

### Canary Deployment

```python
def canary_deploy(runtime_arn, new_version):
    """Deploy to 10% of traffic, then gradually increase."""
    
    # Create canary runtime
    canary_arn = create_runtime(f"{runtime_arn}-canary", new_version)
    
    # Route 10% traffic to canary
    update_traffic_split(runtime_arn, canary_arn, weight=10)
    
    # Monitor for 15 minutes
    if monitor_canary(canary_arn, duration=900):
        # Gradually increase: 25%, 50%, 100%
        for weight in [25, 50, 100]:
            update_traffic_split(runtime_arn, canary_arn, weight=weight)
            time.sleep(300)  # Wait 5 minutes
            
            if not monitor_canary(canary_arn):
                rollback(runtime_arn, canary_arn)
                return False
        
        # Success - promote canary
        promote_canary(runtime_arn, canary_arn)
        return True
    else:
        rollback(runtime_arn, canary_arn)
        return False
```

## Next Steps

1. **Start simple**: Use manual deployments with starter toolkit
2. **Add basic CI**: Implement automated tests
3. **Deploy to dev**: Automate dev environment deployments
4. **Add staging**: Multi-environment pipeline
5. **Production**: Manual approval gates and monitoring
6. **Advanced**: Canary deployments and automated rollback

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [AWS CodePipeline Documentation](https://docs.aws.amazon.com/codepipeline/)
- [AgentCore Deployment Guide](./AGENTCORE_DEPLOYMENT_GUIDE.md)
