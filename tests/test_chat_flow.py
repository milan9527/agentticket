#!/usr/bin/env python3
"""
Test Chat Flow with Ticket ID

Test the complete chat flow to ensure ticket ID recognition works properly.
"""

import requests
import json

# API Configuration
API_BASE_URL = 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod'

def test_auth():
    """Test authentication"""
    print("🔐 Testing Authentication...")
    
    auth_data = {
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    }
    
    response = requests.post(f'{API_BASE_URL}/auth', json=auth_data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print("✅ Authentication successful")
            return result['tokens']['access_token']
        else:
            print("❌ Authentication failed:", result)
            return None
    else:
        print(f"❌ Auth request failed: {response.status_code}")
        return None

def test_chat_with_ticket_id(token):
    """Test chat with ticket ID"""
    print("\n💬 Testing Chat with Ticket ID...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test message with ticket ID
    chat_data = {
        'message': '550e8400-e29b-41d4-a716-446655440002',
        'conversationHistory': [],
        'context': {}
    }
    
    response = requests.post(f'{API_BASE_URL}/chat', json=chat_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Chat request successful")
        print(f"📝 Response: {result.get('response', 'No response')}")
        print(f"🎫 Show Upgrade Buttons: {result.get('showUpgradeButtons', False)}")
        print(f"🔧 Upgrade Options: {len(result.get('upgradeOptions', []))} options")
        
        if result.get('showUpgradeButtons'):
            print("✅ Ticket ID recognized and upgrade options shown!")
            return True
        else:
            print("❌ Ticket ID not recognized - no upgrade options shown")
            return False
    else:
        print(f"❌ Chat request failed: {response.status_code}")
        print(f"Response: {response.text}")
        return False

def test_chat_with_upgrade_keyword(token):
    """Test chat with upgrade keyword"""
    print("\n🔄 Testing Chat with 'upgrade' keyword...")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Test message with upgrade keyword
    chat_data = {
        'message': 'I want to upgrade my ticket',
        'conversationHistory': [],
        'context': {}
    }
    
    response = requests.post(f'{API_BASE_URL}/chat', json=chat_data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ Chat request successful")
        print(f"📝 Response: {result.get('response', 'No response')}")
        print(f"🎫 Show Upgrade Buttons: {result.get('showUpgradeButtons', False)}")
        
        if "ticket ID" in result.get('response', ''):
            print("✅ Correctly asks for ticket ID when no ID provided")
            return True
        else:
            print("❌ Should ask for ticket ID when none provided")
            return False
    else:
        print(f"❌ Chat request failed: {response.status_code}")
        return False

def main():
    """Run all tests"""
    print("🧪 TESTING CHAT FLOW")
    print("=" * 40)
    
    # Test authentication
    token = test_auth()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    # Test chat with ticket ID
    ticket_test = test_chat_with_ticket_id(token)
    
    # Test chat with upgrade keyword
    upgrade_test = test_chat_with_upgrade_keyword(token)
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 40)
    print(f"🔐 Authentication: ✅ PASS")
    print(f"🎫 Ticket ID Recognition: {'✅ PASS' if ticket_test else '❌ FAIL'}")
    print(f"🔄 Upgrade Keyword: {'✅ PASS' if upgrade_test else '❌ FAIL'}")
    
    if ticket_test and upgrade_test:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print("\n⚠️ SOME TESTS FAILED - Check implementation")

if __name__ == "__main__":
    main()