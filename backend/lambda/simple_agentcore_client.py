#!/usr/bin/env python3
"""
Simplified AgentCore Client for Lambda

This client makes direct HTTP calls to AgentCore agents without using MCP libraries.
"""

import json
import boto3
import os
from typing import Dict, Any, Optional


class SimpleAgentCoreClient:
    """Simplified client for AgentCore communication"""
    
    def __init__(self):
        self.bearer_token = None
        self.data_agent_arn = os.getenv('DATA_AGENT_ARN', 
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_data_agent-mNwb8TETc3')
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN',
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR')
        
        # Initialize Bedrock AgentCore client
        self.bedrock_agentcore = boto3.client('bedrock-agentcore', region_name='us-west-2')
    
    def get_bearer_token(self):
        """Get OAuth bearer token for AgentCore"""
        if self.bearer_token:
            return self.bearer_token
            
        try:
            # Get Cognito credentials
            cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
            cognito_user = os.getenv('COGNITO_TEST_USER')
            cognito_password = os.getenv('COGNITO_TEST_PASSWORD')
            
            if not all([cognito_client_id, cognito_user, cognito_password]):
                raise Exception("Missing Cognito configuration")
            
            # Authenticate with Cognito
            cognito_client = boto3.client('cognito-idp', region_name='us-west-2')
            
            response = cognito_client.initiate_auth(
                ClientId=cognito_client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': cognito_user,
                    'PASSWORD': cognito_password
                }
            )
            
            self.bearer_token = response['AuthenticationResult']['AccessToken']
            return self.bearer_token
            
        except Exception as e:
            print(f"Failed to get bearer token: {e}")
            return None
    
    def invoke_agent(self, agent_arn: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke AgentCore agent using Bedrock AgentCore client"""
        try:
            bearer_token = self.get_bearer_token()
            if not bearer_token:
                return {'success': False, 'error': 'Failed to get authentication token'}
            
            # Create the invocation request
            request_body = {
                'tool': tool_name,
                'arguments': arguments
            }
            
            # Invoke the agent
            response = self.bedrock_agentcore.invoke_agent(
                agentRuntimeId=agent_arn,
                inputText=json.dumps(request_body),
                sessionId='lambda-session-' + str(hash(agent_arn + tool_name))[:8]
            )
            
            # Parse response
            if 'completion' in response:
                try:
                    result = json.loads(response['completion'])
                    return {'success': True, 'data': result}
                except json.JSONDecodeError:
                    return {'success': True, 'data': response['completion']}
            else:
                return {'success': False, 'error': 'No completion in response'}
                
        except Exception as e:
            print(f"Agent invocation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    # Data Agent methods
    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer by ID"""
        return self.invoke_agent(self.data_agent_arn, 'get_customer', {'customer_id': customer_id})
    
    async def get_tickets_for_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get tickets for customer"""
        return self.invoke_agent(self.data_agent_arn, 'get_tickets_for_customer', {'customer_id': customer_id})
    
    async def create_upgrade_order(self, customer_id: str, ticket_id: str, upgrade_tier: str, 
                                 travel_date: str, total_amount: float) -> Dict[str, Any]:
        """Create upgrade order"""
        return self.invoke_agent(self.data_agent_arn, 'create_upgrade_order', {
            'customer_id': customer_id,
            'ticket_id': ticket_id,
            'upgrade_tier': upgrade_tier,
            'travel_date': travel_date,
            'total_amount': total_amount
        })
    
    # Ticket Agent methods
    async def validate_ticket_eligibility(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Validate ticket eligibility for upgrade"""
        return self.invoke_agent(self.ticket_agent_arn, 'validate_ticket_eligibility', {
            'ticket_id': ticket_id,
            'upgrade_tier': upgrade_tier
        })
    
    async def calculate_upgrade_pricing(self, ticket_id: str, upgrade_tier: str, travel_date: str) -> Dict[str, Any]:
        """Calculate upgrade pricing"""
        return self.invoke_agent(self.ticket_agent_arn, 'calculate_upgrade_pricing', {
            'ticket_id': ticket_id,
            'upgrade_tier': upgrade_tier,
            'travel_date': travel_date
        })
    
    async def get_upgrade_recommendations(self, customer_id: str, ticket_id: str) -> Dict[str, Any]:
        """Get upgrade recommendations"""
        return self.invoke_agent(self.ticket_agent_arn, 'get_upgrade_recommendations', {
            'customer_id': customer_id,
            'ticket_id': ticket_id
        })
    
    async def get_available_upgrade_tiers(self, ticket_id: str) -> Dict[str, Any]:
        """Get available upgrade tiers"""
        return self.invoke_agent(self.ticket_agent_arn, 'get_available_upgrade_tiers', {
            'ticket_id': ticket_id
        })


def create_client():
    """Create and return a SimpleAgentCoreClient instance"""
    return SimpleAgentCoreClient()