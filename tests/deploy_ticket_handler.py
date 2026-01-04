#!/usr/bin/env python3
"""
Deploy Ticket Handler Lambda

Deploy the ticket handler with all required dependencies.
"""

import boto3
import zipfile
import os

def deploy_ticket_handler():
    """Deploy ticket handler with dependencies"""
    print("🚀 DEPLOYING TICKET HANDLER LAMBDA")
    print("=" * 40)
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Create deployment package
    package_name = "ticket-handler.zip"
    print(f"📦 Creating deployment package: {package_name}")
    
    with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main handler
        zipf.write("backend/lambda/agentcore_ticket_handler.py", "agentcore_ticket_handler.py")
        # Add dependencies
        zipf.write("backend/lambda/direct_agent_client.py", "direct_agent_client.py")
        zipf.write("backend/lambda/auth_handler.py", "auth_handler.py")
    
    print("✅ Deployment package created")
    
    # Update function code
    function_name = 'ticket-handler'
    print(f"📝 Updating Lambda function: {function_name}")
    
    try:
        with open(package_name, 'rb') as f:
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=f.read()
            )
        
        print("✅ Ticket handler deployed successfully!")
        print(f"📋 Function ARN: {response['FunctionArn']}")
        
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
    
    finally:
        # Clean up package
        if os.path.exists(package_name):
            os.remove(package_name)
            print("🧹 Cleaned up deployment package")

if __name__ == "__main__":
    deploy_ticket_handler()