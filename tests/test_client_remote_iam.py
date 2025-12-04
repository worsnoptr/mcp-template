#!/usr/bin/env python3
"""
Remote testing client for MCP servers deployed to AgentCore with IAM authentication.
 
This script demonstrates the correct way to invoke an MCP server on AgentCore
using IAM (SigV4) authentication via boto3.
 
Usage:
    export AGENT_ARN="arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/your-server-xyz"
    python tests/test_client_remote_iam.py
 
Requirements:
    - AWS credentials configured (via AWS CLI, environment variables, or IAM role)
    - boto3 installed
    - bedrock-agentcore:InvokeAgentRuntime permission
 
IMPORTANT: The accept header MUST include both 'application/json' AND 'text/event-stream'
as required by the MCP protocol. Using only 'application/json' will result in HTTP 406 errors.
"""
 
import boto3
import json
import os
import sys
import uuid
 
 
def get_agent_arn():
    """Get agent ARN from environment or config."""
    arn = os.getenv('AGENT_ARN')
    if not arn:
        # Try to read from .bedrock_agentcore.yaml
        try:
            import yaml
            with open('.bedrock_agentcore.yaml', 'r') as f:
                config = yaml.safe_load(f)
                arn = config.get('agent_runtime_arn')
        except:
            pass
    if not arn:
        print("Error: AGENT_ARN environment variable not set")
        print("Usage: export AGENT_ARN='arn:aws:bedrock-agentcore:...'")
        sys.exit(1)
    return arn
 
 
def invoke_mcp(client, agent_arn, runtime_session_id, mcp_session_id, method, params=None, request_id=1):
    """
    Invoke an MCP method on the deployed server.
    CRITICAL: The accept header MUST include both 'application/json' AND 'text/event-stream'
    as required by the MCP protocol. Using only 'application/json' will result in HTTP 406 errors.
    Args:
        client: boto3 bedrock-agentcore client
        agent_arn: ARN of the deployed agent
        runtime_session_id: Unique session ID for the runtime
        mcp_session_id: MCP-specific session ID
        method: MCP method to call (e.g., "tools/list", "tools/call")
        params: Optional parameters for the method
        request_id: JSON-RPC request ID
    Returns:
        Parsed JSON response from the MCP server
    """
    payload = {"jsonrpc": "2.0", "method": method, "id": request_id}
    if params:
        payload["params"] = params
    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=runtime_session_id,
        mcpSessionId=mcp_session_id,
        mcpProtocolVersion="2024-11-05",
        payload=json.dumps(payload).encode('utf-8'),
        qualifier='DEFAULT',
        contentType='application/json',
        # CRITICAL: Must accept both content types per MCP protocol spec
        accept='application/json, text/event-stream'
    )
    # Parse SSE (Server-Sent Events) response format
    # The response stream returns raw bytes in SSE format
    full_response = b""
    for chunk in response['response']:
        if isinstance(chunk, bytes):
            full_response += chunk
    # Extract JSON from SSE format (event: message\ndata: {...})
    text = full_response.decode('utf-8')
    for line in text.strip().split('\n'):
        if line.startswith('data: '):
            return json.loads(line[6:])
    return None
 
 
def main():
    agent_arn = get_agent_arn()
    region = agent_arn.split(':')[3]  # Extract region from ARN
    print("=" * 80)
    print("MCP Server Remote Test (IAM Authentication)")
    print("=" * 80)
    print(f"Agent ARN: {agent_arn}")
    print(f"Region: {region}")
    # Create boto3 client
    client = boto3.client('bedrock-agentcore', region_name=region)
    # Generate session IDs
    runtime_session_id = f"test-{uuid.uuid4().hex}"
    mcp_session_id = f"mcp-{uuid.uuid4().hex}"
    print(f"Runtime Session: {runtime_session_id}")
    print(f"MCP Session: {mcp_session_id}")
    print("=" * 80)
    # Test 1: List tools
    print("\n1. Listing available tools...")
    try:
        result = invoke_mcp(client, agent_arn, runtime_session_id, mcp_session_id, "tools/list")
        if result and 'result' in result:
            tools = result['result'].get('tools', [])
            print(f"   ✓ Found {len(tools)} tools:")
            for tool in tools:
                print(f"      - {tool['name']}")
        else:
            print(f"   ✗ Unexpected response: {result}")
            return 1
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    # Test 2: Call a tool (if any tools exist)
    if tools:
        tool = tools[0]
        print(f"\n2. Testing tool: {tool['name']}...")
        try:
            # Get the first tool's required parameters
            schema = tool.get('inputSchema', {})
            required = schema.get('required', [])
            properties = schema.get('properties', {})
            # Build test arguments with sample values
            test_args = {}
            for param in required:
                prop = properties.get(param, {})
                param_type = prop.get('type', 'string')
                default = prop.get('default')
                if default is not None:
                    test_args[param] = default
                elif param_type == 'number':
                    test_args[param] = 0.0
                elif param_type == 'integer':
                    test_args[param] = 0
                elif param_type == 'boolean':
                    test_args[param] = True
                else:
                    test_args[param] = "test"
            print(f"   Arguments: {test_args}")
            result = invoke_mcp(
                client, agent_arn, runtime_session_id, mcp_session_id,
                "tools/call",
                {"name": tool['name'], "arguments": test_args},
                request_id=2
            )
            if result and 'result' in result:
                is_error = result['result'].get('isError', False)
                if is_error:
                    print(f"   ⚠ Tool returned error (expected with test values)")
                else:
                    print(f"   ✓ Tool executed successfully")
                content = result['result'].get('content', [])
                if content:
                    text_content = content[0].get('text', '')
                    print(f"   Response preview: {text_content[:200]}...")
            else:
                print(f"   Response: {result}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    print("\n" + "=" * 80)
    print("✓ Remote testing complete!")
    print("=" * 80)
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())
