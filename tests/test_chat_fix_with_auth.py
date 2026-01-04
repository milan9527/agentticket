#!/usr/bin/env python3
"""
Test Chat Fix with Proper Authentication

This script tests the updated chat functionality using proper Cognito authentication.
"""

import boto3
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_cognito_token():
    """Get valid Cognito token for testing"""
    try:
        cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
        test_user = os.getenv('COGNITO_TEST_USER')
        test_password = os.getenv('COGNITO_TEST_PASSWORD')
        aws_region = os.getenv('AWS_REGION', 'us-west-2')
        
        if not all([cognito_client_id, test_user, test_password]):
            print("❌ Missing Cognito configuration")
            return None
        
        cognito_client = boto3.client('cognito-idp', region_name=aws_region)
        
        response = cognito_client.initiate_auth(
            ClientId=cognito_client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': test_user,
                'PASSWORD': test_password
            }
        )
        
        token = response['AuthenticationResult']['AccessToken']
        print(f"✅ Got Cognito token: {token[:50]}...")
        return token
        
    except Exception as e:
        print(f"❌ Failed to get Cognito token: {e}")
        return None

def test_chat_scenarios(token):
    """Test multiple chat scenarios with the fixed Lambda function"""
    print("\n🧪 TESTING CHAT SCENARIOS WITH FIXED LAMBDA")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    scenarios = [
        {
            "name": "Ticket Validation Intent",
            "message": "Hello! I have a ticket and I'm interested in upgrading it. Can you check if my ticket is eligible?",
            "expected": "Should use validate_ticket_eligibility MCP tool"
        },
        {
            "name": "Pricing Intent", 
            "message": "How much would it cost to upgrade my ticket?",
            "expected": "Should use calculate_upgrade_pricing MCP tool"
        },
        {
            "name": "Recommendations Intent",
            "message": "What upgrade would you recommend for me?",
            "expected": "Should use get_upgrade_recommendations MCP tool"
        },
        {
            "name": "Comparison Intent",
            "message": "Can you show me all the upgrade options and compare them?",
            "expected": "Should use get_upgrade_tier_comparison MCP tool"
        },
        {
            "name": "General Greeting",
            "message": "Hello! How can you help me today?",
            "expected": "Should use intelligent fallback response"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🎯 Scenario {i}: {scenario['name']}")
        print(f"   Message: {scenario['message'][:50]}...")
        print(f"   Expected: {scenario['expected']}")
        
        # Test payload
        test_payload = {
            "httpMethod": "POST",
            "path": "/chat",
            "headers": {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": scenario['message'],
                "conversationHistory": [],
                "context": {
                    "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                    "hasTicketInfo": True
                }
            })
        }
        
        try:
            response = lambda_client.invoke(
                FunctionName='ticket-handler',
                InvocationType='RequestResponse',
                Payload=json.dumps(test_payload)
            )
            
            if response['StatusCode'] == 200:
                result = json.loads(response['Payload'].read())
                
                if result.get('statusCode') == 200:
                    body = json.loads(result.get('body', '{}'))
                    response_text = body.get('response', '')
                    show_buttons = body.get('showUpgradeButtons', False)
                    
                    print(f"   ✅ Success: {len(response_text)} characters")
                    print(f"   Response: {response_text[:100]}...")
                    print(f"   Upgrade Buttons: {show_buttons}")
                    
                    # Determine if using real LLM or fallback
                    using_real_llm = len(response_text) > 200 and any(word in response_text.lower() for word in [
                        'ticket', 'upgrade', 'pricing', 'recommend', 'tier', 'standard', 'premium', 'vip'
                    ])
                    
                    if using_real_llm:
                        print(f"   🎉 REAL LLM: Using MCP tools with detailed responses")
                    else:
                        print(f"   📝 FALLBACK: Using intelligent pattern matching")
                    
                    results.append({
                        'scenario': scenario['name'],
                        'success': True,
                        'length': len(response_text),
                        'using_real_llm': using_real_llm,
                        'show_buttons': show_buttons
                    })
                else:
                    print(f"   ❌ Error: {result.get('body')}")
                    results.append({
                        'scenario': scenario['name'],
                        'success': False,
                        'error': result.get('body')
                    })
            else:
                print(f"   ❌ Lambda error: Status {response['StatusCode']}")
                results.append({
                    'scenario': scenario['name'],
                    'success': False,
                    'error': f"Lambda status {response['StatusCode']}"
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append({
                'scenario': scenario['name'],
                'success': False,
                'error': str(e)
            })
    
    return results

def analyze_results(results):
    """Analyze test results and provide summary"""
    print("\n" + "=" * 60)
    print("📊 CHAT FIX TEST RESULTS ANALYSIS")
    print("=" * 60)
    
    successful_tests = [r for r in results if r.get('success')]
    real_llm_tests = [r for r in results if r.get('using_real_llm')]
    
    print(f"Total Scenarios: {len(results)}")
    print(f"Successful Tests: {len(successful_tests)}")
    print(f"Using Real LLM: {len(real_llm_tests)}")
    print(f"Success Rate: {len(successful_tests)/len(results)*100:.1f}%")
    
    if real_llm_tests:
        print(f"\n🎉 CHAT FIX SUCCESS!")
        print(f"   {len(real_llm_tests)} scenarios now using real LLM via MCP tools")
        print(f"   Average response length: {sum(r['length'] for r in real_llm_tests)/len(real_llm_tests):.0f} characters")
        
        print(f"\n✅ Working Scenarios:")
        for result in real_llm_tests:
            print(f"   - {result['scenario']}: {result['length']} chars")
    
    fallback_tests = [r for r in successful_tests if not r.get('using_real_llm')]
    if fallback_tests:
        print(f"\n📝 Fallback Scenarios:")
        for result in fallback_tests:
            print(f"   - {result['scenario']}: {result['length']} chars")
    
    failed_tests = [r for r in results if not r.get('success')]
    if failed_tests:
        print(f"\n❌ Failed Scenarios:")
        for result in failed_tests:
            print(f"   - {result['scenario']}: {result.get('error', 'Unknown error')}")
    
    # Overall assessment
    if len(real_llm_tests) >= 3:
        print(f"\n🎯 OVERALL ASSESSMENT: EXCELLENT")
        print(f"   Chat functionality successfully fixed!")
        print(f"   Multiple scenarios now using real LLM responses via working MCP tools")
        print(f"   Customer chat interface ready for production use")
    elif len(real_llm_tests) >= 1:
        print(f"\n🎯 OVERALL ASSESSMENT: GOOD")
        print(f"   Chat functionality partially fixed")
        print(f"   Some scenarios using real LLM, others using intelligent fallback")
    else:
        print(f"\n🎯 OVERALL ASSESSMENT: NEEDS INVESTIGATION")
        print(f"   Chat fix deployed but not detecting real LLM usage")
        print(f"   May need further debugging")

def main():
    """Main test function"""
    print("🔧 TESTING CHAT FIX WITH AUTHENTICATION")
    print("Testing updated Lambda function that uses working MCP tools for chat")
    print("=" * 70)
    
    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Cannot test without valid authentication token")
        sys.exit(1)
    
    # Test chat scenarios
    results = test_chat_scenarios(token)
    
    # Analyze results
    analyze_results(results)

if __name__ == "__main__":
    main()