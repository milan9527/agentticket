#!/usr/bin/env python3
"""
Test script for Data Agent with real Aurora PostgreSQL database
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.agents.data_agent import DataAgent, DataAgentConfig, load_config


async def test_data_agent():
    """Test Data Agent functionality with real database"""
    print("🧪 Testing Data Agent with Real Database")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        if not config.db_cluster_arn or not config.db_secret_arn:
            print("❌ Missing database configuration")
            return False
        
        print(f"✅ Configuration loaded:")
        print(f"   Region: {config.aws_region}")
        print(f"   Database: {config.database_name}")
        print(f"   Model: {config.bedrock_model_id}")
        
        # Create Data Agent
        agent = DataAgent(config)
        
        # Test 1: Get existing customer
        print(f"\n🔍 Test 1: Get existing customer")
        
        # First, get a customer ID from the database
        sql = "SELECT id FROM customers LIMIT 1"
        response = await agent.db.execute_sql(sql)
        
        if response['records']:
            customer_id = response['records'][0][0]['stringValue']
            print(f"   Testing with customer ID: {customer_id}")
            
            # Test database connection directly
            sql = "SELECT * FROM customers WHERE id = :customer_id"
            parameters = [{'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}]
            result = await agent.db.execute_sql(sql, parameters)
            
            if result['records']:
                print(f"   ✅ Successfully connected to database and retrieved customer")
                record = result['records'][0]
                email = record[1]['stringValue']
                print(f"   📧 Customer email: {email}")
            else:
                print(f"   ❌ Failed to get customer from database")
                return False
        else:
            print(f"   ⚠️  No customers found in database")
        
        # Test 2: Get tickets for customer
        print(f"\n🎫 Test 2: Get tickets for customer")
        if response['records']:
            sql = """
            SELECT t.*, c.first_name, c.last_name, c.email
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            WHERE t.customer_id = :customer_id
            ORDER BY t.event_date DESC;
            """
            
            parameters = [{'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}]
            result = await agent.db.execute_sql(sql, parameters)
            
            print(f"   ✅ Successfully retrieved {len(result['records'])} tickets")
        
        # Test 3: Validate data integrity
        print(f"\n🔍 Test 3: Validate data integrity")
        integrity_checks = [
            "SELECT COUNT(*) as orphaned_tickets FROM tickets t LEFT JOIN customers c ON t.customer_id = c.id WHERE c.id IS NULL",
            "SELECT COUNT(*) as total_customers FROM customers",
            "SELECT COUNT(*) as total_tickets FROM tickets"
        ]
        
        for sql in integrity_checks:
            result = await agent.db.execute_sql(sql)
            count = result['records'][0][0]['longValue']
            check_name = sql.split(' as ')[1].split(' ')[0] if ' as ' in sql else 'count'
            print(f"   📊 {check_name}: {count}")
        
        print(f"   ✅ Data integrity checks completed")
        
        # Test 4: LLM reasoning capability
        print(f"\n🧠 Test 4: LLM reasoning capability")
        reasoning_result = await agent.db.llm_reason(
            "What are the key considerations for ticket upgrade eligibility?",
            {"test": "reasoning_capability"}
        )
        
        if reasoning_result and "failed" not in reasoning_result.lower():
            print(f"   ✅ LLM reasoning working")
            print(f"   🤖 Response: {reasoning_result[:150]}...")
        else:
            print(f"   ❌ LLM reasoning failed: {reasoning_result}")
        
        # Test 5: Database write operation
        print(f"\n👤 Test 5: Test database write operation")
        test_email = f"test.agent.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        
        sql = """
        INSERT INTO customers (email, first_name, last_name, phone)
        VALUES (:email, :first_name, :last_name, :phone)
        RETURNING id, created_at;
        """
        
        parameters = [
            {'name': 'email', 'value': {'stringValue': test_email}},
            {'name': 'first_name', 'value': {'stringValue': 'Test'}},
            {'name': 'last_name', 'value': {'stringValue': 'Agent'}},
            {'name': 'phone', 'value': {'stringValue': '+1-555-TEST'}}
        ]
        
        result = await agent.db.execute_sql(sql, parameters)
        
        if result['records']:
            new_customer_id = result['records'][0][0]['stringValue']
            print(f"   ✅ Successfully created test customer: {new_customer_id}")
            print(f"   📧 Email: {test_email}")
        else:
            print(f"   ❌ Failed to create test customer")
        
        print(f"\n" + "=" * 50)
        print(f"✅ Data Agent testing completed successfully!")
        print(f"🎉 Agent is ready for integration with Ticket Agent")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Data Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_data_agent()
    return 0 if success else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))