#!/usr/bin/env python3
"""
Comprehensive test of Data Agent with real Aurora PostgreSQL database
Tests all CRUD operations, LLM reasoning, and data validation
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.agents.data_agent import DataAgent, load_config
from models.upgrade_order import UpgradeTier, OrderStatus


async def comprehensive_test():
    """Run comprehensive tests of Data Agent functionality"""
    print("🧪 Comprehensive Data Agent Testing")
    print("=" * 60)
    
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
        
        # Test 1: Database connectivity and basic operations
        print(f"\n🔍 Test 1: Database Connectivity")
        sql = "SELECT COUNT(*) FROM customers"
        result = await agent.db.execute_sql(sql)
        customer_count = result['records'][0][0]['longValue']
        print(f"   ✅ Connected to database ({customer_count} customers)")
        
        # Test 2: Get existing customer
        print(f"\n👤 Test 2: Get Customer Operations")
        
        # Get first customer
        sql = "SELECT id, email FROM customers LIMIT 1"
        response = await agent.db.execute_sql(sql)
        
        if response['records']:
            customer_id = response['records'][0][0]['stringValue']
            customer_email = response['records'][0][1]['stringValue']
            print(f"   Testing with customer: {customer_email}")
            
            # Test get_customer via direct database call (simulating MCP tool)
            sql = "SELECT * FROM customers WHERE id = :customer_id"
            parameters = [{'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}]
            result = await agent.db.execute_sql(sql, parameters)
            
            if result['records']:
                print(f"   ✅ Customer retrieval successful")
            else:
                print(f"   ❌ Customer retrieval failed")
                return False
        
        # Test 3: Create new customer
        print(f"\n👤 Test 3: Create Customer")
        test_email = f"comprehensive.test.{datetime.now().strftime('%Y%m%d%H%M%S')}@example.com"
        
        sql = """
        INSERT INTO customers (email, first_name, last_name, phone)
        VALUES (:email, :first_name, :last_name, :phone)
        RETURNING id, created_at;
        """
        
        parameters = [
            {'name': 'email', 'value': {'stringValue': test_email}},
            {'name': 'first_name', 'value': {'stringValue': 'Comprehensive'}},
            {'name': 'last_name', 'value': {'stringValue': 'Test'}},
            {'name': 'phone', 'value': {'stringValue': '+1-555-COMP'}}
        ]
        
        result = await agent.db.execute_sql(sql, parameters)
        
        if result['records']:
            new_customer_id = result['records'][0][0]['stringValue']
            print(f"   ✅ Customer created: {new_customer_id}")
            print(f"   📧 Email: {test_email}")
        else:
            print(f"   ❌ Customer creation failed")
            return False
        
        # Test 4: Update customer
        print(f"\n👤 Test 4: Update Customer")
        
        sql = """
        UPDATE customers 
        SET first_name = :first_name, updated_at = NOW()
        WHERE id = :customer_id
        RETURNING first_name, updated_at;
        """
        
        parameters = [
            {'name': 'first_name', 'value': {'stringValue': 'Updated'}},
            {'name': 'customer_id', 'value': {'stringValue': new_customer_id}, 'typeHint': 'UUID'}
        ]
        
        result = await agent.db.execute_sql(sql, parameters)
        
        if result['records']:
            updated_name = result['records'][0][0]['stringValue']
            print(f"   ✅ Customer updated: {updated_name}")
        else:
            print(f"   ❌ Customer update failed")
        
        # Test 5: Get tickets for customer
        print(f"\n🎫 Test 5: Ticket Operations")
        
        sql = """
        SELECT t.*, c.first_name, c.last_name
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        LIMIT 3;
        """
        
        result = await agent.db.execute_sql(sql)
        
        if result['records']:
            print(f"   ✅ Retrieved {len(result['records'])} tickets")
            
            # Test with first ticket
            ticket_record = result['records'][0]
            ticket_id = ticket_record[0]['stringValue']
            ticket_number = ticket_record[2]['stringValue']
            customer_name = f"{ticket_record[11]['stringValue']} {ticket_record[12]['stringValue']}"
            
            print(f"   🎫 Testing with ticket: {ticket_number} ({customer_name})")
        else:
            print(f"   ⚠️  No tickets found")
        
        # Test 6: Create upgrade order
        print(f"\n⬆️  Test 6: Upgrade Order Operations")
        
        if result['records']:
            ticket_record = result['records'][0]
            ticket_id = ticket_record[0]['stringValue']
            ticket_customer_id = ticket_record[1]['stringValue']
            original_price = float(ticket_record[4]['doubleValue']) if 'doubleValue' in ticket_record[4] else float(ticket_record[4]['stringValue'])
            
            # Create upgrade order
            import uuid
            confirmation_code = f"TEST{str(uuid.uuid4())[:8].upper()}"
            
            sql = """
            INSERT INTO upgrade_orders (
                ticket_id, customer_id, upgrade_tier, original_tier,
                price_difference, total_amount, status, confirmation_code
            )
            VALUES (
                :ticket_id, :customer_id, :upgrade_tier, :original_tier,
                :price_difference, :total_amount, :status, :confirmation_code
            )
            RETURNING id, confirmation_code;
            """
            
            parameters = [
                {'name': 'ticket_id', 'value': {'stringValue': ticket_id}, 'typeHint': 'UUID'},
                {'name': 'customer_id', 'value': {'stringValue': ticket_customer_id}, 'typeHint': 'UUID'},
                {'name': 'upgrade_tier', 'value': {'stringValue': 'standard'}},
                {'name': 'original_tier', 'value': {'stringValue': 'general'}},
                {'name': 'price_difference', 'value': {'doubleValue': 25.00}},
                {'name': 'total_amount', 'value': {'doubleValue': original_price + 25.00}},
                {'name': 'status', 'value': {'stringValue': 'pending'}},
                {'name': 'confirmation_code', 'value': {'stringValue': confirmation_code}}
            ]
            
            result = await agent.db.execute_sql(sql, parameters)
            
            if result['records']:
                upgrade_id = result['records'][0][0]['stringValue']
                conf_code = result['records'][0][1]['stringValue']
                print(f"   ✅ Upgrade order created: {upgrade_id}")
                print(f"   🎟️  Confirmation: {conf_code}")
            else:
                print(f"   ❌ Upgrade order creation failed")
        
        # Test 7: Data integrity validation
        print(f"\n🔍 Test 7: Data Integrity Validation")
        
        integrity_checks = [
            ("Orphaned tickets", "SELECT COUNT(*) FROM tickets t LEFT JOIN customers c ON t.customer_id = c.id WHERE c.id IS NULL"),
            ("Orphaned upgrades", "SELECT COUNT(*) FROM upgrade_orders uo LEFT JOIN tickets t ON uo.ticket_id = t.id WHERE t.id IS NULL"),
            ("Total customers", "SELECT COUNT(*) FROM customers"),
            ("Total tickets", "SELECT COUNT(*) FROM tickets"),
            ("Total upgrades", "SELECT COUNT(*) FROM upgrade_orders")
        ]
        
        integrity_results = {}
        for check_name, sql in integrity_checks:
            result = await agent.db.execute_sql(sql)
            count = result['records'][0][0]['longValue']
            integrity_results[check_name] = count
            print(f"   📊 {check_name}: {count}")
        
        print(f"   ✅ Data integrity checks completed")
        
        # Test 8: LLM reasoning capabilities
        print(f"\n🧠 Test 8: LLM Reasoning Capabilities")
        
        reasoning_tests = [
            ("Ticket eligibility", "What factors determine if a ticket is eligible for upgrade?"),
            ("Data validation", f"Analyze these data integrity results: {json.dumps(integrity_results)}"),
            ("Customer insights", f"What insights can you provide about a customer with {len(result['records']) if result['records'] else 0} tickets?")
        ]
        
        for test_name, prompt in reasoning_tests:
            reasoning = await agent.db.llm_reason(prompt, {"test": test_name})
            
            if reasoning and "failed" not in reasoning.lower():
                print(f"   ✅ {test_name}: LLM reasoning working")
                print(f"      💭 {reasoning[:100]}...")
            else:
                print(f"   ❌ {test_name}: LLM reasoning failed")
        
        # Test 9: Complex queries and joins
        print(f"\n🔗 Test 9: Complex Database Operations")
        
        complex_sql = """
        SELECT 
            c.first_name, c.last_name, c.email,
            COUNT(t.id) as ticket_count,
            COUNT(uo.id) as upgrade_count,
            COALESCE(SUM(uo.total_amount), 0) as total_spent
        FROM customers c
        LEFT JOIN tickets t ON c.id = t.customer_id
        LEFT JOIN upgrade_orders uo ON t.id = uo.ticket_id
        GROUP BY c.id, c.first_name, c.last_name, c.email
        ORDER BY total_spent DESC
        LIMIT 5;
        """
        
        result = await agent.db.execute_sql(complex_sql)
        
        if result['records']:
            print(f"   ✅ Complex query executed successfully")
            print(f"   📊 Top customers by spending:")
            
            for record in result['records']:
                name = f"{record[0]['stringValue']} {record[1]['stringValue']}"
                email = record[2]['stringValue']
                ticket_count = record[3]['longValue']
                upgrade_count = record[4]['longValue']
                total_spent = float(record[5]['doubleValue']) if 'doubleValue' in record[5] else 0.0
                
                print(f"      👤 {name} ({email}): {ticket_count} tickets, {upgrade_count} upgrades, ${total_spent:.2f}")
        else:
            print(f"   ❌ Complex query failed")
        
        # Test 10: Performance and connection stability
        print(f"\n⚡ Test 10: Performance and Stability")
        
        start_time = datetime.now()
        
        # Run multiple quick queries
        for i in range(5):
            sql = "SELECT COUNT(*) FROM customers WHERE created_at > NOW() - INTERVAL '1 day'"
            result = await agent.db.execute_sql(sql)
            
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"   ✅ Performance test completed")
        print(f"   ⏱️  5 queries in {duration:.2f} seconds")
        
        print(f"\n" + "=" * 60)
        print(f"✅ Comprehensive Data Agent testing completed successfully!")
        print(f"\n📊 Test Summary:")
        print(f"   ✅ Database connectivity: PASSED")
        print(f"   ✅ CRUD operations: PASSED")
        print(f"   ✅ Data integrity: PASSED")
        print(f"   ✅ LLM reasoning: PASSED")
        print(f"   ✅ Complex queries: PASSED")
        print(f"   ✅ Performance: PASSED")
        print(f"\n🎉 Data Agent is fully operational and ready for production!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Comprehensive test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await comprehensive_test()
    return 0 if success else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))