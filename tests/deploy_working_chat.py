#!/usr/bin/env python3
"""
Deploy Working Chat Handler

Deploy the working chat handler with authentication and intelligent responses.
"""

import boto3
import zipfile
import os
from dotenv import load_dotenv

def deploy_working_chat():
    """Deploy working chat handler"""
    print("🚀 DEPLOYING WORKING CHAT HANDLER")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Create deployment package
    package_name = "working-chat-handler.zip"
    print(f"📦 Creating deployment package: {package_name}")
    
    with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add working chat handler
        zipf.write("working_chat_handler.py", "chat_handler.py")
        # Add direct agent client for ticket operations
        zipf.write("backend/lambda/direct_agent_client.py", "direct_agent_client.py")
    
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
        
        print("✅ Working chat handler code deployed successfully!")
        print(f"📋 Function ARN: {response['FunctionArn']}")
        
        # Wait for function to be ready before updating environment
        print("⏳ Waiting for function to be ready...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName=function_name)
        
        # Update environment variables
        print("🔧 Updating Lambda environment variables")
        
        environment_vars = {
            'API_GATEWAY_URL': os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod'),
            'DB_CLUSTER_ARN': os.getenv('DB_CLUSTER_ARN', ''),
            'DB_SECRET_ARN': os.getenv('DB_SECRET_ARN', ''),
            'DATABASE_NAME': os.getenv('DATABASE_NAME', 'ticket_system')
        }
        
        # Filter out empty values
        environment_vars = {k: v for k, v in environment_vars.items() if v}
        
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={
                'Variables': environment_vars
            }
        )
        
        print("✅ Environment variables updated successfully!")
        print(f"🔧 Environment variables set: {list(environment_vars.keys())}")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
    
    finally:
        # Clean up package
        if os.path.exists(package_name):
            os.remove(package_name)
            print("🧹 Cleaned up deployment package")

if __name__ == "__main__":
    deploy_working_chat()