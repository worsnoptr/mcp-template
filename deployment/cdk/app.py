#!/usr/bin/env python3
"""
CDK Application for MCP Server Infrastructure

Usage:
    # Development environment
    cdk deploy --context environment=dev
    
    # Staging environment
    cdk deploy --context environment=staging
    
    # Production environment with Docker
    cdk deploy --context environment=prod --context deployment-method=docker
"""

import aws_cdk as cdk
from mcp_infrastructure_stack import McpInfrastructureStack


app = cdk.App()

# Get context values
project_name = app.node.try_get_context("project") or "mcp-server"
environment = app.node.try_get_context("environment") or "dev"
deployment_method = app.node.try_get_context("deployment-method") or "s3"
enable_oauth = app.node.try_get_context("enable-oauth") or False

# Create stack
stack = McpInfrastructureStack(
    app,
    f"{project_name}-{environment}-stack",
    project_name=project_name,
    environment=environment,
    deployment_method=deployment_method,
    enable_oauth=enable_oauth,
    description=f"Infrastructure for {project_name} MCP server ({environment} environment)",
    tags={
        "Project": project_name,
        "Environment": environment,
        "ManagedBy": "CDK",
    },
)

app.synth()
