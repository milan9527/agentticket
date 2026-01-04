#!/usr/bin/env python3
"""
Test Context Flow

Test that the chat maintains context between messages.
"""

import requests
import json

# API Configuration
API_BASE_URL = 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod'

def test_context_flow():
    """Test context maintenance in chat"""
    print("🧪 TESTING CONTEXT FLOW")
    print("=" * 40)
    
    # Get authentication token
    auth_data = {
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    }
    
    response = requests.post(f'{API_BASE_URL}/auth', json=auth_data)
    
    if response.status_code != 200:
        print("❌ Authentication failed")
        return
        
    token = response.json()['tokens']['access_token']
    print("✅ Authentication successful")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 1: Provide ticket ID
    print("\n📝 Step 1: Providing ticket ID...")
    chat_data = {
        'message': '550e8400-e29b-41d4-a716-446655440002',
        'conversationHistory': [],
        'context': {}
    }
    
    response = requests.post(f'{API_BASE_URL}/chat', json=chat_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Response: {result.get('response', 'No response')[:100]}...")
        print(f"🎫 Show Upgrade Buttons: {result.get('showUpgradeButtons', False)}")
        
        if result.get('showUpgradeButtons'):
            print("✅ Upgrade options shown - ticket recognized")
            
            # Step 2: Select an upgrade (simulating frontend context)
            print("\n📝 Step 2: Selecting upgrade with context...")
            
            # Simulate the context that frontend would send
            upgrade_context = {
                'hasTicketInfo': True,
                'ticketId': '550e8400-e29b-41d4-a716-446655440002',
                'hasUpgradeOptions': True,
                'selectedUpgrade': {
                    'id': 'standard',
                    'name': 'Standard Upgrade',
                    'price': 50,
                    'features': ['Priority boarding', 'Extra legroom', 'Complimentary drink']
                }
            }
            
            chat_data2 = {
                'message': 'I want to proceed with the Standard Upgrade upgrade for 50. Please help me complete this upgrade.',
                'conversationHistory': [
                    {'content': '550e8400-e29b-41d4-a716-446655440002', 'sender': 'customer'},
                    {'content': result.get('response', ''), 'sender': 'ai'}
                ],
                'context': upgrade_context
            }
            
            response2 = requests.post(f'{API_BASE_URL}/chat', json=chat_data2, headers=headers)
            
            if response2.status_code == 200:
                result2 = response2.json()
                print(f"✅ Response: {result2.get('response', 'No response')[:100]}...")
                
                if 'ticket ID' in result2.get('response', ''):
                    print("❌ Still asking for ticket ID - context not maintained")
                else:
                    print("✅ Context maintained - proceeding with upgrade")
            else:
                print(f"❌ Step 2 failed: {response2.status_code}")
        else:
            print("❌ No upgrade options shown")
    else:
        print(f"❌ Step 1 failed: {response.status_code}")

if __name__ == "__main__":
    test_context_flow()