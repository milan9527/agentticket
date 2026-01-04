#!/usr/bin/env python3
"""
Deploy Chat Handler Lambda Function

Quick deployment script for just the chat handler.
"""

import boto3
import zipfile
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def deploy_chat_handler():
    """Deploy the chat handler Lambda function"""
    print("🚀 DEPLOYING CHAT HANDLER")
    print("=" * 40)
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Create deployment package
    package_name = "chat-handler.zip"
    print(f"📦 Creating deployment package: {package_name}")
    
    with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main handler file
        zipf.write("backend/lambda/chat_handler.py", "chat_handler.py")
        
        # Add dependencies
        zipf.write("backend/lambda/auth_handler.py", "auth_handler.py")
        zipf.write("backend/lambda/agentcore_http_client.py", "agentcore_http_client.py")
    
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
        
        print("✅ Chat handler deployed successfully!")
        print(f"📋 Function ARN: {response['FunctionArn']}")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
    
    finally:
        # Clean up package
        if os.path.exists(package_name):
            os.remove(package_name)
            print("🧹 Cleaned up deployment package")

if __name__ == "__main__":
    deploy_chat_handler()