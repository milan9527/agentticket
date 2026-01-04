#!/usr/bin/env python3
"""
Test script to verify real data exists in Aurora PostgreSQL database
"""

import boto3
import json
import os
from typing import Dict, Any, List

def test_database_data():
    """Test that real data exists in the database"""
    region = os.getenv('AWS_REGION', 'us-west-2')
    cluster_arn = os.getenv('DB_CLUSTER_ARN')
    secret_arn = os.getenv('DB_SECRET_ARN')
    database_name = os.getenv('DATABASE_NAME', 'ticket_system')
    
    if not cluster_arn or not secret_arn:
        raise ValueError("DB_CLUSTER_ARN and DB_SECRET_ARN must be set in environment")
    
    rds_data = boto3.client('rds-data', region_name=region)
    
    def execute_sql(sql: str) -> Dict[str, Any]:
        """Execute SQL statement using RDS Data API"""
        try:
            response = rds_data.execute_statement(
                resourceArn=cluster_arn,
                secretArn=secret_arn,
                database=database_name,
                sql=sql
            )
            return response
        except Exception as e:
            print(f"Error executing SQL: {e}")
            raise
    
    print("🧪 Testing Real Database Data")
    print("=" * 50)
    
    # Test 1: Count records in each table
    tables = ['customers', 'tickets', 'upgrade_orders']
    
    for table in tables:
        count_sql = f"SELECT COUNT(*) FROM {table};"
        response = execute_sql(count_sql)
        count = response['records'][0][0]['longValue']
        print(f"📊 {table}: {count} records")
        
        if count == 0:
            print(f"❌ No data found in {table} table!")
            return False
    
    # Test 2: Sample customer data
    print("\n👥 Sample Customer Data:")
    customer_sql = "SELECT first_name, last_name, email FROM customers LIMIT 3;"
    response = execute_sql(customer_sql)
    
    for record in response['records']:
        first_name = record[0]['stringValue']
        last_name = record[1]['stringValue']
        email = record[2]['stringValue']
        print(f"  • {first_name} {last_name} ({email})")
    
    # Test 3: Sample ticket data
    print("\n🎫 Sample Ticket Data:")
    ticket_sql = """
    SELECT t.ticket_number, t.ticket_type, t.original_price, c.first_name, c.last_name
    FROM tickets t
    JOIN customers c ON t.customer_id = c.id
    LIMIT 3;
    """
    response = execute_sql(ticket_sql)
    
    for record in response['records']:
        ticket_number = record[0]['stringValue']
        ticket_type = record[1]['stringValue']
        # Handle different price formats
        price_field = record[2]
        if 'doubleValue' in price_field:
            price = price_field['doubleValue']
        elif 'stringValue' in price_field:
            price = float(price_field['stringValue'])
        else:
            price = 0.0
        first_name = record[3]['stringValue']
        last_name = record[4]['stringValue']
        print(f"  • {ticket_number} ({ticket_type}) - ${price:.2f} - {first_name} {last_name}")
    
    # Test 4: Sample upgrade order data
    print("\n⬆️  Sample Upgrade Order Data:")
    upgrade_sql = """
    SELECT uo.confirmation_code, uo.upgrade_tier, uo.status, uo.total_amount, c.first_name, c.last_name
    FROM upgrade_orders uo
    JOIN customers c ON uo.customer_id = c.id
    LIMIT 3;
    """
    response = execute_sql(upgrade_sql)
    
    for record in response['records']:
        confirmation_code = record[0]['stringValue']
        upgrade_tier = record[1]['stringValue']
        status = record[2]['stringValue']
        # Handle different amount formats
        amount_field = record[3]
        if 'doubleValue' in amount_field:
            amount = amount_field['doubleValue']
        elif 'stringValue' in amount_field:
            amount = float(amount_field['stringValue'])
        else:
            amount = 0.0
        first_name = record[4]['stringValue']
        last_name = record[5]['stringValue']
        print(f"  • {confirmation_code} - {upgrade_tier} ({status}) - ${amount:.2f} - {first_name} {last_name}")
    
    # Test 5: Complex join query to verify relationships
    print("\n🔗 Testing Table Relationships:")
    relationship_sql = """
    SELECT 
        c.email,
        COUNT(t.id) as ticket_count,
        COUNT(uo.id) as upgrade_count
    FROM customers c
    LEFT JOIN tickets t ON c.id = t.customer_id
    LEFT JOIN upgrade_orders uo ON t.id = uo.ticket_id
    GROUP BY c.id, c.email
    ORDER BY c.email
    LIMIT 5;
    """
    response = execute_sql(relationship_sql)
    
    for record in response['records']:
        email = record[0]['stringValue']
        ticket_count = record[1]['longValue']
        upgrade_count = record[2]['longValue']
        print(f"  • {email}: {ticket_count} tickets, {upgrade_count} upgrades")
    
    print("\n" + "=" * 50)
    print("✅ Real database data verification completed!")
    print("🎉 Aurora PostgreSQL database is populated with sample data")
    return True

def main():
    """Main function"""
    # Load environment variables from .env file if it exists
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    try:
        success = test_database_data()
        if success:
            print("\n📋 Next Steps:")
            print("1. ✅ Task 2.1: Database schema - COMPLETE")
            print("2. ✅ Task 2.3: Python data models - COMPLETE")
            print("3. 🔄 Ready for Task 3.1: AgentCore development environment")
            return 0
        else:
            print("\n❌ Database data verification failed!")
            return 1
    except Exception as e:
        print(f"\n❌ Error testing database: {e}")
        return 1

if __name__ == "__main__":
    exit(main())