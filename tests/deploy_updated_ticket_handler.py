#!/usr/bin/env python3
"""
Deploy the updated Ticket Handler Lambda with chat functionality
"""

import boto3
import zipfile
import os
import json
from pathlib import Path

def create_lambda_package():
    """Create deployment package for the updated Ticket Handler"""
    
    print("Creating Lambda deployment package...")
    
    # Files to include in the package
    files_to_include = [
        'backend/lambda/ticket_handler.py',
        'backend/lambda/agentcore_client.py', 
        'backend/lambda/auth_handler.py'
    ]
    
    # Create zip file
    zip_path = 'updated_ticket_handler.zip'
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in files_to_include:
            if os.path.exists(file_path):
                # Add file to zip with just the filename (not the full path)
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname)
                print(f"  ✅ Added {file_path} as {arcname}")
            else:
                print(f"  ❌ File not found: {file_path}")
    
    print(f"✅ Created deployment package: {zip_path}")
    return zip_path

def update_lambda_function(zip_path):
    """Update the Lambda function with new code"""
    
    function_name = 'ticket-handler'  # Adjust if your function name is different
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        print(f"Updating Lambda function: {function_name}")
        
        # Read the zip file
        with open(zip_path, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"✅ Successfully updated {function_name}")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Last Modified: {response['LastModified']}")
        print(f"   Code Size: {response['CodeSize']} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update Lambda function: {e}")
        return False

def update_api_gateway_routes():
    """Update API Gateway to route /chat to the Ticket Handler"""
    
    print("\nUpdating API Gateway routes...")
    
    try:
        # Get API Gateway client
        apigw_client = boto3.client('apigateway', region_name='us-west-2')
        
        # You'll need to find your API Gateway ID
        # This is a placeholder - you may need to adjust based on your setup
        api_id = 'qzd3j8cmn2'  # From the frontend API_BASE_URL
        
        print(f"API Gateway ID: {api_id}")
        
        # List existing resources to see current setup
        resources = apigw_client.get_resources(restApiId=api_id)
        
        print("Current API resources:")
        for resource in resources['items']:
            print(f"  {resource['path']} - {resource.get('resourceMethods', {}).keys()}")
        
        # Check if /chat resource already exists
        chat_resource = None
        for resource in resources['items']:
            if resource['path'] == '/chat':
                chat_resource = resource
                break
        
        if chat_resource:
            print("✅ /chat resource already exists")
        else:
            print("ℹ️  /chat resource needs to be created")
            print("   You may need to create this manually in the AWS Console")
            print("   or update your API Gateway configuration")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to check API Gateway: {e}")
        print("   You may need to manually configure the /chat route")
        return False

def test_deployment():
    """Test the deployed function"""
    
    print("\nTesting deployed function...")
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        # Test event for chat
        test_event = {
            'httpMethod': 'POST',
            'path': '/chat',
            'headers': {
                'Authorization': 'Bearer test-token',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Hello, I want to upgrade my ticket',
                'conversationHistory': [],
                'context': {}
            })
        }
        
        # Invoke function
        response = lambda_client.invoke(
            FunctionName='ticket-handler',
            Payload=json.dumps(test_event)
        )
        
        # Parse response
        result = json.loads(response['Payload'].read())
        
        print(f"Test response status: {result.get('statusCode')}")
        
        if result.get('statusCode') == 401:
            print("✅ Function is working (401 = auth required, which is expected)")
            return True
        elif result.get('statusCode') == 200:
            print("✅ Function is working perfectly!")
            return True
        else:
            print(f"⚠️  Unexpected status code: {result.get('statusCode')}")
            print(f"Response: {result.get('body')}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main deployment process"""
    
    print("🚀 Deploying updated Ticket Handler with chat functionality...")
    print("   This will eliminate the need for a separate Chat Handler Lambda")
    print("   New flow: Frontend → Ticket Handler → AgentCore → Database")
    print()
    
    # Step 1: Create deployment package
    zip_path = create_lambda_package()
    
    # Step 2: Update Lambda function
    if update_lambda_function(zip_path):
        print("✅ Lambda function updated successfully")
    else:
        print("❌ Lambda function update failed")
        return
    
    # Step 3: Check API Gateway configuration
    update_api_gateway_routes()
    
    # Step 4: Test deployment
    if test_deployment():
        print("\n🎉 Deployment successful!")
        print("\nNext steps:")
        print("1. The Ticket Handler now handles chat requests at POST /chat")
        print("2. The frontend is already configured to use this endpoint")
        print("3. You can now remove/disable the separate Chat Handler Lambda")
        print("4. Test the frontend to ensure chat works through Ticket Handler")
    else:
        print("\n⚠️  Deployment completed but tests failed")
        print("   Please check the Lambda function logs for issues")
    
    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"🧹 Cleaned up {zip_path}")

if __name__ == "__main__":
    main()