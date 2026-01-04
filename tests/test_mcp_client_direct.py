#!/usr/bin/env python3
"""
Test AgentCore MCP servers using direct MCP client approach
Based on AWS documentation example
"""

import asyncio
import os
import boto3
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test_data_agent_mcp_direct():
    """Test Data Agent using direct MCP client"""
    print("🔍 Testing Data Agent with Direct MCP Client...")
    
    try:
        # Get AWS credentials for authentication
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # Agent ARN
        agent_arn = "arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/dataagent-DModvU2th0"
        
        # Encode ARN for URL
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        
        # Construct MCP URL
        mcp_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        # Use AWS SigV4 authentication
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        import httpx
        
        # Create headers with AWS authentication
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # Add AWS SigV4 signature
        request = AWSRequest(method='POST', url=mcp_url, headers=headers)
        SigV4Auth(credentials, 'bedrock-agentcore', 'us-west-2').add_auth(request)
        
        # Update headers with signature
        headers.update(dict(request.headers))
        
        print(f"🔗 Connecting to: {mcp_url}")
        print(f"📋 Using AWS SigV4 authentication")
        
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                print("🤝 Initializing MCP session...")
                await session.initialize()
                print("✅ Session initialized successfully!")
                
                # List tools
                print("📋 Listing available tools...")
                tool_result = await session.list_tools()
                print(f"✅ Found {len(tool_result.tools)} tools:")
                for tool in tool_result.tools:
                    print(f"   - {tool.name}: {tool.description}")
                
                # Test a tool call
                if tool_result.tools:
                    print(f"\n🔧 Testing tool: {tool_result.tools[0].name}")
                    result = await session.call_tool(
                        tool_result.tools[0].name,
                        {"customer_id": "550e8400-e29b-41d4-a716-446655440001"}
                    )
                    print(f"✅ Tool result: {result}")
                
                return True
                
    except Exception as e:
        print(f"❌ Data Agent MCP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ticket_agent_mcp_direct():
    """Test Ticket Agent using direct MCP client"""
    print("\n🎫 Testing Ticket Agent with Direct MCP Client...")
    
    try:
        # Get AWS credentials for authentication
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # Agent ARN
        agent_arn = "arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/ticketagent-1MDfbW6bm5"
        
        # Encode ARN for URL
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        
        # Construct MCP URL
        mcp_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        # Use AWS SigV4 authentication
        from botocore.auth import SigV4Auth
        from botocore.awsrequest import AWSRequest
        
        # Create headers with AWS authentication
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # Add AWS SigV4 signature
        request = AWSRequest(method='POST', url=mcp_url, headers=headers)
        SigV4Auth(credentials, 'bedrock-agentcore', 'us-west-2').add_auth(request)
        
        # Update headers with signature
        headers.update(dict(request.headers))
        
        print(f"🔗 Connecting to: {mcp_url}")
        print(f"📋 Using AWS SigV4 authentication")
        
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                print("🤝 Initializing MCP session...")
                await session.initialize()
                print("✅ Session initialized successfully!")
                
                # List tools
                print("📋 Listing available tools...")
                tool_result = await session.list_tools()
                print(f"✅ Found {len(tool_result.tools)} tools:")
                for tool in tool_result.tools:
                    print(f"   - {tool.name}: {tool.description}")
                
                # Test a tool call
                if tool_result.tools:
                    print(f"\n🎯 Testing tool: {tool_result.tools[0].name}")
                    result = await session.call_tool(
                        tool_result.tools[0].name,
                        {
                            "ticket_id": "550e8400-e29b-41d4-a716-446655440002",
                            "upgrade_tier": "Standard"
                        }
                    )
                    print(f"✅ Tool result: {result}")
                
                return True
                
    except Exception as e:
        print(f"❌ Ticket Agent MCP test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_local_mcp_for_comparison():
    """Test local MCP server for comparison"""
    print("\n🏠 Testing Local MCP Server for Comparison...")
    
    try:
        # Test local server
        mcp_url = "http://localhost:8000/mcp"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        print(f"🔗 Connecting to local server: {mcp_url}")
        
        async with streamablehttp_client(mcp_url, headers, timeout=30, terminate_on_close=False) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
                # List tools
                tool_result = await session.list_tools()
                print(f"✅ Local server has {len(tool_result.tools)} tools:")
                for tool in tool_result.tools:
                    print(f"   - {tool.name}: {tool.description}")
                
                return True
                
    except Exception as e:
        print(f"⚠️ Local MCP test failed (expected if not running): {e}")
        return False

def check_agent_status():
    """Check agent status"""
    print("📊 Checking Agent Status...")
    
    try:
        client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
        
        # Check Data Agent
        data_response = client.get_agent_runtime(agentRuntimeId='dataagent-DModvU2th0')
        print(f"📈 Data Agent Status: {data_response['status']}")
        
        # Check Ticket Agent
        ticket_response = client.get_agent_runtime(agentRuntimeId='ticketagent-1MDfbW6bm5')
        print(f"🎫 Ticket Agent Status: {ticket_response['status']}")
        
        return data_response['status'] == 'READY' and ticket_response['status'] == 'READY'
        
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🚀 Direct MCP Client Testing")
    print("=" * 60)
    
    # Check status first
    if not check_agent_status():
        print("❌ Agents not ready - skipping tests")
        return
    
    print("\n" + "=" * 60)
    
    # Test local MCP for comparison
    await test_local_mcp_for_comparison()
    
    print("\n" + "=" * 60)
    
    # Test AgentCore MCP servers
    data_success = await test_data_agent_mcp_direct()
    ticket_success = await test_ticket_agent_mcp_direct()
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Data Agent MCP: {'✅ PASS' if data_success else '❌ FAIL'}")
    print(f"   Ticket Agent MCP: {'✅ PASS' if ticket_success else '❌ FAIL'}")
    
    if data_success and ticket_success:
        print("\n🎉 Both AgentCore agents working with MCP protocol!")
    else:
        print("\n⚠️ AgentCore MCP tests failed - check authentication or runtime issues")

if __name__ == "__main__":
    asyncio.run(main())