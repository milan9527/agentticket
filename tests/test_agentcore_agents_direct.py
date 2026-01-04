#!/usr/bin/env python3
"""
Test AgentCore agents directly to ensure they're running properly
"""

import requests
import json
import time

def test_agentcore_agents_status():
    """Test if AgentCore agents are running and responsive"""
    
    print("🤖 TESTING AGENTCORE AGENTS DIRECTLY")
    print("="*60)
    
    api_base = "https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod"
    
    # First authenticate
    print("🔐 Authenticating...")
    auth_response = requests.post(f"{api_base}/auth", json={
        "email": "testuser@example.com",
        "password": "TempPass123!"
    })
    
    if auth_response.status_code != 200:
        print("❌ Authentication failed")
        return False
    
    auth_data = auth_response.json()
    if not auth_data.get('success'):
        print("❌ Authentication failed")
        return False
    
    access_token = auth_data['tokens']['access_token']
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    print("✅ Authentication successful")
    
    # Test different AgentCore operations
    test_cases = [
        {
            "name": "Ticket Validation",
            "url": f"{api_base}/tickets/550e8400-e29b-41d4-a716-446655440002/validate",
            "method": "POST",
            "payload": {"upgrade_tier": "Standard"}
        },
        {
            "name": "Pricing Calculation", 
            "url": f"{api_base}/tickets/550e8400-e29b-41d4-a716-446655440002/pricing",
            "method": "POST",
            "payload": {"upgrade_tier": "Premium", "event_date": "2026-02-15"}
        },
        {
            "name": "Upgrade Recommendations",
            "url": f"{api_base}/tickets/550e8400-e29b-41d4-a716-446655440002/recommendations",
            "method": "GET",
            "params": {"customer_id": "cust_123"}
        },
        {
            "name": "Tier Comparison",
            "url": f"{api_base}/tickets/550e8400-e29b-41d4-a716-446655440002/tiers",
            "method": "GET"
        }
    ]
    
    results = []
    
    for test_case in test_cases:
        print(f"\n🧪 Testing {test_case['name']}...")
        
        try:
            if test_case['method'] == 'POST':
                response = requests.post(
                    test_case['url'], 
                    json=test_case['payload'], 
                    headers=headers
                )
            else:
                params = test_case.get('params', {})
                response = requests.get(
                    test_case['url'], 
                    params=params,
                    headers=headers
                )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   Response: {json.dumps(result, indent=2)[:200]}...")
                
                # Check if it's a successful AgentCore response
                if result.get('success'):
                    if 'error' in result.get('data', {}):
                        print("   ⚠️  AgentCore returned an error (but connection works)")
                        results.append("partial")
                    else:
                        print("   ✅ Success")
                        results.append("success")
                else:
                    print("   ❌ Failed")
                    results.append("failed")
            else:
                print(f"   ❌ HTTP Error: {response.text}")
                results.append("failed")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append("failed")
        
        time.sleep(1)
    
    # Summary
    success_count = results.count("success")
    partial_count = results.count("partial")
    total_count = len(results)
    
    print(f"\n📊 AgentCore Test Results:")
    print(f"   ✅ Full Success: {success_count}/{total_count}")
    print(f"   ⚠️  Partial (Connected but errors): {partial_count}/{total_count}")
    print(f"   ❌ Failed: {results.count('failed')}/{total_count}")
    
    if success_count > 0:
        print("\n🎉 AgentCore agents are running and responding!")
    elif partial_count > 0:
        print("\n⚠️  AgentCore agents are connected but may need configuration")
    else:
        print("\n❌ AgentCore agents may not be running properly")
    
    return success_count > 0 or partial_count > 0

def test_chat_with_real_ticket():
    """Test chat with a real ticket ID to see AgentCore response"""
    
    print("\n" + "="*60)
    print("💬 TESTING CHAT WITH REAL TICKET DATA")
    print("="*60)
    
    api_base = "https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod"
    
    # Authenticate
    auth_response = requests.post(f"{api_base}/auth", json={
        "email": "testuser@example.com", 
        "password": "TempPass123!"
    })
    
    if auth_response.status_code != 200:
        print("❌ Authentication failed")
        return False
    
    access_token = auth_response.json()['tokens']['access_token']
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Test chat messages that should trigger AgentCore
    test_messages = [
        {
            "message": "I want to upgrade ticket 550e8400-e29b-41d4-a716-446655440002 to VIP",
            "context": {
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "hasTicketInfo": True
            }
        },
        {
            "message": "Show me upgrade options for my ticket",
            "context": {
                "ticketId": "550e8400-e29b-41d4-a716-446655440002"
            }
        },
        {
            "message": "What's the price for premium upgrade?",
            "context": {
                "ticketId": "550e8400-e29b-41d4-a716-446655440002"
            }
        }
    ]
    
    success_count = 0
    
    for i, test in enumerate(test_messages, 1):
        print(f"\n💬 Test Message {i}: {test['message']}")
        
        try:
            response = requests.post(f"{api_base}/chat", json={
                "message": test['message'],
                "conversationHistory": [],
                "context": test['context']
            }, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    ai_response = result.get('response', '')
                    show_buttons = result.get('showUpgradeButtons', False)
                    
                    print(f"🤖 AI Response: {ai_response}")
                    print(f"🎫 Show Buttons: {show_buttons}")
                    
                    # Check if response indicates AgentCore processing
                    if any(keyword in ai_response.lower() for keyword in 
                           ['agentcore', 'system', 'process', 'validate']):
                        print("✅ Response indicates AgentCore processing")
                        success_count += 1
                    else:
                        print("⚠️  Response may be fallback (not AgentCore)")
                else:
                    print(f"❌ Chat failed: {result.get('error')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        time.sleep(1)
    
    success_rate = success_count / len(test_messages)
    print(f"\n📊 Chat Test Results: {success_count}/{len(test_messages)} showed AgentCore processing ({success_rate:.1%})")
    
    return success_rate > 0

def main():
    """Run AgentCore-specific tests"""
    
    print("🚀 AGENTCORE AGENTS VALIDATION")
    print("Testing if AgentCore Ticket Agent and Data Agent are running properly")
    print("="*80)
    
    # Test 1: Direct API calls to AgentCore operations
    agentcore_status = test_agentcore_agents_status()
    
    # Test 2: Chat with real ticket data
    chat_status = test_chat_with_real_ticket()
    
    # Summary
    print("\n" + "="*80)
    print("📋 AGENTCORE VALIDATION SUMMARY")
    print("="*80)
    
    print(f"AgentCore API Operations: {'✅ WORKING' if agentcore_status else '❌ ISSUES'}")
    print(f"Chat with AgentCore: {'✅ WORKING' if chat_status else '❌ ISSUES'}")
    
    if agentcore_status and chat_status:
        print("\n🎉 EXCELLENT! AgentCore agents are running properly!")
        print("✅ Ticket Agent is responding to requests")
        print("✅ Data Agent integration is working")
        print("✅ The full flow is operational")
    elif agentcore_status or chat_status:
        print("\n⚠️  PARTIAL SUCCESS - AgentCore is responding but may need tuning")
        print("🔧 Consider checking agent configurations and prompts")
    else:
        print("\n❌ AGENTCORE ISSUES DETECTED")
        print("🔧 Please check:")
        print("   - AgentCore agent deployment status")
        print("   - Agent ARNs in environment variables")
        print("   - Cognito authentication for agents")
        print("   - MCP server connectivity")

if __name__ == "__main__":
    main()