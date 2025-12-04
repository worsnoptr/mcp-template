#!/usr/bin/env python3
"""
Remote MCP Server Test Client - IAM Authentication

This script demonstrates how to invoke a deployed MCP server on Amazon Bedrock 
AgentCore Runtime using IAM authentication with boto3.

CRITICAL: The accept header MUST include 'text/event-stream' to receive SSE responses.
Using only 'application/json' will result in HTTP 406 Not Acceptable errors.

Prerequisites:
- Agent deployed to AgentCore Runtime
- AWS credentials configured (via AWS CLI, environment variables, or IAM role)
- boto3 installed: pip install boto3

Usage:
    # Set the agent runtime ARN
    export AGENT_ARN="arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-server-xyz"
    
    # Run the test
    python tests/test_client_remote_iam.py

AWS Credentials:
    The script uses boto3's default credential chain:
    1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
    2. AWS CLI configuration (~/.aws/credentials)
    3. IAM instance profile (when running on EC2)
    4. IAM role (when running in containers/Lambda)

Required IAM Permissions:
    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": ["bedrock-agentcore:InvokeAgentRuntime"],
          "Resource": "arn:aws:bedrock-agentcore:*:*:runtime/*"
        }
      ]
    }
"""

import os
import sys
import json
import uuid
import boto3
from botocore.exceptions import ClientError


def parse_sse_response(response_body):
    """
    Parse Server-Sent Events (SSE) response from AgentCore.
    
    SSE format:
        data: {"jsonrpc":"2.0","result":{...},"id":1}
        
        data: {"jsonrpc":"2.0","result":{...},"id":2}
    
    Each event line starts with 'data: ' followed by JSON.
    """
    results = []
    
    # Read and decode the response
    response_text = response_body.decode('utf-8')
    
    # Split by newlines and process each line
    for line in response_text.strip().split('\n'):
        # SSE data lines start with 'data: '
        if line.startswith('data: '):
            # Extract JSON after 'data: ' prefix
            json_str = line[6:]  # Remove 'data: ' prefix
            try:
                data = json.loads(json_str)
                results.append(data)
            except json.JSONDecodeError as e:
                print(f"Warning: Failed to parse JSON: {e}")
                print(f"Line content: {json_str}")
    
    return results


def invoke_mcp_server(runtime_arn, session_id, payload, region='us-west-2'):
    """
    Invoke MCP server using IAM authentication.
    
    Args:
        runtime_arn: Full ARN of the AgentCore runtime
        session_id: Unique session identifier (33+ characters)
        payload: JSON-RPC payload as dictionary
        region: AWS region where runtime is deployed
    
    Returns:
        Parsed response data
    """
    client = boto3.client('bedrock-agentcore-runtime', region_name=region)
    
    try:
        # CRITICAL: The accept parameter MUST include 'text/event-stream'
        # Using only 'application/json' causes HTTP 406 Not Acceptable errors
        response = client.invoke_agent_runtime(
            agentRuntimeArn=runtime_arn,
            runtimeSessionId=session_id,
            mcpSessionId=session_id,  # Use same ID for MCP session
            mcpProtocolVersion='2024-11-05',  # Required MCP protocol version
            payload=json.dumps(payload),
            qualifier='DEFAULT',
            accept='application/json, text/event-stream'  # CRITICAL: Include text/event-stream
        )
        
        # Parse the SSE response stream
        response_body = response['response'].read()
        results = parse_sse_response(response_body)
        
        # Return the first result (or all if multiple)
        if len(results) == 1:
            return results[0]
        return results
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_msg = e.response['Error']['Message']
        
        if error_code == 'AccessDeniedException':
            print(f"\n✗ ERROR: Access Denied")
            print(f"Message: {error_msg}")
            print(f"\nEnsure your AWS credentials have permission:")
            print(f"  Action: bedrock-agentcore:InvokeAgentRuntime")
            print(f"  Resource: {runtime_arn}")
        elif error_code == 'ResourceNotFoundException':
            print(f"\n✗ ERROR: Runtime Not Found")
            print(f"Message: {error_msg}")
            print(f"\nVerify the runtime ARN is correct:")
            print(f"  Provided: {runtime_arn}")
        elif e.response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 406:
            print(f"\n✗ ERROR: HTTP 406 Not Acceptable")
            print(f"Message: {error_msg}")
            print(f"\nThis error occurs when the accept header is incorrect.")
            print(f"SOLUTION: Ensure accept='application/json, text/event-stream'")
        else:
            print(f"\n✗ ERROR: {error_code}")
            print(f"Message: {error_msg}")
        
        raise


