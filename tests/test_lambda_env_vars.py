#!/usr/bin/env python3
"""
Test Lambda environment variables directly
"""

import boto3
import json

def test_lambda_env_vars():
    """Test Lambda environment variables"""
    print("🔧 Testing Lambda Environment Variables")
    print("=" * 50)
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        # Test ticket-handler function
        print("\n🎫 Checking ticket-handler environment variables...")
        response = lambda_client.get_function_configuration(FunctionName='ticket-handler')
        env_vars = response.get('Environment', {}).get('Variables', {})
        
        required_vars = [
            'COGNITO_CLIENT_ID',
            'COGNITO_TEST_USER', 
            'COGNITO_TEST_PASSWORD',
            'TICKET_AGENT_ARN',
            'DATA_AGENT_ARN'
        ]
        
        print(f"📋 Environment Variables Found:")
        for var in required_vars:
            value = env_vars.get(var, 'NOT SET')
            if var in ['COGNITO_TEST_PASSWORD']:
                print(f"   {var}: {'✅ SET' if value != 'NOT SET' else '❌ NOT SET'}")
            else:
                print(f"   {var}: {value}")
        
        # Test if all required vars are present
        missing_vars = [var for var in required_vars if var not in env_vars]
        if missing_vars:
            print(f"\n❌ Missing environment variables: {missing_vars}")
            return False
        else:
            print(f"\n✅ All required environment variables are set")
            return True
            
    except Exception as e:
        print(f"❌ Error checking Lambda environment: {e}")
        return False

def test_lambda_invocation():
    """Test Lambda function invocation with a simple test"""
    print("\n🧪 Testing Lambda Function Invocation")
    print("=" * 50)
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        # Test with OPTIONS request (should work without auth)
        test_event = {
            "httpMethod": "OPTIONS",
            "path": "/test",
            "headers": {},
            "body": None
        }
        
        print("🔧 Invoking ticket-handler with OPTIONS request...")
        response = lambda_client.invoke(
            FunctionName='ticket-handler',
            Payload=json.dumps(test_event)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"📋 Response: {result}")
        
        if result.get('statusCode') == 200:
            print("✅ Lambda function is responding correctly")
            return True
        else:
            print(f"❌ Lambda function returned unexpected status: {result.get('statusCode')}")
            return False
            
    except Exception as e:
        print(f"❌ Error invoking Lambda function: {e}")
        return False

if __name__ == "__main__":
    env_success = test_lambda_env_vars()
    invoke_success = test_lambda_invocation()
    
    print(f"\n🎯 LAMBDA DIAGNOSIS RESULTS:")
    print(f"{'✅' if env_success else '❌'} Environment Variables: {'OK' if env_success else 'ISSUES FOUND'}")
    print(f"{'✅' if invoke_success else '❌'} Lambda Invocation: {'OK' if invoke_success else 'ISSUES FOUND'}")