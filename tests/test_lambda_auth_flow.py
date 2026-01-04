#!/usr/bin/env python3
"""
Test Lambda authentication flow end-to-end
"""

import boto3
import json
import os

def test_lambda_auth_flow():
    """Test Lambda authentication flow"""
    print("🔐 Testing Lambda Authentication Flow")
    print("=" * 50)
    
    try:
        # Step 1: Get a valid token from Cognito
        print("🔧 Step 1: Getting Cognito token...")
        cognito_client = boto3.client('cognito-idp', region_name='us-west-2')
        
        response = cognito_client.initiate_auth(
            ClientId='11m43vg72idbvlf5pc5d6qhsc4',
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': 'testuser@example.com',
                'PASSWORD': 'TempPass123!'
            }
        )
        
        access_token = response['AuthenticationResult']['AccessToken']
        print(f"✅ Got access token: {access_token[:50]}...")
        
        # Step 2: Test Lambda with valid token
        print("\n🔧 Step 2: Testing Lambda with valid token...")
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        test_event = {
            "httpMethod": "POST",
            "path": "/tickets/550e8400-e29b-41d4-a716-446655440002/validate",
            "headers": {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            "pathParameters": {
                "ticket_id": "550e8400-e29b-41d4-a716-446655440002"
            },
            "body": json.dumps({
                "upgrade_tier": "standard"
            })
        }
        
        print("🔧 Invoking ticket-handler with authenticated request...")
        response = lambda_client.invoke(
            FunctionName='ticket-handler',
            Payload=json.dumps(test_event)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"📋 Response Status: {result.get('statusCode')}")
        print(f"📋 Response Body: {result.get('body', 'No body')[:200]}...")
        
        if result.get('statusCode') == 200:
            print("✅ Lambda authentication flow working!")
            return True
        elif result.get('statusCode') == 401:
            print("❌ Lambda returned 401 - authentication issue")
            return False
        elif result.get('statusCode') == 500:
            print("❌ Lambda returned 500 - internal server error")
            body = json.loads(result.get('body', '{}'))
            print(f"   Error: {body.get('error', 'Unknown error')}")
            return False
        else:
            print(f"❌ Lambda returned unexpected status: {result.get('statusCode')}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Lambda auth flow: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_lambda_auth_flow()