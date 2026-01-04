#!/usr/bin/env python3
"""
Update Lambda Environment Variables

Add database configuration to Lambda functions.
"""

import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def update_lambda_env():
    """Update Lambda environment variables"""
    print("🔧 UPDATING LAMBDA ENVIRONMENT VARIABLES")
    print("=" * 50)
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Environment variables to add
    env_vars = {
        'DB_CLUSTER_ARN': os.getenv('DB_CLUSTER_ARN'),
        'DB_SECRET_ARN': os.getenv('DB_SECRET_ARN'),
        'DATABASE_NAME': os.getenv('DATABASE_NAME'),
        'BEDROCK_MODEL_ID': os.getenv('BEDROCK_MODEL_ID'),
        'API_GATEWAY_URL': os.getenv('API_GATEWAY_URL')
    }
    
    # Functions to update
    functions = ['ticket-handler', 'chat-handler', 'customer-handler']
    
    for function_name in functions:
        try:
            print(f"\n📝 Updating {function_name}...")
            
            # Get current environment
            current_config = lambda_client.get_function_configuration(FunctionName=function_name)
            current_env = current_config.get('Environment', {}).get('Variables', {})
            
            # Merge with new variables
            updated_env = {**current_env, **env_vars}
            
            # Update function configuration
            response = lambda_client.update_function_configuration(
                FunctionName=function_name,
                Environment={'Variables': updated_env}
            )
            
            print(f"✅ Updated {function_name} environment variables")
            
        except Exception as e:
            print(f"❌ Error updating {function_name}: {e}")
    
    print("\n✅ Lambda environment variables updated!")

if __name__ == "__main__":
    update_lambda_env()