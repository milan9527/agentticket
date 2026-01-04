#!/usr/bin/env python3
"""
Test Chat Endpoint

Test the new chat endpoint to ensure it's working with AgentCore.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_chat_endpoint():
    """Test the chat endpoint"""
    print("🤖 TESTING CHAT ENDPOINT")
    print("=" * 50)
    
    # API configuration
    api_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    test_user = os.getenv('COGNITO_TEST_USER', 'testuser@example.com')
    test_password = os.getenv('COGNITO_TEST_PASSWORD', 'TempPass123!')
    
    print(f"🌐 API URL: {api_url}")
    print(f"👤 Test User: {test_user}")
    
    # Step 1: Authenticate
    print("\n🔐 Testing Authentication...")
    auth_response = requests.post(
        f"{api_url}/auth",
        json={
            "email": test_user,
            "password": test_password
        },
        headers={'Content-Type': 'application/json'}
    )
    
    if auth_response.status_code == 200:
        auth_data = auth_response.json()
        if auth_data.get('success'):
            access_token = auth_data['tokens']['access_token']
            print("✅ Authentication successful")
        else:
            print(f"❌ Authentication failed: {auth_data}")
            return
    else:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        print(f"Response: {auth_response.text}")
        return
    
    # Step 2: Test Chat
    print("\n💬 Testing Chat with AgentCore...")
    
    test_messages = [
        "Hello, I need help with my ticket",
        "I want to upgrade my ticket 550e8400-e29b-41d4-a716-446655440002",
        "What upgrade options are available?",
        "How much does a premium upgrade cost?"
    ]
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 Test Message {i}: {message}")
        
        chat_response = requests.post(
            f"{api_url}/chat",
            json={
                "message": message,
                "conversationHistory": [],
                "context": {"ticketId": "550e8400-e29b-41d4-a716-446655440002"}
            },
            headers=headers
        )
        
        print(f"📋 Status Code: {chat_response.status_code}")
        
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            if chat_data.get('success'):
                print(f"✅ Chat successful")
                print(f"🤖 AI Response: {chat_data.get('response', 'No response')}")
                if chat_data.get('showUpgradeButtons'):
                    print(f"🎯 Upgrade buttons shown: {len(chat_data.get('upgradeOptions', []))} options")
                else:
                    print("ℹ️ No upgrade buttons shown")
            else:
                print(f"❌ Chat failed: {chat_data}")
        else:
            print(f"❌ Chat request failed: {chat_response.status_code}")
            print(f"Response: {chat_response.text}")
        
        print("-" * 30)
    
    print("\n🎯 CHAT TEST SUMMARY")
    print("=" * 50)
    print("✅ Authentication: Working")
    print("🤖 Chat Endpoint: Testing complete")
    print("🔗 AgentCore Integration: See results above")


if __name__ == "__main__":
    test_chat_endpoint()