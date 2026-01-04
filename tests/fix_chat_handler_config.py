#!/usr/bin/env python3
"""
Fix Chat Handler Configuration

Update the Lambda function configuration to ensure it has the correct handler.
"""

import boto3
import json

def fix_chat_handler_config():
    """Fix the chat handler Lambda function configuration"""
    print("🔧 FIXING CHAT HANDLER CONFIGURATION")
    print("=" * 50)
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    function_name = 'chat-handler'
    
    try:
        # Get current function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        
        print(f"📋 Current handler: {response.get('Handler', 'Not set')}")
        print(f"📋 Current runtime: {response.get('Runtime', 'Not set')}")
        
        # Update function configuration
        print("🔧 Updating function configuration...")
        
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Handler='chat_handler.lambda_handler',
            Runtime='python3.11',
            Timeout=30,
            MemorySize=256
        )
        
        print("✅ Function configuration updated successfully!")
        
        # Verify the update
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        print(f"📋 New handler: {response.get('Handler', 'Not set')}")
        print(f"📋 New runtime: {response.get('Runtime', 'Not set')}")
        
    except Exception as e:
        print(f"❌ Failed to fix configuration: {e}")

if __name__ == "__main__":
    fix_chat_handler_config()