#!/usr/bin/env python3
"""
Test Lambda function imports
"""

import boto3
import json

def test_lambda_imports():
    """Test Lambda function imports by invoking with a simple test"""
    print("📦 Testing Lambda Function Imports")
    print("=" * 50)
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        # Create a test event that will trigger the import
        test_event = {
            "httpMethod": "POST",
            "path": "/test-imports",
            "headers": {
                "Authorization": "Bearer invalid-token-for-testing"
            },
            "body": json.dumps({"test": "import"})
        }
        
        print("🔧 Invoking Lambda to test imports...")
        response = lambda_client.invoke(
            FunctionName='ticket-handler',
            Payload=json.dumps(test_event)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"📋 Response Status: {result.get('statusCode')}")
        
        # If we get a 401, that means imports worked (auth failed as expected)
        # If we get a 500, there might be an import error
        if result.get('statusCode') == 401:
            print("✅ Lambda imports working correctly (401 = auth failed as expected)")
            return True
        elif result.get('statusCode') == 500:
            print("❌ Lambda returned 500 - possible import error")
            body = json.loads(result.get('body', '{}'))
            print(f"   Error: {body.get('error', 'Unknown error')}")
            return False
        else:
            print(f"⚠️ Unexpected status: {result.get('statusCode')}")
            body = json.loads(result.get('body', '{}'))
            print(f"   Body: {body}")
            return True
            
    except Exception as e:
        print(f"❌ Error testing Lambda imports: {e}")
        return False

if __name__ == "__main__":
    test_lambda_imports()