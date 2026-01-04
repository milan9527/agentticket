#!/usr/bin/env python3
"""
Query Real Database to Find Actual Customer and Ticket IDs

This script queries the Aurora database to find real customer and ticket IDs.
"""

import boto3
import json
import os
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

def query_database():
    """Query the Aurora database directly to find real data"""
    
    print("🔍 QUERYING REAL AURORA DATABASE")
    print("Finding actual customer and ticket IDs")
    print("="*70)
    
    try:
        # Get database connection info
        db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
        db_secret_arn = os.getenv('DB_SECRET_ARN')
        database_name = os.getenv('DATABASE_NAME', 'ticket_system')
        
        if not db_cluster_arn or not db_secret_arn:
            print("❌ Missing database configuration")
            return False
        
        # Create RDS Data API client
        rds_data = boto3.client('rds-data', region_name='us-west-2')
        
        # Query 1: Get all customers
        print(f"\n📊 QUERY 1: All Customers")
        
        customers_sql = "SELECT id, first_name, last_name, email FROM customers LIMIT 10"
        
        response = rds_data.execute_statement(
            resourceArn=db_cluster_arn,
            secretArn=db_secret_arn,
            database=database_name,
            sql=customers_sql
        )
        
        print(f"   Found {len(response['records'])} customers:")
        for i, record in enumerate(response['records']):
            customer_id = record[0]['stringValue']
            first_name = record[1]['stringValue']
            last_name = record[2]['stringValue']
            email = record[3]['stringValue']
            print(f"   {i+1}. ID: {customer_id}")
            print(f"      Name: {first_name} {last_name}")
            print(f"      Email: {email}")
        
        # Query 2: Get all tickets
        print(f"\n🎫 QUERY 2: All Tickets")
        
        tickets_sql = "SELECT id, customer_id, ticket_number, ticket_type, status FROM tickets LIMIT 10"
        
        response = rds_data.execute_statement(
            resourceArn=db_cluster_arn,
            secretArn=db_secret_arn,
            database=database_name,
            sql=tickets_sql
        )
        
        print(f"   Found {len(response['records'])} tickets:")
        target_ticket_found = False
        
        for i, record in enumerate(response['records']):
            ticket_id = record[0]['stringValue']
            customer_id = record[1]['stringValue']
            ticket_number = record[2]['stringValue']
            ticket_type = record[3]['stringValue']
            status = record[4]['stringValue']
            
            print(f"   {i+1}. ID: {ticket_id}")
            print(f"      Customer: {customer_id}")
            print(f"      Number: {ticket_number}")
            print(f"      Type: {ticket_type}")
            print(f"      Status: {status}")
            
            # Check if this is the target ticket
            if ticket_id == '550e8400-e29b-41d4-a716-446655440002':
                target_ticket_found = True
                print(f"      🎯 THIS IS THE TARGET TICKET!")
        
        # Query 3: Look specifically for the target ticket
        print(f"\n🎯 QUERY 3: Looking for Target Ticket")
        target_ticket_id = '550e8400-e29b-41d4-a716-446655440002'
        
        target_sql = "SELECT * FROM tickets WHERE id = :ticket_id"
        
        try:
            response = rds_data.execute_statement(
                resourceArn=db_cluster_arn,
                secretArn=db_secret_arn,
                database=database_name,
                sql=target_sql,
                parameters=[
                    {'name': 'ticket_id', 'value': {'stringValue': target_ticket_id}, 'typeHint': 'UUID'}
                ]
            )
            
            if response['records']:
                print(f"   ✅ TARGET TICKET FOUND!")
                record = response['records'][0]
                print(f"   Ticket ID: {record[0]['stringValue']}")
                print(f"   Customer ID: {record[1]['stringValue']}")
                print(f"   Ticket Number: {record[2]['stringValue']}")
                print(f"   Type: {record[3]['stringValue']}")
                print(f"   Status: {record[7]['stringValue']}")
                
                # Get the customer for this ticket
                customer_id = record[1]['stringValue']
                print(f"\n👤 QUERY 4: Customer for Target Ticket")
                
                customer_sql = "SELECT * FROM customers WHERE id = :customer_id"
                
                customer_response = rds_data.execute_statement(
                    resourceArn=db_cluster_arn,
                    secretArn=db_secret_arn,
                    database=database_name,
                    sql=customer_sql,
                    parameters=[
                        {'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}
                    ]
                )
                
                if customer_response['records']:
                    customer_record = customer_response['records'][0]
                    print(f"   ✅ CUSTOMER FOUND!")
                    print(f"   Customer ID: {customer_record[0]['stringValue']}")
                    print(f"   Name: {customer_record[3]['stringValue']} {customer_record[4]['stringValue']}")
                    print(f"   Email: {customer_record[1]['stringValue']}")
                    
                    print(f"\n🎉 SUCCESS: Found real customer and ticket pair!")
                    print(f"   Customer ID: {customer_id}")
                    print(f"   Ticket ID: {target_ticket_id}")
                    print(f"   Use these IDs for testing real database integration")
                    
                    return {
                        'customer_id': customer_id,
                        'ticket_id': target_ticket_id,
                        'success': True
                    }
                else:
                    print(f"   ❌ Customer not found for ticket")
            else:
                print(f"   ❌ Target ticket {target_ticket_id} not found in database")
                
        except Exception as e:
            print(f"   ❌ Error querying target ticket: {e}")
        
        return {'success': False}
        
    except Exception as e:
        print(f"❌ Database query failed: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False}

if __name__ == "__main__":
    result = query_database()
    
    if result.get('success'):
        print(f"\n🎯 REAL DATABASE INTEGRATION READY!")
        print(f"✅ Customer ID: {result['customer_id']}")
        print(f"✅ Ticket ID: {result['ticket_id']}")
        print(f"💡 Use these IDs to test real database access")
    else:
        print(f"\n❌ Could not find target ticket in database")
        print(f"💡 The ticket may need to be added to the database first")