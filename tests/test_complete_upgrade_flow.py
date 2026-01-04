#!/usr/bin/env python3
"""
Test Complete Upgrade Flow

This script tests the complete upgrade flow from initial chat to upgrade selection.
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

def test_complete_upgrade_flow(token):
    """Test the complete upgrade flow from start to finish"""
    print("\n🧪 TESTING COMPLETE UPGRADE FLOW")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    conversation_history = []
    context = {}
    
    # Step 1: Initial ticket inquiry
    print("\n📝 Step 1: Customer provides ticket ID")
    message1 = "Hi, I have ticket 550e8400-e29b-41d4-a716-446655440002 and I'm interested in upgrading"
    
    response1 = send_chat_message(lambda_client, token, message1, conversation_history, context)
    
    if response1['success']:
        print(f"   ✅ Response: {response1['response'][:100]}...")
        print(f"   Show buttons: {response1['showUpgradeButtons']}")
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": message1})
        conversation_history.append({"role": "assistant", "content": response1['response']})
        
        # Update context if ticket was recognized
        if '550e8400' in response1['response']:
            context.update({
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "hasTicketInfo": True
            })
        
        if response1['showUpgradeButtons'] and response1['upgradeOptions']:
            context['upgradeOptions'] = response1['upgradeOptions']
            context['hasUpgradeOptions'] = True
    else:
        print(f"   ❌ Failed: {response1.get('error')}")
        return False
    
    # Step 2: Customer asks for upgrade options (if not already shown)
    if not response1['showUpgradeButtons']:
        print("\n📝 Step 2: Customer asks for upgrade options")
        message2 = "Can you show me the available upgrade options?"
        
        response2 = send_chat_message(lambda_client, token, message2, conversation_history, context)
        
        if response2['success']:
            print(f"   ✅ Response: {response2['response'][:100]}...")
            print(f"   Show buttons: {response2['showUpgradeButtons']}")
            
            # Update conversation history
            conversation_history.append({"role": "user", "content": message2})
            conversation_history.append({"role": "assistant", "content": response2['response']})
            
            if response2['upgradeOptions']:
                context['upgradeOptions'] = response2['upgradeOptions']
                context['hasUpgradeOptions'] = True
        else:
            print(f"   ❌ Failed: {response2.get('error')}")
            return False
    else:
        print("\n📝 Step 2: Upgrade options already shown in step 1")
        response2 = response1
    
    # Step 3: Customer selects an upgrade (this is the critical test)
    print("\n📝 Step 3: Customer selects Premium Experience upgrade")
    message3 = "I'd like the Premium Experience upgrade"
    
    # Add selected upgrade to context
    context['selectedUpgrade'] = {
        "id": "premium",
        "name": "Premium Experience", 
        "price": 150,
        "features": ["Premium seating", "Gourmet meal", "Fast track entry", "Lounge access"]
    }
    
    response3 = send_chat_message(lambda_client, token, message3, conversation_history, context)
    
    if response3['success']:
        print(f"   ✅ Response: {response3['response'][:150]}...")
        print(f"   Show buttons: {response3['showUpgradeButtons']}")
        
        # Check if this is proper upgrade processing
        is_upgrade_processing = any(phrase in response3['response'].lower() for phrase in [
            'perfect choice', 'excellent choice', 'processing', 'confirmation email',
            'upgrade now', 'being updated', 'thank you for', 'selected the'
        ])
        
        is_greeting_revert = any(phrase in response3['response'].lower() for phrase in [
            'hello! i\'m your ai ticket assistant',
            'what can i help you with today',
            'i\'m here to help you explore upgrade options'
        ])
        
        if is_upgrade_processing and not is_greeting_revert:
            print(f"   🎉 SUCCESS: Upgrade selection properly processed!")
            upgrade_status = "WORKING"
        elif is_greeting_revert:
            print(f"   ❌ ISSUE: Reverted to initial greeting")
            upgrade_status = "BROKEN"
        else:
            print(f"   ⚠️  UNCLEAR: Unexpected response pattern")
            upgrade_status = "UNCLEAR"
    else:
        print(f"   ❌ Failed: {response3.get('error')}")
        upgrade_status = "FAILED"
    
    return {
        'step1_success': response1['success'],
        'step1_shows_buttons': response1['showUpgradeButtons'],
        'step2_success': response2['success'],
        'step2_shows_buttons': response2['showUpgradeButtons'],
        'step3_success': response3['success'],
        'step3_upgrade_status': upgrade_status,
        'conversation_length': len(conversation_history)
    }

def main():
    """Main test function"""
    print("🔧 TESTING COMPLETE UPGRADE FLOW")
    print("Testing the full customer journey from ticket inquiry to upgrade selection")
    print("=" * 70)
    
    # Get authentication token
    token = get_cognito_token()
    if not token:
        print("❌ Cannot test without valid authentication token")
        sys.exit(1)
    
    # Test complete flow
    results = test_complete_upgrade_flow(token)
    
    if results:
        print("\n" + "=" * 60)
        print("📊 COMPLETE UPGRADE FLOW RESULTS")
        print("=" * 60)
        
        print(f"Step 1 (Ticket Inquiry): {'✅ Success' if results['step1_success'] else '❌ Failed'}")
        print(f"Step 1 Shows Buttons: {'✅ Yes' if results['step1_shows_buttons'] else '📝 No (normal)'}")
        
        print(f"Step 2 (Show Options): {'✅ Success' if results['step2_success'] else '❌ Failed'}")
        print(f"Step 2 Shows Buttons: {'✅ Yes' if results['step2_shows_buttons'] else '❌ No'}")
        
        print(f"Step 3 (Upgrade Selection): {'✅ Success' if results['step3_success'] else '❌ Failed'}")
        print(f"Step 3 Upgrade Processing: {results['step3_upgrade_status']}")
        
        if results['step3_upgrade_status'] == 'WORKING':
            print(f"\n🎉 COMPLETE UPGRADE FLOW SUCCESS!")
            print(f"   ✅ Customer can provide ticket ID")
            print(f"   ✅ System shows upgrade options")
            print(f"   ✅ Customer can select upgrades without reverting to greeting")
            print(f"   ✅ Full customer journey working end-to-end")
        elif results['step3_upgrade_status'] == 'BROKEN':
            print(f"\n❌ UPGRADE SELECTION STILL BROKEN")
            print(f"   Customer selections still revert to initial greeting")
        else:
            print(f"\n⚠️  UPGRADE FLOW NEEDS INVESTIGATION")
            print(f"   Some steps working, others need attention")
    else:
        print(f"\n❌ COMPLETE FLOW TEST FAILED")

if __name__ == "__main__":
    main()