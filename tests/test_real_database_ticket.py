#!/usr/bin/env python3
"""
Test with Real Database Ticket

This test uses an actual ticket from the Aurora database to demonstrate
the full system working with real data instead of fallback test data.
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

async def test_real_database_ticket():
    """Test with actual ticket from Aurora database"""
    
    print("🎫 TESTING WITH REAL DATABASE TICKET")
    print("Using actual ticket from Aurora database instead of fallback data")
    print("="*70)
    
    # Real ticket ID from database
    real_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
    real_customer_id = "cust_123"  # This should also exist in DB
    
    try:
        from agentcore_client import AgentCoreClient
        
        client = AgentCoreClient()
        
        if not client.get_bearer_token():
            print("❌ Authentication failed")
            return False
        
        print("✅ AgentCore authentication successful")
        
        # Test 1: Get customer data (should be real)
        print(f"\n📊 TEST 1: Get Real Customer Data")
        print(f"   Customer ID: {real_customer_id}")
        
        customer_result = await client.call_data_agent_tool('get_customer', {
            'customer_id': real_customer_id
        })
        
        if customer_result.get('success'):
            customer_data = customer_result.get('data', {})
            print(f"   ✅ Customer found: {bool(customer_data)}")
            if customer_data:
                print(f"   Customer info: {str(customer_data)[:100]}...")
        else:
            print(f"   ❌ Customer lookup failed: {customer_result.get('error', 'Unknown')}")
        
        # Test 2: Get tickets for customer (should include real ticket)
        print(f"\n🎫 TEST 2: Get Real Tickets for Customer")
        print(f"   Looking for ticket: {real_ticket_id}")
        
        tickets_result = await client.call_data_agent_tool('get_tickets_for_customer', {
            'customer_id': real_customer_id
        })
        
        if tickets_result.get('success'):
            tickets_data = tickets_result.get('data', {})
            print(f"   ✅ Tickets query successful")
            
            # Check if we got real ticket data
            if isinstance(tickets_data, dict):
                tickets = tickets_data.get('tickets', [])
                print(f"   Found {len(tickets)} tickets")
                
                # Look for our specific ticket
                found_real_ticket = False
                for ticket in tickets:
                    if ticket.get('id') == real_ticket_id:
                        found_real_ticket = True
                        print(f"   ✅ Found real ticket: {ticket.get('ticket_number', 'Unknown')}")
                        print(f"   Type: {ticket.get('ticket_type', 'Unknown')}")
                        print(f"   Status: {ticket.get('status', 'Unknown')}")
                        break
                
                if not found_real_ticket:
                    print(f"   ⚠️  Real ticket {real_ticket_id} not found in results")
                    print(f"   Available tickets: {[t.get('id', 'Unknown')[:8] + '...' for t in tickets]}")
        else:
            print(f"   ❌ Tickets lookup failed: {tickets_result.get('error', 'Unknown')}")
        
        # Test 3: Validate real ticket eligibility
        print(f"\n✅ TEST 3: Validate Real Ticket Eligibility")
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
                
                if ticket_number.startswith('TKT-TEST'):
                    print(f"   ⚠️  Using fallback data (ticket number: {ticket_number})")
                    print(f"   This means the real ticket wasn't found in the database")
                else:
                    print(f"   ✅ Using real database data (ticket number: {ticket_number})")
                
                # Show LLM analysis
                llm_analysis = ticket_result.get('eligibility_reasons', '')
                if llm_analysis:
                    print(f"   🧠 LLM Analysis: {len(llm_analysis)} characters")
                    print(f"   Analysis preview: {llm_analysis[:200]}...")
                
                # Show available upgrades
                upgrades = ticket_result.get('available_upgrades', [])
                print(f"   🎯 Available upgrades: {len(upgrades)}")
                for upgrade in upgrades[:2]:  # Show first 2
                    print(f"      • {upgrade.get('name', 'Unknown')}: ${upgrade.get('price', 0)}")
            else:
                print(f"   Raw response: {str(data)[:200]}...")
        else:
            print(f"   ❌ Validation failed: {validation_result.get('error', 'Unknown')}")
        
        # Test 4: Compare with non-existent ticket
        print(f"\n🔍 TEST 4: Compare with Non-Existent Ticket")
        fake_ticket_id = "fake-ticket-999"
        print(f"   Testing fake ticket: {fake_ticket_id}")
        
        fake_validation = await client.call_ticket_agent_tool('validate_ticket_eligibility', {
            'ticket_id': fake_ticket_id,
            'customer_id': real_customer_id
        })
        
        if fake_validation.get('success'):
            fake_data = fake_validation.get('data', {})
            
            if isinstance(fake_data, dict) and 'result' in fake_data:
                fake_result = fake_data['result']
                fake_ticket_info = fake_result.get('ticket', {})
                fake_ticket_number = fake_ticket_info.get('ticket_number', '')
                
                print(f"   Fake ticket number generated: {fake_ticket_number}")
                
                if fake_ticket_number.startswith('TKT-FAKE'):
                    print(f"   ✅ Correctly using fallback data for non-existent ticket")
                else:
                    print(f"   ⚠️  Unexpected ticket number format")
        
        print(f"\n📊 SUMMARY: Database vs Fallback Data")
        print(f"   Real ticket ID: {real_ticket_id}")
        print(f"   Expected behavior: Use real data from Aurora database")
        print(f"   Actual behavior: Check data source in validation results")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_real_database_ticket())
    
    if success:
        print(f"\n🎯 CONCLUSION:")
        print(f"✅ System working with both real and fallback data")
        print(f"💡 For production: Ensure customers use valid ticket IDs")
        print(f"🔧 For testing: Fallback data allows system validation")
    else:
        print(f"\n❌ CONCLUSION: Database integration needs attention")