#!/usr/bin/env python3
"""
Create Parameter Store Configuration for AgentCore Data Agent

This script creates the required parameters in AWS Systems Manager Parameter Store
for the AgentCore Data Agent to access Aurora database.
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_parameters():
    """Create parameters in Parameter Store"""
    print("🔧 CREATING PARAMETER STORE CONFIGURATION FOR AGENTCORE DATA AGENT")
    print("=" * 70)
    
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
    updated_params = []
    
    for param_name, param_value in parameters.items():
        if param_value:
            try:
                # Check if parameter already exists
                try:
                    existing = ssm_client.get_parameter(Name=param_name)
                    # Update existing parameter
                    ssm_client.put_parameter(
                        Name=param_name,
                        Value=param_value,
                        Type='SecureString' if 'arn' in param_name.lower() else 'String',
                        Description=f'AgentCore Data Agent configuration: {param_name.split("/")[-1]}',
                        Overwrite=True
                    )
                    print(f"✅ Updated parameter: {param_name}")
                    updated_params.append(param_name)
                    
                except ssm_client.exceptions.ParameterNotFound:
                    # Create new parameter
                    ssm_client.put_parameter(
                        Name=param_name,
                        Value=param_value,
                        Type='SecureString' if 'arn' in param_name.lower() else 'String',
                        Description=f'AgentCore Data Agent configuration: {param_name.split("/")[-1]}',
                        Overwrite=False
                    )
                    print(f"✅ Created parameter: {param_name}")
                    created_params.append(param_name)
                
            except Exception as e:
                print(f"❌ Failed to create/update parameter {param_name}: {e}")
        else:
            print(f"⚠️  Skipping empty parameter: {param_name}")
    
    print(f"\n📊 PARAMETER STORE CONFIGURATION RESULTS:")
    print(f"   ✅ Created: {len(created_params)} parameters")
    print(f"   ✅ Updated: {len(updated_params)} parameters")
    
    if created_params:
        print(f"\n📋 CREATED PARAMETERS:")
        for param in created_params:
            print(f"   ✅ {param}")
    
    if updated_params:
        print(f"\n📋 UPDATED PARAMETERS:")
        for param in updated_params:
            print(f"   ✅ {param}")
    
    return len(created_params) + len(updated_params) > 0

def verify_parameters():
    """Verify that all parameters were created correctly"""
    print(f"\n🔍 VERIFYING PARAMETER STORE CONFIGURATION")
    print("=" * 60)
    
    ssm_client = boto3.client('ssm', region_name='us-west-2')
    
    parameter_names = [
        '/agentcore/data-agent/aws-region',
        '/agentcore/data-agent/db-cluster-arn',
        '/agentcore/data-agent/db-secret-arn',
        '/agentcore/data-agent/database-name',
        '/agentcore/data-agent/bedrock-model-id'
    ]
    
    try:
        response = ssm_client.get_parameters(
            Names=parameter_names,
            WithDecryption=True
        )
        
        found_params = {param['Name']: param['Value'] for param in response['Parameters']}
        missing_params = [name for name in parameter_names if name not in found_params]
        
        print(f"📋 PARAMETER VERIFICATION RESULTS:")
        for param_name in parameter_names:
            if param_name in found_params:
                value = found_params[param_name]
                # Mask sensitive values
                if 'arn' in param_name.lower():
                    display_value = f"{value[:30]}...{value[-15:]}" if len(value) > 45 else value
                else:
                    display_value = value
                print(f"   ✅ {param_name}: {display_value}")
            else:
                print(f"   ❌ {param_name}: NOT FOUND")
        
        if missing_params:
            print(f"\n⚠️  MISSING PARAMETERS: {len(missing_params)}")
            return False
        else:
            print(f"\n🎉 ALL PARAMETERS CONFIGURED CORRECTLY!")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying parameters: {e}")
        return False

def main():
    """Main function"""
    print("🔧 AGENTCORE DATA AGENT PARAMETER STORE SETUP")
    print("Setting up configuration for Aurora database access")
    print("=" * 70)
    
    # Create parameters
    success = create_parameters()
    
    if success:
        # Verify parameters
        verified = verify_parameters()
        
        if verified:
            print(f"\n🎯 PARAMETER STORE SETUP COMPLETE!")
            print(f"   ✅ All required parameters configured")
            print(f"   ✅ AgentCore Data Agent should now have access to Aurora database")
            print(f"   ✅ The 'llm_reason' error should be resolved after deployment")
            
            print(f"\n🚀 NEXT STEPS:")
            print(f"   1. Deploy the updated Data Agent to AgentCore")
            print(f"   2. Test the Data Agent Aurora database access")
            print(f"   3. Verify that the 'llm_reason' error is resolved")
        else:
            print(f"\n⚠️  PARAMETER VERIFICATION FAILED")
            print(f"   Some parameters may not have been created correctly")
    else:
        print(f"\n❌ PARAMETER CREATION FAILED")
        print(f"   Check AWS credentials and permissions")

if __name__ == "__main__":
    main()