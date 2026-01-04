#!/usr/bin/env python3
"""
AgentCore MCP Client for Lambda

This client connects to the existing AgentCore runtime agents using MCP protocol.
The AgentCore agents are already deployed and working as MCP servers.
"""

import asyncio
import json
import os
import boto3
from typing import Dict, Any, Optional
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.client.stdio import StdioServerParameters


class AgentCoreMCPClient:
    """Client for connecting to AgentCore MCP agents"""
    
    def __init__(self):
        self.data_agent_arn = os.getenv('DATA_AGENT_ARN', 
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_data_agent-mNwb8TETc3')
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN',
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR')
        
        # Get authentication token
        self.bearer_token = self._get_bearer_token()
    
    def _get_bearer_token(self) -> Optional[str]:
        """Get OAuth bearer token for AgentCore authentication"""
        try:
            # Get Cognito credentials
            cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
            cognito_user = os.getenv('COGNITO_TEST_USER')
            cognito_password = os.getenv('COGNITO_TEST_PASSWORD')
            
            if not all([cognito_client_id, cognito_user, cognito_password]):
                print("Missing Cognito configuration")
                return None
            
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
            
            return response['AuthenticationResult']['AccessToken']
            
        except Exception as e:
            print(f"Failed to get bearer token: {e}")
            return None
    
    async def _connect_to_agent(self, agent_arn: str):
        """Connect to AgentCore agent using MCP SSE transport"""
        if not self.bearer_token:
            raise Exception("No bearer token available")
        
        # AgentCore MCP endpoint URL
        agent_url = f"https://agentcore.us-west-2.amazonaws.com/runtime/{agent_arn.split('/')[-1]}/mcp"
        
        # Headers for authentication
        headers = {
            'Authorization': f'Bearer {self.bearer_token}',
            'Content-Type': 'application/json'
        }
        
        # Connect using SSE client
        return sse_client(agent_url, headers=headers)
    
    async def call_agent_tool(self, agent_arn: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on an AgentCore agent"""
        try:
            async with await self._connect_to_agent(agent_arn) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    
                    # List available tools to verify the tool exists
                    tools_result = await session.list_tools()
                    
                    # Find the requested tool
                    tool = None
                    for t in tools_result.tools:
                        if t.name == tool_name:
                            tool = t
                            break
                    
                    if not tool:
                        return {'success': False, 'error': f'Tool {tool_name} not found'}
                    
                    # Call the tool
                    result = await session.call_tool(tool_name, arguments)
                    
                    # Return the result
                    if result.isError:
                        return {
                            'success': False, 
                            'error': result.content[0].text if result.content else 'Tool execution failed'
                        }
                    else:
                        # Try to parse the result as JSON, fallback to text
                        result_text = result.content[0].text if result.content else 'Success'
                        try:
                            result_data = json.loads(result_text)
                            return {'success': True, 'data': result_data}
                        except json.JSONDecodeError:
                            return {'success': True, 'data': {'result': result_text}}
                        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # Data Agent methods
    async def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer by ID"""
        return await self.call_agent_tool(
            self.data_agent_arn, 
            'get_customer', 
            {'customer_id': customer_id}
        )
    
    async def get_tickets_for_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get tickets for customer"""
        return await self.call_agent_tool(
            self.data_agent_arn, 
            'get_tickets_for_customer', 
            {'customer_id': customer_id}
        )
    
    async def create_upgrade_order(self, customer_id: str, ticket_id: str, upgrade_tier: str, 
                                 travel_date: str, total_amount: float) -> Dict[str, Any]:
        """Create upgrade order"""
        return await self.call_agent_tool(
            self.data_agent_arn, 
            'create_upgrade_order', 
            {
                'customer_id': customer_id,
                'ticket_id': ticket_id,
                'upgrade_tier': upgrade_tier,
                'travel_date': travel_date,
                'total_amount': total_amount
            }
        )
    
    # Ticket Agent methods
    async def validate_ticket_eligibility(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Validate ticket eligibility for upgrade"""
        return await self.call_agent_tool(
            self.ticket_agent_arn, 
            'validate_ticket_eligibility', 
            {
                'ticket_id': ticket_id,
                'upgrade_tier': upgrade_tier
            }
        )
    
    async def calculate_upgrade_pricing(self, ticket_id: str, upgrade_tier: str, travel_date: str) -> Dict[str, Any]:
        """Calculate upgrade pricing"""
        return await self.call_agent_tool(
            self.ticket_agent_arn, 
            'calculate_upgrade_pricing', 
            {
                'ticket_id': ticket_id,
                'upgrade_tier': upgrade_tier,
                'travel_date': travel_date
            }
        )
    
    async def get_upgrade_recommendations(self, customer_id: str, ticket_id: str) -> Dict[str, Any]:
        """Get upgrade recommendations"""
        return await self.call_agent_tool(
            self.ticket_agent_arn, 
            'get_upgrade_recommendations', 
            {
                'customer_id': customer_id,
                'ticket_id': ticket_id
            }
        )
    
    async def get_available_upgrade_tiers(self, ticket_id: str) -> Dict[str, Any]:
        """Get available upgrade tiers"""
        return await self.call_agent_tool(
            self.ticket_agent_arn, 
            'get_available_upgrade_tiers', 
            {
                'ticket_id': ticket_id
            }
        )


def create_client():
    """Create and return an AgentCoreMCPClient instance"""
    return AgentCoreMCPClient()