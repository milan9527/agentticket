#!/usr/bin/env python3
"""
Test MCP tool calls directly to AgentCore agents
"""

import sys
import os
import asyncio
from pathlib import Path

# Load environment
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Add path and import
sys.path.append('backend/lambda')

async def test_mcp_tool_calls():
    print("🔧 Testing MCP Tool Calls to AgentCore Agents")
    print("="*60)
    
    try:
        from agentcore_client import AgentCoreClient
        
        client = AgentCoreClient()
        
        if not client.get_bearer_token():
            print("❌ Authentication failed")
            return
        
        print("✅ Authentication successful")
        
        # Test Data Agent MCP tool call
        print("\n📊 Testing Data Agent MCP Tool Call...")
        print("   Tool: get_customer")
        print("   Parameters: {'customer_id': 'test-customer-123'}")
        
        result = await client.call_data_agent_tool('get_customer', {
            'customer_id': 'test-customer-123'
        })
        
        print(f"   Success: {result.get('success', False)}")
        if result.get('success'):
            print(f"   Data: {result.get('data', {})}")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")
        
        # Test Ticket Agent MCP tool call
        print("\n🎫 Testing Ticket Agent MCP Tool Call...")
        print("   Tool: validate_ticket_eligibility")
        print("   Parameters: {'ticket_id': 'test-ticket-456', 'customer_id': 'test-customer-123'}")
        
        result2 = await client.call_ticket_agent_tool('validate_ticket_eligibility', {
            'ticket_id': 'test-ticket-456',
            'customer_id': 'test-customer-123'
        })
        
        print(f"   Success: {result2.get('success', False)}")
        if result2.get('success'):
            print(f"   Data: {result2.get('data', {})}")
        else:
            print(f"   Error: {result2.get('error', 'Unknown error')}")
        
        # Test another Ticket Agent tool
        print("\n🎫 Testing Ticket Agent Pricing Tool...")
        print("   Tool: calculate_upgrade_pricing")
        print("   Parameters: {'ticket_type': 'general', 'upgrade_tier': 'standard', 'original_price': 50.0}")
        
        result3 = await client.call_ticket_agent_tool('calculate_upgrade_pricing', {
            'ticket_type': 'general',
            'upgrade_tier': 'standard',
            'original_price': 50.0
        })
        
        print(f"   Success: {result3.get('success', False)}")
        if result3.get('success'):
            print(f"   Data: {result3.get('data', {})}")
        else:
            print(f"   Error: {result3.get('error', 'Unknown error')}")
        
        # Summary
        working_tools = sum([
            result.get('success', False),
            result2.get('success', False),
            result3.get('success', False)
        ])
        
        print(f"\n📊 MCP Tool Call Results: {working_tools}/3 tools working")
        
        if working_tools == 3:
            print("🎉 EXCELLENT! All MCP tool calls working!")
            print("✅ AgentCore agents responding to structured tool calls")
            print("✅ Full business functionality available")
        elif working_tools > 0:
            print("⚠️  PARTIAL SUCCESS: Some tools working")
            print("🔧 Some tools may need parameter adjustments")
        else:
            print("❌ MCP tool calls not working")
            print("🔧 Need to investigate tool call format or agent configuration")
        
        return working_tools == 3
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_tool_calls())
    if success:
        print("\n🎯 NEXT STEP: Run full customer journey test to verify end-to-end functionality")
    else:
        print("\n🔧 NEXT STEP: Debug MCP tool call format or agent configuration")