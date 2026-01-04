#!/usr/bin/env python3
"""
Check if test ticket exists in database
"""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def check_ticket():
    """Check if test ticket exists"""
    print("🔍 CHECKING TEST TICKET IN DATABASE")
    print("=" * 40)
    
    rds_client = boto3.client('rds-data', region_name='us-west-2')
    
    cluster_arn = os.getenv('DB_CLUSTER_ARN')
    secret_arn = os.getenv('DB_SECRET_ARN')
    database_name = os.getenv('DATABASE_NAME')
    
    test_ticket_id = '550e8400-e29b-41d4-a716-446655440002'
    
    try:
        # Check if ticket exists by ID
        response = rds_client.execute_statement(
            resourceArn=cluster_arn,
            secretArn=secret_arn,
            database=database_name,
            sql="SELECT id, ticket_number, ticket_type, status FROM tickets WHERE id = :ticket_id::uuid",
            parameters=[
                {'name': 'ticket_id', 'value': {'stringValue': test_ticket_id}}
            ]
        )
        
        print(f"🎫 Searching for ticket ID: {test_ticket_id}")
        print(f"📋 Found {len(response['records'])} records")
        
        if response['records']:
            for record in response['records']:
                print(f"   ID: {record[0]['stringValue']}")
                print(f"   Number: {record[1]['stringValue']}")
                print(f"   Type: {record[2]['stringValue']}")
                print(f"   Status: {record[3]['stringValue']}")
        else:
            print("❌ Ticket not found")
            
            # Let's see what tickets do exist
            all_tickets = rds_client.execute_statement(
                resourceArn=cluster_arn,
                secretArn=secret_arn,
                database=database_name,
                sql="SELECT id, ticket_number, ticket_type, status FROM tickets LIMIT 5"
            )
            
            print(f"\n📋 Sample tickets in database ({len(all_tickets['records'])} found):")
            for record in all_tickets['records']:
                print(f"   ID: {record[0]['stringValue']}")
                print(f"   Number: {record[1]['stringValue']}")
                print(f"   Type: {record[2]['stringValue']}")
                print(f"   Status: {record[3]['stringValue']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_ticket()