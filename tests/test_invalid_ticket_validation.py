#!/usr/bin/env python3
"""
Test Invalid Ticket Validation

This script tests what happens when users provide invalid/wrong ticket numbers.
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

def test_invalid_ticket_scenarios(token):
    """Test various invalid ticket scenarios"""
    print("\n🧪 TESTING INVALID TICKET VALIDATION")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    invalid_ticket_scenarios = [
        {
            "name": "Completely Wrong Ticket ID",
            "ticket_id": "12345678-1234-1234-1234-123456789012",
            "expected": "Should reject invalid ticket and not show upgrade options"
        },
        {
            "name": "Invalid Format Ticket ID",
            "ticket_id": "invalid-ticket-123",
            "expected": "Should reject malformed ticket ID"
        },
        {
            "name": "Non-existent Valid Format Ticket",
            "ticket_id": "99999999-9999-9999-9999-999999999999",
            "expected": "Should reject non-existent ticket"
        },
        {
            "name": "Empty Ticket ID",
            "ticket_id": "",
            "expected": "Should ask for valid ticket ID"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(invalid_ticket_scenarios, 1):
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
        
        # Step 2: Provide invalid ticket ID
        message2 = f"My ticket ID is {scenario['ticket_id']}" if scenario['ticket_id'] else "My ticket ID is "
        
        # Update context with the invalid ticket info
        context.update({
            "ticketId": scenario['ticket_id'],
            "hasTicketInfo": bool(scenario['ticket_id'])
        })
        
        response2 = send_chat_message(lambda_client, token, message2, conversation_history, context)
        
        if response2['success']:
            print(f"   ✅ Response: {response2['response'][:150]}...")
            print(f"   Show upgrade buttons: {response2['showUpgradeButtons']}")
            
            # Analyze if system properly rejects invalid ticket
            rejects_invalid_ticket = any(phrase in response2['response'].lower() for phrase in [
                "not found", "invalid", "doesn't exist", "cannot find", "not valid", 
                "unable to locate", "not in our system", "please check", "verify"
            ])
            
            allows_upgrade_with_invalid = response2['showUpgradeButtons']
            
            if rejects_invalid_ticket and not allows_upgrade_with_invalid:
                print(f"   🎉 SECURITY WORKING: Properly rejects invalid ticket")
                status = "SECURE"
            elif allows_upgrade_with_invalid:
                print(f"   🚨 SECURITY ISSUE: Shows upgrade options with invalid ticket!")
                status = "VULNERABLE"
            elif not rejects_invalid_ticket and not allows_upgrade_with_invalid:
                print(f"   ⚠️  UNCLEAR: Doesn't explicitly reject but also doesn't show upgrades")
                status = "UNCLEAR"
            else:
                print(f"   ⚠️  MIXED: Rejects ticket but behavior unclear")
                status = "MIXED"
            
            # Update conversation for potential step 3
            conversation_history.append({"role": "user", "content": message2})
            conversation_history.append({"role": "assistant", "content": response2['response']})
            
            results.append({
                'scenario': scenario['name'],
                'ticket_id': scenario['ticket_id'],
                'success': True,
                'status': status,
                'response_length': len(response2['response']),
                'shows_upgrades': allows_upgrade_with_invalid,
                'rejects_ticket': rejects_invalid_ticket,
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

def analyze_security_results(results):
    """Analyze security test results"""
    print("\n" + "=" * 60)
    print("🔒 INVALID TICKET SECURITY ANALYSIS")
    print("=" * 60)
    
    successful_tests = [r for r in results if r.get('success')]
    secure_tests = [r for r in results if r.get('status') == 'SECURE']
    vulnerable_tests = [r for r in results if r.get('status') == 'VULNERABLE']
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful Tests: {len(successful_tests)}")
    print(f"Secure Responses: {len(secure_tests)}")
    print(f"Vulnerable Responses: {len(vulnerable_tests)}")
    
    if secure_tests:
        print(f"\n🎉 SECURE RESPONSES:")
        for result in secure_tests:
            print(f"   ✅ {result['scenario']}")
            print(f"      Ticket: {result['ticket_id']}")
            print(f"      Response: {result['response_preview'][:100]}...")
    
    if vulnerable_tests:
        print(f"\n🚨 SECURITY VULNERABILITIES:")
        for result in vulnerable_tests:
            print(f"   🚨 {result['scenario']}")
            print(f"      Ticket: {result['ticket_id']}")
            print(f"      Shows Upgrades: {result['shows_upgrades']}")
            print(f"      Response: {result['response_preview'][:100]}...")
    
    failed_tests = [r for r in results if not r.get('success')]
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for result in failed_tests:
            print(f"   ❌ {result['scenario']}: {result.get('error', 'Unknown error')}")
    
    # Overall security assessment
    if len(vulnerable_tests) == 0:
        print(f"\n🎯 SECURITY ASSESSMENT: SECURE")
        print(f"   ✅ All invalid tickets properly rejected")
        print(f"   ✅ No upgrade options shown for invalid tickets")
        print(f"   ✅ System properly validates ticket existence")
    elif len(vulnerable_tests) < len(successful_tests) / 2:
        print(f"\n🎯 SECURITY ASSESSMENT: MOSTLY SECURE")
        print(f"   ⚠️  Some vulnerabilities present")
        print(f"   🔧 Needs security improvements")
    else:
        print(f"\n🎯 SECURITY ASSESSMENT: VULNERABLE")
        print(f"   🚨 CRITICAL: System accepts invalid tickets")
        print(f"   🚨 CRITICAL: Shows upgrade options without proper validation")
        print(f"   🚨 IMMEDIATE FIX REQUIRED")

def main():
    """Main test function"""
    print("🔒 TESTING INVALID TICKET VALIDATION SECURITY")
    print("Testing what happens when users provide wrong/invalid ticket numbers")
    print("=" * 70)
    
    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Cannot test without valid authentication token")
        sys.exit(1)
    
    # Test invalid ticket scenarios
    results = test_invalid_ticket_scenarios(token)
    
    # Analyze security implications
    analyze_security_results(results)

if __name__ == "__main__":
    main()