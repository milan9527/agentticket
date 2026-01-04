#!/usr/bin/env python3
"""
Simplified AgentCore Client for Lambda

This client uses MCP to communicate with AgentCore agents.
"""

import asyncio
import os
import boto3
import json
from typing import Dict, Any, Optional
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class SimpleAgentCoreClient:
    """Simplified client for AgentCore communication using MCP"""
    
    def __init__(self):
        self.bearer_token = None
        self.data_agent_arn = os.getenv('DATA_AGENT_ARN', 
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_data_agent-mNwb8TETc3')
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN',
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR')
    
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

    async def connect_to_agent(self, agent_arn: str):
        """Create MCP connection to an agent"""
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        mcp_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        headers = {
            "authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        return streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False)

    async def call_ticket_agent_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the Ticket Agent"""
        try:
            async with await self.connect_to_agent(self.ticket_agent_arn) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(tool_name, arguments)
                    
                    # Parse result
                    if hasattr(result, 'structuredContent') and result.structuredContent:
                        return {
                            'success': True,
                            'data': result.structuredContent,
                            'raw_content': [content.text if hasattr(content, 'text') else str(content) 
                                          for content in result.content] if hasattr(result, 'content') else []
                        }
                    elif hasattr(result, 'content'):
                        return {
                            'success': True,
                            'data': {},
                            'raw_content': [content.text if hasattr(content, 'text') else str(content) 
                                          for content in result.content]
                        }
                    else:
                        return {
                            'success': True,
                            'data': {},
                            'raw_content': [str(result)]
                        }
                        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'raw_content': []
            }
    
    # Ticket Agent methods
    async def validate_ticket_eligibility(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Validate ticket eligibility for upgrade"""
        return await self.call_ticket_agent_tool('validate_ticket_eligibility', {
            'ticket_id': ticket_id,
            'upgrade_tier': upgrade_tier
        })
    
    async def calculate_upgrade_pricing(self, ticket_id: str, upgrade_tier: str, travel_date: str) -> Dict[str, Any]:
        """Calculate upgrade pricing"""
        return await self.call_ticket_agent_tool('calculate_upgrade_pricing', {
            'ticket_id': ticket_id,
            'upgrade_tier': upgrade_tier,
            'event_date': travel_date
        })
    
    async def get_upgrade_recommendations(self, customer_id: str, ticket_id: str) -> Dict[str, Any]:
        """Get upgrade recommendations"""
        return await self.call_ticket_agent_tool('get_upgrade_recommendations', {
            'customer_id': customer_id,
            'ticket_id': ticket_id
        })
    
    async def get_available_upgrade_tiers(self, ticket_id: str) -> Dict[str, Any]:
        """Get available upgrade tiers"""
        return await self.call_ticket_agent_tool('get_upgrade_tier_comparison', {
            'ticket_id': ticket_id
        })


def create_client():
    """Create and return a SimpleAgentCoreClient instance"""
    client = SimpleAgentCoreClient()
    if not client.get_bearer_token():
        raise Exception("Failed to authenticate with AgentCore")
    return client