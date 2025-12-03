#!/usr/bin/env python3
"""
Local MCP Server Test Client

This script tests the MCP server running locally on http://localhost:8000/mcp
Use this to verify your tools work correctly before deploying.

Usage:
    # Start your server first
    python src/server.py
    
    # Then run this test client
    python tests/test_client_local.py
"""

import asyncio
import sys
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def test_list_tools(session):
    """Test listing all available tools."""
    print("\n" + "="*80)
    print("TEST: List all tools")
    print("="*80)
    
    try:
        result = await session.list_tools()
        print(f"✓ Found {len(result.tools)} tools:")
        
        for tool in result.tools:
            print(f"\n  Tool: {tool.name}")
            print(f"  Description: {tool.description}")
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                print(f"  Input Schema: {tool.inputSchema}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to list tools: {e}")
        return False


async def test_calculator_tools(session):
    """Test calculator tools."""
    print("\n" + "="*80)
    print("TEST: Calculator Tools")
    print("="*80)
    
    tests = [
        {
            "name": "add_numbers",
            "args": {"a": 5, "b": 3},
            "expected": 8,
            "description": "Addition: 5 + 3"
        },
        {
            "name": "subtract_numbers",
            "args": {"a": 10, "b": 4},
            "expected": 6,
            "description": "Subtraction: 10 - 4"
        },
        {
            "name": "multiply_numbers",
            "args": {"a": 6, "b": 7},
            "expected": 42,
            "description": "Multiplication: 6 * 7"
        },
        {
            "name": "divide_numbers",
            "args": {"a": 20, "b": 4},
            "expected": 5.0,
            "description": "Division: 20 / 4"
        },
        {
            "name": "calculate_average",
            "args": {"numbers": [1, 2, 3, 4, 5]},
            "expected": 3.0,
            "description": "Average of [1, 2, 3, 4, 5]"
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\n  Testing: {test['description']}")
            result = await session.call_tool(test["name"], test["args"])
            
            # Extract the actual value from the result
            actual = result.content[0].text if hasattr(result.content[0], 'text') else result
            
            # Try to convert to appropriate type for comparison
            try:
                actual_value = float(actual) if isinstance(actual, (int, float, str)) else actual
            except:
                actual_value = actual
            
            if actual_value == test["expected"]:
                print(f"  ✓ PASS: {actual_value}")
                passed += 1
            else:
                print(f"  ✗ FAIL: Expected {test['expected']}, got {actual_value}")
                failed += 1
        
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1
    
    print(f"\n  Results: {passed} passed, {failed} failed")
    return failed == 0


async def test_direct_tools(session):
    """Test direct tools."""
    print("\n" + "="*80)
    print("TEST: Direct Tools")
    print("="*80)
    
    tests = [
        {
            "name": "process_text",
            "args": {"text": "hello world", "operation": "uppercase"},
            "description": "Text processing: uppercase"
        },
        {
            "name": "process_text",
            "args": {"text": "HELLO WORLD", "operation": "lowercase"},
            "description": "Text processing: lowercase"
        }
    ]
    
    for test in tests:
        try:
            print(f"\n  Testing: {test['description']}")
            result = await session.call_tool(test["name"], test["args"])
            print(f"  ✓ Result: {result.content[0].text if hasattr(result.content[0], 'text') else result}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")


async def test_error_handling(session):
    """Test error handling."""
    print("\n" + "="*80)
    print("TEST: Error Handling")
    print("="*80)
    
    # Test division by zero
    print("\n  Testing: Division by zero (should handle gracefully)")
    try:
        result = await session.call_tool("divide_numbers", {"a": 10, "b": 0})
        print(f"  ✗ Should have raised an error: {result}")
    except Exception as e:
        print(f"  ✓ Correctly handled error: {e}")
    
    # Test non-existent tool
    print("\n  Testing: Non-existent tool (should handle gracefully)")
    try:
        result = await session.call_tool("nonexistent_tool", {})
        print(f"  ✗ Should have raised an error: {result}")
    except Exception as e:
        print(f"  ✓ Correctly handled error: {e}")


async def main():
    """Main test runner."""
    mcp_url = "http://localhost:8000/mcp"
    headers = {}
    
    print("="*80)
    print("MCP Server Local Test Client")
    print("="*80)
    print(f"Testing server at: {mcp_url}")
    
    try:
        async with streamablehttp_client(
            mcp_url,
            headers,
            timeout=120,
            terminate_on_close=False
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize session
                await session.initialize()
                print("✓ Connected to MCP server")
                
                # Run tests
                await test_list_tools(session)
                await test_calculator_tools(session)
                await test_direct_tools(session)
                await test_error_handling(session)
                
                print("\n" + "="*80)
                print("All tests completed!")
                print("="*80)
    
    except ConnectionRefusedError:
        print("\n✗ ERROR: Could not connect to MCP server")
        print("  Make sure the server is running: python src/server.py")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
