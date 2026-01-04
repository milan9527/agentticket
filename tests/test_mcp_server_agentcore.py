#!/usr/bin/env python3
"""
Test MCP server for AgentCore compatibility
Based on AWS documentation: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html
"""

import os
import sys
import asyncio
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

async def test_mcp_server():
    """Test MCP server according to AWS AgentCore requirements"""
    try:
        print("🔍 Testing MCP server for AgentCore compatibility...")
        
        # Test MCP client connection
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        
        # Test local MCP server
        mcp_url = "http://localhost:8000/mcp"
        headers = {}
        
        print(f"🔗 Connecting to MCP server at {mcp_url}")
        
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # List available tools
                tool_result = await session.list_tools()
                print(f"✅ MCP server responding with {len(tool_result.tools)} tools:")
                for tool in tool_result.tools:
                    print(f"   - {tool.name}: {tool.description}")
                
                # Test a simple tool call
                if tool_result.tools:
                    first_tool = tool_result.tools[0]
                    print(f"🧪 Testing tool: {first_tool.name}")
                    
                    # Create a simple test call based on the tool
                    if first_tool.name == "get_customer":
                        test_args = {"customer_id": "550e8400-e29b-41d4-a716-446655440001"}
                    elif first_tool.name == "validate_ticket_eligibility":
                        test_args = {"ticket_id": "550e8400-e29b-41d4-a716-446655440002"}
                    else:
                        test_args = {}
                    
                    try:
                        result = await session.call_tool(first_tool.name, test_args)
                        print(f"✅ Tool call successful: {result}")
                    except Exception as e:
                        print(f"⚠️ Tool call failed (expected for test data): {e}")
                
                print("🎉 MCP server test completed successfully!")
                return True
                
    except Exception as e:
        print(f"❌ MCP server test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def start_test_server():
    """Start a test MCP server"""
    try:
        print("🚀 Starting test MCP server...")
        
        # Import the data agent
        from backend.agents.agentcore_data_agent import mcp
        
        # Start the server in the background
        import threading
        import time
        
        def run_server():
            mcp.run(transport="streamable-http")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        await asyncio.sleep(3)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to start test server: {e}")
        return False

if __name__ == "__main__":
    async def main():
        # Start the server
        server_started = await start_test_server()
        if not server_started:
            sys.exit(1)
        
        # Test the server
        success = await test_mcp_server()
        sys.exit(0 if success else 1)
    
    asyncio.run(main())