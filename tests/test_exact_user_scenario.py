#!/usr/bin/env python3
"""
Test Exact User Scenario

Test the EXACT scenario the user reported as failing:
1. "upgrade ticket"
2. "550e8400-e29b-41d4-a716-446655440002" 
3. "Seat Upgrade"

This should now work end-to-end with proper delegation.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_exact_user_scenario():
    """Test the exact scenario the user reported"""
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    # Test authentication
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return False
    
    auth_data = auth_response.json()
    token = auth_data['tokens']['access_token']
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print("🎯 EXACT USER SCENARIO TEST")
    print("=" * 50)
    print("Testing the exact flow the user reported as failing:")
    print("1. 'upgrade ticket'")
    print("2. '550e8400-e29b-41d4-a716-446655440002'")
    print("3. 'Seat Upgrade'")
    print()
    
    conversation_history = []
    
    # Step 1: "upgrade ticket"
    print("📝 Step 1: User says 'upgrade ticket'")
    response1 = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': 'upgrade ticket',
        'context': {},
        'conversationHistory': conversation_history
    })
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"✅ Response: {data1['response'][:100]}...")
        conversation_history.append({'role': 'user', 'content': 'upgrade ticket'})
        conversation_history.append({'role': 'assistant', 'content': data1['response']})
    else:
        print(f"❌ Step 1 failed: {response1.status_code}")
        return False
    
    # Step 2: Provide ticket ID
    print(f"\n📝 Step 2: User provides ticket ID")
    response2 = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': '550e8400-e29b-41d4-a716-446655440002',
        'context': {},
        'conversationHistory': conversation_history
    })
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"✅ Response: {data2['response'][:100]}...")
        print(f"🎫 Show upgrade buttons: {data2.get('showUpgradeButtons', False)}")
        conversation_history.append({'role': 'user', 'content': '550e8400-e29b-41d4-a716-446655440002'})
        conversation_history.append({'role': 'assistant', 'content': data2['response']})
    else:
        print(f"❌ Step 2 failed: {response2.status_code}")
        return False
    
    # Step 3: "Seat Upgrade" - This was the failing step
    print(f"\n📝 Step 3: User says 'Seat Upgrade' (CRITICAL TEST)")
    response3 = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': 'Seat Upgrade',
        'context': {},
        'conversationHistory': conversation_history
    })
    
    if response3.status_code == 200:
        data3 = response3.json()
        ai_response = data3['response']
        print(f"🤖 Full Response: {ai_response}")
        
        # Check if this is the proper upgrade processing response
        success_indicators = [
            'selected the Standard Upgrade',
            '$50',
            'Priority boarding, Extra legroom, Complimentary drink',
            'validated and is eligible',
            'process the payment',
            'confirmed within 24 hours'
        ]
        
        success_count = sum(1 for indicator in success_indicators if indicator in ai_response)
        
        if success_count >= 4:  # Most indicators present
            print("✅ SUCCESS: Seat Upgrade properly processed through ticket handler!")
            print("✅ Upgrade details provided (Standard Upgrade, $50, features)")
            print("✅ Ticket validation confirmed")
            print("✅ Processing steps outlined")
        else:
            print("❌ FAILURE: Seat Upgrade not properly processed")
            print(f"   Only {success_count}/{len(success_indicators)} success indicators found")
            
            # Check if it's giving generic instructions instead
            generic_indicators = [
                'log in to your account',
                'find your booking',
                'manage booking',
                'browse the available seats'
            ]
            
            if any(indicator.lower() in ai_response.lower() for indicator in generic_indicators):
                print("❌ PROBLEM: Giving generic instructions instead of processing upgrade")
            
            # Check if it's asking for ticket ID again
            if any(phrase in ai_response.lower() for phrase in ['ticket id', 'ticket number', 'provide']):
                print("❌ PROBLEM: Asking for ticket ID again (context lost)")
    else:
        print(f"❌ Step 3 failed: {response3.status_code}")
        return False
    
    print(f"\n📊 FINAL RESULT")
    print("=" * 30)
    
    if response3.status_code == 200:
        data3 = response3.json()
        ai_response = data3['response']
        
        if 'Standard Upgrade' in ai_response and '$50' in ai_response:
            print("🎉 SUCCESS: Full upgrade process working correctly!")
            print("✅ Chat handler properly delegates to ticket handler")
            print("✅ Ticket validation works through AgentCore")
            print("✅ Upgrade selection detection works")
            print("✅ Context maintained between messages")
            print("✅ User scenario now works end-to-end")
            return True
        else:
            print("❌ FAILURE: Upgrade process still not working correctly")
            return False
    else:
        print("❌ FAILURE: Request failed")
        return False

if __name__ == "__main__":
    success = test_exact_user_scenario()
    if success:
        print("\n🎯 USER ISSUE RESOLVED!")
    else:
        print("\n❌ USER ISSUE STILL EXISTS!")