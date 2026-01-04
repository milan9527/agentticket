#!/usr/bin/env python3
"""
Test Ticket Recognition

Test the specific scenario where user says "ticket 333" to ensure it gets recognized
and delegated to the ticket handler properly.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ticket_recognition():
    """Test ticket recognition and delegation for the specific user scenario"""
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    # Test authentication first
    print("🔐 Testing authentication...")
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return False
    
    auth_data = auth_response.json()
    token = auth_data['tokens']['access_token']
    print("✅ Authentication successful")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print(f"\n🎯 Testing Specific User Scenario")
    print("=" * 50)
    
    # Test the exact user flow
    test_messages = [
        "hello",
        "upgrade ticket", 
        "ticket 333",
        "what's upgrade options",
        "Seat Upgrade"
    ]
    
    conversation_history = []
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 Step {i}: User says '{message}'")
        
        response = requests.post(f'{api_base_url}/chat', headers=headers, json={
            'message': message,
            'context': {},
            'conversationHistory': conversation_history
        })
        
        if response.status_code == 200:
            data = response.json()
            ai_response = data['response']
            show_buttons = data.get('showUpgradeButtons', False)
            
            print(f"🤖 AI Response: {ai_response}")
            print(f"🎫 Show upgrade buttons: {show_buttons}")
            
            # Add to conversation history
            conversation_history.append({'role': 'user', 'content': message})
            conversation_history.append({'role': 'assistant', 'content': ai_response})
            
            # Keep only last 6 messages (3 exchanges)
            if len(conversation_history) > 6:
                conversation_history = conversation_history[-6:]
            
            # Check specific expectations for "ticket 333"
            if message == "ticket 333":
                if any(indicator in ai_response.lower() for indicator in ['validated', 'verified', 'eligible', 'standard']):
                    print("✅ Ticket 333 was properly recognized and validated through ticket handler")
                else:
                    print("❌ Ticket 333 was not properly validated - may not have called ticket handler")
            
            # Check for upgrade options when asked
            if message == "what's upgrade options":
                if show_buttons or any(word in ai_response.lower() for word in ['standard', 'premium', 'vip']):
                    print("✅ Upgrade options properly shown")
                else:
                    print("⚠️ Upgrade options may not be properly shown")
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(response.text)
            return False
    
    # Test direct ticket handler for comparison
    print(f"\n📝 Direct Ticket Handler Test (for comparison)")
    direct_response = requests.post(
        f'{api_base_url}/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
        headers=headers,
        json={'upgrade_tier': 'Standard Upgrade'}
    )
    
    if direct_response.status_code == 200:
        direct_data = direct_response.json()
        print(f"🎯 Direct validation result: {direct_data}")
        
        if direct_data.get('success') and direct_data.get('data'):
            ticket_info = direct_data['data']
            print(f"   - Eligible: {ticket_info.get('eligible')}")
            print(f"   - Current tier: {ticket_info.get('current_tier')}")
            print(f"   - Reason: {ticket_info.get('reason')}")
        else:
            print("⚠️ Direct validation returned unexpected format")
    else:
        print(f"❌ Direct validation failed: {direct_response.status_code}")
    
    print(f"\n📊 TEST SUMMARY")
    print("=" * 30)
    print("✅ Chat handler responding to all messages")
    print("✅ Conversation flow maintained")
    print("🔍 Check above for proper ticket recognition and validation")
    
    return True

if __name__ == "__main__":
    test_ticket_recognition()