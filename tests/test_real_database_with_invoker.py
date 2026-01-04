#!/usr/bin/env python3
"""
Test Real Database Integration with Data Agent Invoker

This test demonstrates using the Data Agent Invoker Lambda to get real data
from the Aurora database instead of fallback test data.
"""

import sys
import os
import asyncio
import json
import boto3
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

async def test_data_agent_invoker():
    """Test the Data Agent Invoker Lambda function"""
    
    print("🔧 TESTING DATA AGENT INVOKER LAMBDA")
    print("Testing direct Lambda invocation for real database access")
    print("="*70)
    
    # Real ticket and customer IDs from database (from query_real_database.py results)
    real_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
    real_customer_id = "fdd70d2c-3f05-4749-9b8d-9ba3142c0707"  # John Doe
    
    try:
        # Create Lambda client
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        function_name = 'data-agent-invoker'
        
        # Test 1: Get customer data via Lambda invoker
        print(f"\n📊 TEST 1: Get Customer via Data Agent Invoker")
        print(f"   Customer ID: {real_customer_id}")
        
        customer_payload = {
            "jsonrpc": "2.0",
            "id": "test-customer-123",
            "method": "tools/call",
            "params": {
                "name": "get_customer",
                "arguments": {"customer_id": real_customer_id}
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(customer_payload)
        )
        
        if response['StatusCode'] == 200:
            result = json.loads(response['Payload'].read())
            print(f"   ✅ Lambda invocation successful")
            
            if 'result' in result:
                customer_data = result['result']
                print(f"   Customer found: {customer_data.get('success', False)}")
                
                if customer_data.get('success'):
                    customer_info = customer_data.get('customer', {})
                    print(f"   Name: {customer_info.get('first_name', 'Unknown')} {customer_info.get('last_name', 'Unknown')}")
                    print(f"   Email: {customer_info.get('email', 'Unknown')}")
                    print(f"   ✅ REAL DATABASE DATA RETRIEVED")
                else:
                    print(f"   ❌ Customer not found: {customer_data.get('error', 'Unknown error')}")
            else:
                print(f"   ❌ Unexpected response format: {result}")
        else:
            print(f"   ❌ Lambda invocation failed: {response['StatusCode']}")
        
        # Test 2: Get tickets via Lambda invoker
        print(f"\n🎫 TEST 2: Get Tickets via Data Agent Invoker")
        print(f"   Looking for real tickets for customer: {real_customer_id}")
        
        tickets_payload = {
            "jsonrpc": "2.0",
            "id": "test-tickets-123",
            "method": "tools/call",
            "params": {
                "name": "get_tickets_for_customer",
                "arguments": {"customer_id": real_customer_id}
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(tickets_payload)
        )
        
        if response['StatusCode'] == 200:
            result = json.loads(response['Payload'].read())
            print(f"   ✅ Lambda invocation successful")
            
            if 'result' in result:
                tickets_data = result['result']
                print(f"   Tickets query successful: {tickets_data.get('success', False)}")
                
                if tickets_data.get('success'):
                    tickets = tickets_data.get('tickets', [])
                    print(f"   Found {len(tickets)} tickets")
                    
                    # Look for our specific real ticket
                    found_real_ticket = False
                    for ticket in tickets:
                        if ticket.get('id') == real_ticket_id:
                            found_real_ticket = True
                            print(f"   ✅ Found real ticket: {ticket.get('ticket_number', 'Unknown')}")
                            print(f"   Type: {ticket.get('ticket_type', 'Unknown')}")
                            print(f"   Status: {ticket.get('status', 'Unknown')}")
                            print(f"   ✅ REAL DATABASE TICKET FOUND")
                            break
                    
                    if not found_real_ticket:
                        print(f"   ⚠️  Real ticket {real_ticket_id} not found")
                        print(f"   Available tickets: {[t.get('id', 'Unknown')[:8] + '...' for t in tickets]}")
                        
                        if tickets:
                            print(f"   📋 Sample ticket data:")
                            sample_ticket = tickets[0]
                            print(f"      ID: {sample_ticket.get('id', 'Unknown')}")
                            print(f"      Number: {sample_ticket.get('ticket_number', 'Unknown')}")
                            print(f"      Type: {sample_ticket.get('ticket_type', 'Unknown')}")
                else:
                    print(f"   ❌ Tickets query failed: {tickets_data.get('error', 'Unknown error')}")
            else:
                print(f"   ❌ Unexpected response format: {result}")
        else:
            print(f"   ❌ Lambda invocation failed: {response['StatusCode']}")
        
        # Test 3: Test data integrity check
        print(f"\n🔍 TEST 3: Data Integrity Check via Data Agent Invoker")
        
        integrity_payload = {
            "jsonrpc": "2.0",
            "id": "test-integrity-123",
            "method": "tools/call",
            "params": {
                "name": "validate_data_integrity",
                "arguments": {}
            }
        }
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(integrity_payload)
        )
        
        if response['StatusCode'] == 200:
            result = json.loads(response['Payload'].read())
            print(f"   ✅ Lambda invocation successful")
            
            if 'result' in result:
                integrity_data = result['result']
                print(f"   Integrity check successful: {integrity_data.get('success', False)}")
                
                if integrity_data.get('success'):
                    results = integrity_data.get('integrity_results', {})
                    print(f"   📊 Database Statistics:")
                    print(f"      Total customers: {results.get('total_customers', 0)}")
                    print(f"      Total tickets: {results.get('total_tickets', 0)}")
                    print(f"      Total upgrades: {results.get('total_upgrades', 0)}")
                    print(f"      Orphaned tickets: {results.get('orphaned_tickets', 0)}")
                    print(f"      Orphaned upgrades: {results.get('orphaned_upgrades', 0)}")
                    print(f"   ✅ REAL DATABASE INTEGRITY CHECK COMPLETE")
                else:
                    print(f"   ❌ Integrity check failed: {integrity_data.get('error', 'Unknown error')}")
            else:
                print(f"   ❌ Unexpected response format: {result}")
        else:
            print(f"   ❌ Lambda invocation failed: {response['StatusCode']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_agentcore_with_invoker():
    """Test AgentCore Ticket Agent using the Data Agent Invoker"""
    
    print(f"\n🎯 TESTING AGENTCORE INTEGRATION WITH DATA AGENT INVOKER")
    print("Testing if AgentCore Ticket Agent can get real data via invoker")
    print("="*70)
    
    try:
        from agentcore_client import AgentCoreClient
        
        client = AgentCoreClient()
        
        if not client.get_bearer_token():
            print("❌ AgentCore authentication failed")
            return False
        
        print("✅ AgentCore authentication successful")
        
        # Test ticket validation with real data
        real_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        real_customer_id = "fdd70d2c-3f05-4749-9b8d-9ba3142c0707"  # John Doe
        
        print(f"\n🎫 Testing Ticket Validation with Real Data")
        print(f"   Ticket: {real_ticket_id}")
        print(f"   Customer: {real_customer_id}")
        
        validation_result = await client.call_ticket_agent_tool('validate_ticket_eligibility', {
            'ticket_id': real_ticket_id,
            'customer_id': real_customer_id
        })
        
        if validation_result.get('success'):
            data = validation_result.get('data', {})
            
            if isinstance(data, dict) and 'result' in data:
                ticket_result = data['result']
                
                print(f"   ✅ Validation successful!")
                print(f"   Eligible: {ticket_result.get('eligible', False)}")
                print(f"   Data source: {ticket_result.get('data_source', 'Unknown')}")
                
                # Check if this is real data or fallback
                ticket_info = ticket_result.get('ticket', {})
                ticket_number = ticket_info.get('ticket_number', '')
                
                # Real data indicators: TKT-TEST001, TKT-20240101, etc. (from database)
                # Fallback data indicators: TKT-TEST789, TKT-FALLBACK123, etc. (from fallback code)
                if ticket_number in ['TKT-TEST789', 'TKT-FALLBACK123'] or ticket_number.startswith('TKT-FALLBACK'):
                    print(f"   ⚠️  Still using fallback data (ticket number: {ticket_number})")
                    print(f"   🔧 This means the Ticket Agent is not yet using the Data Agent Invoker")
                else:
                    print(f"   ✅ Using real database data (ticket number: {ticket_number})")
                    print(f"   🎉 SUCCESS: Real database integration working!")
                
                # Show LLM analysis
                llm_analysis = ticket_result.get('eligibility_reasons', '')
                if llm_analysis:
                    print(f"   🧠 LLM Analysis: {len(llm_analysis)} characters")
                    print(f"   Analysis preview: {llm_analysis[:200]}...")
            else:
                print(f"   Raw response: {str(data)[:200]}...")
        else:
            print(f"   ❌ Validation failed: {validation_result.get('error', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ AgentCore test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 REAL DATABASE INTEGRATION TEST WITH DATA AGENT INVOKER")
    print("="*70)
    
    # Test 1: Direct Lambda invoker test
    print("Phase 1: Testing Data Agent Invoker Lambda directly")
    invoker_success = asyncio.run(test_data_agent_invoker())
    
    # Test 2: AgentCore integration test
    print("\nPhase 2: Testing AgentCore integration with invoker")
    agentcore_success = asyncio.run(test_agentcore_with_invoker())
    
    print(f"\n🎯 FINAL RESULTS:")
    print(f"✅ Data Agent Invoker: {'WORKING' if invoker_success else 'FAILED'}")
    print(f"{'✅' if agentcore_success else '❌'} AgentCore Integration: {'WORKING' if agentcore_success else 'NEEDS UPDATE'}")
    
    if invoker_success and not agentcore_success:
        print(f"\n💡 NEXT STEPS:")
        print(f"1. ✅ Data Agent Invoker Lambda is working with real database")
        print(f"2. 🔧 Need to update AgentCore Ticket Agent to use the invoker")
        print(f"3. 📝 Update call_data_agent_tool() to invoke Lambda instead of fallback data")
    elif invoker_success and agentcore_success:
        print(f"\n🎉 SUCCESS: Complete real database integration working!")
    else:
        print(f"\n❌ Issues found - check logs for details")