#!/usr/bin/env python3
"""
Natural Language Conversation Test

This script demonstrates the enhanced natural language conversation capabilities
of the customer chat interface, showing how customers can interact using
natural speech instead of commands.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from customer_chat_interface import CustomerChatInterface


async def simulate_natural_conversations():
    """Simulate natural language conversations with the AI assistant"""
    
    print("🗣️ Natural Language Conversation Demonstration")
    print("=" * 60)
    print("This demo shows how customers can chat naturally with the AI assistant")
    print("instead of using specific commands or following a rigid wizard flow.")
    print()
    
    # Initialize the interface
    interface = CustomerChatInterface()
    
    try:
        # Initialize system
        print("🤖 Initializing AI system...")
        if not await interface.initialize_system():
            print("❌ Failed to initialize system")
            return False
        
        # Simulate customer authentication
        print("\n👤 Simulating customer authentication...")
        
        # Mock customer session for demo
        interface.customer_session = {
            'id': 'demo-customer-id',
            'email': 'john.doe@example.com',
            'first_name': 'John',
            'last_name': 'Doe',
            'tickets': [
                {
                    'id': 'demo-ticket-1',
                    'ticket_number': 'TKT-DEMO001',
                    'ticket_type': 'general',
                    'original_price': 75.00,
                    'event_date': '2026-02-15T19:00:00',
                    'status': 'active'
                }
            ]
        }
        
        print(f"✅ Demo customer: {interface.customer_session['first_name']} {interface.customer_session['last_name']}")
        print(f"📧 Email: {interface.customer_session['email']}")
        print(f"🎫 Tickets: {len(interface.customer_session['tickets'])} active ticket(s)")
        
        # Demonstrate natural conversation scenarios
        conversation_scenarios = [
            {
                "name": "Greeting and Ticket Inquiry",
                "queries": [
                    "Hi there! Can you tell me about my tickets?",
                    "What upgrade options do I have?"
                ]
            },
            {
                "name": "Pricing Questions",
                "queries": [
                    "How much would it cost to upgrade my ticket?",
                    "What's the difference between the upgrade options?"
                ]
            },
            {
                "name": "Feature Inquiry",
                "queries": [
                    "What's included in the premium upgrade?",
                    "Tell me more about the VIP features"
                ]
            },
            {
                "name": "Natural Upgrade Request",
                "queries": [
                    "I think I'd like to upgrade to something better",
                    "The standard upgrade sounds good to me"
                ]
            }
        ]
        
        print(f"\n🎭 Demonstrating Natural Language Conversations")
        print("=" * 50)
        
        for scenario in conversation_scenarios:
            print(f"\n📋 Scenario: {scenario['name']}")
            print("-" * 30)
            
            for query in scenario['queries']:
                print(f"\n👤 Customer: {query}")
                
                # Process the query naturally
                await interface.process_customer_query(query)
                
                # Brief pause between queries
                await asyncio.sleep(2)
            
            print(f"\n" + "="*50)
            await asyncio.sleep(3)
        
        print(f"\n🎉 Natural Language Conversation Demo Complete!")
        print(f"\nKey Features Demonstrated:")
        print(f"✅ Natural language understanding")
        print(f"✅ Contextual AI responses")
        print(f"✅ Intelligent action detection")
        print(f"✅ Conversational upgrade flow")
        print(f"✅ No rigid commands or wizards")
        print(f"✅ Personalized recommendations")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main demo function"""
    success = await simulate_natural_conversations()
    return 0 if success else 1


if __name__ == "__main__":
    print("🎫 Natural Language Customer Chat Demo")
    print("Real conversational AI with Aurora database and Nova Pro LLM")
    print()
    
    exit(asyncio.run(main()))