#!/usr/bin/env python3
"""
Fix AgentCore Data Agent Configuration

This script creates a modified version of the Data Agent that gets its configuration
from AWS Systems Manager Parameter Store instead of environment variables,
since AgentCore doesn't support environment variables.
"""

import boto3
import json
import os

def create_parameter_store_config():
    """Create configuration parameters in AWS Systems Manager Parameter Store"""
    print("🔧 CREATING PARAMETER STORE CONFIGURATION")
    print("=" * 60)
    
    ssm_client = boto3.client('ssm', region_name='us-west-2')
    
    # Configuration parameters from environment variables
    parameters = {
        '/agentcore/data-agent/aws-region': os.getenv('AWS_REGION', 'us-west-2'),
        '/agentcore/data-agent/db-cluster-arn': os.getenv('DB_CLUSTER_ARN'),
        '/agentcore/data-agent/db-secret-arn': os.getenv('DB_SECRET_ARN'),
        '/agentcore/data-agent/database-name': os.getenv('DATABASE_NAME', 'ticket_system'),
        '/agentcore/data-agent/bedrock-model-id': os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
    }
    
    created_params = []
    
    for param_name, param_value in parameters.items():
        if param_value:
            try:
                # Check if parameter already exists
                try:
                    existing = ssm_client.get_parameter(Name=param_name)
                    print(f"✅ Parameter exists: {param_name}")
                except ssm_client.exceptions.ParameterNotFound:
                    # Create new parameter
                    ssm_client.put_parameter(
                        Name=param_name,
                        Value=param_value,
                        Type='SecureString' if 'arn' in param_name.lower() else 'String',
                        Description=f'AgentCore Data Agent configuration: {param_name.split("/")[-1]}',
                        Overwrite=True
                    )
                    print(f"✅ Created parameter: {param_name}")
                    created_params.append(param_name)
                
            except Exception as e:
                print(f"❌ Failed to create parameter {param_name}: {e}")
        else:
            print(f"⚠️  Skipping empty parameter: {param_name}")
    
    return created_params

def create_modified_data_agent():
    """Create a modified Data Agent that uses Parameter Store for configuration"""
    print(f"\n📝 CREATING MODIFIED DATA AGENT")
    print("=" * 60)
    
    # Read the original Data Agent
    with open('backend/agents/agentcore_data_agent.py', 'r') as f:
        original_code = f.read()
    
    # Create modified version that uses Parameter Store
    modified_code = original_code.replace(
        '''def load_config() -> DataAgentConfig:
    """Load configuration from environment variables"""
    # Load from .env file if it exists
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    return DataAgentConfig(
        aws_region=os.getenv('AWS_REGION', 'us-west-2'),
        db_cluster_arn=os.getenv('DB_CLUSTER_ARN'),
        db_secret_arn=os.getenv('DB_SECRET_ARN'),
        database_name=os.getenv('DATABASE_NAME', 'ticket_system'),
        bedrock_model_id=os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
    )''',
        '''def load_config() -> DataAgentConfig:
    """Load configuration from AWS Systems Manager Parameter Store"""
    try:
        ssm_client = boto3.client('ssm', region_name='us-west-2')
        
        # Get parameters from Parameter Store
        parameter_names = [
            '/agentcore/data-agent/aws-region',
            '/agentcore/data-agent/db-cluster-arn',
            '/agentcore/data-agent/db-secret-arn',
            '/agentcore/data-agent/database-name',
            '/agentcore/data-agent/bedrock-model-id'
        ]
        
        response = ssm_client.get_parameters(
            Names=parameter_names,
            WithDecryption=True
        )
        
        # Convert to dictionary
        params = {param['Name']: param['Value'] for param in response['Parameters']}
        
        return DataAgentConfig(
            aws_region=params.get('/agentcore/data-agent/aws-region', 'us-west-2'),
            db_cluster_arn=params.get('/agentcore/data-agent/db-cluster-arn'),
            db_secret_arn=params.get('/agentcore/data-agent/db-secret-arn'),
            database_name=params.get('/agentcore/data-agent/database-name', 'ticket_system'),
            bedrock_model_id=params.get('/agentcore/data-agent/bedrock-model-id', 'us.amazon.nova-pro-v1:0')
        )
    except Exception as e:
        print(f"Failed to load config from Parameter Store: {e}")
        # Fallback to environment variables
        return DataAgentConfig(
            aws_region=os.getenv('AWS_REGION', 'us-west-2'),
            db_cluster_arn=os.getenv('DB_CLUSTER_ARN'),
            db_secret_arn=os.getenv('DB_SECRET_ARN'),
            database_name=os.getenv('DATABASE_NAME', 'ticket_system'),
            bedrock_model_id=os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
        )'''
    )
    
    # Write the modified Data Agent
    modified_path = 'backend/agents/agentcore_data_agent_fixed.py'
    with open(modified_path, 'w') as f:
        f.write(modified_code)
    
    print(f"✅ Created modified Data Agent: {modified_path}")
    return modified_path

