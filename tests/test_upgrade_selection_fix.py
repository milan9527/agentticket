#!/usr/bin/env python3
"""
Test Upgrade Selection Fix

This script tests the upgrade selection functionality with proper authentication.
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

def test_upgrade_selection_scenarios(token):
    """Test upgrade selection scenarios"""
    print("\n🧪 TESTING UPGRADE SELECTION SCENARIOS")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    scenarios = [
        {
            "name": "Premium Experience Selection",
            "message": "I want to proceed with the Premium Experience upgrade for 150. Please help me complete this upgrade.",
            "context": {
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "hasTicketInfo": True,
                "selectedUpgrade": {
                    "id": "premium",
                    "name": "Premium Experience",
                    "price": 150,
                    "features": ["Premium seating", "Gourmet meal", "Fast track entry", "Lounge access"]
                }
            },
            "expected": "Should process upgrade selection, not revert to greeting"
        },
        {
            "name": "Standard Upgrade Selection",
            "message": "I'd like the Standard Upgrade",
            "context": {
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "hasTicketInfo": True,
                "selectedUpgrade": {
                    "id": "standard",
                    "name": "Standard Upgrade",
                    "price": 50,
                    "features": ["Priority boarding", "Extra legroom", "Complimentary drink"]
                }
            },
            "expected": "Should process standard upgrade selection"
        },
        {
            "name": "VIP Package Selection",
            "message": "I choose the VIP Package upgrade",
            "context": {
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "hasTicketInfo": True,
                "selectedUpgrade": {
                    "id": "vip",
                    "name": "VIP Package",
                    "price": 300,
                    "features": ["VIP seating", "Meet & greet", "Exclusive merchandise", "Photo opportunities", "Backstage tour"]
                }
            },
            "expected": "Should process VIP upgrade selection"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🎯 Scenario {i}: {scenario['name']}")
        print(f"   Message: {scenario['message']}")
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
                "conversationHistory": [
                    {"role": "assistant", "content": "Here are your upgrade options with detailed pricing and features..."},
                    {"role": "user", "content": scenario['message']}
                ],
                "context": scenario['context']
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
                    print(f"   Response: {response_text[:150]}...")
                    print(f"   Show upgrade buttons: {show_buttons}")
                    
                    # Check if this is upgrade processing (not reverting to greeting)
                    is_upgrade_processing = any(phrase in response_text.lower() for phrase in [
                        'perfect choice', 'excellent choice', 'processing', 'confirmation email',
                        'upgrade now', 'being updated', 'thank you for', 'selected the'
                    ])
                    
                    is_greeting_revert = any(phrase in response_text.lower() for phrase in [
                        'hello! i\'m your ai ticket assistant',
                        'what can i help you with today',
                        'i\'m here to help you explore upgrade options'
                    ])
                    
                    if is_upgrade_processing and not is_greeting_revert:
                        print(f"   🎉 SUCCESS: Properly processing upgrade selection!")
                        status = "FIXED"
                    elif is_greeting_revert:
                        print(f"   ❌ ISSUE: Still reverting to initial greeting")
                        status = "BROKEN"
                    else:
                        print(f"   ⚠️  UNCLEAR: Response doesn't match expected patterns")
                        status = "UNCLEAR"
                    
                    results.append({
                        'scenario': scenario['name'],
                        'success': True,
                        'status': status,
                        'length': len(response_text),
                        'show_buttons': show_buttons,
                        'response_preview': response_text[:200]
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

def analyze_upgrade_fix_results(results):
    """Analyze upgrade selection fix results"""
    print("\n" + "=" * 60)
    print("📊 UPGRADE SELECTION FIX ANALYSIS")
    print("=" * 60)
    
    successful_tests = [r for r in results if r.get('success')]
    fixed_tests = [r for r in results if r.get('status') == 'FIXED']
    broken_tests = [r for r in results if r.get('status') == 'BROKEN']
    
    print(f"Total Scenarios: {len(results)}")
    print(f"Successful Tests: {len(successful_tests)}")
    print(f"Fixed (Proper Processing): {len(fixed_tests)}")
    print(f"Broken (Greeting Revert): {len(broken_tests)}")
    
    if fixed_tests:
        print(f"\n🎉 UPGRADE SELECTION FIX SUCCESS!")
        print(f"   {len(fixed_tests)} scenarios now properly process upgrade selections")
        print(f"   No longer reverting to initial AI greeting")
        
        print(f"\n✅ Fixed Scenarios:")
        for result in fixed_tests:
            print(f"   - {result['scenario']}")
            print(f"     Response: {result['response_preview'][:100]}...")
    
    if broken_tests:
        print(f"\n❌ Still Broken Scenarios:")
        for result in broken_tests:
            print(f"   - {result['scenario']}")
            print(f"     Still reverting to greeting")
    
    failed_tests = [r for r in results if not r.get('success')]
    if failed_tests:
        print(f"\n❌ Failed Tests:")
        for result in failed_tests:
            print(f"   - {result['scenario']}: {result.get('error', 'Unknown error')}")
    
    # Overall assessment
    if len(fixed_tests) == len(results):
        print(f"\n🎯 OVERALL ASSESSMENT: PERFECT FIX")
        print(f"   All upgrade selection scenarios working correctly")
        print(f"   Customer can now complete upgrade selections without issues")
    elif len(fixed_tests) >= len(results) * 0.8:
        print(f"\n🎯 OVERALL ASSESSMENT: MOSTLY FIXED")
        print(f"   Most upgrade selections working, minor issues remain")
    elif len(fixed_tests) > 0:
        print(f"\n🎯 OVERALL ASSESSMENT: PARTIALLY FIXED")
        print(f"   Some upgrade selections working, needs more work")
    else:
        print(f"\n🎯 OVERALL ASSESSMENT: NOT FIXED")
        print(f"   Upgrade selections still reverting to greeting")
        print(f"   Further debugging needed")

def main():
    """Main test function"""
    print("🔧 TESTING UPGRADE SELECTION FIX")
    print("Verifying that upgrade button clicks no longer revert to initial greeting")
    print("=" * 70)
    
    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Cannot test without valid authentication token")
        sys.exit(1)
    
    # Test upgrade selection scenarios
    results = test_upgrade_selection_scenarios(token)
    
    # Analyze results
    analyze_upgrade_fix_results(results)

if __name__ == "__main__":
    main()