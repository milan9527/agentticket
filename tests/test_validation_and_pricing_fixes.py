#!/usr/bin/env python3
"""
Test Validation and Pricing Fixes

This script tests both fixes with proper authentication:
1. Ticket validation required before showing upgrade options
2. Fixed MCP tool parameters for calculate_upgrade_pricing
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

def test_validation_and_pricing_fixes(token):
    """Test both validation and pricing fixes"""
    print("\n🧪 TESTING VALIDATION AND PRICING FIXES")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    test_scenarios = [
        {
            "name": "Issue 1: Upgrade without ticket validation",
            "message": "I want to upgrade",
            "context": {},  # No ticket info
            "expected": "Should ask for ticket ID first, not show upgrade options"
        },
        {
            "name": "Upgrade with valid ticket context",
            "message": "I want to upgrade", 
            "context": {
                "hasTicketInfo": True,
                "ticketId": "550e8400-e29b-41d4-a716-446655440002"
            },
            "expected": "Should show upgrade options with valid ticket"
        },
        {
            "name": "Issue 2: VIP upgrade selection MCP error",
            "message": "I'd like the VIP Package upgrade",
            "context": {
                "hasTicketInfo": True,
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "selectedUpgrade": {
                    "id": "vip",
                    "name": "VIP Package",
                    "price": 300,
                    "features": ["VIP seating", "Meet & greet", "Exclusive merchandise"]
                }
            },
            "expected": "Should process upgrade without MCP parameter validation errors"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🎯 Test {i}: {scenario['name']}")
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
                "conversationHistory": [],
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
                    
                    # Analyze specific fixes
                    if scenario['name'] == "Issue 1: Upgrade without ticket validation":
                        asks_for_ticket = any(phrase in response_text.lower() for phrase in [
                            "ticket information", "ticket id", "share your ticket", "550e8400"
                        ])
                        shows_options_without_ticket = show_buttons and not scenario['context'].get('hasTicketInfo')
                        
                        if asks_for_ticket and not shows_options_without_ticket:
                            print(f"   🎉 ISSUE 1 FIXED: Now requires ticket validation before showing options")
                            status = "FIXED"
                        elif shows_options_without_ticket:
                            print(f"   ❌ ISSUE 1 NOT FIXED: Still shows upgrade options without ticket validation")
                            status = "BROKEN"
                        else:
                            print(f"   ⚠️  ISSUE 1 UNCLEAR: Response doesn't match expected patterns")
                            status = "UNCLEAR"
                    
                    elif scenario['name'] == "Upgrade with valid ticket context":
                        if show_buttons:
                            print(f"   ✅ VALIDATION WORKING: Shows options with valid ticket context")
                            status = "WORKING"
                        else:
                            print(f"   ❌ VALIDATION ISSUE: Doesn't show options even with valid ticket")
                            status = "BROKEN"
                    
                    elif scenario['name'] == "Issue 2: VIP upgrade selection MCP error":
                        has_mcp_error = any(phrase in response_text for phrase in [
                            "Error executing tool", "validation error", "Field required", "ticket_type"
                        ])
                        processes_upgrade = any(phrase in response_text.lower() for phrase in [
                            "perfect choice", "excellent choice", "processing", "selected the vip"
                        ])
                        
                        if not has_mcp_error and processes_upgrade:
                            print(f"   🎉 ISSUE 2 FIXED: No MCP parameter errors, upgrade processed successfully")
                            status = "FIXED"
                        elif has_mcp_error:
                            print(f"   ❌ ISSUE 2 NOT FIXED: Still has MCP parameter validation errors")
                            status = "BROKEN"
                        else:
                            print(f"   ⚠️  ISSUE 2 UNCLEAR: Response doesn't show clear upgrade processing")
                            status = "UNCLEAR"
                    else:
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

def analyze_fix_results(results):
    """Analyze the fix results"""
    print("\n" + "=" * 60)
    print("📊 VALIDATION AND PRICING FIX ANALYSIS")
    print("=" * 60)
    
    successful_tests = [r for r in results if r.get('success')]
    fixed_tests = [r for r in results if r.get('status') == 'FIXED']
    broken_tests = [r for r in results if r.get('status') == 'BROKEN']
    working_tests = [r for r in results if r.get('status') == 'WORKING']
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful Tests: {len(successful_tests)}")
    print(f"Fixed Issues: {len(fixed_tests)}")
    print(f"Working Features: {len(working_tests)}")
    print(f"Remaining Issues: {len(broken_tests)}")
    
    if fixed_tests:
        print(f"\n🎉 ISSUES FIXED!")
        for result in fixed_tests:
            print(f"   ✅ {result['scenario']}")
            print(f"      Response: {result['response_preview'][:100]}...")
    
    if working_tests:
        print(f"\n✅ WORKING FEATURES:")
        for result in working_tests:
            print(f"   ✅ {result['scenario']}")
    
    if broken_tests:
        print(f"\n❌ STILL BROKEN:")
        for result in broken_tests:
            print(f"   ❌ {result['scenario']}")
            print(f"      Response: {result['response_preview'][:100]}...")
    
    failed_tests = [r for r in results if not r.get('success')]
    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for result in failed_tests:
            print(f"   ❌ {result['scenario']}: {result.get('error', 'Unknown error')}")
    
    # Overall assessment
    if len(fixed_tests) == 2:  # Both main issues fixed
        print(f"\n🎯 OVERALL ASSESSMENT: BOTH ISSUES FIXED")
        print(f"   ✅ Issue 1: Ticket validation now required before showing upgrades")
        print(f"   ✅ Issue 2: MCP tool parameter errors resolved")
        print(f"   ✅ Customer chat interface fully functional")
    elif len(fixed_tests) == 1:
        print(f"\n🎯 OVERALL ASSESSMENT: ONE ISSUE FIXED")
        print(f"   Partial success - one issue resolved, one remaining")
    elif len(fixed_tests) == 0 and len(broken_tests) > 0:
        print(f"\n🎯 OVERALL ASSESSMENT: ISSUES NOT FIXED")
        print(f"   Both issues still present, needs further debugging")
    else:
        print(f"\n🎯 OVERALL ASSESSMENT: UNCLEAR RESULTS")
        print(f"   Test results inconclusive, manual verification recommended")

def main():
    """Main test function"""
    print("🔧 TESTING VALIDATION AND PRICING FIXES")
    print("Testing fixes for:")
    print("  Issue 1: Upgrade options shown without ticket validation")
    print("  Issue 2: MCP tool parameter errors in upgrade selection")
    print("=" * 70)
    
    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Cannot test without valid authentication token")
        sys.exit(1)
    
    # Test the fixes
    results = test_validation_and_pricing_fixes(token)
    
    # Analyze results
    analyze_fix_results(results)

if __name__ == "__main__":
    main()