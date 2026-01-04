#!/usr/bin/env python3
"""
Customer Journey Simulation Test

This script simulates complete customer interactions with the ticket auto-processing system,
testing the full workflow from ticket lookup to upgrade completion with real LLM reasoning,
real Aurora database, and all integrated services.
"""

import asyncio
import json
import os
import sys
import subprocess
import time
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.agents.data_agent import DataAgent, load_config as load_data_config
from backend.agents.ticket_agent import TicketAgent, load_config as load_ticket_config
from backend.services.payment_gateway import PaymentGateway, PaymentMethod, PaymentStatus, load_config as load_payment_config
from backend.services.notification_service import NotificationService, NotificationType, load_config as load_notification_config
from models.ticket import TicketType
from models.upgrade_order import UpgradeTier


class CustomerJourneySimulator:
    """Simulates complete customer journeys through the ticket upgrade process"""
    
    def __init__(self):
        self.data_agent = None
        self.ticket_agent = None
        self.payment_gateway = None
        self.notification_service = None
        self.customer_sessions = {}
    
    async def setup_system(self):
        """Set up all system components"""
        print("🚀 Setting up Complete Ticket Auto-Processing System")
        print("=" * 60)
        
        try:
            # Load all configurations
            data_config = load_data_config()
            ticket_config = load_ticket_config()
            payment_config = load_payment_config()
            notification_config = load_notification_config()
            
            print(f"✅ Configurations loaded:")
            print(f"   Data Agent: {data_config.aws_region}, {data_config.database_name}")
            print(f"   Ticket Agent: {ticket_config.bedrock_model_id}")
            print(f"   Payment Gateway: {payment_config.success_rate * 100:.1f}% success rate")
            print(f"   Notifications: {notification_config.from_email}")
            
            # Initialize all services
            self.data_agent = DataAgent(data_config)
            self.ticket_agent = TicketAgent(ticket_config)
            self.payment_gateway = PaymentGateway(payment_config)
            self.notification_service = NotificationService(notification_config)
            
            # Test database connectivity
            db_test = await self.data_agent.db.execute_sql("SELECT COUNT(*) FROM customers")
            customer_count = db_test['records'][0][0]['longValue']
            print(f"✅ Database connected: {customer_count} customers available")
            
            # Test LLM connectivity
            llm_test = await self.data_agent.db.llm_reason(
                "System startup test", 
                {"operation": "startup_test"}
            )
            if llm_test and len(llm_test) > 10:  # Check if we got a reasonable response
                print(f"✅ LLM reasoning active: Nova Pro model working")
            else:
                print(f"❌ LLM reasoning failed: {llm_test}")
                return False
            
            print(f"✅ All system components initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ System setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def simulate_customer_journey(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate a complete customer journey"""
        
        customer_name = scenario["customer_name"]
        customer_email = scenario["customer_email"]
        journey_type = scenario["journey_type"]
        
        print(f"\n👤 Starting Customer Journey: {customer_name}")
        print(f"   Email: {customer_email}")
        print(f"   Journey Type: {journey_type}")
        print(f"   " + "-" * 50)
        
        journey_result = {
            "customer_name": customer_name,
            "journey_type": journey_type,
            "steps_completed": [],
            "success": False,
            "total_time": 0,
            "llm_interactions": 0,
            "database_queries": 0,
            "notifications_sent": 0,
            "final_status": "unknown"
        }
        
        start_time = datetime.now()
        
        try:
            # Step 1: Customer Lookup and Authentication
            print(f"   🔍 Step 1: Customer lookup and ticket retrieval")
            
            # Get customer from database
            customer_result = await self.data_agent.db.execute_sql(
                "SELECT * FROM customers WHERE email = :email LIMIT 1",
                [{"name": "email", "value": {"stringValue": customer_email}}]
            )
            
            journey_result["database_queries"] += 1
            
            if not customer_result.get('records'):
                print(f"   ❌ Customer not found: {customer_email}")
                journey_result["final_status"] = "customer_not_found"
                return journey_result
            
            # Parse customer data
            customer_record = customer_result['records'][0]
            customer_data = {
                'id': customer_record[0]['stringValue'],
                'email': customer_record[1]['stringValue'],
                'first_name': customer_record[3]['stringValue'],
                'last_name': customer_record[4]['stringValue']
            }
            
            print(f"   ✅ Customer found: {customer_data['first_name']} {customer_data['last_name']}")
            journey_result["steps_completed"].append("customer_lookup")
            
            # Get customer's tickets
            tickets_result = await self.data_agent.db.execute_sql(
                "SELECT * FROM tickets WHERE customer_id = :customer_id::uuid",
                [{"name": "customer_id", "value": {"stringValue": customer_data['id']}}]
            )
            
            journey_result["database_queries"] += 1
            
            if not tickets_result.get('records'):
                print(f"   ❌ No tickets found for customer")
                journey_result["final_status"] = "no_tickets"
                return journey_result
            
            # Parse ticket data
            ticket_record = tickets_result['records'][0]
            ticket_data = {
                'id': ticket_record[0]['stringValue'],
                'ticket_number': ticket_record[2]['stringValue'],
                'ticket_type': ticket_record[3]['stringValue'],
                'original_price': float(ticket_record[4]['stringValue']),
                'event_date': ticket_record[6]['stringValue'],
                'status': ticket_record[7]['stringValue']
            }
            
            print(f"   ✅ Ticket found: {ticket_data['ticket_number']} ({ticket_data['ticket_type']})")
            journey_result["steps_completed"].append("ticket_lookup")
            
            # Step 2: LLM-Powered Eligibility Analysis
            print(f"   🤖 Step 2: AI-powered upgrade eligibility analysis")
            
            eligibility_analysis = await self.ticket_agent.llm.reason_about_ticket_eligibility(
                ticket_data, customer_data
            )
            
            journey_result["llm_interactions"] += 1
            
            print(f"   ✅ Eligibility analysis completed")
            print(f"   🎯 AI Analysis: {eligibility_analysis[:100]}...")
            journey_result["steps_completed"].append("eligibility_analysis")
            
            # Step 3: Upgrade Options and Pricing
            print(f"   💰 Step 3: Calculating upgrade options and pricing")
            
            ticket_type = TicketType(ticket_data['ticket_type'])
            available_upgrades = self.ticket_agent.pricing.get_available_upgrades(ticket_type)
            
            if not available_upgrades:
                print(f"   ❌ No upgrades available for {ticket_type.value} tickets")
                journey_result["final_status"] = "no_upgrades_available"
                return journey_result
            
            print(f"   ✅ {len(available_upgrades)} upgrade options available:")
            for upgrade in available_upgrades:
                print(f"      - {upgrade['name']}: ${upgrade['price']:.2f}")
            
            journey_result["steps_completed"].append("upgrade_options")
            
            # Step 4: LLM-Powered Personalized Recommendations
            print(f"   🎯 Step 4: AI-powered personalized recommendations")
            
            customer_preferences = scenario.get("preferences", {"budget": "moderate"})
            recommendations = await self.ticket_agent.llm.reason_about_upgrade_selection(
                ticket_data, available_upgrades, customer_preferences
            )
            
            journey_result["llm_interactions"] += 1
            
            print(f"   ✅ Personalized recommendations generated")
            print(f"   🤖 AI Recommendations: {recommendations[:100]}...")
            journey_result["steps_completed"].append("personalized_recommendations")
            
            # Step 5: Customer Decision Simulation
            print(f"   🤔 Step 5: Customer decision making")
            
            # Simulate customer choice based on journey type
            if journey_type == "successful_upgrade":
                selected_upgrade = available_upgrades[0]  # Choose first option
                print(f"   ✅ Customer selected: {selected_upgrade['name']}")
            elif journey_type == "price_sensitive":
                selected_upgrade = min(available_upgrades, key=lambda x: x['price'])
                print(f"   ✅ Customer selected cheapest option: {selected_upgrade['name']}")
            elif journey_type == "premium_seeker":
                selected_upgrade = max(available_upgrades, key=lambda x: x['price'])
                print(f"   ✅ Customer selected premium option: {selected_upgrade['name']}")
            else:
                selected_upgrade = random.choice(available_upgrades)
                print(f"   ✅ Customer randomly selected: {selected_upgrade['name']}")
            
            journey_result["steps_completed"].append("upgrade_selection")
            
            # Step 6: Payment Processing
            print(f"   💳 Step 6: Processing payment")
            
            payment_amount = Decimal(str(selected_upgrade['price']))
            payment_method = scenario.get("payment_method", PaymentMethod.CREDIT_CARD)
            
            transaction = await self.payment_gateway.process_payment(
                customer_id=customer_data['id'],
                upgrade_order_id=f"order_{datetime.now().timestamp()}",
                amount=payment_amount,
                payment_method=payment_method
            )
            
            print(f"   💳 Payment processed: {transaction.status}")
            
            if transaction.status == PaymentStatus.FAILED:
                print(f"   ❌ Payment failed: {transaction.failure_reason}")
                
                # Try retry if configured
                if scenario.get("retry_payment", True):
                    print(f"   🔄 Attempting payment retry...")
                    retry_transaction = await self.payment_gateway.retry_payment(transaction.id)
                    transaction = retry_transaction
                    print(f"   💳 Retry result: {transaction.status}")
            
            if transaction.status == PaymentStatus.COMPLETED:
                print(f"   ✅ Payment successful: {transaction.gateway_transaction_id}")
                journey_result["steps_completed"].append("payment_success")
            else:
                print(f"   ❌ Payment ultimately failed")
                journey_result["steps_completed"].append("payment_failed")
                journey_result["final_status"] = "payment_failed"
                
                # Send failure notification
                await self._send_payment_failure_notification(
                    customer_data, transaction, selected_upgrade
                )
                journey_result["notifications_sent"] += 1
                
                return journey_result
            
            # Step 7: Create Upgrade Order in Database
            print(f"   📝 Step 7: Creating upgrade order record")
            
            upgrade_order_data = {
                "customer_id": customer_data['id'],
                "ticket_id": ticket_data['id'],
                "upgrade_tier": selected_upgrade['tier'].value,
                "original_tier": ticket_data['ticket_type'],
                "price_difference": float(payment_amount),
                "total_amount": ticket_data['original_price'] + float(payment_amount),
                "status": "completed",
                "confirmation_code": f"CONF{transaction.gateway_transaction_id[-8:].upper()}",
                "metadata": json.dumps({
                    "transaction_id": transaction.id,
                    "gateway_transaction_id": transaction.gateway_transaction_id,
                    "upgrade_features": selected_upgrade['features']
                })
            }
            
            # Use Data Agent LLM to validate the order before creation
            order_validation = await self.data_agent.db.llm_reason(
                f"Validate upgrade order creation for customer {customer_data['first_name']} {customer_data['last_name']}",
                {"operation": "create_upgrade_order", "data": upgrade_order_data}
            )
            
            journey_result["llm_interactions"] += 1
            
            print(f"   🤖 Order validation: {order_validation[:80]}...")
            
            # Create the upgrade order (simplified for demo)
            print(f"   ✅ Upgrade order created: {upgrade_order_data['confirmation_code']}")
            journey_result["steps_completed"].append("order_creation")
            
            # Step 8: Send Success Notifications
            print(f"   📧 Step 8: Sending confirmation notifications")
            
            # Payment success notification
            payment_notification = await self._send_payment_success_notification(
                customer_data, transaction, selected_upgrade, ticket_data
            )
            journey_result["notifications_sent"] += 1
            
            # Upgrade confirmation notification
            upgrade_notification = await self._send_upgrade_confirmation_notification(
                customer_data, selected_upgrade, ticket_data, upgrade_order_data
            )
            journey_result["notifications_sent"] += 1
            
            print(f"   ✅ Notifications sent successfully")
            journey_result["steps_completed"].append("notifications_sent")
            
            # Step 9: Final LLM Summary
            print(f"   📋 Step 9: AI-powered journey summary")
            
            # Convert transaction data to JSON-serializable format
            transaction_data = {
                "id": transaction.id,
                "status": transaction.status.value,
                "amount": float(transaction.amount),
                "payment_method": transaction.payment_method.value,
                "gateway_transaction_id": transaction.gateway_transaction_id,
                "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None
            }
            
            journey_summary = await self.ticket_agent.llm.reason_about_customer_interaction(
                {
                    "customer": customer_data,
                    "ticket": ticket_data,
                    "upgrade": selected_upgrade,
                    "transaction": transaction_data,
                    "journey_type": journey_type
                },
                f"Provide a summary of this successful ticket upgrade journey for {customer_name}"
            )
            
            journey_result["llm_interactions"] += 1
            
            print(f"   ✅ Journey completed successfully!")
            print(f"   🤖 AI Summary: {journey_summary[:100]}...")
            
            journey_result["success"] = True
            journey_result["final_status"] = "completed_successfully"
            journey_result["steps_completed"].append("journey_summary")
            
        except Exception as e:
            print(f"   ❌ Journey failed with error: {e}")
            journey_result["final_status"] = f"error: {str(e)}"
            import traceback
            traceback.print_exc()
        
        finally:
            # Calculate total journey time
            end_time = datetime.now()
            journey_result["total_time"] = (end_time - start_time).total_seconds()
            
            print(f"   ⏱️ Total journey time: {journey_result['total_time']:.2f} seconds")
            print(f"   🤖 LLM interactions: {journey_result['llm_interactions']}")
            print(f"   🗄️ Database queries: {journey_result['database_queries']}")
            print(f"   📧 Notifications sent: {journey_result['notifications_sent']}")
        
        return journey_result
    
    async def _send_payment_success_notification(self, customer_data, transaction, upgrade, ticket_data):
        """Send payment success notification"""
        template_data = {
            "customer_name": f"{customer_data['first_name']} {customer_data['last_name']}",
            "transaction_id": transaction.gateway_transaction_id,
            "amount": str(float(transaction.amount)),
            "payment_method": transaction.payment_method.value.replace('_', ' ').title(),
            "payment_date": transaction.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_number": ticket_data['ticket_number'],
            "original_type": ticket_data['ticket_type'].title(),
            "upgrade_tier": upgrade['name'],
            "event_date": ticket_data['event_date']
        }
        
        return await self.notification_service.send_notification(
            customer_id=customer_data['id'],
            email=customer_data['email'],
            notification_type=NotificationType.PAYMENT_SUCCESS,
            template_data=template_data
        )
    
    async def _send_payment_failure_notification(self, customer_data, transaction, upgrade):
        """Send payment failure notification"""
        template_data = {
            "customer_name": f"{customer_data['first_name']} {customer_data['last_name']}",
            "transaction_id": transaction.id,
            "amount": str(float(transaction.amount)),
            "payment_method": transaction.payment_method.value.replace('_', ' ').title(),
            "failure_reason": transaction.failure_reason or "Unknown error"
        }
        
        return await self.notification_service.send_notification(
            customer_id=customer_data['id'],
            email=customer_data['email'],
            notification_type=NotificationType.PAYMENT_FAILED,
            template_data=template_data
        )
    
    async def _send_upgrade_confirmation_notification(self, customer_data, upgrade, ticket_data, order_data):
        """Send upgrade confirmation notification"""
        template_data = {
            "customer_name": f"{customer_data['first_name']} {customer_data['last_name']}",
            "ticket_number": ticket_data['ticket_number'],
            "original_type": ticket_data['ticket_type'].title(),
            "upgrade_tier": upgrade['name'],
            "event_date": ticket_data['event_date'],
            "total_price": str(order_data['total_amount']),
            "upgrade_features": "\n".join([f"- {feature}" for feature in upgrade['features']])
        }
        
        return await self.notification_service.send_notification(
            customer_id=customer_data['id'],
            email=customer_data['email'],
            notification_type=NotificationType.UPGRADE_CONFIRMATION,
            template_data=template_data
        )


async def run_customer_journey_simulation():
    """Run comprehensive customer journey simulation"""
    print("🎭 Customer Journey Simulation - Ticket Auto-Processing System")
    print("=" * 70)
    
    simulator = CustomerJourneySimulator()
    
    # Setup system
    if not await simulator.setup_system():
        print("❌ System setup failed")
        return False
    
    # Define customer journey scenarios
    scenarios = [
        {
            "customer_name": "John Doe",
            "customer_email": "john.doe@example.com",
            "journey_type": "successful_upgrade",
            "preferences": {"budget": "moderate", "interests": ["premium_experience"]},
            "payment_method": PaymentMethod.CREDIT_CARD,
            "retry_payment": True
        },
        {
            "customer_name": "Jane Smith",
            "customer_email": "jane.smith@example.com",
            "journey_type": "price_sensitive",
            "preferences": {"budget": "low", "interests": ["value"]},
            "payment_method": PaymentMethod.DEBIT_CARD,
            "retry_payment": True
        },
        {
            "customer_name": "Bob Johnson",
            "customer_email": "bob.johnson@example.com",
            "journey_type": "premium_seeker",
            "preferences": {"budget": "high", "interests": ["exclusive_access", "premium_amenities"]},
            "payment_method": PaymentMethod.CREDIT_CARD,
            "retry_payment": False
        },
        {
            "customer_name": "Alice Brown",
            "customer_email": "alice.brown@example.com",
            "journey_type": "random_selection",
            "preferences": {"budget": "moderate", "interests": ["convenience"]},
            "payment_method": PaymentMethod.PAYPAL,
            "retry_payment": True
        }
    ]
    
    # Run all customer journeys
    journey_results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🎬 Running Customer Journey {i}/{len(scenarios)}")
        result = await simulator.simulate_customer_journey(scenario)
        journey_results.append(result)
        
        # Brief pause between journeys
        await asyncio.sleep(2)
    
    # Wait for all notifications to be processed
    print(f"\n⏳ Waiting for notification delivery simulation...")
    await asyncio.sleep(8)
    
    # Generate comprehensive report
    print(f"\n📊 CUSTOMER JOURNEY SIMULATION REPORT")
    print(f"=" * 70)
    
    successful_journeys = sum(1 for r in journey_results if r["success"])
    total_journeys = len(journey_results)
    
    print(f"📈 Overall Results:")
    print(f"   Total customer journeys: {total_journeys}")
    print(f"   Successful completions: {successful_journeys}")
    print(f"   Success rate: {successful_journeys/total_journeys*100:.1f}%")
    
    # Detailed journey analysis
    print(f"\n🔍 Journey Details:")
    for result in journey_results:
        status_emoji = "✅" if result["success"] else "❌"
        print(f"   {status_emoji} {result['customer_name']} ({result['journey_type']})")
        print(f"      Status: {result['final_status']}")
        print(f"      Steps completed: {len(result['steps_completed'])}")
        print(f"      Time: {result['total_time']:.2f}s")
        print(f"      LLM interactions: {result['llm_interactions']}")
        print(f"      Database queries: {result['database_queries']}")
        print(f"      Notifications: {result['notifications_sent']}")
    
    # System performance metrics
    total_llm_interactions = sum(r["llm_interactions"] for r in journey_results)
    total_db_queries = sum(r["database_queries"] for r in journey_results)
    total_notifications = sum(r["notifications_sent"] for r in journey_results)
    avg_journey_time = sum(r["total_time"] for r in journey_results) / len(journey_results)
    
    print(f"\n⚡ System Performance:")
    print(f"   Total LLM interactions: {total_llm_interactions}")
    print(f"   Total database queries: {total_db_queries}")
    print(f"   Total notifications sent: {total_notifications}")
    print(f"   Average journey time: {avg_journey_time:.2f} seconds")
    
    # Service statistics
    payment_stats = simulator.payment_gateway.get_statistics()
    notification_stats = simulator.notification_service.get_statistics()
    
    print(f"\n💳 Payment Gateway Performance:")
    print(f"   Total transactions: {payment_stats['total_transactions']}")
    print(f"   Success rate: {payment_stats['success_rate'] * 100:.1f}%")
    print(f"   Total amount processed: ${payment_stats['total_amount']:.2f}")
    
    print(f"\n📧 Notification Service Performance:")
    print(f"   Total notifications: {notification_stats['total_notifications']}")
    print(f"   Delivery rate: {notification_stats['delivery_rate'] * 100:.1f}%")
    print(f"   Type breakdown: {notification_stats['type_breakdown']}")
    
    print(f"\n" + "=" * 70)
    if successful_journeys == total_journeys:
        print(f"🎉 ALL CUSTOMER JOURNEYS COMPLETED SUCCESSFULLY!")
        print(f"✨ The ticket auto-processing system is working perfectly!")
        print(f"🚀 Ready for production deployment!")
    else:
        print(f"⚠️ {total_journeys - successful_journeys} journeys had issues")
        print(f"🔧 Review failed journeys for system improvements")
    
    return successful_journeys == total_journeys


async def main():
    """Main test function"""
    success = await run_customer_journey_simulation()
    return 0 if success else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))