#!/usr/bin/env python3
"""
Test normal invoke for both AgentCore agents using proper MCP protocol
"""

import boto3
import json
import time

def test_data_agent():
    """Test Data Agent with normal invoke"""
    print("🔍 Testing Data Agent Normal Invoke...")
    
    try:
        client = boto3.client('bedrock-agentcore', region_name='us-west-2')
        
        # Test 1: List tools (MCP protocol)
        print("📋 Test 1: List available tools")
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        payload = json.dumps(mcp_request).encode()
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/dataagent-DModvU2th0',
            runtimeSessionId='test-session-data-12345678901234567890123456789012',
            payload=payload
        )
        
        response_body = response['response'].read()
        response_data = json.loads(response_body)
        print(f"✅ Tools list response: {response_data}")
        
        # Test 2: Call a specific tool
        print("\n🔧 Test 2: Call get_customer tool")
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_customer",
                "arguments": {
                    "customer_id": "550e8400-e29b-41d4-a716-446655440001"
                }
            }
        }
        
        payload = json.dumps(mcp_request).encode()
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/dataagent-DModvU2th0',
            runtimeSessionId='test-session-data-12345678901234567890123456789012',
            payload=payload
        )
        
        response_body = response['response'].read()
        response_data = json.loads(response_body)
        print(f"✅ Tool call response: {response_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data Agent test failed: {e}")
        return False

def test_ticket_agent():
    """Test Ticket Agent with normal invoke"""
    print("\n🎫 Testing Ticket Agent Normal Invoke...")
    
    try:
        client = boto3.client('bedrock-agentcore', region_name='us-west-2')
        
        # Test 1: List tools (MCP protocol)
        print("📋 Test 1: List available tools")
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/list",
            "params": {}
        }
        
        payload = json.dumps(mcp_request).encode()
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/ticketagent-1MDfbW6bm5',
            runtimeSessionId='test-session-ticket-12345678901234567890123456789012',
            payload=payload
        )
        
        response_body = response['response'].read()
        response_data = json.loads(response_body)
        print(f"✅ Tools list response: {response_data}")
        
        # Test 2: Call a specific tool
        print("\n🎯 Test 2: Call validate_ticket_eligibility tool")
        mcp_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "validate_ticket_eligibility",
                "arguments": {
                    "ticket_id": "550e8400-e29b-41d4-a716-446655440002",
                    "upgrade_tier": "Standard"
                }
            }
        }
        
        payload = json.dumps(mcp_request).encode()
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/ticketagent-1MDfbW6bm5',
            runtimeSessionId='test-session-ticket-12345678901234567890123456789012',
            payload=payload
        )
        
        response_body = response['response'].read()
        response_data = json.loads(response_body)
        print(f"✅ Tool call response: {response_data}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ticket Agent test failed: {e}")
        return False

def test_simple_invoke():
    """Test simple text invoke (non-MCP)"""
    print("\n💬 Testing Simple Text Invoke...")
    
    try:
        client = boto3.client('bedrock-agentcore', region_name='us-west-2')
        
        # Test simple text payload
        payload = "Hello, can you help me with customer data?"
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/dataagent-DModvU2th0',
            runtimeSessionId='test-session-simple-12345678901234567890123456789012',
            payload=payload.encode()
        )
        
        response_body = response['response'].read()
        print(f"✅ Simple invoke response: {response_body.decode()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Simple invoke test failed: {e}")
        return False

def check_agent_status():
    """Check the status of both agents"""
    print("📊 Checking Agent Status...")
    
    try:
        client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
        
        # Check Data Agent
        data_agent_response = client.get_agent_runtime(
            agentRuntimeId='dataagent-DModvU2th0'
        )
        print(f"📈 Data Agent Status: {data_agent_response['status']}")
        
        # Check Ticket Agent  
        ticket_agent_response = client.get_agent_runtime(
            agentRuntimeId='ticketagent-1MDfbW6bm5'
        )
        print(f"🎫 Ticket Agent Status: {ticket_agent_response['status']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting AgentCore Normal Invoke Tests")
    print("=" * 60)
    
    # Check agent status first
    status_ok = check_agent_status()
    
    if status_ok:
        print("\n" + "=" * 60)
        
        # Test Data Agent
        data_success = test_data_agent()
        
        # Wait a moment between tests
        time.sleep(2)
        
        # Test Ticket Agent
        ticket_success = test_ticket_agent()
        
        # Wait a moment between tests
        time.sleep(2)
        
        # Test simple invoke
        simple_success = test_simple_invoke()
        
        print("\n" + "=" * 60)
        print("📊 Test Results Summary:")
        print(f"   Data Agent MCP: {'✅ PASS' if data_success else '❌ FAIL'}")
        print(f"   Ticket Agent MCP: {'✅ PASS' if ticket_success else '❌ FAIL'}")
        print(f"   Simple Text Invoke: {'✅ PASS' if simple_success else '❌ FAIL'}")
        
        if data_success and ticket_success:
            print("\n🎉 Both agents are working correctly!")
        else:
            print("\n⚠️ Some tests failed - check logs for details")
    else:
        print("\n❌ Agent status check failed - agents may not be ready")