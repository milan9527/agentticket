#!/usr/bin/env python3
"""
AgentCore MCP Client for Lambda Functions

This module provides a client interface for Lambda functions to communicate
with deployed AgentCore MCP agents using OAuth authentication.
"""

import asyncio
import os
import boto3
import json
from typing import Dict, Any, Optional
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


class AgentCoreClient:
    """Client for communicating with AgentCore MCP agents"""
    
    def __init__(self):
        self.bearer_token = None
        self.data_agent_arn = os.getenv('DATA_AGENT_ARN', 
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_data_agent-mNwb8TETc3')
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN',
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR')
        
    def get_bearer_token(self) -> bool:
        """Get Bearer token from Cognito"""
        try:
            cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
            test_user = os.getenv('COGNITO_TEST_USER')
            test_password = os.getenv('COGNITO_TEST_PASSWORD')
            aws_region = os.getenv('AWS_REGION', 'us-west-2')
            
            if not all([cognito_client_id, test_user, test_password]):
                print("Missing Cognito configuration")
                return False
            
            cognito_client = boto3.client('cognito-idp', region_name=aws_region)
            
            response = cognito_client.initiate_auth(
                ClientId=cognito_client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': test_user,
                    'PASSWORD': test_password
                }
            )
            
            self.bearer_token = response['AuthenticationResult']['AccessToken']
            return True
            
        except Exception as e:
            print(f"Failed to get Bearer token: {e}")
            return False

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

    async def call_data_agent_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the Data Agent"""
        try:
            async with await self.connect_to_agent(self.data_agent_arn) as (read_stream, write_stream, _):
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

    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer information"""
        return await self.call_data_agent_tool('get_customer', {'customer_id': customer_id})

    async def get_tickets_for_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get tickets for a customer"""
        return await self.call_data_agent_tool('get_tickets_for_customer', {'customer_id': customer_id})

    async def validate_ticket_eligibility(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Validate ticket eligibility for upgrades"""
        return await self.call_ticket_agent_tool('validate_ticket_eligibility', {
            'ticket_id': ticket_id,
            'upgrade_tier': upgrade_tier
        })

    async def calculate_upgrade_pricing(self, ticket_id: str, upgrade_tier: str, event_date: str) -> Dict[str, Any]:
        """Calculate upgrade pricing"""
        return await self.call_ticket_agent_tool('calculate_upgrade_pricing', {
            'ticket_id': ticket_id,
            'upgrade_tier': upgrade_tier,
            'event_date': event_date
        })

    async def get_upgrade_recommendations(self, customer_id: str, ticket_id: str) -> Dict[str, Any]:
        """Get personalized upgrade recommendations"""
        return await self.call_ticket_agent_tool('get_upgrade_recommendations', {
            'customer_id': customer_id,
            'ticket_id': ticket_id
        })

    async def get_upgrade_tier_comparison(self, ticket_id: str) -> Dict[str, Any]:
        """Get upgrade tier comparison"""
        return await self.call_ticket_agent_tool('get_upgrade_tier_comparison', {
            'ticket_id': ticket_id
        })

    async def create_upgrade_order(self, customer_id: str, ticket_id: str, upgrade_tier: str, 
                                 upgrade_price: float, payment_method: str) -> Dict[str, Any]:
        """Create an upgrade order"""
        return await self.call_data_agent_tool('create_upgrade_order', {
            'customer_id': customer_id,
            'ticket_id': ticket_id,
            'upgrade_tier': upgrade_tier,
            'upgrade_price': upgrade_price,
            'payment_method': payment_method
        })


def create_client() -> AgentCoreClient:
    """Factory function to create and authenticate AgentCore client"""
    client = AgentCoreClient()
    if not client.get_bearer_token():
        raise Exception("Failed to authenticate with AgentCore")
    return client