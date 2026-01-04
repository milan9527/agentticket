#!/usr/bin/env python3
"""
Customer Chat Interface - Ticket Auto-Processing System

Interactive customer-facing script that allows customers to chat with AI agents
for ticket upgrades, pricing inquiries, and support using real LLM reasoning
and Aurora database integration.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.agents.data_agent import DataAgent, load_config as load_data_config
from backend.agents.ticket_agent import TicketAgent, load_config as load_ticket_config
from backend.services.payment_gateway import PaymentGateway, PaymentMethod, load_config as load_payment_config
from backend.services.notification_service import NotificationService, NotificationType, load_config as load_notification_config
from models.ticket import TicketType
from models.upgrade_order import UpgradeTier


class CustomerChatInterface:
    """Interactive customer chat interface with AI agents"""
    
    def __init__(self):
        self.data_agent = None
        self.ticket_agent = None
        self.payment_gateway = None
        self.notification_service = None
        self.customer_session = {}
        self.conversation_history = []
    
    async def initialize_system(self):
        """Initialize all system components"""
        print("🤖 Initializing AI Ticket Assistant...")
        
        try:
            # Load configurations and initialize agents
            self.data_agent = DataAgent(load_data_config())
            self.ticket_agent = TicketAgent(load_ticket_config())
            self.payment_gateway = PaymentGateway(load_payment_config())
            self.notification_service = NotificationService(load_notification_config())
            
            # Test database connectivity
            db_test = await self.data_agent.db.execute_sql("SELECT COUNT(*) FROM customers")
            customer_count = db_test['records'][0][0]['longValue']
            
            print(f"✅ AI Assistant ready! Connected to database with {customer_count} customers.")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize system: {e}")
            return False
    
    async def authenticate_customer(self):
        """Authenticate customer by email"""
        print("\n👋 Welcome to the AI Ticket Upgrade Assistant!")
        print("=" * 50)
        
        while True:
            email = input("\n📧 Please enter your email address: ").strip()
            
            if not email or '@' not in email:
                print("❌ Please enter a valid email address.")
                continue
            
            # Look up customer in database
            try:
                customer_result = await self.data_agent.db.execute_sql(
                    "SELECT * FROM customers WHERE email = :email LIMIT 1",
                    [{"name": "email", "value": {"stringValue": email}}]
                )
                
                if not customer_result.get('records'):
                    print(f"❌ No account found for {email}")
                    retry = input("Would you like to try another email? (y/n): ").strip().lower()
                    if retry != 'y':
                        return False
                    continue
                
                # Parse customer data
                customer_record = customer_result['records'][0]
                self.customer_session = {
                    'id': customer_record[0]['stringValue'],
                    'email': customer_record[1]['stringValue'],
                    'first_name': customer_record[3]['stringValue'],
                    'last_name': customer_record[4]['stringValue'],
                    'tickets': []
                }
                
                print(f"\n✅ Welcome back, {self.customer_session['first_name']} {self.customer_session['last_name']}!")
                
                # Get customer's tickets
                await self.load_customer_tickets()
                return True
                
            except Exception as e:
                print(f"❌ Error looking up customer: {e}")
                return False
    
    async def load_customer_tickets(self):
        """Load customer's tickets from database"""
        try:
            tickets_result = await self.data_agent.db.execute_sql(
                "SELECT * FROM tickets WHERE customer_id = :customer_id::uuid",
                [{"name": "customer_id", "value": {"stringValue": self.customer_session['id']}}]
            )
            
            if not tickets_result.get('records'):
                print("❌ No tickets found for your account.")
                return
            
            # Parse ticket data
            for ticket_record in tickets_result['records']:
                ticket_data = {
                    'id': ticket_record[0]['stringValue'],
                    'ticket_number': ticket_record[2]['stringValue'],
                    'ticket_type': ticket_record[3]['stringValue'],
                    'original_price': float(ticket_record[4]['stringValue']),
                    'event_date': ticket_record[6]['stringValue'],
                    'status': ticket_record[7]['stringValue']
                }
                self.customer_session['tickets'].append(ticket_data)
            
            print(f"\n🎫 Found {len(self.customer_session['tickets'])} ticket(s) in your account:")
            for i, ticket in enumerate(self.customer_session['tickets'], 1):
                print(f"   {i}. {ticket['ticket_number']} - {ticket['ticket_type'].title()} (${ticket['original_price']:.2f})")
                print(f"      Event Date: {ticket['event_date'][:10]} | Status: {ticket['status'].title()}")
            
        except Exception as e:
            print(f"❌ Error loading tickets: {e}")
    
    async def start_conversation(self):
        """Start the interactive conversation with the AI assistant"""
        print(f"\n💬 Natural Language Chat with AI Assistant")
        print("=" * 50)
        print("Hi! I'm your AI ticket assistant. I can help you with:")
        print("• Understanding your tickets and upgrade options")
        print("• Answering questions about pricing and features")
        print("• Guiding you through the upgrade process")
        print("• Providing personalized recommendations")
        print("\nJust talk to me naturally! Type 'quit' to exit anytime.")
        
        # Initial AI greeting
        await self.ai_greeting()
        
        while True:
            try:
                # Get user input
                user_input = input(f"\n{self.customer_session['first_name']}: ").strip()
                
                if not user_input:
                    continue
                
                # Handle quit command
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    print("\n👋 Thank you for using our AI Ticket Assistant! Have a great day!")
                    break
                
                # Process all input with AI - no special commands needed
                await self.process_customer_query(user_input)
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
    
    async def ai_greeting(self):
        """AI provides personalized greeting based on customer's tickets"""
        try:
            # Build context for AI greeting
            context = {
                "customer": {
                    "name": f"{self.customer_session['first_name']} {self.customer_session['last_name']}",
                    "email": self.customer_session['email'],
                    "tickets": self.customer_session['tickets']
                },
                "is_greeting": True
            }
            
            greeting_prompt = f"""
            Provide a warm, personalized greeting for {self.customer_session['first_name']}. 
            Look at their tickets and mention something relevant about their upcoming events.
            Keep it friendly and helpful, and let them know you're here to help with any questions.
            """
            
            ai_greeting = await self.ticket_agent.llm.reason_about_customer_interaction(
                context, greeting_prompt
            )
            
            print(f"\n🤖 AI Assistant:")
            print(f"{ai_greeting}")
            
        except Exception as e:
            print(f"\n🤖 AI Assistant:")
            print(f"Hello {self.customer_session['first_name']}! I'm here to help you with your tickets and any upgrade questions you might have. What can I assist you with today?")
    
    async def process_customer_query(self, query: str):
        """Process customer query with AI reasoning and natural conversation flow"""
        print("\n🤖 AI Assistant: Let me help you with that...")
        
        try:
            # Build comprehensive conversation context
            context = {
                "customer": {
                    "name": f"{self.customer_session['first_name']} {self.customer_session['last_name']}",
                    "email": self.customer_session['email'],
                    "tickets": self.customer_session['tickets']
                },
                "conversation_history": self.conversation_history[-5:],  # Last 5 exchanges
                "current_query": query,
                "system_capabilities": {
                    "can_show_tickets": True,
                    "can_calculate_upgrades": True,
                    "can_process_payments": True,
                    "can_provide_recommendations": True
                }
            }
            
            # Enhanced AI prompt for natural conversation
            conversation_prompt = f"""
            You are a helpful, knowledgeable ticket upgrade assistant. A customer named {self.customer_session['first_name']} has said: "{query}"
            
            Based on their query, provide a natural, conversational response that:
            1. Directly addresses what they asked
            2. Provides specific information about their tickets if relevant
            3. Offers to help with next steps naturally
            4. If they're asking about upgrades, mention you can show them options and pricing
            5. If they want to proceed with something, guide them naturally through the process
            6. Keep the tone friendly, professional, and helpful
            
            If they're asking about:
            - Ticket details: Offer to show their specific tickets
            - Upgrades: Explain available options and offer to calculate pricing
            - Pricing: Provide specific costs and value explanations
            - Process: Guide them through steps naturally
            - General questions: Answer helpfully and suggest related actions
            
            Don't mention commands or technical terms. Just have a natural conversation.
            """
            
            # Get AI response
            ai_response = await self.ticket_agent.llm.reason_about_customer_interaction(
                context, conversation_prompt
            )
            
            # Store in conversation history
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "customer_query": query,
                "ai_response": ai_response
            })
            
            # Display AI response
            print(f"\n🤖 AI Assistant:")
            print(f"{ai_response}")
            
            # Analyze query and take intelligent actions
            await self.handle_intelligent_actions(query, ai_response, context)
            
        except Exception as e:
            print(f"\n❌ Sorry, I encountered an error processing your request: {e}")
            print("Could you please try rephrasing your question?")
    
    async def handle_intelligent_actions(self, query: str, ai_response: str, context: Dict):
        """Intelligently handle follow-up actions based on customer query"""
        query_lower = query.lower()
        
        # Detect if customer wants to see their tickets
        if any(phrase in query_lower for phrase in ["my tickets", "show tickets", "what tickets", "ticket details", "my bookings"]):
            print(f"\n📋 Here are your ticket details:")
            await self.show_ticket_details_inline()
        
        # Detect if customer wants upgrade information
        elif any(phrase in query_lower for phrase in ["upgrade", "better seat", "premium", "vip", "improve", "enhance"]):
            if "how much" in query_lower or "cost" in query_lower or "price" in query_lower:
                await self.show_upgrade_pricing_inline()
            else:
                await self.show_upgrade_options_inline()
        
        # Detect if customer wants to proceed with upgrade
        elif any(phrase in query_lower for phrase in ["yes", "proceed", "go ahead", "do it", "buy", "purchase", "upgrade me"]):
            # Check if we're in an upgrade context
            recent_queries = [h["customer_query"].lower() for h in self.conversation_history[-3:]]
            if any("upgrade" in q for q in recent_queries):
                print(f"\n🎯 Great! Let me help you complete your upgrade.")
                await self.start_upgrade_process_natural()
        
        # Detect if customer has questions about specific features
        elif any(phrase in query_lower for phrase in ["what's included", "features", "benefits", "what do i get"]):
            await self.explain_upgrade_features_inline()
    
    async def show_ticket_details_inline(self):
        """Show ticket details in a conversational way"""
        if not self.customer_session['tickets']:
            print("I don't see any tickets in your account. Would you like me to help you find them?")
            return
        
        for i, ticket in enumerate(self.customer_session['tickets'], 1):
            print(f"\n🎫 Ticket {i}: {ticket['ticket_number']}")
            print(f"   • Type: {ticket['ticket_type'].title()}")
            print(f"   • Price: ${ticket['original_price']:.2f}")
            print(f"   • Event Date: {ticket['event_date'][:10]}")
            print(f"   • Status: {ticket['status'].title()}")
            
            # Show upgrade availability
            try:
                ticket_type = TicketType(ticket['ticket_type'])
                available_upgrades = self.ticket_agent.pricing.get_available_upgrades(ticket_type)
                
                if available_upgrades:
                    print(f"   • Upgrades available: {len(available_upgrades)} options")
                else:
                    print(f"   • No upgrades available for this ticket type")
            except:
                pass
        
        print(f"\nWould you like to know more about upgrade options for any of these tickets?")
    
    async def show_upgrade_options_inline(self):
        """Show upgrade options in a conversational way"""
        if not self.customer_session['tickets']:
            print("I'd love to help with upgrades, but I don't see any tickets in your account.")
            return
        
        # Use the first ticket for demonstration
        ticket = self.customer_session['tickets'][0]
        
        try:
            ticket_type = TicketType(ticket['ticket_type'])
            available_upgrades = self.ticket_agent.pricing.get_available_upgrades(ticket_type)
            
            if not available_upgrades:
                print(f"Unfortunately, there are no upgrade options available for your {ticket_type.value} ticket.")
                return
            
            print(f"\n🎯 Here are the upgrade options for your {ticket['ticket_type'].title()} ticket:")
            
            for i, upgrade in enumerate(available_upgrades, 1):
                total_price = ticket['original_price'] + upgrade['price']
                print(f"\n{i}. {upgrade['name']} (+${upgrade['price']:.2f})")
                print(f"   Total: ${total_price:.2f}")
                print(f"   Includes: {', '.join(upgrade['features'][:2])}...")
            
            print(f"\nWould you like me to explain any of these options in more detail, or help you with pricing?")
            
        except Exception as e:
            print(f"I'm having trouble loading upgrade options right now. Could you try again?")
    
    async def show_upgrade_pricing_inline(self):
        """Show detailed pricing in a conversational way"""
        if not self.customer_session['tickets']:
            return
        
        ticket = self.customer_session['tickets'][0]
        
        try:
            ticket_type = TicketType(ticket['ticket_type'])
            available_upgrades = self.ticket_agent.pricing.get_available_upgrades(ticket_type)
            
            if available_upgrades:
                print(f"\n💰 Here's the pricing breakdown for your {ticket['ticket_type'].title()} ticket:")
                print(f"   Current ticket value: ${ticket['original_price']:.2f}")
                
                for upgrade in available_upgrades:
                    total_price = ticket['original_price'] + upgrade['price']
                    savings = upgrade['price'] * 0.2  # Assume 20% savings vs buying new
                    print(f"\n   {upgrade['name']}:")
                    print(f"   • Upgrade cost: +${upgrade['price']:.2f}")
                    print(f"   • Total value: ${total_price:.2f}")
                    print(f"   • You save: ~${savings:.2f} vs buying new")
                
                print(f"\nThese prices include all taxes and fees. Would you like to proceed with any of these upgrades?")
        
        except Exception as e:
            print(f"I'm having trouble calculating pricing right now. Let me try again...")
    
    async def explain_upgrade_features_inline(self):
        """Explain upgrade features in detail"""
        if not self.customer_session['tickets']:
            return
        
        ticket = self.customer_session['tickets'][0]
        
        try:
            ticket_type = TicketType(ticket['ticket_type'])
            available_upgrades = self.ticket_agent.pricing.get_available_upgrades(ticket_type)
            
            if available_upgrades:
                print(f"\n✨ Here's what each upgrade includes:")
                
                for upgrade in available_upgrades:
                    print(f"\n🎯 {upgrade['name']}:")
                    for feature in upgrade['features']:
                        print(f"   ✓ {feature}")
                    print(f"   Price: +${upgrade['price']:.2f}")
                
                print(f"\nEach upgrade builds on your current ticket, so you get everything plus these extras!")
                print(f"Which upgrade sounds most interesting to you?")
        
        except Exception as e:
            print(f"Let me get those feature details for you...")
    
    async def start_upgrade_process_natural(self):
        """Start upgrade process in a natural, conversational way"""
        if not self.customer_session['tickets']:
            print("I'd love to help you upgrade, but I don't see any tickets to upgrade. Let me check your account...")
            return
        
        print(f"Perfect! Let me walk you through upgrading your ticket.")
        
        # Select ticket naturally
        if len(self.customer_session['tickets']) == 1:
            selected_ticket = self.customer_session['tickets'][0]
            print(f"I'll upgrade your {selected_ticket['ticket_type'].title()} ticket ({selected_ticket['ticket_number']}).")
        else:
            print(f"I see you have {len(self.customer_session['tickets'])} tickets. Which one would you like to upgrade?")
            for i, ticket in enumerate(self.customer_session['tickets'], 1):
                print(f"   {i}. {ticket['ticket_number']} - {ticket['ticket_type'].title()} (${ticket['original_price']:.2f})")
            
            while True:
                try:
                    choice = input(f"\nJust tell me the number (1-{len(self.customer_session['tickets'])}): ").strip()
                    ticket_index = int(choice) - 1
                    if 0 <= ticket_index < len(self.customer_session['tickets']):
                        selected_ticket = self.customer_session['tickets'][ticket_index]
                        print(f"Great choice! Let's upgrade your {selected_ticket['ticket_type'].title()} ticket.")
                        break
                    else:
                        print("That number doesn't match any of your tickets. Could you try again?")
                except ValueError:
                    print("I didn't catch that. Could you just give me the number?")
        
        # Continue with natural upgrade flow
        await self.continue_upgrade_naturally(selected_ticket)
    
    async def continue_upgrade_naturally(self, ticket: Dict):
        """Continue the upgrade process in a natural conversation flow"""
        try:
            # AI-powered eligibility analysis
            print(f"\nLet me check what upgrade options are available for your ticket...")
            
            eligibility_analysis = await self.ticket_agent.llm.reason_about_ticket_eligibility(
                ticket, self.customer_session
            )
            
            print(f"\n🤖 AI Assistant:")
            print(f"{eligibility_analysis}")
            
            # Get upgrade options
            ticket_type = TicketType(ticket['ticket_type'])
            available_upgrades = self.ticket_agent.pricing.get_available_upgrades(ticket_type)
            
            if not available_upgrades:
                print(f"\nI'm sorry, but there aren't any upgrade options available for {ticket_type.value} tickets right now.")
                print("Is there anything else I can help you with?")
                return
            
            print(f"\n🎯 Here are your upgrade options:")
            
            for i, upgrade in enumerate(available_upgrades, 1):
                total_price = ticket['original_price'] + upgrade['price']
                print(f"\n{i}. {upgrade['name']} - ${upgrade['price']:.2f} more")
                print(f"   Total ticket value: ${total_price:.2f}")
                print(f"   What you get: {', '.join(upgrade['features'][:3])}")
                if len(upgrade['features']) > 3:
                    print(f"   ...and more!")
            
            # AI recommendations
            print(f"\nLet me get you some personalized recommendations...")
            
            recommendations = await self.ticket_agent.llm.reason_about_upgrade_selection(
                ticket, available_upgrades, {"budget": "moderate"}
            )
            
            print(f"\n🤖 AI Assistant:")
            print(f"{recommendations}")
            
            # Natural upgrade selection
            print(f"\nWhich upgrade interests you most? Just tell me the name or number, or ask me any questions!")
            
            while True:
                user_choice = input(f"\n{self.customer_session['first_name']}: ").strip()
                
                if not user_choice:
                    continue
                
                # Handle natural language selection
                selected_upgrade = await self.parse_upgrade_selection(user_choice, available_upgrades)
                
                if selected_upgrade:
                    await self.complete_upgrade_naturally(ticket, selected_upgrade)
                    break
                elif any(word in user_choice.lower() for word in ["question", "tell me", "explain", "what", "how"]):
                    # Handle questions about upgrades
                    await self.answer_upgrade_question(user_choice, available_upgrades, ticket)
                elif user_choice.lower() in ["none", "no", "cancel", "nevermind", "back"]:
                    print("No problem! Is there anything else I can help you with?")
                    break
                else:
                    print("I didn't quite catch which upgrade you're interested in. Could you tell me the name or number?")
                    print("Or feel free to ask me any questions about the options!")
            
        except Exception as e:
            print(f"I'm having some trouble with the upgrade process. Let me try again: {e}")
    
    async def parse_upgrade_selection(self, user_input: str, available_upgrades: List[Dict]) -> Optional[Dict]:
        """Parse natural language upgrade selection"""
        user_input_lower = user_input.lower()
        
        # Try to match by number
        try:
            choice_num = int(user_input.strip())
            if 1 <= choice_num <= len(available_upgrades):
                return available_upgrades[choice_num - 1]
        except ValueError:
            pass
        
        # Try to match by name or keywords
        for upgrade in available_upgrades:
            upgrade_name_lower = upgrade['name'].lower()
            
            # Direct name match
            if upgrade_name_lower in user_input_lower or user_input_lower in upgrade_name_lower:
                return upgrade
            
            # Keyword matching
            if "standard" in user_input_lower and "standard" in upgrade_name_lower:
                return upgrade
            elif "non-stop" in user_input_lower or "nonstop" in user_input_lower and "non-stop" in upgrade_name_lower:
                return upgrade
            elif "double" in user_input_lower and "double" in upgrade_name_lower:
                return upgrade
            elif "premium" in user_input_lower or "best" in user_input_lower or "top" in user_input_lower:
                # Return the most expensive option
                return max(available_upgrades, key=lambda x: x['price'])
            elif "cheap" in user_input_lower or "basic" in user_input_lower or "least" in user_input_lower:
                # Return the least expensive option
                return min(available_upgrades, key=lambda x: x['price'])
        
        return None
    
    async def answer_upgrade_question(self, question: str, available_upgrades: List[Dict], ticket: Dict):
        """Answer questions about upgrades naturally"""
        context = {
            "question": question,
            "available_upgrades": available_upgrades,
            "ticket": ticket,
            "customer": self.customer_session
        }
        
        question_prompt = f"""
        The customer asked: "{question}"
        
        Please provide a helpful, detailed answer about the upgrade options.
        Be specific about features, pricing, and benefits.
        Keep it conversational and friendly.
        """
        
        try:
            answer = await self.ticket_agent.llm.reason_about_customer_interaction(context, question_prompt)
            print(f"\n🤖 AI Assistant:")
            print(f"{answer}")
        except Exception as e:
            print(f"\nLet me help answer that question about the upgrades...")
            # Provide a fallback answer based on the question content
            if "price" in question.lower() or "cost" in question.lower():
                await self.show_upgrade_pricing_inline()
            elif "feature" in question.lower() or "include" in question.lower():
                await self.explain_upgrade_features_inline()
    
    async def complete_upgrade_naturally(self, ticket: Dict, selected_upgrade: Dict):
        """Complete the upgrade process naturally"""
        total_price = ticket['original_price'] + selected_upgrade['price']
        
        print(f"\n🎉 Excellent choice! You've selected the {selected_upgrade['name']}.")
        print(f"\n📋 Here's your upgrade summary:")
        print(f"   • Current ticket: {ticket['ticket_number']} ({ticket['ticket_type'].title()})")
        print(f"   • Upgrade to: {selected_upgrade['name']}")
        print(f"   • Upgrade cost: ${selected_upgrade['price']:.2f}")
        print(f"   • New total value: ${total_price:.2f}")
        
        print(f"\nThis upgrade includes:")
        for feature in selected_upgrade['features']:
            print(f"   ✓ {feature}")
        
        # Natural confirmation
        confirm_input = input(f"\nDoes this look good to you? (yes/no): ").strip().lower()
        
        if confirm_input in ['yes', 'y', 'yeah', 'yep', 'sure', 'ok', 'okay']:
            await self.process_payment_naturally(ticket, selected_upgrade)
        else:
            print("No worries! Would you like to look at other upgrade options, or is there something else I can help with?")
    
    async def process_payment_naturally(self, ticket: Dict, selected_upgrade: Dict):
        """Process payment in a natural way"""
        print(f"\n💳 Great! Let me process your upgrade payment...")
        print("This will just take a moment...")
        
        try:
            transaction = await self.payment_gateway.process_payment(
                customer_id=self.customer_session['id'],
                upgrade_order_id=f"upgrade_{datetime.now().timestamp()}",
                amount=Decimal(str(selected_upgrade['price'])),
                payment_method=PaymentMethod.CREDIT_CARD
            )
            
            if transaction.status.value == "completed":
                print(f"\n🎉 Payment successful! Your upgrade is confirmed!")
                print(f"Transaction ID: {transaction.gateway_transaction_id}")
                
                # Send confirmation
                await self.notification_service.send_notification(
                    customer_id=self.customer_session['id'],
                    email=self.customer_session['email'],
                    notification_type=NotificationType.PAYMENT_SUCCESS,
                    template_data={
                        "customer_name": f"{self.customer_session['first_name']} {self.customer_session['last_name']}",
                        "transaction_id": transaction.gateway_transaction_id,
                        "amount": str(float(transaction.amount)),
                        "payment_method": "Credit Card",
                        "payment_date": transaction.completed_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "ticket_number": ticket['ticket_number'],
                        "original_type": ticket['ticket_type'].title(),
                        "upgrade_tier": selected_upgrade['name'],
                        "event_date": ticket['event_date']
                    }
                )
                
                print(f"\n📧 I've sent a confirmation email to {self.customer_session['email']}")
                print(f"✨ You're all set! Enjoy your enhanced {selected_upgrade['name']} experience!")
                print(f"\nIs there anything else I can help you with today?")
                
            elif transaction.status.value == "failed":
                print(f"\n😔 I'm sorry, but there was an issue processing your payment.")
                print(f"Error: {transaction.failure_reason}")
                
                retry_input = input("Would you like me to try processing the payment again? (yes/no): ").strip().lower()
                if retry_input in ['yes', 'y', 'yeah', 'sure']:
                    print(f"🔄 Let me try that again...")
                    retry_transaction = await self.payment_gateway.retry_payment(transaction.id)
                    
                    if retry_transaction.status.value == "completed":
                        print(f"🎉 Success! Your payment went through on the second try!")
                        print(f"Transaction ID: {retry_transaction.gateway_transaction_id}")
                        print(f"✨ Your upgrade is confirmed!")
                    else:
                        print(f"I'm still having trouble with the payment. Let me connect you with our support team to help resolve this.")
                else:
                    print("No problem! Your upgrade selection is saved. Feel free to try again later or contact our support team if you need help.")
            
        except Exception as e:
            print(f"\n😔 I encountered an error while processing your payment: {e}")
            print("Let me connect you with our support team to help complete your upgrade.")
    
    # Legacy methods kept for compatibility but not used in natural conversation flow
    async def show_ticket_details(self):
        """Show detailed ticket information (legacy method)"""
        await self.show_ticket_details_inline()


async def main():
    """Main function to run the customer chat interface"""
    interface = CustomerChatInterface()
    
    try:
        # Initialize system
        if not await interface.initialize_system():
            print("❌ Failed to initialize system. Please try again later.")
            return 1
        
        # Authenticate customer
        if not await interface.authenticate_customer():
            print("❌ Authentication failed. Goodbye!")
            return 1
        
        # Start conversation
        await interface.start_conversation()
        
        return 0
        
    except Exception as e:
        print(f"\n❌ System error: {e}")
        return 1


if __name__ == "__main__":
    print("🎫 AI Ticket Upgrade Assistant - Natural Language Chat")
    print("Talk to me naturally! I understand conversational language.")
    print("Real-time AI powered by Aurora database and Nova Pro LLM")
    print()
    print("💬 Example things you can say:")
    print("   • 'Hi, can you show me my tickets?'")
    print("   • 'What upgrade options do I have?'")
    print("   • 'How much does it cost to upgrade?'")
    print("   • 'I'd like to upgrade to something better'")
    print("   • 'Tell me about the VIP features'")
    print("   • 'The premium option sounds good'")
    print()
    
    exit(asyncio.run(main()))