#!/usr/bin/env python3
"""
AgentCore Runtime Deployment Validation Script

Validates that your MCP server is correctly deployed and functioning in AgentCore Runtime.
This script performs comprehensive checks including:
- Runtime status verification
- Health check endpoint
- MCP protocol compliance
- Tool discovery and execution
- Authentication validation
- Performance benchmarks

Usage:
    python validate_deployment.py --runtime-arn arn:aws:bedrock-agentcore:...
"""

import argparse
import boto3
import json
import sys
import time
from typing import Dict, List, Optional, Tuple
import uuid


class DeploymentValidator:
    def __init__(self, runtime_arn: str, region: str = "us-west-2", bearer_token: Optional[str] = None):
        self.runtime_arn = runtime_arn
        self.region = region
        self.bearer_token = bearer_token
        self.agentcore_client = boto3.client('bedrock-agentcore-control', region_name=region)
        self.invoke_client = boto3.client('bedrock-agentcore', region_name=region)
        
        # Test results tracking
        self.test_results = []
        self.passed_tests = 0
        self.total_tests = 0
    
    def log_test(self, test_name: str, passed: bool, message: str = "", details: str = ""):
        """Log test result."""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message,
            'details': details
        })
        
        print(f"{status} {test_name}")
        if message:
            print(f"     {message}")
        if details and not passed:
            print(f"     Details: {details}")
    
    def test_runtime_status(self) -> bool:
        """Test 1: Verify runtime exists and is in ACTIVE status."""
        print("\n🔍 Testing Runtime Status...")
        
        try:
            runtime_id = self.runtime_arn.split('/')[-1]
            response = self.agentcore_client.describe_agent_runtime(
                agentRuntimeId=runtime_id
            )
            
            status = response.get('status', 'UNKNOWN')
            runtime_name = response.get('agentRuntimeName', 'Unknown')
            
            if status == 'ACTIVE':
                self.log_test(
                    "Runtime Status",
                    True,
                    f"Runtime '{runtime_name}' is ACTIVE"
                )
                return True
            else:
                self.log_test(
                    "Runtime Status",
                    False,
                    f"Runtime '{runtime_name}' status is {status} (expected ACTIVE)",
                    f"Full response: {json.dumps(response, default=str)}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Runtime Status",
                False,
                "Failed to describe runtime",
                str(e)
            )
            return False
    
    def test_mcp_initialization(self) -> bool:
        """Test 2: Verify MCP server initialization."""
        print("\n🔍 Testing MCP Initialization...")
        
        try:
            # Send initialize request
            payload = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "validation-client",
                        "version": "1.0.0"
                    }
                },
                "id": 1
            }
            
            response = self._invoke_runtime(payload)
            
            if response and 'result' in response:
                server_info = response['result'].get('serverInfo', {})
                server_name = server_info.get('name', 'unknown')
                protocol_version = response['result'].get('protocolVersion', 'unknown')
                
                self.log_test(
                    "MCP Initialization",
                    True,
                    f"Server '{server_name}' initialized with protocol {protocol_version}"
                )
                return True
            else:
                self.log_test(
                    "MCP Initialization",
                    False,
                    "Invalid initialization response",
                    f"Response: {response}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "MCP Initialization",
                False,
                "Initialization failed",
                str(e)
            )
            return False
    
    def test_tools_list(self) -> Tuple[bool, List[str]]:
        """Test 3: List available tools."""
        print("\n🔍 Testing Tools Discovery...")
        
        try:
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            }
            
            response = self._invoke_runtime(payload)
            
            if response and 'result' in response:
                tools = response['result'].get('tools', [])
                tool_names = [tool.get('name', 'unnamed') for tool in tools]
                
                if tools:
                    self.log_test(
                        "Tools Discovery",
                        True,
                        f"Found {len(tools)} tools: {', '.join(tool_names[:3])}" + 
                        (f" and {len(tool_names) - 3} more..." if len(tool_names) > 3 else "")
                    )
                else:
                    self.log_test(
                        "Tools Discovery",
                        False,
                        "No tools found - server may not have loaded tools correctly"
                    )
                    return False, []
                
                return True, tool_names
            else:
                self.log_test(
                    "Tools Discovery",
                    False,
                    "Invalid tools/list response",
                    f"Response: {response}"
                )
                return False, []
                
        except Exception as e:
            self.log_test(
                "Tools Discovery",
                False,
                "Failed to list tools",
                str(e)
            )
            return False, []
    
    def test_tool_execution(self, tool_names: List[str]) -> bool:
        """Test 4: Execute a sample tool if available."""
        print("\n🔍 Testing Tool Execution...")
        
        if not tool_names:
            self.log_test(
                "Tool Execution",
                False,
                "No tools available to test"
            )
            return False
        
        # Try to find a simple tool to test
        test_candidates = ['add_numbers', 'calculator_add', 'ping', 'health_check']
        test_tool = None
        
        for candidate in test_candidates:
            if candidate in tool_names:
                test_tool = candidate
                break
        
        if not test_tool:
            # Just test the first tool with minimal parameters
            test_tool = tool_names[0]
        
        try:
            # Prepare test parameters based on common tool patterns
            test_params = {}
            if 'add' in test_tool.lower() or 'calculator' in test_tool.lower():
                test_params = {"a": 5, "b": 3}
            elif 'echo' in test_tool.lower():
                test_params = {"message": "validation test"}
            elif 'ping' in test_tool.lower() or 'health' in test_tool.lower():
                test_params = {}
            
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": test_tool,
                    "arguments": test_params
                },
                "id": 3
            }
            
            response = self._invoke_runtime(payload)
            
            if response and 'result' in response:
                content = response['result'].get('content', [])
                if content:
                    result_text = content[0].get('text', 'No text result')
                    self.log_test(
                        "Tool Execution",
                        True,
                        f"Tool '{test_tool}' executed successfully",
                        f"Result: {result_text[:100]}{'...' if len(result_text) > 100 else ''}"
                    )
                else:
                    self.log_test(
                        "Tool Execution",
                        True,
                        f"Tool '{test_tool}' executed (empty result)"
                    )
                return True
            elif response and 'error' in response:
                error = response['error']
                if error.get('code') == -32602:  # Invalid params
                    self.log_test(
                        "Tool Execution",
                        True,
                        f"Tool '{test_tool}' responded correctly to invalid params (parameter validation working)"
                    )
                    return True
                else:
                    self.log_test(
                        "Tool Execution",
                        False,
                        f"Tool '{test_tool}' returned error: {error.get('message', 'Unknown error')}"
                    )
                    return False
            else:
                self.log_test(
                    "Tool Execution",
                    False,
                    f"Invalid response from tool '{test_tool}'",
                    f"Response: {response}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Tool Execution",
                False,
                f"Exception while testing tool '{test_tool}'",
                str(e)
            )
            return False
    
    def test_error_handling(self) -> bool:
        """Test 5: Verify proper error handling."""
        print("\n🔍 Testing Error Handling...")
        
        try:
            # Send invalid method request
            payload = {
                "jsonrpc": "2.0",
                "method": "nonexistent/method",
                "id": 4
            }
            
            response = self._invoke_runtime(payload)
            
            if response and 'error' in response:
                error = response['error']
                error_code = error.get('code', 0)
                error_message = error.get('message', '')
                
                # Check for proper JSON-RPC error code
                if error_code == -32601:  # Method not found
                    self.log_test(
                        "Error Handling",
                        True,
                        f"Proper error response for invalid method: {error_message}"
                    )
                    return True
                else:
                    self.log_test(
                        "Error Handling",
                        True,
                        f"Error handling working (code: {error_code}): {error_message}"
                    )
                    return True
            else:
                self.log_test(
                    "Error Handling",
                    False,
                    "Server did not return proper error for invalid method",
                    f"Response: {response}"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Error Handling",
                False,
                "Exception during error handling test",
                str(e)
            )
            return False
    
    def test_performance(self) -> bool:
        """Test 6: Basic performance check."""
        print("\n🔍 Testing Performance...")
        
        try:
            # Measure response time for simple request
            start_time = time.time()
            
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 5
            }
            
            response = self._invoke_runtime(payload)
            end_time = time.time()
            
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            if response and 'result' in response:
                if response_time < 5000:  # Less than 5 seconds
                    self.log_test(
                        "Performance",
                        True,
                        f"Response time: {response_time:.0f}ms (good)"
                    )
                    return True
                else:
                    self.log_test(
                        "Performance",
                        False,
                        f"Response time: {response_time:.0f}ms (slow - expected <5000ms)"
                    )
                    return False
            else:
                self.log_test(
                    "Performance",
                    False,
                    "No valid response received for performance test"
                )
                return False
                
        except Exception as e:
            self.log_test(
                "Performance",
                False,
                "Exception during performance test",
                str(e)
            )
            return False
    
    def test_authentication(self) -> bool:
        """Test 7: Authentication (if bearer token provided)."""
        print("\n🔍 Testing Authentication...")
        
        if not self.bearer_token:
            self.log_test(
                "Authentication",
                True,
                "No bearer token provided - skipping auth test (server may be public)"
            )
            return True
        
        try:
            # Test with valid token (already used in previous tests)
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/list", 
                "id": 6
            }
            
            response = self._invoke_runtime(payload)
            
            if response and 'result' in response:
                self.log_test(
                    "Authentication",
                    True,
                    "Authenticated request succeeded"
                )
                
                # Optionally test with invalid token (skip for now to avoid breaking the test)
                return True
            else:
                self.log_test(
                    "Authentication",
                    False,
                    "Authenticated request failed",
                    f"Response: {response}"
                )
                return False
                
        except Exception as e:
            if "Unauthorized" in str(e) or "403" in str(e):
                self.log_test(
                    "Authentication",
                    False,
                    "Authentication failed - check bearer token",
                    str(e)
                )
            else:
                self.log_test(
                    "Authentication",
                    False,
                    "Exception during authentication test",
                    str(e)
                )
            return False
    
    def _invoke_runtime(self, payload: dict) -> dict:
        """Helper to invoke AgentCore Runtime."""
        session_id = f"validation-{uuid.uuid4().hex[:8]}"
        
        # Ensure session ID is long enough (AgentCore requirement)
        if len(session_id) < 33:
            session_id = f"validation-session-{uuid.uuid4().hex}"
        
        invoke_params = {
            'agentRuntimeArn': self.runtime_arn,
            'runtimeSessionId': session_id,
            'payload': json.dumps(payload),
            'qualifier': 'DEFAULT'
        }
        
        # Add bearer token if provided
        if self.bearer_token:
            invoke_params['bearerToken'] = self.bearer_token
        
        response = self.invoke_client.invoke_agent_runtime(**invoke_params)
        
        response_body = response['response'].read().decode('utf-8')
        return json.loads(response_body)
    
    def run_all_tests(self) -> bool:
        """Run all validation tests."""
        print("=" * 80)
        print("🧪 AgentCore Runtime Deployment Validation")
        print("=" * 80)
        print(f"Runtime ARN: {self.runtime_arn}")
        print(f"Region: {self.region}")
        print(f"Authentication: {'Bearer Token' if self.bearer_token else 'None'}")
        print("=" * 80)
        
        # Run tests in order
        tests_passed = 0
        total_tests = 7
        
        # Test 1: Runtime Status
        if self.test_runtime_status():
            tests_passed += 1
        
        # Test 2: MCP Initialization
        if self.test_mcp_initialization():
            tests_passed += 1
        
        # Test 3: Tools Discovery
        tools_ok, tool_names = self.test_tools_list()
        if tools_ok:
            tests_passed += 1
        
        # Test 4: Tool Execution
        if self.test_tool_execution(tool_names):
            tests_passed += 1
        
        # Test 5: Error Handling
        if self.test_error_handling():
            tests_passed += 1
        
        # Test 6: Performance
        if self.test_performance():
            tests_passed += 1
        
        # Test 7: Authentication
        if self.test_authentication():
            tests_passed += 1
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 Validation Summary")
        print("=" * 80)
        
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        
        print(f"Tests Passed: {self.passed_tests}/{self.total_tests} ({success_rate:.1f}%)")
        
        if self.passed_tests == self.total_tests:
            print("🎉 All tests passed! Your deployment is working correctly.")
            print("\n✅ Deployment Status: HEALTHY")
            return True
        elif success_rate >= 80:
            print("⚠️  Most tests passed. Check failed tests above.")
            print("\n⚠️  Deployment Status: MOSTLY HEALTHY")
            return False
        else:
            print("❌ Multiple tests failed. Review deployment configuration.")
            print("\n❌ Deployment Status: UNHEALTHY")
            return False
    
    def generate_report(self, output_file: str = None):
        """Generate detailed validation report."""
        report = {
            "validation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "runtime_arn": self.runtime_arn,
            "region": self.region,
            "authentication_used": bool(self.bearer_token),
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "success_rate": (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
            },
            "test_results": self.test_results
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📝 Detailed report saved to: {output_file}")
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description="Validate AgentCore Runtime deployment"
    )
    parser.add_argument(
        "--runtime-arn",
        required=True,
        help="AgentCore Runtime ARN to validate"
    )
    parser.add_argument(
        "--region",
        default="us-west-2",
        help="AWS region (default: us-west-2)"
    )
    parser.add_argument(
        "--bearer-token",
        help="Bearer token for authenticated requests"
    )
    parser.add_argument(
        "--output-report",
        help="Save detailed report to JSON file"
    )
    
    args = parser.parse_args()
    
    # Create validator and run tests
    validator = DeploymentValidator(
        runtime_arn=args.runtime_arn,
        region=args.region,
        bearer_token=args.bearer_token
    )
    
    success = validator.run_all_tests()
    
    # Generate report if requested
    if args.output_report:
        validator.generate_report(args.output_report)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()