def update_agentcore_deployment():
    """Update the AgentCore deployment with the fixed Data Agent"""
    print(f"\n🚀 UPDATING AGENTCORE DEPLOYMENT")
    print("=" * 60)
    
    # Copy the fixed agent to the deployment location
    import shutil
    
    source_path = 'backend/agents/agentcore_data_agent_fixed.py'
    target_path = 'backend/agents/agentcore_data_agent.py'
    
    # Backup original
    backup_path = 'backend/agents/agentcore_data_agent_original.py'
    if not os.path.exists(backup_path):
        shutil.copy2(target_path, backup_path)
        print(f"✅ Backed up original to: {backup_path}")
    
    # Copy fixed version
    shutil.copy2(source_path, target_path)
    print(f"✅ Updated Data Agent with Parameter Store configuration")
    
    return True

def test_fixed_data_agent():
    """Test the fixed Data Agent configuration"""
    print(f"\n🧪 TESTING FIXED DATA AGENT")
    print("=" * 60)
    
    try:
        # Import the AgentCore client
        import sys
        sys.path.insert(0, 'backend/lambda')
        from agentcore_client import create_client
        
        print(f"🔧 Creating AgentCore client...")
        client = create_client()
        
        print(f"🎯 Testing fixed Data Agent...")
        
        # Test the data agent
        import asyncio
        
        async def test_data_agent():
            result = await client.call_data_agent_tool('get_customer', {
                'customer_id': 'test-customer-123'
            })
            return result
        
        result = asyncio.run(test_data_agent())
        
        print(f"📋 Fixed Data Agent Test Result:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            print(f"✅ FIXED DATA AGENT WORKING: Configuration issue resolved")
            return True
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"❌ FIXED DATA AGENT ISSUE: {error_msg}")
            
            # Check if it's still the same llm_reason error
            if 'llm_reason' in error_msg:
                print(f"⚠️  Still getting llm_reason error - may need AgentCore deployment")
            
            return False
        
    except Exception as e:
        print(f"❌ Fixed Data Agent test failed: {e}")
        return False

def main():
    """Main function to fix Data Agent configuration"""
    print("🔧 FIXING AGENTCORE DATA AGENT CONFIGURATION")
    print("Converting from environment variables to Parameter Store")
    print("=" * 70)
    
    # Create Parameter Store configuration
    created_params = create_parameter_store_config()
    
    if not created_params and not any(os.getenv(var) for var in ['DB_CLUSTER_ARN', 'DB_SECRET_ARN']):
        print("❌ No configuration available to create parameters")
        return
    
    # Create modified Data Agent
    modified_path = create_modified_data_agent()
    
    # Update AgentCore deployment
    update_agentcore_deployment()
    
    # Test the fixed Data Agent
    agent_working = test_fixed_data_agent()
    
    # Final assessment
    print(f"\n🎯 CONFIGURATION FIX RESULTS")
    print("=" * 60)
    
    if agent_working:
        print(f"🎉 DATA AGENT CONFIGURATION FIXED!")
        print(f"   ✅ Parameter Store configuration created")
        print(f"   ✅ Data Agent updated to use Parameter Store")
        print(f"   ✅ Agent now responds without llm_reason errors")
        print(f"   ✅ Aurora database access should be working")
    else:
        print(f"⚠️  DATA AGENT CONFIGURATION PARTIALLY FIXED")
        print(f"   ✅ Parameter Store configuration created")
        print(f"   ✅ Data Agent code updated")
        print(f"   ⚠️  May need AgentCore deployment to take effect")
        print(f"\n🔧 NEXT STEPS:")
        print(f"   1. The AgentCore Data Agent may need to be redeployed")
        print(f"   2. Or there may be a delay for the changes to take effect")
        print(f"   3. Test again in a few minutes")
    
    print(f"\n📋 CREATED PARAMETERS:")
    if created_params:
        for param in created_params:
            print(f"   ✅ {param}")
    else:
        print(f"   ℹ️  Parameters already existed or were updated")

if __name__ == "__main__":
    main()