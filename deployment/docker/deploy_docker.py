#!/usr/bin/env python3
"""
Docker-based AgentCore Runtime Deployment Script

Deploys or updates AgentCore Runtime using Docker images from ECR.

Usage:
    python deploy_docker.py --image-uri 123456789012.dkr.ecr.us-west-2.amazonaws.com/mcp:latest \
                            --role-arn arn:aws:iam::123456789012:role/AgentCoreRole \
                            --runtime-name mcp-server-prod
"""

import argparse
import boto3
import sys


def create_or_update_runtime(
    image_uri: str,
    role_arn: str,
    runtime_name: str,
    region: str = "us-west-2",
    update: str = None,
    oauth_config: dict = None
):
    """Create or update AgentCore Runtime with Docker image."""
    
    client = boto3.client('bedrock-agentcore-control', region_name=region)
    
    artifact_config = {
        'containerConfiguration': {
            'containerUri': image_uri
        }
    }
    
    runtime_config = {
        'agentRuntimeName': runtime_name,
        'agentRuntimeArtifact': artifact_config,
        'networkConfiguration': {'networkMode': 'PUBLIC'},
        'roleArn': role_arn
    }
    
    if oauth_config:
        runtime_config['authenticationConfiguration'] = {
            'oauthConfiguration': oauth_config
        }
    
    try:
        if update:
            # Update existing runtime
            runtime_id = update.split('/')[-1]
            response = client.update_agent_runtime(
                agentRuntimeId=runtime_id,
                agentRuntimeArtifact=artifact_config
            )
            print(f"✅ Updated runtime: {update}")
        else:
            # Create new runtime
            response = client.create_agent_runtime(**runtime_config)
            print(f"✅ Created runtime: {response['agentRuntimeArn']}")
        
        return response['agentRuntimeArn']
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Deploy MCP server via Docker")
    parser.add_argument("--image-uri", required=True, help="ECR image URI")
    parser.add_argument("--role-arn", required=True, help="IAM execution role ARN")
    parser.add_argument("--runtime-name", default="mcp-server", help="Runtime name")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    parser.add_argument("--update", help="Update existing runtime ARN")
    parser.add_argument("--oauth-discovery-url", help="OAuth discovery URL")
    parser.add_argument("--oauth-client-id", help="OAuth client ID")
    
    args = parser.parse_args()
    
    oauth_config = None
    if args.oauth_discovery_url and args.oauth_client_id:
        oauth_config = {
            'discoveryUrl': args.oauth_discovery_url,
            'clientId': args.oauth_client_id
        }
    
    runtime_arn = create_or_update_runtime(
        image_uri=args.image_uri,
        role_arn=args.role_arn,
        runtime_name=args.runtime_name,
        region=args.region,
        update=args.update,
        oauth_config=oauth_config
    )
    
    print(f"\n✅ Deployment complete!")
    print(f"Runtime ARN: {runtime_arn}")
    print("\nNext steps:")
    print(f"  1. Validate: python deployment/validation/validate_deployment.py --runtime-arn {runtime_arn}")
    print(f"  2. Monitor: aws logs tail /aws/bedrock-agentcore/{args.runtime_name} --follow")


if __name__ == "__main__":
    main()