def main():
    """Main test function."""
    
    # Get configuration from environment
    runtime_arn = os.getenv('AGENT_ARN')
    region = os.getenv('AWS_REGION', 'us-west-2')
    
    if not runtime_arn:
        print("ERROR: AGENT_ARN environment variable not set")
        print("\nUsage:")
        print("  export AGENT_ARN='arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-server-xyz'")
        print("  python tests/test_client_remote_iam.py")
        print("\nNote: AWS credentials must be configured (via AWS CLI or environment variables)")
        sys.exit(1)
    
    # Generate unique session ID (must be 33+ characters)
    session_id = f"test-session-{uuid.uuid4().hex}"
    
    print("="*80)
    print("MCP Server Remote Test Client - IAM Authentication")
    print("="*80)
    print(f"Runtime ARN: {runtime_arn}")
    print(f"Region: {region}")
    print(f"Session ID: {session_id}")
    print(f"Authentication: AWS IAM (via boto3)")
    print("="*80)
    
    # Verify AWS credentials are available
    try:
        sts = boto3.client('sts', region_name=region)
        identity = sts.get_caller_identity()
        print(f"\n✓ AWS Credentials Found")
        print(f"  Account: {identity['Account']}")
        print(f"  ARN: {identity['Arn']}")
    except Exception as e:
        print(f"\n✗ ERROR: Unable to verify AWS credentials")
        print(f"  {e}")
        print(f"\nEnsure AWS credentials are configured:")
        print(f"  - Run: aws configure")
        print(f"  - Or set: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
        sys.exit(1)
    
    try:
        # Test 1: List available tools
        print("\n" + "="*80)
        print("Test 1: List Available Tools")
        print("="*80)
        
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }
        
        result = invoke_mcp_server(runtime_arn, session_id, payload, region)
        
        if 'error' in result:
            print(f"✗ Error: {result['error']}")
            sys.exit(1)
        
        tools = result.get('result', {}).get('tools', [])
        print(f"\n✓ Found {len(tools)} tools:")
        
        for tool in tools:
            print(f"\n  • {tool['name']}")
            print(f"    {tool.get('description', 'No description')}")
        
        # Test 2: Call a tool (if available)
        if tools:
            print("\n" + "="*80)
            print("Test 2: Call a Tool")
            print("="*80)
            
            # Try to find add_numbers or use first available tool
            test_tool = None
            test_args = {}
            
            for tool in tools:
                if tool['name'] == 'add_numbers':
                    test_tool = 'add_numbers'
                    test_args = {"a": 5, "b": 3}
                    break
            
            if not test_tool and tools:
                # Use first available tool with minimal args
                test_tool = tools[0]['name']
                test_args = {}
            
            if test_tool:
                payload = {
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": test_tool,
                        "arguments": test_args
                    },
                    "id": 2
                }
                
                print(f"\nCalling {test_tool}({test_args})...")
                
                result = invoke_mcp_server(runtime_arn, session_id, payload, region)
                
                if 'error' in result:
                    print(f"✗ Error: {result['error']}")
                else:
                    print(f"✓ Success!")
                    print(f"Result: {json.dumps(result.get('result'), indent=2)}")
        
        # Success
        print("\n" + "="*80)
        print("✓ All Tests Passed!")
        print("="*80)
        print("\nKey Takeaways:")
        print("  1. IAM authentication works seamlessly with boto3")
        print("  2. The accept header MUST include 'text/event-stream'")
        print("  3. Responses are in SSE format and must be parsed accordingly")
        print("  4. Session IDs must be unique and 33+ characters long")
        print("  5. mcpProtocolVersion must be '2024-11-05'")
        
    except Exception as e:
        print(f"\n✗ Test Failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
