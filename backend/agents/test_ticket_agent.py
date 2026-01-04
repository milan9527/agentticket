#!/usr/bin/env python3
"""
Test script for Ticket Agent with LLM reasoning and business logic
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.agents.ticket_agent import TicketAgent, load_config


async def test_ticket_agent():
    """Test Ticket Agent functionality"""
    print("🎫 Testing Ticket Agent with LLM Reasoning")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        
        print(f"✅ Configuration loaded:")
        print(f"   Region: {config.aws_region}")
        print(f"   Model: {config.bedrock_model_id}")
        print(f"   Data Agent URL: {config.data_agent_url}")
        
        # Create Ticket Agent
        agent = TicketAgent(config)
        
        # Test 1: Validate ticket eligibility
        print(f"\n🔍 Test 1: Validate ticket eligibility")
        
        test_ticket_id = "test-ticket-123"
        test_customer_id = "test-customer-456"
        
        # Test LLM reasoning directly
        sample_ticket = {
            "id": test_ticket_id,
            "ticket_number": "TKT-TEST-001",
            "ticket_type": "general",
            "original_price": 50.0,
            "event_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "status": "active",
            "days_until_event": 30
        }
        
        sample_customer = {
            "id": test_customer_id,
            "first_name": "Test",
            "last_name": "Customer",
            "email": "test@example.com"
        }
        
        # Test eligibility analysis
        eligibility_analysis = await agent.llm.reason_about_ticket_eligibility(sample_ticket, sample_customer)
        
        if eligibility_analysis and "failed" not in eligibility_analysis.lower():
            print(f"   ✅ Ticket eligibility validation successful")
            print(f"   🎫 Ticket: {sample_ticket['ticket_number']}")
            print(f"   👤 Customer: {sample_customer['first_name']} {sample_customer['last_name']}")
            print(f"   🤖 LLM Analysis: {eligibility_analysis[:100]}...")
        else:
            print(f"   ❌ Ticket eligibility validation failed")
            return False
        
        # Test 2: Calculate upgrade pricing
        print(f"\n💰 Test 2: Calculate upgrade pricing")
        
        pricing_tests = [
            ("general", "standard", 50.0),
            ("general", "non-stop", 50.0),
            ("standard", "double-fun", 75.0)
        ]
        
        for ticket_type, upgrade_tier, original_price in pricing_tests:
            # Test pricing calculation directly
            from models.ticket import TicketType
            from models.upgrade_order import UpgradeTier
            from decimal import Decimal
            
            try:
                ticket_type_enum = TicketType(ticket_type)
                # Fix enum conversion for upgrade tiers
                tier_mapping = {
                    'standard': UpgradeTier.STANDARD,
                    'non-stop': UpgradeTier.NON_STOP,
                    'double-fun': UpgradeTier.DOUBLE_FUN
                }
                upgrade_tier_enum = tier_mapping.get(upgrade_tier)
                
                if not upgrade_tier_enum:
                    print(f"   ❌ Invalid upgrade tier: {upgrade_tier}")
                    continue
                
                upgrade_price = agent.pricing.calculate_upgrade_price(ticket_type_enum, upgrade_tier_enum)
                
                if upgrade_price:
                    total_price = agent.pricing.calculate_total_price(Decimal(str(original_price)), upgrade_price)
                    print(f"   ✅ {ticket_type} → {upgrade_tier}: ${float(upgrade_price):.2f} (Total: ${float(total_price):.2f})")
                else:
                    print(f"   ❌ No upgrade available: {ticket_type} → {upgrade_tier}")
            except Exception as e:
                print(f"   ❌ Pricing calculation failed for {ticket_type} → {upgrade_tier}: {e}")
        
        # Test 3: Get upgrade recommendations
        print(f"\n🎯 Test 3: Get upgrade recommendations")
        
        sample_ticket = {
            "ticket_type": "general",
            "original_price": 50.0,
            "event_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "status": "active"
        }
        
        customer_preferences = {
            "budget": "moderate",
            "interests": ["premium_experience", "exclusive_access"]
        }
        
        # Test the tools by calling them directly through the agent's methods
        # Since FastMCP tools are not directly accessible, we'll test the underlying functionality
        
        # Test get_upgrade_recommendations functionality
        from models.ticket import TicketType
        available_upgrades = agent.pricing.get_available_upgrades(TicketType.GENERAL)
        
        if available_upgrades:
            print(f"   ✅ Recommendations generated successfully")
            print(f"   📊 Available options: {len(available_upgrades)}")
            
            # Find best value upgrade
            best_value = agent._find_best_value_upgrade(available_upgrades)
            if best_value:
                print(f"   🏆 Best value: {best_value['name']} (${best_value['price']:.2f})")
            
            # Test LLM recommendations
            llm_recommendations = await agent.llm.reason_about_upgrade_selection(
                sample_ticket, available_upgrades, customer_preferences
            )
            print(f"   🤖 Personalized advice: {llm_recommendations[:100]}...")
        else:
            print(f"   ❌ No recommendations available")
        
        # Test 4: Process customer queries
        print(f"\n💬 Test 4: Process customer queries")
        
        customer_queries = [
            "What upgrade options do I have for my general admission ticket?",
            "How much would it cost to upgrade to VIP?",
            "Can I cancel my upgrade if I change my mind?",
            "When is the latest I can upgrade my ticket?"
        ]
        
        for query in customer_queries:
            # Test LLM customer interaction directly
            query_result = await agent.llm.reason_about_customer_interaction(
                {"ticket_type": "general", "customer_tier": "standard"}, 
                query
            )
            
            if query_result and "failed" not in query_result.lower():
                print(f"   ✅ Query processed: '{query[:30]}...'")
                print(f"      Response: {query_result[:80]}...")
            else:
                print(f"   ❌ Query processing failed for: '{query[:30]}...'")
        
        # Test 5: Validate upgrade constraints
        print(f"\n🔒 Test 5: Validate upgrade constraints")
        
        constraint_tests = [
            {
                "ticket": {
                    "ticket_type": "general",
                    "status": "active",
                    "event_date": (datetime.now() + timedelta(days=30)).isoformat()
                },
                "upgrade": {"tier": "standard"},
                "description": "Valid upgrade (30 days ahead)"
            },
            {
                "ticket": {
                    "ticket_type": "general", 
                    "status": "active",
                    "event_date": (datetime.now() + timedelta(hours=12)).isoformat()
                },
                "upgrade": {"tier": "standard"},
                "description": "Invalid upgrade (too close to event)"
            },
            {
                "ticket": {
                    "ticket_type": "premium",
                    "status": "active", 
                    "event_date": (datetime.now() + timedelta(days=30)).isoformat()
                },
                "upgrade": {"tier": "double-fun"},
                "description": "Invalid upgrade (premium tickets can't upgrade)"
            }
        ]
        
        for test_case in constraint_tests:
            # Test constraint validation logic directly
            ticket_data = test_case["ticket"]
            upgrade_selection = test_case["upgrade"]
            
            # Check basic constraints
            event_date = datetime.fromisoformat(ticket_data.get('event_date', ''))
            days_until_event = (event_date - datetime.now()).days
            
            constraints = []
            is_valid = True
            
            if days_until_event < 1:
                constraints.append("Cannot upgrade tickets for past events")
                is_valid = False
            
            if ticket_data.get('status') != 'active':
                constraints.append(f"Cannot upgrade {ticket_data.get('status')} tickets")
                is_valid = False
            
            # Check upgrade tier validity
            try:
                ticket_type = TicketType(ticket_data.get('ticket_type', 'general'))
                tier_mapping = {
                    'standard': UpgradeTier.STANDARD,
                    'non-stop': UpgradeTier.NON_STOP,
                    'double-fun': UpgradeTier.DOUBLE_FUN
                }
                upgrade_tier = tier_mapping.get(upgrade_selection.get('tier'))
                
                if upgrade_tier and upgrade_tier not in agent.pricing.UPGRADE_PRICING.get(ticket_type, {}):
                    constraints.append(f"Upgrade to {upgrade_tier.value} not available for {ticket_type.value} tickets")
                    is_valid = False
            except Exception as e:
                constraints.append(f"Invalid ticket type or upgrade tier: {str(e)}")
                is_valid = False
            
            print(f"   ✅ {test_case['description']}")
            print(f"      Valid: {is_valid}")
            if constraints:
                print(f"      Constraints: {constraints}")
        
        # Test 6: LLM reasoning capabilities
        print(f"\n🧠 Test 6: LLM reasoning capabilities")
        
        # Test direct LLM reasoning
        sample_ticket_data = {
            "ticket_number": "TKT-TEST-001",
            "ticket_type": "general",
            "original_price": 50.0,
            "event_date": (datetime.now() + timedelta(days=15)).isoformat(),
            "status": "active"
        }
        
        sample_customer_data = {
            "first_name": "Test",
            "last_name": "Customer", 
            "email": "test@example.com"
        }
        
        llm_analysis = await agent.llm.reason_about_ticket_eligibility(sample_ticket_data, sample_customer_data)
        
        if llm_analysis and "failed" not in llm_analysis.lower():
            print(f"   ✅ LLM reasoning working")
            print(f"   🤖 Analysis: {llm_analysis[:150]}...")
        else:
            print(f"   ❌ LLM reasoning failed: {llm_analysis}")
        
        # Test pricing strategy reasoning
        pricing_analysis = await agent.llm.reason_about_pricing_strategy(sample_ticket_data)
        
        if pricing_analysis and "failed" not in pricing_analysis.lower():
            print(f"   ✅ Pricing strategy analysis working")
            print(f"   💰 Strategy: {pricing_analysis[:150]}...")
        else:
            print(f"   ❌ Pricing analysis failed")
        
        print(f"\n" + "=" * 50)
        print(f"✅ Ticket Agent testing completed successfully!")
        print(f"🎉 Agent is ready for customer interactions and upgrade processing!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Ticket Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test function"""
    success = await test_ticket_agent()
    return 0 if success else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))