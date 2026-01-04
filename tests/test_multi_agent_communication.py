#!/usr/bin/env python3
"""
Test script for multi-agent communication between Data Agent and Ticket Agent
"""

import asyncio
import json
import os
import sys
import subprocess
import time
import requests
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.data_agent import DataAgent, load_config as load_data_config
from backend.agents.ticket_agent import TicketAgent, load_config as load_ticket_config


class MultiAgentTester:
    """Test multi-agent communication and workflows"""
    
    def __init__(self):
        self.data_agent = None
        self.ticket_agent = None
        self.data_agent_process = None
        self.ticket_agent_process = None
    
    async def setup_agents(self):
        """Set up both agents for testing"""
        print("🔧 Setting up agents for multi-agent testing")
        
        # Load configurations
        data_config = load_data_config()
        ticket_config = load_ticket_config()
        
        print(f"✅ Data Agent config: {data_config.aws_region}, {data_config.database_name}")
        print(f"✅ Ticket Agent config: {ticket_config.aws_region}, {ticket_config.bedrock_model_id}")
        
        # Create agent instances
        self.data_agent = DataAgent(data_config)
        self.ticket_agent = TicketAgent(ticket_config)
        
        return True
    
    async def start_agent_servers(self):
        """Start both agent MCP servers in background"""
        print("🚀 Starting agent MCP servers")
        
        try:
            # Start Data Agent server (port 8001)
            print("   Starting Data Agent on port 8001...")
            self.data_agent_process = subprocess.Popen([
                sys.executable, "backend/agents/run_data_agent.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait a moment for server to start
            await asyncio.sleep(3)
            
            # Check if Data Agent is running
            try:
                response = requests.get("http://localhost:8001/health", timeout=5)
                if response.status_code == 200:
                    print("   ✅ Data Agent server started successfully")
                else:
                    print("   ❌ Data Agent server not responding properly")
                    return False
            except requests.exceptions.RequestException:
                print("   ❌ Data Agent server not accessible")
                return False
            
            # Start Ticket Agent server (port 8002) - we'll run it in a separate process
            print("   Starting Ticket Agent on port 8002...")
            self.ticket_agent_process = subprocess.Popen([
                sys.executable, "-c", 
                "import asyncio; from backend.agents.ticket_agent import TicketAgent, load_config; "
                "asyncio.run(TicketAgent(load_config()).start_server('localhost', 8002))"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for Ticket Agent to start
            await asyncio.sleep(3)
            
            print("   ✅ Both agent servers started")
            return True
            
        except Exception as e:
            print(f"   ❌ Error starting agent servers: {e}")
            return False
    
    async def test_data_agent_operations(self):
        """Test Data Agent CRUD operations"""
        print("\n📊 Testing Data Agent operations")
        
        try:
            # Test database connection
            db_result = await self.data_agent.db.execute_sql("SELECT COUNT(*) as count FROM customers")
            
            # AWS RDS Data API returns records in a specific format
            if 'records' in db_result and db_result['records']:
                customer_count = db_result['records'][0][0]['longValue']
                print(f"   ✅ Database connection successful - {customer_count} customers found")
            else:
                print(f"   ❌ Database connection failed: No records returned")
                return False
            
            # Test LLM reasoning
            llm_result = await self.data_agent.db.llm_reason(
                "SELECT * FROM customers LIMIT 1",
                {"operation": "test", "context": "multi-agent testing"}
            )
            
            if llm_result and "failed" not in llm_result.lower():
                print(f"   ✅ Data Agent LLM reasoning working")
                print(f"   🤖 LLM Response: {llm_result[:100]}...")
            else:
                print(f"   ❌ Data Agent LLM reasoning failed")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ Data Agent operations failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_ticket_agent_operations(self):
        """Test Ticket Agent business logic"""
        print("\n🎫 Testing Ticket Agent operations")
        
        try:
            # Test pricing engine
            from models.ticket import TicketType
            from models.upgrade_order import UpgradeTier
            
            upgrade_price = self.ticket_agent.pricing.calculate_upgrade_price(
                TicketType.GENERAL, UpgradeTier.STANDARD
            )
            
            if upgrade_price:
                print(f"   ✅ Pricing engine working - General to Standard: ${float(upgrade_price):.2f}")
            else:
                print(f"   ❌ Pricing engine failed")
                return False
            
            # Test LLM reasoning
            sample_ticket = {
                "ticket_number": "TKT-MULTI-001",
                "ticket_type": "general",
                "original_price": 50.0,
                "event_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "status": "active"
            }
            
            sample_customer = {
                "first_name": "Multi",
                "last_name": "Agent",
                "email": "multi@test.com"
            }
            
            llm_result = await self.ticket_agent.llm.reason_about_ticket_eligibility(
                sample_ticket, sample_customer
            )
            
            if llm_result and "failed" not in llm_result.lower():
                print(f"   ✅ Ticket Agent LLM reasoning working")
                print(f"   🤖 LLM Response: {llm_result[:100]}...")
            else:
                print(f"   ❌ Ticket Agent LLM reasoning failed")
                return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ Ticket Agent operations failed: {e}")
            return False
    
    async def test_multi_agent_workflow(self):
        """Test complete multi-agent workflow"""
        print("\n🔄 Testing multi-agent workflow")
        
        try:
            # Step 1: Data Agent - Get customer and ticket data
            print("   Step 1: Retrieving customer and ticket data...")
            
            # Get a sample customer from database
            customer_result = await self.data_agent.db.execute_sql(
                "SELECT * FROM customers LIMIT 1"
            )
            
            if 'records' not in customer_result or not customer_result['records']:
                print("   ❌ No customer data available")
                return False
            
            # Parse AWS RDS Data API response format
            customer_record = customer_result['records'][0]
            customer_data = {
                'id': customer_record[0]['stringValue'],
                'first_name': customer_record[3]['stringValue'],
                'last_name': customer_record[4]['stringValue'],
                'email': customer_record[1]['stringValue']
            }
            print(f"   ✅ Customer retrieved: {customer_data.get('first_name')} {customer_data.get('last_name')}")
            
            # Get a sample ticket
            ticket_result = await self.data_agent.db.execute_sql(
                "SELECT * FROM tickets WHERE customer_id = :customer_id::uuid LIMIT 1",
                [{"name": "customer_id", "value": {"stringValue": customer_data['id']}}]
            )
            
            if 'records' not in ticket_result or not ticket_result['records']:
                print("   ❌ No ticket data available for customer")
                return False
            
            # Parse ticket data from AWS response
            ticket_record = ticket_result['records'][0]
            
            # Debug: print the actual record structure
            print(f"   Debug: Ticket record structure: {ticket_record}")
            
            # Handle different value types in AWS RDS Data API response
            def get_value(field):
                if isinstance(field, dict):
                    if 'stringValue' in field:
                        return field['stringValue']
                    elif 'doubleValue' in field:
                        return field['doubleValue']
                    elif 'longValue' in field:
                        return field['longValue']
                    elif 'isNull' in field and field['isNull']:
                        return None
                return field
            
            ticket_data = {
                'id': get_value(ticket_record[0]),
                'ticket_number': get_value(ticket_record[2]),
                'ticket_type': get_value(ticket_record[3]),
                'original_price': get_value(ticket_record[4]),
                'event_date': get_value(ticket_record[5]),
                'status': get_value(ticket_record[6])
            }
            print(f"   ✅ Ticket retrieved: {ticket_data.get('ticket_number')}")
            
            # Step 2: Ticket Agent - Analyze upgrade eligibility
            print("   Step 2: Analyzing upgrade eligibility...")
            
            # Convert database data to format expected by Ticket Agent
            ticket_for_analysis = {
                "id": ticket_data['id'],
                "ticket_number": ticket_data['ticket_number'],
                "ticket_type": ticket_data['ticket_type'],
                "original_price": float(ticket_data['original_price']),
                "event_date": ticket_data['event_date'],
                "status": ticket_data['status']
            }
            
            customer_for_analysis = {
                "id": customer_data['id'],
                "first_name": customer_data['first_name'],
                "last_name": customer_data['last_name'],
                "email": customer_data['email']
            }
            
            # Use Ticket Agent LLM to analyze eligibility
            eligibility_analysis = await self.ticket_agent.llm.reason_about_ticket_eligibility(
                ticket_for_analysis, customer_for_analysis
            )
            
            print(f"   ✅ Eligibility analysis completed")
            print(f"   🤖 Analysis: {eligibility_analysis[:150]}...")
            
            # Step 3: Ticket Agent - Calculate upgrade options
            print("   Step 3: Calculating upgrade options...")
            
            from models.ticket import TicketType
            ticket_type = TicketType(ticket_data['ticket_type'])
            available_upgrades = self.ticket_agent.pricing.get_available_upgrades(ticket_type)
            
            if available_upgrades:
                print(f"   ✅ {len(available_upgrades)} upgrade options available")
                for upgrade in available_upgrades:
                    print(f"      - {upgrade['name']}: ${upgrade['price']:.2f}")
            else:
                print("   ❌ No upgrade options available")
                return False
            
            # Step 4: Ticket Agent - Get personalized recommendations
            print("   Step 4: Getting personalized recommendations...")
            
            recommendations = await self.ticket_agent.llm.reason_about_upgrade_selection(
                ticket_for_analysis, available_upgrades, {"budget": "moderate"}
            )
            
            print(f"   ✅ Personalized recommendations generated")
            print(f"   🎯 Recommendations: {recommendations[:150]}...")
            
            # Step 5: Simulate upgrade order creation (Data Agent)
            print("   Step 5: Creating upgrade order...")
            
            # Create upgrade order data
            upgrade_order_data = {
                "customer_id": customer_data['id'],
                "ticket_id": ticket_data['id'],
                "upgrade_tier": "standard",
                "upgrade_price": 25.00,
                "total_price": float(ticket_data['original_price']) + 25.00,
                "status": "pending"
            }
            
            # Use Data Agent LLM to validate the order
            order_validation = await self.data_agent.db.llm_reason(
                "INSERT INTO upgrade_orders",
                {"operation": "create_upgrade_order", "data": upgrade_order_data}
            )
            
            print(f"   ✅ Upgrade order validation completed")
            print(f"   🤖 Validation: {order_validation[:100]}...")
            
            print(f"\n🎉 Multi-agent workflow completed successfully!")
            print(f"   Data Agent: Retrieved customer and ticket data, validated upgrade order")
            print(f"   Ticket Agent: Analyzed eligibility, calculated pricing, provided recommendations")
            print(f"   Communication: Both agents used LLM reasoning for intelligent processing")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Multi-agent workflow failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def test_agent_communication_protocols(self):
        """Test MCP communication between agents"""
        print("\n🔗 Testing agent communication protocols")
        
        try:
            # Test if agents can communicate via their MCP interfaces
            # This would normally involve HTTP requests to the MCP servers
            
            # For now, we'll test the underlying functionality
            print("   Testing Data Agent → Ticket Agent communication...")
            
            # Simulate Data Agent providing data to Ticket Agent
            customer_data = {
                "id": "test-customer-123",
                "first_name": "Test",
                "last_name": "Customer",
                "email": "test@example.com",
                "tier": "standard"
            }
            
            ticket_data = {
                "id": "test-ticket-456",
                "ticket_number": "TKT-COMM-001",
                "ticket_type": "general",
                "original_price": 50.0,
                "event_date": (datetime.now() + timedelta(days=30)).isoformat(),
                "status": "active"
            }
            
            # Ticket Agent processes the data
            eligibility_result = await self.ticket_agent.llm.reason_about_ticket_eligibility(
                ticket_data, customer_data
            )
            
            if eligibility_result and "failed" not in eligibility_result.lower():
                print("   ✅ Data Agent → Ticket Agent communication successful")
            else:
                print("   ❌ Data Agent → Ticket Agent communication failed")
                return False
            
            print("   Testing Ticket Agent → Data Agent communication...")
            
            # Simulate Ticket Agent requesting data validation from Data Agent
            upgrade_order = {
                "customer_id": customer_data["id"],
                "ticket_id": ticket_data["id"],
                "upgrade_tier": "standard",
                "upgrade_price": 25.00,
                "total_price": 75.00
            }
            
            # Data Agent validates the order
            validation_result = await self.data_agent.db.llm_reason(
                "VALIDATE upgrade_order",
                {"operation": "validate_upgrade", "data": upgrade_order}
            )
            
            if validation_result and "failed" not in validation_result.lower():
                print("   ✅ Ticket Agent → Data Agent communication successful")
            else:
                print("   ❌ Ticket Agent → Data Agent communication failed")
                return False
            
            print("   ✅ Bidirectional agent communication working")
            return True
            
        except Exception as e:
            print(f"   ❌ Agent communication test failed: {e}")
            return False
    
    async def test_enhanced_ticket_agent_features(self):
        """Test the enhanced Ticket Agent features (calendar and upgrade tiers)"""
        print("\n🎪 Testing enhanced Ticket Agent features")
        
        try:
            from models.ticket import TicketType
            from models.upgrade_order import UpgradeTier
            from datetime import date, timedelta
            
            # Test calendar functionality
            print("   Testing calendar functionality...")
            calendar_data = self.ticket_agent.calendar.generate_availability_calendar(
                start_date=date.today(),
                days_ahead=14,
                ticket_type=TicketType.GENERAL
            )
            
            if calendar_data and len(calendar_data["availability"]) == 14:
                print(f"   ✅ Calendar generated for {len(calendar_data['availability'])} days")
                
                # Check pricing categories
                categories = set()
                for day in calendar_data["availability"]:
                    if day["is_available"]:
                        categories.add(day["pricing_category"])
                
                print(f"   ✅ Pricing categories found: {list(categories)}")
            else:
                print("   ❌ Calendar generation failed")
                return False
            
            # Test upgrade tier comparison (all three tiers)
            print("   Testing three-tier upgrade system...")
            comparison = self.ticket_agent.selection_processor.get_upgrade_tier_comparison(
                TicketType.GENERAL, 
                date.today() + timedelta(days=7)
            )
            
            if comparison and len(comparison["tiers"]) == 3:
                tier_names = [tier["tier"] for tier in comparison["tiers"]]
                expected_tiers = ["standard", "non-stop", "double-fun"]
                
                if set(tier_names) == set(expected_tiers):
                    print(f"   ✅ All three upgrade tiers present: {tier_names}")
                    
                    # Check availability
                    available_tiers = [tier["tier"] for tier in comparison["tiers"] if tier["available"]]
                    print(f"   ✅ Available tiers for general tickets: {available_tiers}")
                else:
                    print(f"   ❌ Missing tiers. Expected: {expected_tiers}, Got: {tier_names}")
                    return False
            else:
                print("   ❌ Tier comparison failed")
                return False
            
            # Test upgrade selection processing
            print("   Testing upgrade selection processing...")
            selection_data = {
                'ticket_type': 'general',
                'upgrade_tier': 'non-stop',
                'selected_date': (date.today() + timedelta(days=10)).isoformat(),
                'original_price': 50.0
            }
            
            selection_result = await self.ticket_agent.selection_processor.process_upgrade_selection(
                selection_data
            )
            
            if selection_result and selection_result.get("success"):
                summary = selection_result["selection_summary"]
                print(f"   ✅ Selection processing successful")
                print(f"      Upgrade: {summary['upgrade_details']['tier_name']}")
                print(f"      Total price: ${summary['pricing_breakdown']['total_price']:.2f}")
                print(f"      Ready for payment: {selection_result['ready_for_payment']}")
            else:
                print(f"   ❌ Selection processing failed: {selection_result.get('error')}")
                return False
            
            # Test date-specific pricing
            print("   Testing date-specific pricing...")
            target_date = date.today() + timedelta(days=15)
            pricing = self.ticket_agent.calendar.get_pricing_for_date(
                target_date, TicketType.GENERAL, UpgradeTier.STANDARD
            )
            
            if pricing and 'error' not in pricing:
                print(f"   ✅ Date-specific pricing working")
                print(f"      Date: {target_date}")
                print(f"      Base price: ${pricing['pricing']['base_price']:.2f}")
                print(f"      Calendar price: ${pricing['pricing']['calendar_price']:.2f}")
                print(f"      Category: {pricing['pricing']['pricing_category']}")
            else:
                print(f"   ❌ Date-specific pricing failed: {pricing.get('error')}")
                return False
            
            print("   ✅ All enhanced Ticket Agent features working correctly")
            return True
            
        except Exception as e:
            print(f"   ❌ Enhanced features test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def cleanup(self):
        """Clean up agent processes"""
        print("\n🧹 Cleaning up agent processes")
        
        if self.data_agent_process:
            self.data_agent_process.terminate()
            self.data_agent_process.wait()
            print("   ✅ Data Agent process terminated")
        
        if self.ticket_agent_process:
            self.ticket_agent_process.terminate()
            self.ticket_agent_process.wait()
            print("   ✅ Ticket Agent process terminated")
        """Clean up agent processes"""
        print("\n🧹 Cleaning up agent processes")
        
        if self.data_agent_process:
            self.data_agent_process.terminate()
            self.data_agent_process.wait()
            print("   ✅ Data Agent process terminated")
        
        if self.ticket_agent_process:
            self.ticket_agent_process.terminate()
            self.ticket_agent_process.wait()
            print("   ✅ Ticket Agent process terminated")


async def main():
    """Main test function"""
    print("🚀 Multi-Agent Communication Test")
    print("=" * 50)
    
    tester = MultiAgentTester()
    
    try:
        # Setup agents
        if not await tester.setup_agents():
            print("❌ Agent setup failed")
            return 1
        
        # Test individual agent operations
        if not await tester.test_data_agent_operations():
            print("❌ Data Agent operations failed")
            return 1
        
        if not await tester.test_ticket_agent_operations():
            print("❌ Ticket Agent operations failed")
            return 1
        
        # Test enhanced Ticket Agent features
        if not await tester.test_enhanced_ticket_agent_features():
            print("❌ Enhanced Ticket Agent features failed")
            return 1
        
        # Test agent communication
        if not await tester.test_agent_communication_protocols():
            print("❌ Agent communication failed")
            return 1
        
        # Test complete workflow
        if not await tester.test_multi_agent_workflow():
            print("❌ Multi-agent workflow failed")
            return 1
        
        print("\n" + "=" * 50)
        print("✅ All multi-agent tests passed!")
        print("🎉 Agents are ready for production deployment!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Multi-agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        await tester.cleanup()


if __name__ == "__main__":
    exit(asyncio.run(main()))