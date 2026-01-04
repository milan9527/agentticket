#!/usr/bin/env python3
"""
Test AgentCore Ticket Agent Lambda Integration

This test specifically checks if the AgentCore Ticket Agent can successfully
call the Data Agent Invoker Lambda and get real database data.
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
sys.path.append('backend/agents')

async def test_agentcore_lambda_integration():
    """Test AgentCore Ticket Agent's Lambda integration directly"""
    
    print("🔧 TESTING AGENTCORE TICKET AGENT LAMBDA INTEGRATION")
    print("Testing direct call_data_agent_tool function")
    print("="*70)
    
    try:
        # Import the AgentCore Ticket Agent
        from agentcore_ticket_agent import call_data_agent_tool, initialize_agent
        
        # Initialize the agent
        initialize_agent()
        print("✅ AgentCore Ticket Agent initialized")
        
        # Real customer and ticket IDs from database
        real_customer_id = "fdd70d2c-3f05-4749-9b8d-9ba3142c0707"  # John Doe
        real_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        
        # Test 1: Get customer via call_data_agent_tool
        print(f"\n👤 TEST 1: Get Customer via call_data_agent_tool")
        print(f"   Customer ID: {real_customer_id}")
        
        customer_result = await call_data_agent_tool("get_customer", {"customer_id": real_customer_id})
        
        if customer_result.get("success"):
            customer = customer_result.get("customer", {})
            print(f"   ✅ Customer retrieved successfully")
            print(f"   Name: {customer.get('first_name', 'Unknown')} {customer.get('last_name', 'Unknown')}")
            print(f"   Email: {customer.get('email', 'Unknown')}")
            
            # Check if this is real data or fallback
            if customer.get('email') == 'fallback.customer@example.com':
                print(f"   ⚠️  Using fallback data - Lambda call failed")
                print(f"   Reasoning: {customer_result.get('reasoning', 'Unknown')}")
            else:
                print(f"   ✅ Using real database data!")
                print(f"   Reasoning: {customer_result.get('reasoning', 'Unknown')}")
        else:
            print(f"   ❌ Customer retrieval failed: {customer_result.get('error', 'Unknown')}")
        
        # Test 2: Get tickets via call_data_agent_tool
        print(f"\n🎫 TEST 2: Get Tickets via call_data_agent_tool")
        print(f"   Customer ID: {real_customer_id}")
        
        tickets_result = await call_data_agent_tool("get_tickets_for_customer", {"customer_id": real_customer_id})
        
        if tickets_result.get("success"):
            tickets = tickets_result.get("tickets", [])
            print(f"   ✅ Tickets retrieved successfully")
            print(f"   Found {len(tickets)} tickets")
            
            # Look for the real ticket
            found_real_ticket = False
            for ticket in tickets:
                if ticket.get('id') == real_ticket_id:
                    found_real_ticket = True
                    print(f"   ✅ Found real ticket: {ticket.get('ticket_number', 'Unknown')}")
                    print(f"   Type: {ticket.get('ticket_type', 'Unknown')}")
                    print(f"   Status: {ticket.get('status', 'Unknown')}")
                    break
            
            if not found_real_ticket:
                # Check if this is fallback data
                if tickets and tickets[0].get('ticket_number', '').startswith('TKT-FALLBACK'):
                    print(f"   ⚠️  Using fallback data - Lambda call failed")
                    print(f"   Reasoning: {tickets_result.get('reasoning', 'Unknown')}")
                else:
                    print(f"   ⚠️  Real ticket {real_ticket_id} not found in results")
                    if tickets:
                        print(f"   Available tickets: {[t.get('ticket_number', 'Unknown') for t in tickets]}")
            else:
                print(f"   ✅ Using real database data!")
                print(f"   Reasoning: {tickets_result.get('reasoning', 'Unknown')}")
        else:
            print(f"   ❌ Tickets retrieval failed: {tickets_result.get('error', 'Unknown')}")
        
        # Test 3: Test the full validate_ticket_eligibility tool
        print(f"\n🎯 TEST 3: Full Ticket Validation via AgentCore Tool")
        print(f"   Ticket ID: {real_ticket_id}")
        print(f"   Customer ID: {real_customer_id}")
        
        from agentcore_ticket_agent import validate_ticket_eligibility
        
        validation_result = await validate_ticket_eligibility(real_ticket_id, real_customer_id)
        
        if validation_result.get("success"):
            print(f"   ✅ Validation successful")
            print(f"   Eligible: {validation_result.get('eligible', False)}")
            print(f"   Data source: {validation_result.get('data_source', 'Unknown')}")
            
            # Check ticket data
            ticket_info = validation_result.get('ticket', {})
            ticket_number = ticket_info.get('ticket_number', '')
            
            if ticket_number.startswith('TKT-TEST') or ticket_number.startswith('TKT-FALLBACK'):
                print(f"   ⚠️  Still using fallback/test data: {ticket_number}")
                print(f"   🔧 Lambda integration not working in validation tool")
            else:
                print(f"   ✅ Using real database data: {ticket_number}")
                print(f"   🎉 SUCCESS: Full Lambda integration working!")
            
            # Show customer data
            customer_info = validation_result.get('customer', {})
            print(f"   Customer: {customer_info.get('first_name', 'Unknown')} {customer_info.get('last_name', 'Unknown')}")
        else:
            print(f"   ❌ Validation failed: {validation_result.get('error', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 AGENTCORE LAMBDA INTEGRATION TEST")
    print("="*70)
    
    success = asyncio.run(test_agentcore_lambda_integration())
    
    if success:
        print(f"\n🎯 TEST COMPLETE")
        print(f"Check the output above to see if Lambda integration is working")
    else:
        print(f"\n❌ TEST FAILED")
        print(f"Check the error logs for details")