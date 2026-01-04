#!/usr/bin/env python3
"""
Deploy Fixed Ticket Handler Lambda Function

Deploys the ticket handler with the corrected AgentCore chat integration.
"""

import boto3
import zipfile
import os
import io

def deploy_fixed_ticket_handler():
    """Deploy the fixed ticket handler Lambda function"""
    print("🚀 Deploying Fixed Ticket Handler Lambda Function")
    print("=" * 60)
    
    try:
        # Create a zip file with the Lambda code
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add the main Lambda files
            zip_file.write('backend/lambda/ticket_handler.py', 'ticket_handler.py')
            zip_file.write('backend/lambda/agentcore_client.py', 'agentcore_client.py')
            zip_file.write('backend/lambda/auth_handler.py', 'auth_handler.py')
        
        zip_content = zip_buffer.getvalue()
        
        # Update Lambda function
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        print("📦 Updating ticket-handler Lambda function...")
        
        response = lambda_client.update_function_code(
            FunctionName='ticket-handler',
            ZipFile=zip_content
        )
        
        print(f"✅ Lambda function updated successfully!")
        print(f"   Function Name: {response.get('FunctionName')}")
        print(f"   Version: {response.get('Version')}")
        print(f"   Last Modified: {response.get('LastModified')}")
        print(f"   Code Size: {response.get('CodeSize')} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ Error deploying Lambda function: {e}")
        return False

if __name__ == "__main__":
    success = deploy_fixed_ticket_handler()
    
    if success:
        print(f"\n🎉 DEPLOYMENT SUCCESSFUL!")
        print(f"   ✅ Fixed ticket handler deployed")
        print(f"   ✅ AgentCore chat integration corrected")
        print(f"   ✅ Ready for testing with real LLM")
    else:
        print(f"\n❌ DEPLOYMENT FAILED")
        print(f"   Please check the error messages above")