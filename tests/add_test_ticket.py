#!/usr/bin/env python3
"""
Add Test Ticket to Database

Add the test ticket UUID that the user expects to work using Aurora Data API.
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def add_test_ticket():
    """Add test ticket to database using Aurora Data API"""
    print("🎫 ADDING TEST TICKET TO DATABASE")
    print("=" * 40)
    
    # Initialize RDS Data API client
    rds_client = boto3.client('rds-data', region_name='us-west-2')
    
    cluster_arn = os.getenv('DB_CLUSTER_ARN')
    secret_arn = os.getenv('DB_SECRET_ARN')
    database_name = os.getenv('DATABASE_NAME')
    
    print(f"🔗 Cluster ARN: {cluster_arn}")
    print(f"🔐 Secret ARN: {secret_arn}")
    print(f"💾 Database: {database_name}")
    
    try:
        # First, get a customer ID to associate with the ticket
        response = rds_client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database_name,
            sql="SELECT id FROM customers LIMIT 1"
        )
        
        if not response['records']:
            print("❌ No customers found in database")
            return
            
        customer_id = response['records'][0][0]['stringValue']
        print(f"👤 Using customer ID: {customer_id}")
        
        # Insert the test ticket with the expected UUID
        test_ticket_id = '550e8400-e29b-41d4-a716-446655440002'
        
        # Insert ticket with specific UUID
        insert_response = rds_client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database_name,
            sql="""
                INSERT INTO tickets (id, customer_id, ticket_number, ticket_type, original_price, event_date, status)
                VALUES (:ticket_id::uuid, :customer_id::uuid, :ticket_number, :ticket_type, :price, NOW() + INTERVAL '30 days', :status)
                ON CONFLICT (id) DO NOTHING
            """,
            parameters=[
                {'name': 'ticket_id', 'value': {'stringValue': test_ticket_id}},
                {'name': 'customer_id', 'value': {'stringValue': customer_id}},
                {'name': 'ticket_number', 'value': {'stringValue': 'TKT-TEST001'}},
                {'name': 'ticket_type', 'value': {'stringValue': 'standard'}},
                {'name': 'price', 'value': {'doubleValue': 75.00}},
                {'name': 'status', 'value': {'stringValue': 'active'}}
            ]
        )
        
        print(f"✅ Added test ticket: {test_ticket_id}")
        print(f"🎫 Ticket number: TKT-TEST001")
        print(f"👤 Customer ID: {customer_id}")
        
        # Verify the ticket was added
        verify_response = rds_client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database_name,
            sql="SELECT id, ticket_number, ticket_type, status FROM tickets WHERE id = :ticket_id::uuid OR ticket_number = :ticket_id",
            parameters=[
                {'name': 'ticket_id', 'value': {'stringValue': test_ticket_id}}
            ]
        )
        
        print(f"\n📋 Verification - Found {len(verify_response['records'])} matching tickets:")
        for record in verify_response['records']:
            print(f"   ID: {record[0]['stringValue']}")
            print(f"   Number: {record[1]['stringValue']}")
            print(f"   Type: {record[2]['stringValue']}")
            print(f"   Status: {record[3]['stringValue']}")
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    add_test_ticket()