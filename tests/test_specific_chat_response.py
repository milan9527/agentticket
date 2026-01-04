#!/usr/bin/env python3
"""
Test Specific Chat Response

This script tests the exact chat scenario the user is experiencing
to see what response they're getting.
"""

import boto3
import json
import os
from dotenv import load_dotenv

def test_specific_chat_response():
    """Test the specific chat response the user is seeing"""
    load_dotenv()
    
    print("🔍 TESTING SPECIFIC CHAT RESPONSE")
    print("=" * 50)
    
    # Get authentication token
    cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
    test_user = os.getenv('COGNITO_TEST_USER')
    test_password = os.getenv('COGNITO_TEST_PASSWORD')
    aws_region = os.getenv('AWS_REGION', 'us-west-2')
    
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
    print(f"✅ Got token: {token[:50]}...")
    
    # Test the exact scenario
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # This is likely what the user typed
    test_payload = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "I have ticket 550e8400-e29b-41d4-a716-446655440002. Can you check if it's eligible for upgrades?",
            "conversationHistory": [],
            "context": {
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "hasTicketInfo": True
            }
        })
    }
    
    print(f"\n🎯 Testing exact user scenario...")
    print(f"Message: 'I have ticket 550e8400-e29b-41d4-a716-446655440002. Can you check if it's eligible for upgrades?'")
    
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
                upgrade_options = body.get('upgradeOptions', [])
                
                print(f"\n📋 RESPONSE ANALYSIS:")
                print(f"✅ Status: Success")
                print(f"📏 Length: {len(response_text)} characters")
                print(f"🔘 Upgrade Buttons: {show_buttons}")
                print(f"📦 Upgrade Options: {len(upgrade_options)}")
                print(f"\n📝 FULL RESPONSE:")
                print(f"{response_text}")
                print(f"\n" + "="*60)
                
                # Check if this contains the error message
                if "validation failed" in response_text.lower():
                    print("❌ FOUND THE ISSUE: Response contains validation failed message")
                    print("This suggests the MCP tool is returning an error response")
                elif "issue" in response_text.lower() and "double-check" in response_text.lower():
                    print("❌ FOUND THE ISSUE: Response contains error guidance")
                    print("The MCP tool is returning an error but the chat is presenting it as a response")
                else:
                    print("✅ Response looks normal - no obvious error messages")
                
                # Check upgrade options
                if upgrade_options:
                    print(f"\n🎁 UPGRADE OPTIONS:")
                    for i, option in enumerate(upgrade_options, 1):
                        print(f"   {i}. {option.get('name', 'Unknown')}: ${option.get('price', 0)}")
                        print(f"      Features: {', '.join(option.get('features', []))}")
                else:
                    print(f"\n⚠️ NO UPGRADE OPTIONS PROVIDED")
                    print("This might be why the user isn't seeing upgrade buttons")
                
            else:
                print(f"❌ Lambda error: {result.get('body')}")
        else:
            print(f"❌ Lambda invocation failed: {response['StatusCode']}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_specific_chat_response()