#!/usr/bin/env python3
"""
Test Cognito authentication for Lambda functions
"""

import boto3
import os
import json

def test_cognito_auth():
    """Test Cognito authentication directly"""
    print("🔐 Testing Cognito Authentication")
    print("=" * 50)
    
    try:
        # Get environment variables
        cognito_client_id = os.getenv('COGNITO_CLIENT_ID', '11m43vg72idbvlf5pc5d6qhsc4')
        test_user = os.getenv('COGNITO_TEST_USER', 'testuser@example.com')
        test_password = os.getenv('COGNITO_TEST_PASSWORD', 'TempPass123!')
        aws_region = os.getenv('AWS_REGION', 'us-west-2')
        
        print(f"🔧 Cognito Client ID: {cognito_client_id}")
        print(f"👤 Test User: {test_user}")
        print(f"🌍 AWS Region: {aws_region}")
        
        # Create Cognito client
        cognito_client = boto3.client('cognito-idp', region_name=aws_region)
        
        print("\n🔑 Attempting authentication...")
        
        response = cognito_client.initiate_auth(
            ClientId=cognito_client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': test_user,
                'PASSWORD': test_password
            }
        )
        
        if 'AuthenticationResult' in response:
            access_token = response['AuthenticationResult']['AccessToken']
            print(f"✅ Authentication successful!")
            print(f"🎫 Access Token: {access_token[:50]}...")
            return True
        else:
            print(f"❌ Authentication failed: {response}")
            return False
            
    except Exception as e:
        print(f"❌ Cognito authentication error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_cognito_auth()