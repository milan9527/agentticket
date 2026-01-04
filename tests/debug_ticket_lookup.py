#!/usr/bin/env python3
"""
Debug Ticket Lookup Issue

This script helps debug why the validate_ticket_eligibility function
can't find the specific ticket ID in the returned tickets list.
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
sys.path.append('backend/agents')

async def debug_ticket_lookup():
    """Debug the ticket lookup issue"""
    
    print("🔍 DEBUGGING TICKET LOOKUP ISSUE")
    print("="*70)
    
    try:
        from agentcore_ticket_agent import call_data_agent_tool, initialize_agent
        
        # Initialize the agent
        initialize_agent()
        print("✅ AgentCore Ticket Agent initialized")
        
        # Real customer and ticket IDs
        real_customer_id = "fdd70d2c-3f05-4749-9b8d-9ba3142c0707"  # John Doe
        target_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        
        print(f"\n🎯 TARGET TICKET ID: {target_ticket_id}")
        print(f"👤 CUSTOMER ID: {real_customer_id}")
        
        # Get tickets for the customer
        print(f"\n📋 Getting all tickets for customer...")
        tickets_result = await call_data_agent_tool("get_tickets_for_customer", {"customer_id": real_customer_id})
        
        if tickets_result.get("success"):
            tickets = tickets_result.get("tickets", [])
            print(f"✅ Found {len(tickets)} tickets")
            
            print(f"\n📊 TICKET DETAILS:")
            for i, ticket in enumerate(tickets):
                ticket_id = ticket.get('id', 'Unknown')
                ticket_number = ticket.get('ticket_number', 'Unknown')
                ticket_type = ticket.get('ticket_type', 'Unknown')
                status = ticket.get('status', 'Unknown')
                
                print(f"   {i+1}. ID: {ticket_id}")
                print(f"      Number: {ticket_number}")
                print(f"      Type: {ticket_type}")
                print(f"      Status: {status}")
                
                # Check if this matches our target
                if ticket_id == target_ticket_id:
                    print(f"      🎯 THIS IS THE TARGET TICKET!")
                else:
                    print(f"      ❌ Not the target ticket")
                print()
            
            # Check if target ticket exists
            target_found = any(ticket.get('id') == target_ticket_id for ticket in tickets)
            
            if target_found:
                print(f"✅ TARGET TICKET FOUND IN LIST!")
                print(f"The validate_ticket_eligibility function should work correctly.")
            else:
                print(f"❌ TARGET TICKET NOT FOUND IN LIST!")
                print(f"This explains why validate_ticket_eligibility falls back to first ticket.")
                
                # Check if the target ticket exists in database at all
                print(f"\n🔍 Checking if target ticket exists in database...")
                
                # Try to query the database directly for this ticket
                import boto3
                
                db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
                db_secret_arn = os.getenv('DB_SECRET_ARN')
                database_name = os.getenv('DATABASE_NAME', 'ticket_system')
                
                if db_cluster_arn and db_secret_arn:
                    rds_data = boto3.client('rds-data', region_name='us-west-2')
                    
                    sql = "SELECT id, customer_id, ticket_number, ticket_type, status FROM tickets WHERE id = :ticket_id"
                    
                    response = rds_data.execute_statement(
                        resourceArn=db_cluster_arn,
                        secretArn=db_secret_arn,
                        database=database_name,
                        sql=sql,
                        parameters=[
                            {'name': 'ticket_id', 'value': {'stringValue': target_ticket_id}, 'typeHint': 'UUID'}
                        ]
                    )
                    
                    if response['records']:
                        record = response['records'][0]
                        db_customer_id = record[1]['stringValue']
                        
                        print(f"✅ Target ticket exists in database!")
                        print(f"   Ticket ID: {record[0]['stringValue']}")
                        print(f"   Customer ID: {db_customer_id}")
                        print(f"   Ticket Number: {record[2]['stringValue']}")
                        print(f"   Type: {record[3]['stringValue']}")
                        print(f"   Status: {record[4]['stringValue']}")
                        
                        if db_customer_id != real_customer_id:
                            print(f"❌ MISMATCH: Ticket belongs to different customer!")
                            print(f"   Expected customer: {real_customer_id}")
                            print(f"   Actual customer: {db_customer_id}")
                            print(f"   This is why the ticket doesn't appear in the customer's ticket list!")
                        else:
                            print(f"✅ Customer ID matches - this is unexpected!")
                    else:
                        print(f"❌ Target ticket does not exist in database!")
                else:
                    print(f"❌ Database configuration missing - cannot check directly")
        else:
            print(f"❌ Failed to get tickets: {tickets_result.get('error', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(debug_ticket_lookup())