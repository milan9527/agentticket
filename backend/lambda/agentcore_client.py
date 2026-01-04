#!/usr/bin/env python3
"""
AgentCore HTTP Client for Lambda Functions (Fixed SSE Parsing)

This module provides a client interface for Lambda functions to communicate
with deployed AgentCore agents using direct HTTP requests and OAuth authentication.
"""

import asyncio
import os
import boto3
import json
import urllib3
from typing import Dict, Any, Optional

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AgentCoreClient:
    """Client for communicating with AgentCore agents via HTTP"""
    
    def __init__(self):
        self.bearer_token = None
        self.data_agent_arn = os.getenv('DATA_AGENT_ARN', 
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_data_agent-mNwb8TETc3')
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN',
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR')
        
        # Create HTTP pool manager with SSL verification disabled for development
        self.http = urllib3.PoolManager(
            cert_reqs='CERT_NONE',
            ca_certs=None
        )
        
    def _parse_sse_response(self, response_data: str) -> Dict[str, Any]:
        """Parse Server-Sent Events (SSE) response format"""
        if response_data.startswith('event:'):
            # Parse SSE format: extract JSON from data: lines
            lines = response_data.strip().split('\n')
            
            for line in lines:
                if line.startswith('data: '):
                    json_str = line[6:]  # Remove 'data: ' prefix
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        continue
            
            raise ValueError("Could not parse SSE response")
        else:
            # Handle regular JSON response
            return json.loads(response_data)

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

    async def call_agent_http(self, agent_arn: str, input_text: str, session_id: str = None) -> Dict[str, Any]:
        """Call AgentCore agent via HTTP"""
        try:
            if not self.bearer_token:
                return {'success': False, 'error': 'No bearer token available'}
            
            # Encode ARN for URL
            encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
            agent_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
            
            # Headers for authentication with proper MCP Accept header
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream'
            }
            
            # Request payload
            payload = {
                'inputText': input_text,
                'sessionId': session_id or f'lambda-session-{hash(agent_arn + input_text)}'[:16]
            }
            
            # Make HTTP request
            response = self.http.request(
                'POST',
                agent_url,
                body=json.dumps(payload),
                headers=headers,
                timeout=30
            )
            
            if response.status == 200:
                response_data = response.data.decode('utf-8')
                
                try:
                    result = self._parse_sse_response(response_data)
                except (json.JSONDecodeError, ValueError) as e:
                    return {
                        'success': False, 
                        'error': f'Response parsing error: {str(e)}',
                        'raw_response': response_data[:500]
                    }
                
                # Check for JSON-RPC errors
                if 'error' in result:
                    error = result['error']
                    return {
                        'success': False, 
                        'error': f"Agent Error {error.get('code', 'Unknown')}: {error.get('message', 'Internal error')}",
                        'error_code': error.get('code'),
                        'raw_response': result
                    }
                
                # Check for successful response
                elif 'result' in result:
                    return {'success': True, 'data': result['result'], 'raw_response': result}
                elif 'output' in result:
                    return {'success': True, 'data': result['output'], 'raw_response': result}
                else:
                    return {'success': True, 'data': result, 'raw_response': result}
                    
            else:
                return {
                    'success': False, 
                    'error': f'HTTP {response.status}: {response.data.decode("utf-8")}',
                    'status_code': response.status
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def call_agent_async(self, agent_arn: str, input_text: str) -> Dict[str, Any]:
        """Call AgentCore agent directly for chat/conversation"""
        return await self.call_agent_http(agent_arn, input_text)

    async def call_data_agent_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the Data Agent via HTTP with proper MCP format"""
        try:
            # Format as proper MCP tool call instead of natural language
            mcp_request = {
                "jsonrpc": "2.0",
                "id": f"tool-call-{hash(str(arguments))}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send as JSON-RPC request to the agent
            if not self.bearer_token:
                return {'success': False, 'error': 'No bearer token available'}
            
            # Encode ARN for URL
            encoded_arn = self.data_agent_arn.replace(':', '%3A').replace('/', '%2F')
            agent_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
            
            # Headers for MCP tool call
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream'
            }
            
            # Make direct MCP tool call
            response = self.http.request(
                'POST',
                agent_url,
                body=json.dumps(mcp_request),
                headers=headers,
                timeout=30
            )
            
            if response.status == 200:
                try:
                    result = self._parse_sse_response(response.data.decode('utf-8'))
                except (json.JSONDecodeError, ValueError) as e:
                    return {
                        'success': False,
                        'error': f'Response parsing error: {str(e)}',
                        'data': {},
                        'raw_content': []
                    }
                
                # Check for JSON-RPC errors
                if 'error' in result:
                    return {
                        'success': False,
                        'error': f"MCP Error {result['error'].get('code', 'Unknown')}: {result['error'].get('message', 'Internal error')}",
                        'data': {},
                        'raw_content': []
                    }
                
                # Check for successful MCP response
                elif 'result' in result:
                    return {
                        'success': True,
                        'data': result['result'],
                        'raw_content': [str(result['result'])]
                    }
                else:
                    return {
                        'success': True,
                        'data': result,
                        'raw_content': [str(result)]
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status}: {response.data.decode("utf-8")}',
                    'data': {},
                    'raw_content': []
                }
                        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data': {},
                'raw_content': []
            }

    async def call_ticket_agent_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the Ticket Agent via HTTP with proper MCP format"""
        try:
            # Format as proper MCP tool call instead of natural language
            mcp_request = {
                "jsonrpc": "2.0",
                "id": f"tool-call-{hash(str(arguments))}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
            
            # Send as JSON-RPC request to the agent
            if not self.bearer_token:
                return {'success': False, 'error': 'No bearer token available'}
            
            # Encode ARN for URL
            encoded_arn = self.ticket_agent_arn.replace(':', '%3A').replace('/', '%2F')
            agent_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
            
            # Headers for MCP tool call
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream'
            }
            
            # Make direct MCP tool call
            response = self.http.request(
                'POST',
                agent_url,
                body=json.dumps(mcp_request),
                headers=headers,
                timeout=30
            )
            
            if response.status == 200:
                try:
                    result = self._parse_sse_response(response.data.decode('utf-8'))
                except (json.JSONDecodeError, ValueError) as e:
                    return {
                        'success': False,
                        'error': f'Response parsing error: {str(e)}',
                        'data': {},
                        'raw_content': []
                    }
                
                # Check for JSON-RPC errors
                if 'error' in result:
                    return {
                        'success': False,
                        'error': f"MCP Error {result['error'].get('code', 'Unknown')}: {result['error'].get('message', 'Internal error')}",
                        'data': {},
                        'raw_content': []
                    }
                
                # Check for successful MCP response
                elif 'result' in result:
                    return {
                        'success': True,
                        'data': result['result'],
                        'raw_content': [str(result['result'])]
                    }
                else:
                    return {
                        'success': True,
                        'data': result,
                        'raw_content': [str(result)]
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status}: {response.data.decode("utf-8")}',
                    'data': {},
                    'raw_content': []
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

    async def calculate_upgrade_pricing(self, ticket_type: str, upgrade_tier: str, original_price: float = None) -> Dict[str, Any]:
        """Calculate upgrade pricing"""
        arguments = {
            'ticket_type': ticket_type,
            'upgrade_tier': upgrade_tier
        }
        if original_price is not None:
            arguments['original_price'] = original_price
            
        return await self.call_ticket_agent_tool('calculate_upgrade_pricing', arguments)

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