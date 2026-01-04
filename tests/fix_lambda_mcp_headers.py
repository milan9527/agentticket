#!/usr/bin/env python3
"""
Fix Lambda MCP Headers Issue

Updates the Lambda function with the corrected agentcore_client.py that includes
proper MCP Accept headers: 'application/json, text/event-stream'
"""

import boto3
import zipfile
import os
import io

def update_lambda_function():
    """Update Lambda function with fixed MCP headers"""
    print("🔧 Fixing Lambda MCP Headers Issue")
    print("=" * 50)
    
    try:
        # Create a zip file with the updated code
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add the fixed agentcore_client.py
            zip_file.write('backend/lambda/agentcore_client.py', 'agentcore_client.py')
            
            # Add other required files
            zip_file.write('backend/lambda/ticket_handler.py', 'ticket_handler.py')
            zip_file.write('backend/lambda/auth_handler.py', 'auth_handler.py')
        
        zip_content = zip_buffer.getvalue()
        
        # Update Lambda function
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        print("🚀 Updating ticket-handler Lambda function...")
        
        response = lambda_client.update_function_code(
            FunctionName='ticket-handler',
            ZipFile=zip_content
        )
        
        print(f"✅ Lambda function updated successfully!")
        print(f"   Version: {response.get('Version')}")
        print(f"   Last Modified: {response.get('LastModified')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating Lambda function: {e}")
        return False

def test_fixed_lambda():
    """Test the fixed Lambda function"""
    print("\n🧪 Testing Fixed Lambda Function")
    print("=" * 50)
    
    try:
        # Get Cognito token
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
        print(f"✅ Got Cognito token: {access_token[:50]}...")
        
        # Test Lambda with proper MCP request
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
            "body": '{"upgrade_tier": "standard"}'
        }
        
        print("🔧 Testing Lambda with MCP tool call...")
        response = lambda_client.invoke(
            FunctionName='ticket-handler',
            Payload=json.dumps(test_event)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"📋 Response Status: {result.get('statusCode')}")
        
        if result.get('statusCode') == 200:
            body = json.loads(result.get('body', '{}'))
            if body.get('success'):
                print("✅ Lambda MCP headers fixed! AgentCore responding correctly")
                return True
            else:
                print(f"⚠️ Lambda working but AgentCore returned error: {body.get('error', 'Unknown')}")
                return False
        else:
            print(f"❌ Lambda returned error: {result.get('statusCode')}")
            body = json.loads(result.get('body', '{}'))
            print(f"   Error: {body.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing fixed Lambda: {e}")
        return False

if __name__ == "__main__":
    import json
    
    update_success = update_lambda_function()
    
    if update_success:
        # Wait a moment for deployment
        import time
        print("\n⏳ Waiting for deployment to complete...")
        time.sleep(5)
        
        test_success = test_fixed_lambda()
        
        print(f"\n🎯 LAMBDA MCP FIX RESULTS:")
        print(f"✅ Lambda Update: {'SUCCESS' if update_success else 'FAILED'}")
        print(f"{'✅' if test_success else '❌'} MCP Headers: {'FIXED' if test_success else 'STILL BROKEN'}")
        
        if test_success:
            print(f"\n🎉 LAMBDA MCP ISSUE RESOLVED!")
            print(f"   The Lambda function now sends proper MCP Accept headers")
            print(f"   AgentCore agents should respond correctly to tool calls")
        else:
            print(f"\n🔧 ADDITIONAL ISSUES FOUND:")
            print(f"   Lambda headers are fixed but there may be other AgentCore issues")
    else:
        print(f"\n❌ LAMBDA UPDATE FAILED")
        print(f"   Could not deploy the MCP header fix")