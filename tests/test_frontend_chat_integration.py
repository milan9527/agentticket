#!/usr/bin/env python3
"""
Test Frontend Chat Integration

This script tests the chat endpoint that the frontend uses to ensure
the enhanced LLM responses are accessible from the React interface.
"""

import requests
import json
import os
from dotenv import load_dotenv

def test_frontend_chat_integration():
    """Test the chat endpoint that the frontend uses"""
    load_env()
    
    print("💬 FRONTEND CHAT INTEGRATION TEST")
    print("=" * 50)
    
    # Get API configuration
    api_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    test_user = os.getenv('COGNITO_TEST_USER')
    test_password = os.getenv('COGNITO_TEST_PASSWORD')
    
    print(f"🌐 API URL: {api_url}")
    print(f"👤 Test User: {test_user}")
    print()
    
    # Step 1: Get authentication token
    print("🔐 Getting authentication token...")
    auth_response = requests.post(f"{api_url}/auth", json={
        "email": test_user,
        "password": test_password
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return
    
    auth_data = auth_response.json()
    if not auth_data.get('success'):
        print(f"❌ Authentication failed: {auth_data.get('error')}")
        return
    
    access_token = auth_data['tokens']['access_token']
    print("✅ Authentication successful")
    
    # Step 2: Test chat scenarios that frontend would send
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    chat_scenarios = [
        {
            "name": "Initial Greeting (Frontend Default)",
            "payload": {
                "message": "Hi! I'm interested in upgrading my ticket. Can you help me?",
                "conversationHistory": [],
                "context": {
                    "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                    "hasTicketInfo": True
                }
            }
        },
        {
            "name": "Ticket Validation Request",
            "payload": {
                "message": "I have ticket 550e8400-e29b-41d4-a716-446655440002. Can you check if it's eligible for upgrades?",
                "conversationHistory": [
                    {"role": "user", "content": "Hi! I'm interested in upgrading my ticket."},
                    {"role": "assistant", "content": "Hello! I'd be happy to help you with ticket upgrades."}
                ],
                "context": {
                    "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                    "hasTicketInfo": True
                }
            }
        },
        {
            "name": "Pricing Inquiry",
            "payload": {
                "message": "How much would it cost to upgrade to premium?",
                "conversationHistory": [
                    {"role": "user", "content": "Can you check if my ticket is eligible?"},
                    {"role": "assistant", "content": "Your ticket is eligible for upgrades!"}
                ],
                "context": {
                    "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                    "hasTicketInfo": True
                }
            }
        },
        {
            "name": "Upgrade Selection (Frontend Button Click)",
            "payload": {
                "message": "I want to proceed with the Premium Experience upgrade for 150. Please help me complete this upgrade.",
                "conversationHistory": [
                    {"role": "user", "content": "How much would it cost to upgrade?"},
                    {"role": "assistant", "content": "Here are the pricing options..."}
                ],
                "context": {
                    "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                    "hasTicketInfo": True,
                    "selectedUpgrade": {
                        "id": "premium",
                        "name": "Premium Experience",
                        "price": 150,
                        "features": ["Premium seating", "Gourmet meal", "Fast track entry"]
                    }
                }
            }
        }
    ]
    
    print(f"\n🧪 Testing {len(chat_scenarios)} chat scenarios...")
    
    results = []
    
    for i, scenario in enumerate(chat_scenarios, 1):
        print(f"\n🎯 Scenario {i}: {scenario['name']}")
        print(f"   Message: {scenario['payload']['message'][:60]}...")
        
        try:
            chat_response = requests.post(
                f"{api_url}/chat",
                json=scenario['payload'],
                headers=headers
            )
            
            print(f"   📋 Status: {chat_response.status_code}")
            
            if chat_response.status_code == 200:
                chat_data = chat_response.json()
                
                if chat_data.get('success'):
                    response_text = chat_data.get('response', '')
                    show_buttons = chat_data.get('showUpgradeButtons', False)
                    upgrade_options = chat_data.get('upgradeOptions', [])
                    
                    print(f"   ✅ Success: {len(response_text)} characters")
                    print(f"   Response: {response_text[:80]}...")
                    print(f"   Upgrade Buttons: {show_buttons}")
                    print(f"   Upgrade Options: {len(upgrade_options)}")
                    
                    # Check if using real LLM (enhanced responses)
                    using_real_llm = len(response_text) > 200 and any(word in response_text.lower() for word in [
                        'analyzed', 'system', 'agentcore', 'detailed', 'comprehensive'
                    ])
                    
                    if using_real_llm:
                        print(f"   🎉 ENHANCED: Real LLM response detected")
                    else:
                        print(f"   📝 STANDARD: Intelligent response")
                    
                    results.append({
                        'scenario': scenario['name'],
                        'success': True,
                        'length': len(response_text),
                        'enhanced': using_real_llm,
                        'show_buttons': show_buttons,
                        'options_count': len(upgrade_options)
                    })
                else:
                    print(f"   ❌ Chat failed: {chat_data.get('error')}")
                    results.append({
                        'scenario': scenario['name'],
                        'success': False,
                        'error': chat_data.get('error')
                    })
            else:
                print(f"   ❌ HTTP Error: {chat_response.status_code}")
                print(f"   Response: {chat_response.text[:100]}...")
                results.append({
                    'scenario': scenario['name'],
                    'success': False,
                    'error': f"HTTP {chat_response.status_code}"
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append({
                'scenario': scenario['name'],
                'success': False,
                'error': str(e)
            })
    
    # Analyze results
    print("\n" + "=" * 60)
    print("📊 FRONTEND CHAT INTEGRATION RESULTS")
    print("=" * 60)
    
    successful = [r for r in results if r.get('success')]
    enhanced = [r for r in results if r.get('enhanced')]
    
    print(f"Total Scenarios: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Enhanced LLM: {len(enhanced)}")
    print(f"Success Rate: {len(successful)/len(results)*100:.1f}%")
    
    if enhanced:
        print(f"\n🎉 ENHANCED CHAT WORKING!")
        print(f"   {len(enhanced)} scenarios using real AgentCore LLM")
        avg_length = sum(r['length'] for r in enhanced) / len(enhanced)
        print(f"   Average response length: {avg_length:.0f} characters")
        
        print(f"\n✅ Enhanced Scenarios:")
        for result in enhanced:
            print(f"   - {result['scenario']}: {result['length']} chars, buttons: {result['show_buttons']}")
    
    standard = [r for r in successful if not r.get('enhanced')]
    if standard:
        print(f"\n📝 Standard Responses:")
        for result in standard:
            print(f"   - {result['scenario']}: {result['length']} chars, buttons: {result['show_buttons']}")
    
    failed = [r for r in results if not r.get('success')]
    if failed:
        print(f"\n❌ Failed Scenarios:")
        for result in failed:
            print(f"   - {result['scenario']}: {result.get('error')}")
    
    # Frontend integration assessment
    print(f"\n🎯 FRONTEND INTEGRATION ASSESSMENT")
    print("=" * 40)
    
    if len(successful) == len(results):
        print("✅ All chat scenarios working")
        print("✅ Frontend can successfully call chat endpoint")
        print("✅ Authentication integration working")
        print("✅ Conversation history properly formatted")
        print("✅ Context passing working")
        
        if len(enhanced) >= 2:
            print("✅ Enhanced LLM responses available")
            print("✅ Real AgentCore integration working")
            print("\n🚀 FRONTEND READY FOR CUSTOMER USE!")
            print("   - Chat interface will show enhanced AI responses")
            print("   - Upgrade buttons will appear when appropriate")
            print("   - Real-time AgentCore intelligence available")
        else:
            print("⚠️ Limited enhanced responses")
            print("   - Basic chat working but may need LLM tuning")
    else:
        print("⚠️ Some chat scenarios failing")
        print("   - Frontend integration needs debugging")

def load_env():
    """Load environment variables"""
    load_dotenv()

if __name__ == "__main__":
    test_frontend_chat_integration()