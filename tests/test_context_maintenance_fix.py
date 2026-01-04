#!/usr/bin/env python3
"""
Test Context Maintenance Fix

Test the exact user scenario where:
1. User provides ticket ID
2. System validates and shows upgrade options
3. User selects upgrade
4. System should remember the ticket ID and process upgrade
"""

import requests
import json
import os
from dotenv import load_dotenv

def test_context_maintenance_fix():
    """Test the context maintenance issue"""
    
    # Load environment variables
    load_dotenv()
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    print("🔍 TESTING CONTEXT MAINTENANCE ISSUE")
    print("=" * 50)
    
    # Step 1: Get authentication token
    print("📝 Step 1: Getting authentication token")
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return False
    
    auth_data = auth_response.json()
    token = auth_data['tokens']['access_token']
    print(f"✅ Got authentication token")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 2: User provides ticket ID (first message)
    print(f"\n📝 Step 2: User provides ticket ID")
    ticket_id = "550e8400-e29b-41d4-a716-446655440002"
    
    conversation_history = []
    
    first_response = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': ticket_id,
        'context': {},
        'conversationHistory': conversation_history
    })
    
    print(f"First message status: {first_response.status_code}")
    if first_response.status_code == 200:
        first_data = first_response.json()
        print(f"✅ Ticket validation response received")
        print(f"Show upgrade buttons: {first_data['showUpgradeButtons']}")
        print(f"Response: {first_data['response'][:150]}...")
        
        # Add to conversation history
        conversation_history.append({
            'role': 'user',
            'content': ticket_id
        })
        conversation_history.append({
            'role': 'assistant', 
            'content': first_data['response']
        })
        
        if not first_data['showUpgradeButtons']:
            print("❌ Upgrade buttons not shown - validation failed")
            return False
            
    else:
        print(f"❌ First message failed: {first_response.status_code}")
        print(f"Response: {first_response.text}")
        return False
    
    # Step 3: User selects upgrade (second message) - this should remember the ticket ID
    print(f"\n📝 Step 3: User selects Standard Upgrade")
    
    # This simulates what the frontend sends when user clicks upgrade button
    upgrade_context = {
        'selectedUpgrade': {
            'id': 'standard',
            'name': 'Standard Upgrade',
            'price': 50,
            'features': ['Priority boarding', 'Extra legroom', 'Complimentary drink']
        },
        'ticketId': ticket_id,  # Frontend should include this
        'hasTicketInfo': True
    }
    
    second_response = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': 'Standard Upgrade',
        'context': upgrade_context,
        'conversationHistory': conversation_history
    })
    
    print(f"Second message status: {second_response.status_code}")
    if second_response.status_code == 200:
        second_data = second_response.json()
        print(f"Response: {second_data['response'][:200]}...")
        
        # Check if it processed the upgrade without asking for ticket ID again
        if 'need your ticket ID' in second_data['response'] or 'provide your ticket' in second_data['response']:
            print("❌ CONTEXT ISSUE: System forgot the ticket ID!")
            return False
        elif 'Standard Upgrade' in second_data['response'] and ('$50' in second_data['response'] or 'eligible' in second_data['response']):
            print("✅ Context maintained - upgrade processed successfully")
        else:
            print("⚠️ Unclear response - may not be processing upgrade correctly")
            
    else:
        print(f"❌ Second message failed: {second_response.status_code}")
        print(f"Response: {second_response.text}")
        return False
    
    # Step 4: Test without context (user types upgrade name directly)
    print(f"\n📝 Step 4: Testing upgrade selection without context")
    
    # Reset conversation but user types upgrade name directly
    direct_upgrade_response = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': 'I want the Standard Upgrade',
        'context': {},
        'conversationHistory': conversation_history  # Has previous ticket ID
    })
    
    print(f"Direct upgrade status: {direct_upgrade_response.status_code}")
    if direct_upgrade_response.status_code == 200:
        direct_data = direct_upgrade_response.json()
        print(f"Response: {direct_data['response'][:200]}...")
        
        # Should extract ticket ID from conversation history
        if 'need your ticket ID' in direct_data['response']:
            print("⚠️ System not extracting ticket ID from conversation history")
        else:
            print("✅ System extracted ticket ID from conversation history")
    
    # Step 5: Check response timing to see if it's going through AgentCore
    print(f"\n📝 Step 5: Checking response timing for AgentCore delegation")
    
    import time
    
    start_time = time.time()
    timing_response = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': ticket_id,
        'context': {},
        'conversationHistory': []
    })
    end_time = time.time()
    
    response_time = end_time - start_time
    print(f"Response time: {response_time:.2f} seconds")
    
    if response_time < 0.5:
        print("⚠️ VERY FAST RESPONSE - May not be going through AgentCore")
        print("   Expected: 1-3 seconds for AgentCore delegation")
        print("   Actual: Less than 0.5 seconds (likely hardcoded)")
    elif response_time < 2.0:
        print("✅ REASONABLE RESPONSE TIME - Likely going through AgentCore")
    else:
        print("⚠️ SLOW RESPONSE - May indicate issues with AgentCore")
    
    return True

if __name__ == "__main__":
    test_context_maintenance_fix()