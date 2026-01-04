#!/usr/bin/env python3
"""
Setup Cognito User Pool for AgentCore Authentication

This script creates a Cognito User Pool and App Client for AgentCore agent authentication.
"""

import boto3
import json
import os
from botocore.exceptions import ClientError


def setup_cognito_for_agentcore():
    """Set up Cognito User Pool for AgentCore authentication"""
    
    # Load AWS region from environment
    aws_region = os.getenv('AWS_REGION', 'us-west-2')
    
    # Initialize Cognito client
    cognito_client = boto3.client('cognito-idp', region_name=aws_region)
    
    try:
        print("🔐 Setting up Cognito User Pool for AgentCore authentication...")
        
        # Create User Pool
        print("📝 Creating Cognito User Pool...")
        user_pool_response = cognito_client.create_user_pool(
            PoolName='TicketSystemAgentCorePool',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': False
                }
            },
            AutoVerifiedAttributes=['email'],
            UsernameAttributes=['email'],
            Schema=[
                {
                    'Name': 'email',
                    'AttributeDataType': 'String',
                    'Required': True,
                    'Mutable': True
                }
            ],
            UserPoolTags={
                'Project': 'TicketAutoProcessing',
                'Environment': 'Development',
                'Purpose': 'AgentCore Authentication'
            }
        )
        
        pool_id = user_pool_response['UserPool']['Id']
        print(f"✅ User Pool created: {pool_id}")
        
        # Create App Client
        print("📱 Creating App Client...")
        app_client_response = cognito_client.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName='AgentCoreClient',
            GenerateSecret=False,  # Public client for AgentCore
            ExplicitAuthFlows=[
                'ALLOW_USER_PASSWORD_AUTH',
                'ALLOW_REFRESH_TOKEN_AUTH',
                'ALLOW_USER_SRP_AUTH'
            ],
            SupportedIdentityProviders=['COGNITO'],
            CallbackURLs=[
                'http://localhost:3030/callback',
                'https://oauth.pstmn.io/v1/callback'  # For testing
            ],
            LogoutURLs=[
                'http://localhost:3030/logout'
            ],
            AllowedOAuthFlows=['code'],
            AllowedOAuthScopes=['openid', 'email', 'profile'],
            AllowedOAuthFlowsUserPoolClient=True,
            TokenValidityUnits={
                'AccessToken': 'hours',
                'IdToken': 'hours',
                'RefreshToken': 'days'
            },
            AccessTokenValidity=1,  # 1 hour
            IdTokenValidity=1,      # 1 hour
            RefreshTokenValidity=30  # 30 days
        )
        
        client_id = app_client_response['UserPoolClient']['ClientId']
        print(f"✅ App Client created: {client_id}")
        
        # Create User Pool Domain
        print("🌐 Creating User Pool Domain...")
        domain_name = f"ticket-system-{pool_id.lower()}"
        try:
            cognito_client.create_user_pool_domain(
                Domain=domain_name,
                UserPoolId=pool_id
            )
            print(f"✅ Domain created: {domain_name}.auth.{aws_region}.amazoncognito.com")
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidParameterException':
                print(f"⚠️  Domain already exists or invalid: {domain_name}")
            else:
                raise
        
        # Create a test user
        print("👤 Creating test user...")
        test_username = "testuser@example.com"
        test_password = "TempPass123!"
        
        try:
            cognito_client.admin_create_user(
                UserPoolId=pool_id,
                Username=test_username,
                TemporaryPassword=test_password,
                MessageAction='SUPPRESS'
            )
            
            # Set permanent password
            cognito_client.admin_set_user_password(
                UserPoolId=pool_id,
                Username=test_username,
                Password=test_password,
                Permanent=True
            )
            
            print(f"✅ Test user created: {test_username} / {test_password}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'UsernameExistsException':
                print(f"⚠️  Test user already exists: {test_username}")
            else:
                raise
        
        # Generate discovery URL
        discovery_url = f"https://cognito-idp.{aws_region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
        
        # Update .env file
        print("📝 Updating .env file with Cognito configuration...")
        env_updates = {
            'COGNITO_USER_POOL_ID': pool_id,
            'COGNITO_CLIENT_ID': client_id,
            'COGNITO_DISCOVERY_URL': discovery_url,
            'COGNITO_DOMAIN': f"{domain_name}.auth.{aws_region}.amazoncognito.com",
            'COGNITO_TEST_USER': test_username,
            'COGNITO_TEST_PASSWORD': test_password
        }
        
        # Read existing .env file
        env_content = []
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                env_content = f.readlines()
        
        # Update or add new values
        updated_keys = set()
        for i, line in enumerate(env_content):
            if '=' in line and not line.startswith('#'):
                key = line.split('=')[0].strip()
                if key in env_updates:
                    env_content[i] = f"{key}={env_updates[key]}\n"
                    updated_keys.add(key)
        
        # Add new keys that weren't found
        for key, value in env_updates.items():
            if key not in updated_keys:
                env_content.append(f"{key}={value}\n")
        
        # Write updated .env file
        with open('.env', 'w') as f:
            f.writelines(env_content)
        
        print("\n🎉 Cognito setup completed successfully!")
        print("\n📋 Configuration Summary:")
        print(f"   User Pool ID: {pool_id}")
        print(f"   Client ID: {client_id}")
        print(f"   Discovery URL: {discovery_url}")
        print(f"   Domain: {domain_name}.auth.{aws_region}.amazoncognito.com")
        print(f"   Test User: {test_username}")
        print(f"   Test Password: {test_password}")
        
        print("\n✅ Ready for AgentCore deployment!")
        
        return {
            'pool_id': pool_id,
            'client_id': client_id,
            'discovery_url': discovery_url,
            'domain': f"{domain_name}.auth.{aws_region}.amazoncognito.com",
            'test_user': test_username,
            'test_password': test_password
        }
        
    except Exception as e:
        print(f"❌ Error setting up Cognito: {e}")
        raise


if __name__ == "__main__":
    setup_cognito_for_agentcore()