#!/usr/bin/env python3
"""
Debug AgentCore HTTP Flow

This script debugs the actual HTTP flow to see what's happening
when the Lambda calls the AgentCore agent via HTTP.
"""

import sys
import os
import asyncio
import json
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

async def debug_http_flow():
    """Debug the HTTP flow from Lambda to AgentCore agent"""
    
    print("🔍 DEBUGGING AGENTCORE HTTP FLOW")
    print("="*70)
    
    try:
        from agentcore_client import AgentCoreClient
        
        client = AgentCoreClient()
        
        if not client.get_bearer_token():
            print("❌ AgentCore authentication failed")
            return False
        
        print("✅ AgentCore authentication successful")
        
        # Real customer and ticket IDs
        real_customer_id = "fdd70d2c-3f05-4749-9b8d-9ba3142c0707"  # John Doe
        real_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        
        print(f"\n🎯 Testing HTTP call to AgentCore Ticket Agent")
        print(f"   Ticket ID: {real_ticket_id}")
        print(f"   Customer ID: {real_customer_id}")
        print(f"   Agent ARN: {client.ticket_agent_arn}")
        
        # Make the HTTP call with detailed logging
        print(f"\n📡 Making HTTP call to AgentCore...")
        
        validation_result = await client.call_ticket_agent_tool('validate_ticket_eligibility', {
            'ticket_id': real_ticket_id,
            'customer_id': real_customer_id
        })
        
        print(f"\n📥 HTTP Response received:")
        print(f"   Success: {validation_result.get('success', False)}")
        print(f"   Error: {validation_result.get('error', 'None')}")
        
        if validation_result.get('success'):
            data = validation_result.get('data', {})
            print(f"\n📊 Response Data Structure:")
            print(f"   Data type: {type(data)}")
            print(f"   Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            
            if isinstance(data, dict):
                # Check for different response formats
                if 'result' in data:
                    result = data['result']
                    print(f"\n🎫 Ticket Result:")
                    print(f"   Result type: {type(result)}")
                    print(f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
                    
                    if isinstance(result, dict):
                        ticket_info = result.get('ticket', {})
                        customer_info = result.get('customer', {})
                        
                        print(f"\n👤 Customer Info:")
                        print(f"   Name: {customer_info.get('first_name', 'Unknown')} {customer_info.get('last_name', 'Unknown')}")
                        print(f"   Email: {customer_info.get('email', 'Unknown')}")
                        
                        print(f"\n🎫 Ticket Info:")
                        ticket_number = ticket_info.get('ticket_number', 'Unknown')
                        print(f"   Ticket Number: {ticket_number}")
                        print(f"   Ticket Type: {ticket_info.get('ticket_type', 'Unknown')}")
                        print(f"   Status: {ticket_info.get('status', 'Unknown')}")
                        
                        # Analyze the ticket number to determine data source
                        if ticket_number == 'TKT-TEST001':
                            print(f"   ✅ REAL DATABASE DATA (from Aurora)")
                        elif ticket_number == 'TKT-TEST789':
                            print(f"   ❌ FALLBACK DATA (from old agent code)")
                        elif ticket_number.startswith('TKT-FALLBACK'):
                            print(f"   ❌ LAMBDA FALLBACK DATA (from Lambda error)")
                        else:
                            print(f"   ⚠️  UNKNOWN DATA SOURCE")
                        
                        print(f"\n🔍 Data Source Analysis:")
                        data_source = result.get('data_source', 'Unknown')
                        print(f"   Data Source: {data_source}")
                        
                        reasoning = result.get('eligibility_reasons', '')
                        if reasoning:
                            print(f"   Reasoning length: {len(reasoning)} characters")
                            if 'fallback' in reasoning.lower() or 'test data' in reasoning.lower():
                                print(f"   ⚠️  Reasoning mentions fallback/test data")
                            else:
                                print(f"   ✅ Reasoning looks like real analysis")
                
                # Show raw response for debugging
                print(f"\n🔧 Raw Response (first 500 chars):")
                print(f"   {str(data)[:500]}...")
            
        else:
            print(f"❌ HTTP call failed: {validation_result.get('error', 'Unknown')}")
        
        return validation_result.get('success', False)
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_direct_lambda_call():
    """Test calling the Data Agent Invoker Lambda directly for comparison"""
    
    print(f"\n🔧 TESTING DIRECT LAMBDA CALL FOR COMPARISON")
    print("="*70)
    
    try:
        import boto3
        
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        # Test the Data Agent Invoker Lambda directly
        real_customer_id = "fdd70d2c-3f05-4749-9b8d-9ba3142c0707"
        
        payload = {
            "jsonrpc": "2.0",
            "id": "debug-test-123",
            "method": "tools/call",
            "params": {
                "name": "get_tickets_for_customer",
                "arguments": {"customer_id": real_customer_id}
            }
        }
        
        print(f"📡 Calling Data Agent Invoker Lambda directly...")
        
        response = lambda_client.invoke(
            FunctionName='data-agent-invoker',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        if response['StatusCode'] == 200:
            result = json.loads(response['Payload'].read())
            
            if 'result' in result:
                tickets_data = result['result']
                if tickets_data.get('success'):
                    tickets = tickets_data.get('tickets', [])
                    print(f"✅ Direct Lambda call successful")
                    print(f"   Found {len(tickets)} tickets")
                    
                    for ticket in tickets:
                        if ticket.get('id') == '550e8400-e29b-41d4-a716-446655440002':
                            print(f"   ✅ Target ticket found: {ticket.get('ticket_number', 'Unknown')}")
                            return True
                else:
                    print(f"❌ Direct Lambda call failed: {tickets_data.get('error', 'Unknown')}")
            else:
                print(f"❌ Unexpected Lambda response: {result}")
        else:
            print(f"❌ Lambda invocation failed: {response['StatusCode']}")
        
        return False
        
    except Exception as e:
        print(f"❌ Direct Lambda test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 AGENTCORE HTTP FLOW DEBUG")
    print("="*70)
    
    # Test 1: Direct Lambda call (should work)
    lambda_success = asyncio.run(test_direct_lambda_call())
    
    # Test 2: HTTP flow through AgentCore (the issue)
    http_success = asyncio.run(debug_http_flow())
    
    print(f"\n🎯 DEBUG RESULTS:")
    print(f"✅ Direct Lambda Call: {'WORKING' if lambda_success else 'FAILED'}")
    print(f"{'✅' if http_success else '❌'} AgentCore HTTP Flow: {'WORKING' if http_success else 'ISSUE FOUND'}")
    
    if lambda_success and not http_success:
        print(f"\n💡 CONCLUSION:")
        print(f"The Data Agent Invoker Lambda works correctly when called directly.")
        print(f"The issue is in the AgentCore agent's HTTP response processing.")
        print(f"The deployed AgentCore agent may not be calling the Lambda correctly.")
    elif lambda_success and http_success:
        print(f"\n🎉 CONCLUSION:")
        print(f"Both direct Lambda and AgentCore HTTP flow are working!")
        print(f"The issue may be in the test interpretation.")
    else:
        print(f"\n❌ CONCLUSION:")
        print(f"There are issues with the Lambda integration that need investigation.")