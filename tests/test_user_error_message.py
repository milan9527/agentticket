#!/usr/bin/env python3
"""
Test User Error Message

This script tests to reproduce the exact error message the user is seeing.
"""

import boto3
import json
import os
from dotenv import load_dotenv

def test_user_error_message():
    """Test to reproduce the user's error message"""
    load_dotenv()
    
    print("🔍 REPRODUCING USER ERROR MESSAGE")
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
    print(f"✅ Got token")
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Test different variations to see if we can reproduce the error
    test_scenarios = [
        {
            "name": "Direct ticket mention",
            "message": "My ticket ID is 550e8400-e29b-41d4-a716-446655440002",
            "context": {}
        },
        {
            "name": "Validation request",
            "message": "Can you check if my ticket 550e8400-e29b-41d4-a716-446655440002 is eligible?",
            "context": {"ticketId": "550e8400-e29b-41d4-a716-446655440002"}
        },
        {
            "name": "Simple validation",
            "message": "validate my ticket",
            "context": {"ticketId": "550e8400-e29b-41d4-a716-446655440002", "hasTicketInfo": True}
        },
        {
            "name": "Check eligibility",
            "message": "check if eligible",
            "context": {"ticketId": "550e8400-e29b-41d4-a716-446655440002", "hasTicketInfo": True}
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🎯 Scenario {i}: {scenario['name']}")
        print(f"Message: '{scenario['message']}'")
        
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
                    
                    print(f"✅ Response ({len(response_text)} chars): {response_text[:100]}...")
                    
                    # Check for the specific error message the user mentioned
                    if "validation failed" in response_text.lower():
                        print("❌ FOUND USER'S ERROR MESSAGE!")
                        print(f"Full response: {response_text}")
                        break
                    elif "issue" in response_text.lower() and "double-check" in response_text.lower():
                        print("❌ FOUND SIMILAR ERROR MESSAGE!")
                        print(f"Full response: {response_text}")
                        break
                else:
                    print(f"❌ Lambda error: {result.get('body')}")
            else:
                print(f"❌ Lambda failed: {response['StatusCode']}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
    
    # Test with invalid ticket to see error format
    print(f"\n🧪 Testing with invalid ticket to see error format...")
    
    invalid_payload = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "My ticket ID is invalid-ticket-123",
            "conversationHistory": [],
            "context": {"ticketId": "invalid-ticket-123", "hasTicketInfo": True}
        })
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='ticket-handler',
            InvocationType='RequestResponse',
            Payload=json.dumps(invalid_payload)
        )
        
        if response['StatusCode'] == 200:
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') == 200:
                body = json.loads(result.get('body', '{}'))
                response_text = body.get('response', '')
                
                print(f"📝 Invalid ticket response: {response_text}")
                
                if "validation failed" in response_text.lower():
                    print("🎯 FOUND THE ERROR MESSAGE FORMAT!")
                    print("This is likely what the user is seeing")
                    
    except Exception as e:
        print(f"❌ Invalid ticket test exception: {e}")

if __name__ == "__main__":
    test_user_error_message()