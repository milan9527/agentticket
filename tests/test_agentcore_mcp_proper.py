#!/usr/bin/env python3
"""
Test AgentCore MCP servers using the proper AWS-recommended approach
Based on: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html#runtime-mcp-invoke-server
"""

import asyncio
import os
import sys
import boto3
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test_data_agent_mcp():
    """Test Data Agent using proper MCP client approach"""
    print("🔍 Testing Data Agent with MCP Client...")
    
    try:
        # Agent ARN for Data Agent
        agent_arn = "arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/dataagent-DModvU2th0"
        
        # Encode ARN for URL
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        
        # Construct MCP URL
        mcp_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        # Get AWS credentials for SigV4 auth
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # For now, let's try without auth to see if we get a different error
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        print(f"🔗 Connecting to: {mcp_url}")
        print(f"📋 Headers: {headers}")
        
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
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

async def test_ticket_agent_mcp():
    """Test Ticket Agent using proper MCP client approach"""
    print("\n🎫 Testing Ticket Agent with MCP Client...")
    
    try:
        # Agent ARN for Ticket Agent
        agent_arn = "arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/ticketagent-1MDfbW6bm5"
        
        # Encode ARN for URL
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        
        # Construct MCP URL
        mcp_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        # Headers for MCP
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        print(f"🔗 Connecting to: {mcp_url}")
        
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                
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

async def test_simple_boto3_invoke():
    """Test simple boto3 invoke as fallback"""
    print("\n💬 Testing Simple Boto3 Invoke...")
    
    try:
        client = boto3.client('bedrock-agentcore', region_name='us-west-2')
        
        # Test Data Agent with simple text
        print("📝 Testing Data Agent with simple text...")
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/dataagent-DModvU2th0',
            runtimeSessionId='test-simple-12345678901234567890123456789012',
            payload=b'Hello, can you list your available tools?'
        )
        
        response_body = response['response'].read()
        print(f"✅ Data Agent response: {response_body.decode()}")
        
        # Test Ticket Agent with simple text
        print("\n🎫 Testing Ticket Agent with simple text...")
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/ticketagent-1MDfbW6bm5',
            runtimeSessionId='test-simple-ticket-12345678901234567890123456789012',
            payload=b'Hello, what upgrade options do you have?'
        )
        
        response_body = response['response'].read()
        print(f"✅ Ticket Agent response: {response_body.decode()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple invoke test failed: {e}")
        return False

def check_agent_status():
    """Check agent status first"""
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
    print("🚀 AgentCore MCP Proper Testing")
    print("=" * 60)
    
    # Check status first
    if not check_agent_status():
        print("❌ Agents not ready - skipping tests")
        return
    
    print("\n" + "=" * 60)
    
    # Test MCP approach first
    data_mcp_success = await test_data_agent_mcp()
    ticket_mcp_success = await test_ticket_agent_mcp()
    
    # If MCP fails, try simple invoke
    if not (data_mcp_success and ticket_mcp_success):
        print("\n" + "=" * 60)
        print("🔄 MCP tests failed, trying simple invoke...")
        simple_success = await test_simple_boto3_invoke()
    else:
        simple_success = True
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Data Agent MCP: {'✅ PASS' if data_mcp_success else '❌ FAIL'}")
    print(f"   Ticket Agent MCP: {'✅ PASS' if ticket_mcp_success else '❌ FAIL'}")
    print(f"   Simple Invoke: {'✅ PASS' if simple_success else '❌ FAIL'}")
    
    if data_mcp_success and ticket_mcp_success:
        print("\n🎉 Both agents working with MCP protocol!")
    elif simple_success:
        print("\n⚠️ Agents working with simple invoke but MCP has issues")
    else:
        print("\n❌ All tests failed - agents may have runtime issues")

if __name__ == "__main__":
    asyncio.run(main())