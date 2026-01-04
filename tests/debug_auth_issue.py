#!/usr/bin/env python3
"""
Debug Authentication Issue

Test authentication flow to identify why chat handler is getting 401 errors
when calling ticket handler.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_auth_issue():
    """Debug the authentication issue between chat and ticket handler"""
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    print("🔍 DEBUGGING AUTHENTICATION ISSUE")
    print("=" * 50)
    
    # Step 1: Test authentication endpoint
    print("📝 Step 1: Testing authentication endpoint")
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        print(auth_response.text)
        return False
    
    auth_data = auth_response.json()
    token = auth_data['tokens']['access_token']
    print(f"✅ Authentication successful, token length: {len(token)}")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 2: Test direct ticket handler call
    print(f"\n📝 Step 2: Testing direct ticket handler call")
    direct_response = requests.post(
        f'{api_base_url}/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
        headers=headers,
        json={'upgrade_tier': 'Standard Upgrade'}
    )
    
    print(f"Direct ticket handler status: {direct_response.status_code}")
    if direct_response.status_code == 200:
        print("✅ Direct ticket handler works fine")
        direct_data = direct_response.json()
        print(f"Response: {direct_data}")
    else:
        print(f"❌ Direct ticket handler failed: {direct_response.status_code}")
        print(f"Response: {direct_response.text}")
    
    # Step 3: Test chat handler call
    print(f"\n📝 Step 3: Testing chat handler call")
    chat_response = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': '550e8400-e29b-41d4-a716-446655440002',
        'context': {},
        'conversationHistory': []
    })
    
    print(f"Chat handler status: {chat_response.status_code}")
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        print(f"Chat response: {chat_data['response'][:100]}...")
        
        # Check if the response indicates a 401 error
        if '401' in chat_data['response']:
            print("❌ Chat handler is getting 401 when calling ticket handler")
        else:
            print("✅ Chat handler working correctly")
    else:
        print(f"❌ Chat handler failed: {chat_response.status_code}")
        print(f"Response: {chat_response.text}")
    
    # Step 4: Check environment variables
    print(f"\n📝 Step 4: Checking environment variables")
    print(f"API_GATEWAY_URL: {api_base_url}")
    
    # Step 5: Test with different API Gateway URL format
    print(f"\n📝 Step 5: Testing API Gateway URL variations")
    
    # Check if there's a mismatch in the URL
    test_urls = [
        'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod',
        'https://zno1ww5qr5.execute-api.us-west-2.amazonaws.com/prod'
    ]
    
    for test_url in test_urls:
        print(f"Testing URL: {test_url}")
        test_response = requests.post(
            f'{test_url}/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
            headers=headers,
            json={'upgrade_tier': 'Standard Upgrade'}
        )
        print(f"  Status: {test_response.status_code}")
        if test_response.status_code == 200:
            print(f"  ✅ This URL works!")
        elif test_response.status_code == 401:
            print(f"  ❌ 401 Unauthorized")
        else:
            print(f"  ⚠️ Other error: {test_response.status_code}")
    
    return True

if __name__ == "__main__":
    debug_auth_issue()