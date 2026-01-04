#!/usr/bin/env python3
"""
Deploy Simple Chat Handler

Deploy a simple test version to see if the issue is with the code or deployment.
"""

import boto3
import zipfile
import os

def deploy_simple_chat():
    """Deploy simple chat handler"""
    print("🚀 DEPLOYING SIMPLE CHAT HANDLER")
    print("=" * 40)
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Create deployment package
    package_name = "simple-chat-handler.zip"
    print(f"📦 Creating deployment package: {package_name}")
    
    with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add simple test handler
        zipf.write("simple_chat_test.py", "chat_handler.py")
    
    print("✅ Deployment package created")
    
    # Update function code
    function_name = 'chat-handler'
    print(f"📝 Updating Lambda function: {function_name}")
    
    try:
        with open(package_name, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        print("✅ Simple chat handler deployed successfully!")
        print(f"📋 Function ARN: {response['FunctionArn']}")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
    
    finally:
        # Clean up package
        if os.path.exists(package_name):
            os.remove(package_name)
            print("🧹 Cleaned up deployment package")

if __name__ == "__main__":
    deploy_simple_chat()