#!/usr/bin/env python3
"""
S3 Direct File Reference Deployment Script

This script deploys your MCP server to AgentCore Runtime using S3 direct file references
instead of Docker containers. This approach is faster for development and doesn't require
container builds.

Usage:
    python deploy_s3.py --bucket my-bucket --role-arn arn:aws:iam::123456789012:role/AgentCoreRole
"""

import argparse
import boto3
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Optional


class S3DirectDeployer:
    def __init__(self, bucket_name: str, role_arn: str, region: str = "us-west-2"):
        self.bucket_name = bucket_name
        self.role_arn = role_arn
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        self.agentcore_client = boto3.client('bedrock-agentcore-control', region_name=region)
        
    def create_deployment_package(self, source_dir: str = "src") -> str:
        """Create a ZIP file containing the MCP server code."""
        print(f"📦 Creating deployment package from {source_dir}...")
        
        zip_path = "/tmp/mcp-server-deployment.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            source_path = Path(source_dir)
            
            # Add all Python files
            for file_path in source_path.rglob('*.py'):
                arcname = file_path.relative_to(source_path.parent)
                zipf.write(file_path, arcname)
                print(f"  ✓ Added: {arcname}")
            
            # Add requirements.txt
            req_file = Path("requirements.txt")
            if req_file.exists():
                zipf.write(req_file, "requirements.txt")
                print(f"  ✓ Added: requirements.txt")
            
            # Add optional OpenAPI requirements
            req_openapi = Path("requirements-openapi.txt")
            if req_openapi.exists():
                zipf.write(req_openapi, "requirements-openapi.txt")
                print(f"  ✓ Added: requirements-openapi.txt")
            
            # Add config.yaml if exists
            config_file = Path("config.yaml")
            if config_file.exists():
                zipf.write(config_file, "config.yaml")
                print(f"  ✓ Added: config.yaml")
        
        print(f"✓ Deployment package created: {zip_path}")
        return zip_path
    
    def upload_to_s3(self, zip_path: str, key_prefix: str = "mcp-server") -> str:
        """Upload the deployment package to S3."""
        print(f"\n☁️  Uploading to S3 bucket: {self.bucket_name}...")
        
        # Generate unique key with timestamp
        import time
        timestamp = int(time.time())
        s3_key = f"{key_prefix}/{timestamp}/mcp-server.zip"
        
        try:
            self.s3_client.upload_file(
                zip_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            s3_uri = f"s3://{self.bucket_name}/{s3_key}"
            print(f"✓ Uploaded to: {s3_uri}")
            return s3_uri
            
        except Exception as e:
            print(f"❌ Failed to upload to S3: {e}")
            sys.exit(1)
    
    def create_agent_runtime(
        self,
        s3_uri: str,
        runtime_name: str,
        entry_point: str = "src/server.py",
        oauth_config: Optional[dict] = None
    ) -> str:
        """Create AgentCore Runtime with S3 direct file reference."""
        print(f"\n🚀 Creating AgentCore Runtime: {runtime_name}...")
        
        # Prepare runtime artifact configuration
        artifact_config = {
            's3Configuration': {
                's3Uri': s3_uri,
                'pythonEntryPoint': entry_point
            }
        }
        
        # Prepare runtime configuration
        runtime_config = {
            'agentRuntimeName': runtime_name,
            'agentRuntimeArtifact': artifact_config,
            'networkConfiguration': {
                'networkMode': 'PUBLIC'
            },
            'roleArn': self.role_arn
        }
        
        # Add OAuth configuration if provided
        if oauth_config:
            runtime_config['authenticationConfiguration'] = {
                'oauthConfiguration': oauth_config
            }
        
        try:
            response = self.agentcore_client.create_agent_runtime(**runtime_config)
            
            runtime_arn = response['agentRuntimeArn']
            status = response['status']
            
            print(f"✓ AgentCore Runtime Created!")
            print(f"  ARN: {runtime_arn}")
            print(f"  Status: {status}")
            
            return runtime_arn
            
        except Exception as e:
            print(f"❌ Failed to create AgentCore Runtime: {e}")
            sys.exit(1)
    
    def update_agent_runtime(
        self,
        runtime_arn: str,
        s3_uri: str,
        entry_point: str = "src/server.py"
    ) -> None:
        """Update existing AgentCore Runtime with new S3 package."""
        print(f"\n🔄 Updating AgentCore Runtime...")
        
        # Extract runtime ID from ARN
        runtime_id = runtime_arn.split('/')[-1]
        
        artifact_config = {
            's3Configuration': {
                's3Uri': s3_uri,
                'pythonEntryPoint': entry_point
            }
        }
        
        try:
            response = self.agentcore_client.update_agent_runtime(
                agentRuntimeId=runtime_id,
                agentRuntimeArtifact=artifact_config
            )
            
            print(f"✓ AgentCore Runtime Updated!")
            print(f"  Status: {response['status']}")
            
        except Exception as e:
            print(f"❌ Failed to update AgentCore Runtime: {e}")
            sys.exit(1)
    
    def deploy(
        self,
        runtime_name: str,
        entry_point: str = "src/server.py",
        update_existing: Optional[str] = None,
        oauth_config: Optional[dict] = None
    ) -> str:
        """Full deployment workflow."""
        print("=" * 80)
        print("S3 Direct File Reference Deployment")
        print("=" * 80)
        
        # Create deployment package
        zip_path = self.create_deployment_package()
        
        # Upload to S3
        s3_uri = self.upload_to_s3(zip_path)
        
        # Create or update runtime
        if update_existing:
            self.update_agent_runtime(update_existing, s3_uri, entry_point)
            return update_existing
        else:
            runtime_arn = self.create_agent_runtime(
                s3_uri, runtime_name, entry_point, oauth_config
            )
            return runtime_arn


def main():
    parser = argparse.ArgumentParser(
        description="Deploy MCP server to AgentCore using S3 direct file reference"
    )
    parser.add_argument(
        "--bucket",
        required=True,
        help="S3 bucket name for deployment packages"
    )
    parser.add_argument(
        "--role-arn",
        required=True,
        help="IAM execution role ARN for AgentCore Runtime"
    )
    parser.add_argument(
        "--runtime-name",
        default="mcp-server-s3",
        help="Name for the AgentCore Runtime (default: mcp-server-s3)"
    )
    parser.add_argument(
        "--entry-point",
        default="src/server.py",
        help="Python entry point (default: src/server.py)"
    )
    parser.add_argument(
        "--region",
        default="us-west-2",
        help="AWS region (default: us-west-2)"
    )
    parser.add_argument(
        "--update",
        help="Update existing runtime ARN instead of creating new one"
    )
    parser.add_argument(
        "--oauth-discovery-url",
        help="OAuth discovery URL for authentication"
    )
    parser.add_argument(
        "--oauth-client-id",
        help="OAuth client ID"
    )
    
    args = parser.parse_args()
    
    # Prepare OAuth config if provided
    oauth_config = None
    if args.oauth_discovery_url and args.oauth_client_id:
        oauth_config = {
            'discoveryUrl': args.oauth_discovery_url,
            'clientId': args.oauth_client_id
        }
    
    # Create deployer and deploy
    deployer = S3DirectDeployer(args.bucket, args.role_arn, args.region)
    
    runtime_arn = deployer.deploy(
        runtime_name=args.runtime_name,
        entry_point=args.entry_point,
        update_existing=args.update,
        oauth_config=oauth_config
    )
    
    print("\n" + "=" * 80)
    print("✅ Deployment Successful!")
    print("=" * 80)
    print(f"Runtime ARN: {runtime_arn}")
    print("\nNext steps:")
    print("1. Test your deployment using the validation script:")
    print(f"   python validate_deployment.py --runtime-arn {runtime_arn}")
    print("2. View logs in CloudWatch")
    print("3. Invoke your MCP server using boto3 or the test client")
    print("=" * 80)


if __name__ == "__main__":
    main()
