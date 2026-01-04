#!/usr/bin/env python3
"""
Test the complete customer journey through the new architecture
Frontend → Ticket Handler → AgentCore Ticket Agent → Data Agent → Database

This test simulates natural language conversations and validates the full process.
"""

import requests
import json
import time
import os
from typing import Dict, Any, List

class CustomerJourneyTester:
    """Test realistic customer interactions with the ticket upgrade system"""
    
    def __init__(self):
        self.api_base = "https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod"
        self.access_token = None
        self.conversation_history = []
        
    def authenticate(self) -> bool:
        """Authenticate with the system"""
        print("🔐 Authenticating customer...")
        
        auth_url = f"{self.api_base}/auth"
        payload = {
            "email": "testuser@example.com",
            "password": "TempPass123!"
        }
        
        try:
            response = requests.post(auth_url, json=payload)
            
            if response.status_code == 200:
                auth_data = response.json()
                if auth_data.get('success') and auth_data.get('tokens'):
                    self.access_token = auth_data['tokens']['access_token']
                    print("✅ Authentication successful")
                    return True
            
            print(f"❌ Authentication failed: {response.status_code} - {response.text}")
            return False
            
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def send_chat_message(self, message: str, context: Dict = None) -> Dict[str, Any]:
        """Send a chat message through the new Ticket Handler flow"""
        
        if not self.access_token:
            return {"success": False, "error": "Not authenticated"}
        
        chat_url = f"{self.api_base}/chat"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": message,
            "conversationHistory": self.conversation_history,
            "context": context or {}
        }
        
        try:
            print(f"\n💬 Customer: {message}")
            
            response = requests.post(chat_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    ai_response = result.get('response', '')
                    show_buttons = result.get('showUpgradeButtons', False)
                    options = result.get('upgradeOptions', [])
                    
                    print(f"🤖 AI Agent: {ai_response}")
                    
                    if show_buttons and options:
                        print("🎫 Available Upgrade Options:")
                        for option in options:
                            print(f"   • {option['name']}: ${option['price']} - {option['description']}")
                    
                    # Update conversation history
                    self.conversation_history.append({
                        "sender": "customer",
                        "content": message
                    })
                    self.conversation_history.append({
                        "sender": "ai",
                        "content": ai_response
                    })
                    
                    return result
                else:
                    print(f"❌ Chat failed: {result.get('error')}")
                    return result
            else:
                print(f"❌ Chat request failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Chat error: {e}")
            return {"success": False, "error": str(e)}
    
    def validate_ticket(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Test ticket validation through the new flow"""
        
        if not self.access_token:
            return {"success": False, "error": "Not authenticated"}
        
        validate_url = f"{self.api_base}/tickets/{ticket_id}/validate"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "upgrade_tier": upgrade_tier
        }
        
        try:
            print(f"\n🔍 Validating ticket {ticket_id} for {upgrade_tier} upgrade...")
            
            response = requests.post(validate_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Validation result: {result}")
                return result
            else:
                print(f"❌ Validation failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return {"success": False, "error": str(e)}
    
    def get_pricing(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Test pricing calculation through the new flow"""
        
        if not self.access_token:
            return {"success": False, "error": "Not authenticated"}
        
        pricing_url = f"{self.api_base}/tickets/{ticket_id}/pricing"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "upgrade_tier": upgrade_tier,
            "event_date": "2026-02-15"
        }
        
        try:
            print(f"\n💰 Getting pricing for {upgrade_tier} upgrade...")
            
            response = requests.post(pricing_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Pricing result: {result}")
                return result
            else:
                print(f"❌ Pricing failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Pricing error: {e}")
            return {"success": False, "error": str(e)}

def test_scenario_1_greeting_and_exploration():
    """Test Scenario 1: Customer greeting and exploring options"""
    
    print("\n" + "="*80)
    print("🎭 SCENARIO 1: Customer Greeting and Exploration")
    print("="*80)
    
    tester = CustomerJourneyTester()
    
    # Authenticate
    if not tester.authenticate():
        print("❌ Scenario 1 failed: Authentication failed")
        return False
    
    # Natural conversation flow
    messages = [
        "Hello! I'm interested in upgrading my ticket.",
        "What upgrade options do you have available?",
        "Can you tell me more about the VIP package?",
        "How much would it cost to upgrade to premium?"
    ]
    
    success_count = 0
    for message in messages:
        result = tester.send_chat_message(message)
        if result.get('success'):
            success_count += 1
        time.sleep(1)  # Be nice to the API
    
    success_rate = success_count / len(messages)
    print(f"\n📊 Scenario 1 Results: {success_count}/{len(messages)} messages successful ({success_rate:.1%})")
    
    return success_rate >= 0.75  # 75% success rate

def test_scenario_2_ticket_specific_inquiry():
    """Test Scenario 2: Customer with specific ticket inquiry"""
    
    print("\n" + "="*80)
    print("🎭 SCENARIO 2: Specific Ticket Inquiry")
    print("="*80)
    
    tester = CustomerJourneyTester()
    
    # Authenticate
    if not tester.authenticate():
        print("❌ Scenario 2 failed: Authentication failed")
        return False
    
    # Ticket-specific conversation
    ticket_id = "550e8400-e29b-41d4-a716-446655440002"
    
    messages = [
        f"Hi, I have ticket {ticket_id} and want to know about upgrades",
        "Is my ticket eligible for upgrade?",
        "What's the difference between Standard and Premium upgrades?",
        "I'd like to proceed with the Premium upgrade"
    ]
    
    success_count = 0
    for message in messages:
        context = {"ticketId": ticket_id, "hasTicketInfo": True}
        result = tester.send_chat_message(message, context)
        if result.get('success'):
            success_count += 1
        time.sleep(1)
    
    # Test direct API calls
    validation_result = tester.validate_ticket(ticket_id, "Premium")
    if validation_result.get('success'):
        success_count += 1
    
    pricing_result = tester.get_pricing(ticket_id, "Premium")
    if pricing_result.get('success'):
        success_count += 1
    
    total_operations = len(messages) + 2  # messages + validation + pricing
    success_rate = success_count / total_operations
    print(f"\n📊 Scenario 2 Results: {success_count}/{total_operations} operations successful ({success_rate:.1%})")
    
    return success_rate >= 0.75

def test_scenario_3_price_sensitive_customer():
    """Test Scenario 3: Price-sensitive customer asking about costs"""
    
    print("\n" + "="*80)
    print("🎭 SCENARIO 3: Price-Sensitive Customer")
    print("="*80)
    
    tester = CustomerJourneyTester()
    
    # Authenticate
    if not tester.authenticate():
        print("❌ Scenario 3 failed: Authentication failed")
        return False
    
    # Price-focused conversation
    messages = [
        "How much does it cost to upgrade my ticket?",
        "What's the cheapest upgrade option?",
        "Are there any discounts available?",
        "Can you show me all the prices?",
        "What do I get for the extra money?"
    ]
    
    success_count = 0
    for message in messages:
        result = tester.send_chat_message(message)
        if result.get('success'):
            success_count += 1
            # Check if upgrade options are shown for price-related queries
            if result.get('showUpgradeButtons'):
                print("✅ Upgrade options displayed for price inquiry")
        time.sleep(1)
    
    success_rate = success_count / len(messages)
    print(f"\n📊 Scenario 3 Results: {success_count}/{len(messages)} messages successful ({success_rate:.1%})")
    
    return success_rate >= 0.75

def test_scenario_4_confused_customer():
    """Test Scenario 4: Confused customer needing help"""
    
    print("\n" + "="*80)
    print("🎭 SCENARIO 4: Confused Customer Needing Help")
    print("="*80)
    
    tester = CustomerJourneyTester()
    
    # Authenticate
    if not tester.authenticate():
        print("❌ Scenario 4 failed: Authentication failed")
        return False
    
    # Confused customer conversation
    messages = [
        "I'm not sure what I need help with",
        "What can you do for me?",
        "I have a ticket but don't know if I can upgrade it",
        "Can you help me understand the process?",
        "What happens after I choose an upgrade?"
    ]
    
    success_count = 0
    for message in messages:
        result = tester.send_chat_message(message)
        if result.get('success'):
            success_count += 1
        time.sleep(1)
    
    success_rate = success_count / len(messages)
    print(f"\n📊 Scenario 4 Results: {success_count}/{len(messages)} messages successful ({success_rate:.1%})")
    
    return success_rate >= 0.75

def test_agentcore_integration():
    """Test AgentCore agent integration and responsiveness"""
    
    print("\n" + "="*80)
    print("🤖 AGENTCORE INTEGRATION TEST")
    print("="*80)
    
    tester = CustomerJourneyTester()
    
    # Authenticate
    if not tester.authenticate():
        print("❌ AgentCore test failed: Authentication failed")
        return False
    
    # Test various agent capabilities
    test_cases = [
        {
            "message": "I want to upgrade my ticket 550e8400-e29b-41d4-a716-446655440002",
            "expected_keywords": ["upgrade", "ticket", "options"],
            "should_show_buttons": True
        },
        {
            "message": "What are the benefits of VIP upgrade?",
            "expected_keywords": ["vip", "benefits", "features"],
            "should_show_buttons": True
        },
        {
            "message": "How much does premium cost?",
            "expected_keywords": ["premium", "cost", "price"],
            "should_show_buttons": True
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 Test Case {i}: {test_case['message']}")
        
        result = tester.send_chat_message(test_case['message'])
        
        if result.get('success'):
            response = result.get('response', '').lower()
            show_buttons = result.get('showUpgradeButtons', False)
            
            # Check for expected keywords
            keywords_found = sum(1 for keyword in test_case['expected_keywords'] 
                               if keyword in response)
            
            # Check button display expectation
            buttons_correct = show_buttons == test_case['should_show_buttons']
            
            if keywords_found > 0 and buttons_correct:
                print(f"✅ Test Case {i} passed")
                success_count += 1
            else:
                print(f"⚠️  Test Case {i} partial success")
                print(f"   Keywords found: {keywords_found}/{len(test_case['expected_keywords'])}")
                print(f"   Buttons shown: {show_buttons} (expected: {test_case['should_show_buttons']})")
        else:
            print(f"❌ Test Case {i} failed")
        
        time.sleep(1)
    
    success_rate = success_count / len(test_cases)
    print(f"\n📊 AgentCore Integration Results: {success_count}/{len(test_cases)} tests passed ({success_rate:.1%})")
    
    return success_rate >= 0.75

def main():
    """Run all customer journey tests"""
    
    print("🚀 TESTING COMPLETE CUSTOMER JOURNEY")
    print("Architecture: Frontend → Ticket Handler → AgentCore Ticket Agent → Data Agent → Database")
    print("="*100)
    
    # Run all test scenarios
    test_results = []
    
    test_results.append(("Greeting & Exploration", test_scenario_1_greeting_and_exploration()))
    test_results.append(("Specific Ticket Inquiry", test_scenario_2_ticket_specific_inquiry()))
    test_results.append(("Price-Sensitive Customer", test_scenario_3_price_sensitive_customer()))
    test_results.append(("Confused Customer", test_scenario_4_confused_customer()))
    test_results.append(("AgentCore Integration", test_agentcore_integration()))
    
    # Summary
    print("\n" + "="*100)
    print("📋 FINAL TEST RESULTS")
    print("="*100)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<50} {status}")
        if result:
            passed_tests += 1
    
    overall_success_rate = passed_tests / total_tests
    
    print(f"\nOverall Success Rate: {passed_tests}/{total_tests} ({overall_success_rate:.1%})")
    
    if overall_success_rate >= 0.8:
        print("\n🎉 EXCELLENT! The new architecture is working well!")
        print("✅ Customers can successfully interact with AgentCore agents")
        print("✅ The flow Frontend → Ticket Handler → AgentCore → Database is functional")
        print("✅ Natural language processing is working")
        print("✅ Ticket operations are properly delegated")
    elif overall_success_rate >= 0.6:
        print("\n⚠️  GOOD with some issues. The system is mostly functional.")
        print("🔧 Some areas may need attention for optimal performance")
    else:
        print("\n❌ NEEDS ATTENTION. Several issues detected.")
        print("🔧 Please check AgentCore agent status and Lambda logs")
    
    print(f"\n📊 Architecture Status: {'✅ OPERATIONAL' if overall_success_rate >= 0.6 else '❌ NEEDS FIXES'}")

if __name__ == "__main__":
    main()