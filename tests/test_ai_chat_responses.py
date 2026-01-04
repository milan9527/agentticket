#!/usr/bin/env python3
"""
Test AI Chat Responses

Test that the chat handler is now generating AI responses instead of hardcoded keyword responses.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ai_chat_responses():
    """Test AI-generated chat responses"""
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    # Test authentication first
    print("🔐 Testing authentication...")
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        print(auth_response.text)
        return False
    
    auth_data = auth_response.json()
    token = auth_data['tokens']['access_token']  # Extract access token from tokens object
    print("✅ Authentication successful")
    
    # Test various conversation scenarios
    test_scenarios = [
        {
            'name': 'General greeting',
            'message': 'Hello, I need help with my ticket',
            'context': {},
            'expected_keywords': ['help', 'assist', 'ticket']
        },
        {
            'name': 'Ticket inquiry',
            'message': 'I have ticket 550e8400-e29b-41d4-a716-446655440002, what can you tell me about it?',
            'context': {},
            'expected_keywords': ['ticket', 'found', 'upgrade']
        },
        {
            'name': 'General question about upgrades',
            'message': 'What upgrade options do you have available?',
            'context': {'ticketId': '550e8400-e29b-41d4-a716-446655440002'},
            'expected_keywords': ['upgrade', 'available', 'options']
        },
        {
            'name': 'Casual conversation',
            'message': 'How does your upgrade system work?',
            'context': {},
            'expected_keywords': ['upgrade', 'system', 'work']
        },
        {
            'name': 'Follow-up question',
            'message': 'That sounds interesting, tell me more',
            'context': {'hasTicketInfo': True},
            'expected_keywords': ['more', 'information', 'help']
        }
    ]
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print(f"\n🤖 Testing AI Chat Responses")
    print("=" * 50)
    
    all_passed = True
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n📝 Test {i}: {scenario['name']}")
        print(f"💬 Message: {scenario['message']}")
        
        # Send chat message
        chat_response = requests.post(
            f'{api_base_url}/chat',
            headers=headers,
            json={
                'message': scenario['message'],
                'context': scenario['context'],
                'conversationHistory': []
            }
        )
        
        if chat_response.status_code != 200:
            print(f"❌ Chat request failed: {chat_response.status_code}")
            print(chat_response.text)
            all_passed = False
            continue
        
        chat_data = chat_response.json()
        response_text = chat_data.get('response', '')
        
        print(f"🤖 AI Response: {response_text}")
        
        # Check if response looks AI-generated (not hardcoded)
        hardcoded_phrases = [
            "No problem at all! I'm here whenever you're ready",
            "I'm here to help with your ticket needs",
            "Hello! I'm your AI ticket assistant"
        ]
        
        is_hardcoded = any(phrase in response_text for phrase in hardcoded_phrases)
        
        if is_hardcoded:
            print("⚠️ Response appears to be hardcoded")
            all_passed = False
        else:
            print("✅ Response appears to be AI-generated")
        
        # Check for expected keywords (basic relevance check)
        has_relevant_keywords = any(keyword.lower() in response_text.lower() 
                                  for keyword in scenario['expected_keywords'])
        
        if has_relevant_keywords:
            print("✅ Response contains relevant keywords")
        else:
            print("⚠️ Response may not be contextually relevant")
            print(f"Expected keywords: {scenario['expected_keywords']}")
        
        # Check response length (AI responses should be substantial)
        if len(response_text) > 50:
            print("✅ Response has good length")
        else:
            print("⚠️ Response is quite short")
        
        print("-" * 30)
    
    print(f"\n📊 SUMMARY")
    print("=" * 30)
    if all_passed:
        print("✅ All AI chat response tests passed!")
        print("🎉 Chat is now generating intelligent AI responses")
    else:
        print("⚠️ Some tests had issues - check responses above")
    
    return all_passed

if __name__ == "__main__":
    test_ai_chat_responses()