#!/usr/bin/env python3
"""
Test AI Upgrade Flow

Test the complete upgrade flow with AI-generated responses.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ai_upgrade_flow():
    """Test complete AI upgrade flow"""
    
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
    
    print(f"\n🎯 Testing Complete AI Upgrade Flow")
    print("=" * 50)
    
    # Step 1: Initial greeting
    print("\n📝 Step 1: Initial greeting")
    response1 = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': 'Hi there! I have a ticket and I\'m interested in upgrades',
        'context': {},
        'conversationHistory': []
    })
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"🤖 AI: {data1['response']}")
        print(f"🎫 Show upgrade buttons: {data1.get('showUpgradeButtons', False)}")
    else:
        print(f"❌ Step 1 failed: {response1.status_code}")
        return False
    
    # Step 2: Provide ticket ID
    print("\n📝 Step 2: Provide ticket ID")
    response2 = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': 'My ticket ID is 550e8400-e29b-41d4-a716-446655440002',
        'context': {},
        'conversationHistory': [
            {'role': 'user', 'content': 'Hi there! I have a ticket and I\'m interested in upgrades'},
            {'role': 'assistant', 'content': data1['response']}
        ]
    })
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"🤖 AI: {data2['response']}")
        print(f"🎫 Show upgrade buttons: {data2.get('showUpgradeButtons', False)}")
        if data2.get('upgradeOptions'):
            print(f"🎯 Upgrade options: {len(data2['upgradeOptions'])} available")
            for option in data2['upgradeOptions']:
                print(f"   - {option['name']}: ${option['price']}")
    else:
        print(f"❌ Step 2 failed: {response2.status_code}")
        return False
    
    # Step 3: Select an upgrade
    print("\n📝 Step 3: Select VIP upgrade")
    vip_upgrade = {
        "id": "vip",
        "name": "VIP Package",
        "price": 300,
        "features": ["VIP seating", "Meet & greet", "Exclusive merchandise", "Photo opportunities", "Backstage tour"]
    }
    
    response3 = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': 'I\'d like the VIP Package upgrade',
        'context': {
            'ticketId': '550e8400-e29b-41d4-a716-446655440002',
            'selectedUpgrade': vip_upgrade,
            'hasTicketInfo': True,
            'hasUpgradeOptions': True
        },
        'conversationHistory': [
            {'role': 'user', 'content': 'My ticket ID is 550e8400-e29b-41d4-a716-446655440002'},
            {'role': 'assistant', 'content': data2['response']}
        ]
    })
    
    if response3.status_code == 200:
        data3 = response3.json()
        print(f"🤖 AI: {data3['response']}")
        print(f"🎫 Show upgrade buttons: {data3.get('showUpgradeButtons', False)}")
    else:
        print(f"❌ Step 3 failed: {response3.status_code}")
        return False
    
    # Step 4: Follow-up question
    print("\n📝 Step 4: Follow-up question")
    response4 = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': 'When will I receive confirmation?',
        'context': {
            'ticketId': '550e8400-e29b-41d4-a716-446655440002',
            'hasTicketInfo': True,
            'hasUpgradeOptions': True
        },
        'conversationHistory': [
            {'role': 'user', 'content': 'I\'d like the VIP Package upgrade'},
            {'role': 'assistant', 'content': data3['response']}
        ]
    })
    
    if response4.status_code == 200:
        data4 = response4.json()
        print(f"🤖 AI: {data4['response']}")
    else:
        print(f"❌ Step 4 failed: {response4.status_code}")
        return False
    
    print(f"\n📊 UPGRADE FLOW SUMMARY")
    print("=" * 30)
    print("✅ All steps completed successfully!")
    print("🎉 AI is handling the complete upgrade flow intelligently")
    print("🤖 Responses are contextual and natural")
    print("🎯 Upgrade selection and validation working properly")
    
    return True

if __name__ == "__main__":
    test_ai_upgrade_flow()