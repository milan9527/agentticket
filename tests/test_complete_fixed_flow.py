#!/usr/bin/env python3
"""
Test Complete Fixed Flow

This script tests the complete customer journey with both fixes applied.
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

def test_complete_fixed_flow(token):
    """Test the complete customer journey with fixes"""
    print("\n🧪 TESTING COMPLETE FIXED CUSTOMER JOURNEY")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    conversation_history = []
    context = {}
    
    # Step 1: Customer asks about upgrades WITHOUT providing ticket (should ask for ticket)
    print("\n📝 Step 1: Customer asks about upgrades without ticket")
    message1 = "I want to upgrade my ticket"
    
    response1 = send_chat_message(lambda_client, token, message1, conversation_history, context)
    
    if response1['success']:
        print(f"   ✅ Response: {response1['response'][:100]}...")
        print(f"   Show buttons: {response1['showUpgradeButtons']}")
        
        # Check if it asks for ticket validation
        asks_for_ticket = any(phrase in response1['response'].lower() for phrase in [
            "ticket information", "ticket id", "share your ticket"
        ])
        
        if asks_for_ticket and not response1['showUpgradeButtons']:
            print(f"   🎉 VALIDATION WORKING: Properly asks for ticket before showing options")
            step1_status = "WORKING"
        else:
            print(f"   ❌ VALIDATION ISSUE: Should ask for ticket first")
            step1_status = "BROKEN"
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": message1})
        conversation_history.append({"role": "assistant", "content": response1['response']})
    else:
        print(f"   ❌ Failed: {response1.get('error')}")
        step1_status = "FAILED"
    
    # Step 2: Customer provides ticket ID
    print("\n📝 Step 2: Customer provides ticket ID")
    message2 = "My ticket ID is 550e8400-e29b-41d4-a716-446655440002"
    
    # Update context with ticket info
    context.update({
        "ticketId": "550e8400-e29b-41d4-a716-446655440002",
        "hasTicketInfo": True
    })
    
    response2 = send_chat_message(lambda_client, token, message2, conversation_history, context)
    
    if response2['success']:
        print(f"   ✅ Response: {response2['response'][:100]}...")
        print(f"   Show buttons: {response2['showUpgradeButtons']}")
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": message2})
        conversation_history.append({"role": "assistant", "content": response2['response']})
        
        step2_status = "WORKING"
    else:
        print(f"   ❌ Failed: {response2.get('error')}")
        step2_status = "FAILED"
    
    # Step 3: Customer asks for upgrades again (now should show options)
    print("\n📝 Step 3: Customer asks for upgrades with valid ticket")
    message3 = "Now can you show me upgrade options?"
    
    response3 = send_chat_message(lambda_client, token, message3, conversation_history, context)
    
    if response3['success']:
        print(f"   ✅ Response: {response3['response'][:100]}...")
        print(f"   Show buttons: {response3['showUpgradeButtons']}")
        
        if response3['showUpgradeButtons'] and response3['upgradeOptions']:
            print(f"   🎉 VALIDATION WORKING: Shows upgrade options with valid ticket")
            step3_status = "WORKING"
            
            # Update context with upgrade options
            context['upgradeOptions'] = response3['upgradeOptions']
            context['hasUpgradeOptions'] = True
        else:
            print(f"   ❌ VALIDATION ISSUE: Should show upgrade options with valid ticket")
            step3_status = "BROKEN"
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": message3})
        conversation_history.append({"role": "assistant", "content": response3['response']})
    else:
        print(f"   ❌ Failed: {response3.get('error')}")
        step3_status = "FAILED"
    
    # Step 4: Customer selects specific upgrade (should work without MCP errors)
    print("\n📝 Step 4: Customer selects Premium Experience upgrade")
    message4 = "I'd like the Premium Experience upgrade"
    
    # Add selected upgrade to context
    context['selectedUpgrade'] = {
        "id": "premium",
        "name": "Premium Experience",
        "price": 150,
        "features": ["Premium seating", "Gourmet meal", "Fast track entry", "Lounge access"]
    }
    
    response4 = send_chat_message(lambda_client, token, message4, conversation_history, context)
    
    if response4['success']:
        print(f"   ✅ Response: {response4['response'][:150]}...")
        print(f"   Show buttons: {response4['showUpgradeButtons']}")
        
        # Check for MCP errors and proper upgrade processing
        has_mcp_error = any(phrase in response4['response'] for phrase in [
            "Error executing tool", "validation error", "Field required"
        ])
        processes_upgrade = any(phrase in response4['response'].lower() for phrase in [
            "perfect choice", "excellent choice", "processing", "selected the premium"
        ])
        
        if not has_mcp_error and processes_upgrade:
            print(f"   🎉 UPGRADE PROCESSING WORKING: No MCP errors, upgrade processed successfully")
            step4_status = "WORKING"
        elif has_mcp_error:
            print(f"   ❌ MCP ERROR: Still has parameter validation errors")
            step4_status = "BROKEN"
        else:
            print(f"   ⚠️  UNCLEAR: Response doesn't show clear upgrade processing")
            step4_status = "UNCLEAR"
    else:
        print(f"   ❌ Failed: {response4.get('error')}")
        step4_status = "FAILED"
    
    return {
        'step1_validation': step1_status,
        'step2_ticket_provided': step2_status,
        'step3_options_shown': step3_status,
        'step4_upgrade_processed': step4_status
    }

def main():
    """Main test function"""
    print("🔧 TESTING COMPLETE FIXED CUSTOMER JOURNEY")
    print("Testing the full flow with both fixes applied:")
    print("  ✅ Fix 1: Ticket validation required before showing upgrades")
    print("  ✅ Fix 2: MCP tool parameter errors resolved")
    print("=" * 70)
    
    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Cannot test without valid authentication token")
        sys.exit(1)
    
    # Test complete flow
    results = test_complete_fixed_flow(token)
    
    print("\n" + "=" * 60)
    print("📊 COMPLETE FIXED FLOW RESULTS")
    print("=" * 60)
    
    print(f"Step 1 (Validation Check): {'✅ Working' if results['step1_validation'] == 'WORKING' else '❌ ' + results['step1_validation']}")
    print(f"Step 2 (Ticket Provided): {'✅ Working' if results['step2_ticket_provided'] == 'WORKING' else '❌ ' + results['step2_ticket_provided']}")
    print(f"Step 3 (Options Shown): {'✅ Working' if results['step3_options_shown'] == 'WORKING' else '❌ ' + results['step3_options_shown']}")
    print(f"Step 4 (Upgrade Processed): {'✅ Working' if results['step4_upgrade_processed'] == 'WORKING' else '❌ ' + results['step4_upgrade_processed']}")
    
    working_steps = sum(1 for status in results.values() if status == 'WORKING')
    
    if working_steps == 4:
        print(f"\n🎉 COMPLETE SUCCESS!")
        print(f"   ✅ All 4 steps working perfectly")
        print(f"   ✅ Issue 1 FIXED: Ticket validation required before upgrades")
        print(f"   ✅ Issue 2 FIXED: No MCP parameter errors in upgrade processing")
        print(f"   ✅ Customer chat interface fully functional end-to-end")
    elif working_steps >= 3:
        print(f"\n🎯 MOSTLY WORKING")
        print(f"   {working_steps}/4 steps working correctly")
        print(f"   Minor issues may remain")
    elif working_steps >= 2:
        print(f"\n⚠️  PARTIALLY WORKING")
        print(f"   {working_steps}/4 steps working correctly")
        print(f"   Some issues still present")
    else:
        print(f"\n❌ MAJOR ISSUES REMAIN")
        print(f"   Only {working_steps}/4 steps working correctly")
        print(f"   Significant debugging needed")

if __name__ == "__main__":
    main()