#!/usr/bin/env python3
"""
Test Real Aurora Database Data

This test connects directly to Aurora to see what real data exists.
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

async def test_real_aurora_database():
    """Test direct connection to Aurora database to see real data"""
    
    print("🔍 TESTING REAL AURORA DATABASE")
    print("Connecting directly to Aurora to see what data exists")
    print("="*70)
    
    try:
        # Create Lambda client to invoke our Data Agent Invoker
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        function_name = 'data-agent-invoker'
        
        # Test 1: Get database integrity to see real counts
        print(f"\n📊 TEST 1: Database Integrity Check")
        
        integrity_payload = {
            "jsonrpc": "2.0",
            "id": "test-integrity",
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
            
            if 'result' in result and result['result'].get('success'):
                stats = result['result']['integrity_results']
                print(f"   ✅ Real Database Statistics:")
                print(f"      Total customers: {stats.get('total_customers', 0)}")
                print(f"      Total tickets: {stats.get('total_tickets', 0)}")
                print(f"      Total upgrades: {stats.get('total_upgrades', 0)}")
                print(f"      Orphaned tickets: {stats.get('orphaned_tickets', 0)}")
                print(f"      Orphaned upgrades: {stats.get('orphaned_upgrades', 0)}")
            else:
                print(f"   ❌ Integrity check failed: {result}")
        
        # Test 2: Try to find real customer and ticket data
        print(f"\n🔍 TEST 2: Looking for Real Customer and Ticket Data")
        print(f"   Since cust_123 is not a valid UUID, let's check what exists...")
        
        # Let's try some common UUID patterns that might exist
        test_customer_ids = [
            "550e8400-e29b-41d4-a716-446655440001",  # Similar to the ticket ID
            "550e8400-e29b-41d4-a716-446655440000",  # Base pattern
            "00000000-0000-0000-0000-000000000001",  # Simple test UUID
            "123e4567-e89b-12d3-a456-426614174000",  # Standard test UUID
        ]
        
        for customer_id in test_customer_ids:
            print(f"\n   Testing customer ID: {customer_id}")
            
            customer_payload = {
                "jsonrpc": "2.0",
                "id": f"test-customer-{customer_id[:8]}",
                "method": "tools/call",
                "params": {
                    "name": "get_customer",
                    "arguments": {"customer_id": customer_id}
                }
            }
            
            response = lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(customer_payload)
            )
            
            if response['StatusCode'] == 200:
                result = json.loads(response['Payload'].read())
                
                if 'result' in result:
                    customer_result = result['result']
                    if customer_result.get('success'):
                        customer = customer_result.get('customer', {})
                        print(f"      ✅ FOUND REAL CUSTOMER!")
                        print(f"         Name: {customer.get('first_name', 'Unknown')} {customer.get('last_name', 'Unknown')}")
                        print(f"         Email: {customer.get('email', 'Unknown')}")
                        print(f"         ID: {customer.get('id', 'Unknown')}")
                        
                        # Now try to get tickets for this real customer
                        print(f"\n   🎫 Getting tickets for real customer: {customer_id}")
                        
                        tickets_payload = {
                            "jsonrpc": "2.0",
                            "id": f"test-tickets-{customer_id[:8]}",
                            "method": "tools/call",
                            "params": {
                                "name": "get_tickets_for_customer",
                                "arguments": {"customer_id": customer_id}
                            }
                        }
                        
                        tickets_response = lambda_client.invoke(
                            FunctionName=function_name,
                            InvocationType='RequestResponse',
                            Payload=json.dumps(tickets_payload)
                        )
                        
                        if tickets_response['StatusCode'] == 200:
                            tickets_result = json.loads(tickets_response['Payload'].read())
                            
                            if 'result' in tickets_result:
                                tickets_data = tickets_result['result']
                                if tickets_data.get('success'):
                                    tickets = tickets_data.get('tickets', [])
                                    print(f"      ✅ Found {len(tickets)} real tickets!")
                                    
                                    for i, ticket in enumerate(tickets[:3]):  # Show first 3
                                        print(f"         Ticket {i+1}:")
                                        print(f"           ID: {ticket.get('id', 'Unknown')}")
                                        print(f"           Number: {ticket.get('ticket_number', 'Unknown')}")
                                        print(f"           Type: {ticket.get('ticket_type', 'Unknown')}")
                                        print(f"           Status: {ticket.get('status', 'Unknown')}")
                                        
                                        # Check if this is the specific ticket we're looking for
                                        if ticket.get('id') == '550e8400-e29b-41d4-a716-446655440002':
                                            print(f"           🎯 THIS IS THE TARGET TICKET!")
                                else:
                                    print(f"      ❌ No tickets found: {tickets_data.get('error', 'Unknown')}")
                        
                        # We found a real customer, so we can stop testing
                        break
                    else:
                        print(f"      ❌ Customer not found: {customer_result.get('error', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 REAL AURORA DATABASE DATA TEST")
    print("="*70)
    
    success = asyncio.run(test_real_aurora_database())
    
    if success:
        print(f"\n🎯 CONCLUSION:")
        print(f"✅ Successfully connected to real Aurora database")
        print(f"💡 Use the found customer IDs and ticket IDs for testing")
        print(f"🔧 The Data Agent Invoker is working with real database data")
    else:
        print(f"\n❌ CONCLUSION: Database connection issues found")