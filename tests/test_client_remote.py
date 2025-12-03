#!/usr/bin/env python3
"""
Remote MCP Server Test Client

This script tests a deployed MCP server on Amazon Bedrock AgentCore Runtime.

Prerequisites:
- Agent deployed to AgentCore Runtime
- Valid OAuth token or AWS credentials

Usage:
    # Set environment variables
    export AGENT_ARN="arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-server-xyz"
    export BEARER_TOKEN="your-oauth-token"  # If using OAuth
    
    # Run the test
    python tests/test_client_remote.py
"""

import asyncio
import os
import sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def test_deployed_server():
    """Test the deployed MCP server."""
    
    # Get configuration from environment
    agent_arn = os.getenv('AGENT_ARN')
    bearer_token = os.getenv('BEARER_TOKEN')
    region = os.getenv('AWS_REGION', 'us-west-2')
    
    if not agent_arn:
        print("ERROR: AGENT_ARN environment variable not set")
        print("\nUsage:")
        print("  export AGENT_ARN='your-agent-runtime-arn'")
        print("  export BEARER_TOKEN='your-oauth-token'  # If using OAuth")
        print("  python tests/test_client_remote.py")
        sys.exit(1)
    
    # URL encode the ARN
    encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
    
    # Construct the MCP URL
    mcp_url = f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
    
    # Setup headers
    headers = {"Content-Type": "application/json"}
    if bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"
    
    print("="*80)
    print("MCP Server Remote Test Client")
    print("="*80)
    print(f"Agent ARN: {agent_arn}")
    print(f"Region: {region}")
    print(f"Authentication: {'OAuth' if bearer_token else 'AWS SigV4'}")
    print("="*80)
    
    try:
        async with streamablehttp_client(
            mcp_url,
            headers,
            timeout=120,
            terminate_on_close=False
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize session
                print("\nInitializing session...")
                await session.initialize()
                print("✓ Connected to remote MCP server")
                
                # List tools
                print("\n" + "="*80)
                print("Available Tools")
                print("="*80)
                result = await session.list_tools()
                print(f"Found {len(result.tools)} tools:")
                
                for tool in result.tools:
                    print(f"\n  • {tool.name}")
                    print(f"    {tool.description}")
                
                # Test a simple tool
                print("\n" + "="*80)
                print("Testing Calculator Tool")
                print("="*80)
                
                print("\nCalling add_numbers(a=5, b=3)...")
                result = await session.call_tool(
                    "add_numbers",
                    {"a": 5, "b": 3}
                )
                print(f"✓ Result: {result.content[0].text if hasattr(result.content[0], 'text') else result}")
                
                print("\nCalling multiply_numbers(a=6, b=7)...")
                result = await session.call_tool(
                    "multiply_numbers",
                    {"a": 6, "b": 7}
                )
                print(f"✓ Result: {result.content[0].text if hasattr(result.content[0], 'text') else result}")
                
                print("\n" + "="*80)
                print("Remote tests completed successfully!")
                print("="*80)
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_deployed_server())
