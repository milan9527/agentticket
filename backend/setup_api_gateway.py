#!/usr/bin/env python3
"""
Setup API Gateway with Lambda Integration

This script creates an API Gateway REST API and integrates it with our Lambda functions
for the ticket auto-processing system.
"""

import boto3
import json
import os
import zipfile
import time
from botocore.exceptions import ClientError


class APIGatewaySetup:
    def __init__(self):
        self.aws_region = os.getenv('AWS_REGION', 'us-west-2')
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        # Initialize AWS clients
        self.apigateway = boto3.client('apigateway', region_name=self.aws_region)
        self.lambda_client = boto3.client('lambda', region_name=self.aws_region)
        self.iam = boto3.client('iam', region_name=self.aws_region)
        
        # Configuration
        self.api_name = 'ticket-auto-processing-api'
        self.stage_name = 'prod'
        
        # Lambda function configurations
        self.lambda_functions = {
            'auth': {
                'name': 'ticket-auth-handler',
                'handler': 'auth_handler.lambda_handler',
                'file': 'auth_handler.py'
            },
            'tickets': {
                'name': 'ticket-handler',
                'handler': 'agentcore_ticket_handler.lambda_handler', 
                'file': 'agentcore_ticket_handler.py'
            },
            'customers': {
                'name': 'customer-handler',
                'handler': 'agentcore_customer_handler.lambda_handler',
                'file': 'agentcore_customer_handler.py'
            },
            'chat': {
                'name': 'chat-handler',
                'handler': 'chat_handler.lambda_handler',
                'file': 'chat_handler.py'
            }
        }

    def create_lambda_execution_role(self):
        """Create IAM role for Lambda execution"""
        role_name = 'TicketSystemLambdaExecutionRole'
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            # Try to get existing role
            response = self.iam.get_role(RoleName=role_name)
            role_arn = response['Role']['Arn']
            print(f"✅ Using existing Lambda execution role: {role_arn}")
            return role_arn
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                # Create new role
                print(f"📝 Creating Lambda execution role: {role_name}")
                
                response = self.iam.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description='Execution role for Ticket System Lambda functions'
                )
                
                role_arn = response['Role']['Arn']
                
                # Attach basic Lambda execution policy
                self.iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
                )
                
                # Attach Cognito access policy
                self.iam.attach_role_policy(
                    RoleName=role_name,
                    PolicyArn='arn:aws:iam::aws:policy/AmazonCognitoPowerUser'
                )
                
                # Wait for role to be available
                print("⏳ Waiting for role to be available...")
                time.sleep(10)
                
                print(f"✅ Created Lambda execution role: {role_arn}")
                return role_arn
            else:
                raise

    def create_lambda_deployment_package(self, function_config):
        """Create deployment package for Lambda function"""
        package_name = f"{function_config['name']}.zip"
        
        print(f"📦 Creating deployment package: {package_name}")
        
        with zipfile.ZipFile(package_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add main handler file
            zipf.write(f"backend/lambda/{function_config['file']}", function_config['file'])
            
            # Add shared dependencies based on handler type
            shared_files = []
            if function_config['file'] == 'auth_handler.py':
                # Auth handler only needs itself
                pass
            elif function_config['file'] == 'chat_handler.py':
                # Chat handler needs auth_handler and agentcore_http_client
                shared_files = ['auth_handler.py', 'agentcore_http_client.py']
            else:
                # Other handlers need auth_handler and direct_agent_client
                shared_files = ['auth_handler.py', 'direct_agent_client.py']
            
            for shared_file in shared_files:
                try:
                    zipf.write(f"backend/lambda/{shared_file}", shared_file)
                except FileNotFoundError:
                    print(f"⚠️ Shared file not found: {shared_file}")
        
        return package_name

    def deploy_lambda_function(self, function_config, role_arn):
        """Deploy Lambda function"""
        function_name = function_config['name']
        
        try:
            # Check if function exists
            self.lambda_client.get_function(FunctionName=function_name)
            print(f"📝 Updating existing Lambda function: {function_name}")
            
            # Create deployment package
            package_name = self.create_lambda_deployment_package(function_config)
            
            # Update function code
            with open(package_name, 'rb') as f:
                self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=f.read()
                )
            
            # Clean up package
            os.remove(package_name)
            
            # Get function ARN
            response = self.lambda_client.get_function(FunctionName=function_name)
            return response['Configuration']['FunctionArn']
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"🚀 Creating new Lambda function: {function_name}")
                
                # Create deployment package
                package_name = self.create_lambda_deployment_package(function_config)
                
                # Create function
                with open(package_name, 'rb') as f:
                    response = self.lambda_client.create_function(
                        FunctionName=function_name,
                        Runtime='python3.11',
                        Role=role_arn,
                        Handler=function_config['handler'],
                        Code={'ZipFile': f.read()},
                        Description=f'Ticket System {function_name}',
                        Timeout=30,
                        MemorySize=256,
                        Environment={
                            'Variables': {
                                'COGNITO_CLIENT_ID': os.getenv('COGNITO_CLIENT_ID', ''),
                                'COGNITO_TEST_USER': os.getenv('COGNITO_TEST_USER', ''),
                                'COGNITO_TEST_PASSWORD': os.getenv('COGNITO_TEST_PASSWORD', ''),
                                'DATA_AGENT_ARN': 'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_data_agent-mNwb8TETc3',
                                'TICKET_AGENT_ARN': 'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR',
                                'DB_CLUSTER_ARN': os.getenv('DB_CLUSTER_ARN', ''),
                                'DB_SECRET_ARN': os.getenv('DB_SECRET_ARN', ''),
                                'DATABASE_NAME': os.getenv('DATABASE_NAME', 'ticket_system'),
                                'BEDROCK_MODEL_ID': os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
                            }
                        }
                    )
                
                # Clean up package
                os.remove(package_name)
                
                print(f"✅ Created Lambda function: {function_name}")
                return response['FunctionArn']
            else:
                raise

    def create_api_gateway(self):
        """Create API Gateway REST API"""
        try:
            # Check if API already exists and delete it to start fresh
            apis = self.apigateway.get_rest_apis()
            for api in apis['items']:
                if api['name'] == self.api_name:
                    print(f"🗑️ Deleting existing API Gateway: {api['id']}")
                    self.apigateway.delete_rest_api(restApiId=api['id'])
                    time.sleep(5)  # Wait for deletion to complete
                    break
            
            # Create new API
            print(f"🚀 Creating API Gateway: {self.api_name}")
            
            response = self.apigateway.create_rest_api(
                name=self.api_name,
                description='Ticket Auto-Processing System API',
                endpointConfiguration={
                    'types': ['REGIONAL']
                }
            )
            
            api_id = response['id']
            print(f"✅ Created API Gateway: {api_id}")
            return api_id
            
        except Exception as e:
            print(f"❌ Failed to create API Gateway: {e}")
            raise

    def setup_api_resources_and_methods(self, api_id, lambda_arns):
        """Set up API resources and methods"""
        print("📋 Setting up API resources and methods...")
        
        # Get root resource
        resources = self.apigateway.get_resources(restApiId=api_id)
        root_resource_id = None
        for resource in resources['items']:
            if resource['path'] == '/':
                root_resource_id = resource['id']
                break
        
        if not root_resource_id:
            raise Exception("Root resource not found")
        
        # Create resources and methods
        resource_configs = [
            {
                'path': 'auth',
                'methods': ['POST', 'OPTIONS'],
                'lambda_arn': lambda_arns['auth']
            },
            {
                'path': 'chat',
                'methods': ['POST', 'OPTIONS'],
                'lambda_arn': lambda_arns['chat']
            },
            {
                'path': 'customers',
                'methods': ['OPTIONS'],
                'sub_resources': [
                    {
                        'path': '{customer_id}',
                        'methods': ['GET', 'OPTIONS'],
                        'lambda_arn': lambda_arns['customers']
                    }
                ]
            },
            {
                'path': 'tickets',
                'methods': ['OPTIONS'],
                'sub_resources': [
                    {
                        'path': '{ticket_id}',
                        'methods': ['OPTIONS'],
                        'sub_resources': [
                            {'path': 'validate', 'methods': ['POST', 'OPTIONS'], 'lambda_arn': lambda_arns['tickets']},
                            {'path': 'pricing', 'methods': ['POST', 'OPTIONS'], 'lambda_arn': lambda_arns['tickets']},
                            {'path': 'recommendations', 'methods': ['GET', 'OPTIONS'], 'lambda_arn': lambda_arns['tickets']},
                            {'path': 'tiers', 'methods': ['GET', 'OPTIONS'], 'lambda_arn': lambda_arns['tickets']}
                        ]
                    }
                ]
            },
            {
                'path': 'orders',
                'methods': ['POST', 'OPTIONS'],
                'lambda_arn': lambda_arns['customers']
            }
        ]
        
        created_resources = {}
        
        def create_resource_recursive(parent_id, configs, parent_path='', parent_lambda_arn=None):
            for config in configs:
                resource_path = f"{parent_path}/{config['path']}"
                
                # Use config lambda_arn or inherit from parent
                current_lambda_arn = config.get('lambda_arn', parent_lambda_arn)
                
                # Create resource
                response = self.apigateway.create_resource(
                    restApiId=api_id,
                    parentId=parent_id,
                    pathPart=config['path']
                )
                resource_id = response['id']
                created_resources[resource_path] = resource_id
                print(f"✅ Created resource: {resource_path}")
                
                # Create methods for this resource
                if 'methods' in config:
                    for method in config['methods']:
                        self.create_method(api_id, resource_id, method, current_lambda_arn)
                
                # Create sub-resources
                if 'sub_resources' in config:
                    create_resource_recursive(resource_id, config['sub_resources'], resource_path, current_lambda_arn)
        
        create_resource_recursive(root_resource_id, resource_configs)
        
        return created_resources

    def create_method(self, api_id, resource_id, http_method, lambda_arn=None):
        """Create API method"""
        if http_method == 'OPTIONS':
            # Create OPTIONS method for CORS
            self.apigateway.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                authorizationType='NONE'
            )
            
            # Set up mock integration for OPTIONS
            self.apigateway.put_integration(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                type='MOCK',
                requestTemplates={
                    'application/json': '{"statusCode": 200}'
                }
            )
            
            # Set up method response
            self.apigateway.put_method_response(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': False,
                    'method.response.header.Access-Control-Allow-Methods': False,
                    'method.response.header.Access-Control-Allow-Origin': False
                }
            )
            
            # Set up integration response
            self.apigateway.put_integration_response(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod='OPTIONS',
                statusCode='200',
                responseParameters={
                    'method.response.header.Access-Control-Allow-Headers': "'Content-Type,Authorization'",
                    'method.response.header.Access-Control-Allow-Methods': "'GET,POST,PUT,DELETE,OPTIONS'",
                    'method.response.header.Access-Control-Allow-Origin': "'*'"
                }
            )
            
        else:
            # Create regular method
            self.apigateway.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod=http_method,
                authorizationType='NONE'
            )
            
            if lambda_arn:
                # Set up Lambda integration
                integration_uri = f"arn:aws:apigateway:{self.aws_region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
                
                self.apigateway.put_integration(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod=http_method,
                    type='AWS_PROXY',
                    integrationHttpMethod='POST',
                    uri=integration_uri
                )
                
                # Add Lambda permission
                function_name = lambda_arn.split(':')[-1]
                try:
                    self.lambda_client.add_permission(
                        FunctionName=function_name,
                        StatementId=f'apigateway-{api_id}-{resource_id}-{http_method}',
                        Action='lambda:InvokeFunction',
                        Principal='apigateway.amazonaws.com',
                        SourceArn=f'arn:aws:execute-api:{self.aws_region}:{self.account_id}:{api_id}/*/*'
                    )
                except ClientError as e:
                    if e.response['Error']['Code'] != 'ResourceConflictException':
                        raise
            else:
                print(f"⚠️ No Lambda ARN provided for {http_method} method - creating mock integration")
                # Create mock integration for methods without Lambda
                self.apigateway.put_integration(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod=http_method,
                    type='MOCK',
                    requestTemplates={
                        'application/json': '{"statusCode": 501}'
                    }
                )
        
        print(f"✅ Created method: {http_method}")

    def deploy_api(self, api_id):
        """Deploy API to stage"""
        print(f"🚀 Deploying API to stage: {self.stage_name}")
        
        try:
            self.apigateway.create_deployment(
                restApiId=api_id,
                stageName=self.stage_name,
                description='Production deployment'
            )
            
            api_url = f"https://{api_id}.execute-api.{self.aws_region}.amazonaws.com/{self.stage_name}"
            print(f"✅ API deployed successfully!")
            print(f"🔗 API URL: {api_url}")
            
            return api_url
            
        except Exception as e:
            print(f"❌ Failed to deploy API: {e}")
            raise

    def setup_complete_api(self):
        """Set up complete API Gateway with Lambda integration"""
        print("🚀 Setting up API Gateway with Lambda Integration")
        print("=" * 60)
        
        try:
            # Create Lambda execution role
            role_arn = self.create_lambda_execution_role()
            
            # Deploy Lambda functions
            lambda_arns = {}
            for key, config in self.lambda_functions.items():
                lambda_arns[key] = self.deploy_lambda_function(config, role_arn)
            
            # Create API Gateway
            api_id = self.create_api_gateway()
            
            # Set up resources and methods
            self.setup_api_resources_and_methods(api_id, lambda_arns)
            
            # Deploy API
            api_url = self.deploy_api(api_id)
            
            # Update .env file with API URL
            self.update_env_file(api_url)
            
            print("\n🎉 API Gateway setup completed successfully!")
            print(f"📋 API ID: {api_id}")
            print(f"🔗 API URL: {api_url}")
            print("\n📋 Available endpoints:")
            print(f"   POST {api_url}/auth")
            print(f"   POST {api_url}/chat")
            print(f"   GET  {api_url}/customers/{{customer_id}}")
            print(f"   POST {api_url}/orders")
            print(f"   POST {api_url}/tickets/{{ticket_id}}/validate")
            print(f"   POST {api_url}/tickets/{{ticket_id}}/pricing")
            print(f"   GET  {api_url}/tickets/{{ticket_id}}/recommendations")
            print(f"   GET  {api_url}/tickets/{{ticket_id}}/tiers")
            
            return {
                'api_id': api_id,
                'api_url': api_url,
                'lambda_arns': lambda_arns
            }
            
        except Exception as e:
            print(f"❌ API Gateway setup failed: {e}")
            raise

    def update_env_file(self, api_url):
        """Update .env file with API URL"""
        try:
            # Read existing .env file
            env_content = []
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    env_content = f.readlines()
            
            # Update or add API_GATEWAY_URL
            updated = False
            for i, line in enumerate(env_content):
                if line.startswith('API_GATEWAY_URL='):
                    env_content[i] = f'API_GATEWAY_URL={api_url}\n'
                    updated = True
                    break
            
            if not updated:
                env_content.append(f'API_GATEWAY_URL={api_url}\n')
            
            # Write updated .env file
            with open('.env', 'w') as f:
                f.writelines(env_content)
            
            print(f"✅ Updated .env file with API URL")
            
        except Exception as e:
            print(f"⚠️ Failed to update .env file: {e}")


def main():
    """Main setup function"""
    setup = APIGatewaySetup()
    result = setup.setup_complete_api()
    return result


if __name__ == "__main__":
    main()