#!/usr/bin/env python3
"""
Test Valid Ticket After Security Fix

This script tests that valid tickets still work correctly after the security fix.
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

def send_chat_message(lambda_client, token, message, conversation_history=None, context=None):
    """Send a chat message to the Lambda function"""
    if conversation_history is None:
        conversation_history = []
    if context is None:
        context = {}
    
    test_payload = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": message,
            "conversationHistory": conversation_history,
            "context": context
        })
    }
    
    response = lambda_client.invoke(
        FunctionName='ticket-handler',
        InvocationType='RequestResponse',
        Payload=json.dumps(test_payload)
    )
    
    if response['StatusCode'] == 200:
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            body = json.loads(result.get('body', '{}'))
            return {
                'success': True,
                'response': body.get('response', ''),
                'showUpgradeButtons': body.get('showUpgradeButtons', False),
                'upgradeOptions': body.get('upgradeOptions', [])
            }
    
    return {'success': False, 'error': 'Request failed'}

def test_valid_ticket_scenarios(token):
    """Test valid ticket scenarios to ensure they still work"""
    print("\n🧪 TESTING VALID TICKET FUNCTIONALITY AFTER SECURITY FIX")
    print("=" * 70)
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    valid_ticket_scenarios = [
        {
            "name": "Known Valid Ticket ID",
            "ticket_id": "550e8400-e29b-41d4-a716-446655440002",
            "expected": "Should show upgrade options for valid ticket"
        },
        {
            "name": "Alternative Valid Ticket ID",
            "ticket_id": "test-ticket-789",
            "expected": "Should show upgrade options for valid ticket"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(valid_ticket_scenarios, 1):
        print(f"\n🎯 Test {i}: {scenario['name']}")
        print(f"   Ticket ID: {scenario['ticket_id']}")
        print(f"   Expected: {scenario['expected']}")
        
        # Step 1: Ask for upgrade without ticket
        conversation_history = []
        context = {}
        
        message1 = "I want to upgrade my ticket"
        response1 = send_chat_message(lambda_client, token, message1, conversation_history, context)
        
        if response1['success']:
            conversation_history.append({"role": "user", "content": message1})
            conversation_history.append({"role": "assistant", "content": response1['response']})
        
        # Step 2: Provide valid ticket ID
        message2 = f"My ticket ID is {scenario['ticket_id']}"
        
        # Update context with the valid ticket info
        context.update({
            "ticketId": scenario['ticket_id'],
            "hasTicketInfo": True
        })
        
        response2 = send_chat_message(lambda_client, token, message2, conversation_history, context)
        
        if response2['success']:
            print(f"   ✅ Response: {response2['response'][:150]}...")
            print(f"   Show upgrade buttons: {response2['showUpgradeButtons']}")
            print(f"   Upgrade options count: {len(response2['upgradeOptions'])}")
            
            # Analyze if system properly accepts valid ticket
            accepts_valid_ticket = response2['showUpgradeButtons']
            has_upgrade_options = len(response2['upgradeOptions']) > 0
            
            if accepts_valid_ticket and has_upgrade_options:
                print(f"   🎉 SUCCESS: Valid ticket properly accepted with upgrade options!")
                status = "WORKING"
            elif accepts_valid_ticket and not has_upgrade_options:
                print(f"   ⚠️  PARTIAL: Shows upgrade buttons but no options")
                status = "PARTIAL"
            else:
                print(f"   🚨 ISSUE: Valid ticket not showing upgrade options!")
                status = "BROKEN"
            
            results.append({
                'scenario': scenario['name'],
                'ticket_id': scenario['ticket_id'],
                'success': True,
                'status': status,
                'response_length': len(response2['response']),
                'shows_upgrades': accepts_valid_ticket,
                'upgrade_count': len(response2['upgradeOptions']),
                'response_preview': response2['response'][:200]
            })
        else:
            print(f"   ❌ Failed: {response2.get('error')}")
            results.append({
                'scenario': scenario['name'],
                'ticket_id': scenario['ticket_id'],
                'success': False,
                'error': response2.get('error')
            })
    
    return results

def analyze_valid_ticket_results(results):
    """Analyze valid ticket test results"""
    print("\n" + "=" * 70)
    print("🎫 VALID TICKET FUNCTIONALITY ANALYSIS")
    print("=" * 70)
    
    successful_tests = [r for r in results if r.get('success')]
    working_tests = [r for r in results if r.get('status') == 'WORKING']
    broken_tests = [r for r in results if r.get('status') == 'BROKEN']
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful Tests: {len(successful_tests)}")
    print(f"Working Tests: {len(working_tests)}")
    print(f"Broken Tests: {len(broken_tests)}")
    
    if working_tests:
        print(f"\n🎉 WORKING RESPONSES:")
        for result in working_tests:
            print(f"   ✅ {result['scenario']}")
            print(f"      Ticket: {result['ticket_id']}")
            print(f"      Shows Upgrades: {result['shows_upgrades']}")
            print(f"      Upgrade Options: {result['upgrade_count']}")
            print(f"      Response: {result['response_preview'][:100]}...")
    
    if broken_tests:
        print(f"\n🚨 BROKEN RESPONSES:")
        for result in broken_tests:
            print(f"   🚨 {result['scenario']}")
            print(f"      Ticket: {result['ticket_id']}")
            print(f"      Shows Upgrades: {result['shows_upgrades']}")
            print(f"      Response: {result['response_preview'][:100]}...")
    
    failed_tests = [r for r in results if not r.get('success')]
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for result in failed_tests:
            print(f"   ❌ {result['scenario']}: {result.get('error', 'Unknown error')}")
    
    # Overall functionality assessment
    if len(working_tests) == len(successful_tests):
        print(f"\n🎯 FUNCTIONALITY ASSESSMENT: FULLY WORKING")
        print(f"   ✅ All valid tickets properly accepted")
        print(f"   ✅ Upgrade options shown for valid tickets")
        print(f"   ✅ Security fix does not break legitimate functionality")
    elif len(working_tests) > 0:
        print(f"\n🎯 FUNCTIONALITY ASSESSMENT: PARTIALLY WORKING")
        print(f"   ⚠️  Some valid tickets working correctly")
        print(f"   🔧 May need additional fixes")
    else:
        print(f"\n🎯 FUNCTIONALITY ASSESSMENT: BROKEN")
        print(f"   🚨 CRITICAL: Valid tickets not working")
        print(f"   🚨 CRITICAL: Security fix may have broken legitimate functionality")
        print(f"   🚨 IMMEDIATE FIX REQUIRED")

def main():
    """Main test function"""
    print("🎫 TESTING VALID TICKET FUNCTIONALITY AFTER SECURITY FIX")
    print("Testing that legitimate users can still use the system normally")
    print("=" * 70)
    
    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Cannot test without valid authentication token")
        sys.exit(1)
    
    # Test valid ticket scenarios
    results = test_valid_ticket_scenarios(token)
    
    # Analyze functionality
    analyze_valid_ticket_results(results)

if __name__ == "__main__":
    main()