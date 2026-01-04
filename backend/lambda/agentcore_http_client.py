#!/usr/bin/env python3
"""
AgentCore HTTP Client for Lambda

This client makes HTTP requests to AgentCore agents without requiring MCP libraries.
"""

import json
import boto3
import urllib3
import os
from typing import Dict, Any, Optional


class AgentCoreHTTPClient:
    """Simple HTTP client for AgentCore Ticket Agent only"""
    
    def __init__(self):
        # Only connect to Ticket Agent - it will call Data Agent tools internally
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN',
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR')
        
        # Initialize urllib3 pool manager
        self.http = urllib3.PoolManager()
        
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
    
    def _call_agent_http(self, agent_arn: str, input_text: str) -> Dict[str, Any]:
        """Call AgentCore agent using HTTP endpoint"""
        try:
            if not self.bearer_token:
                return {'success': False, 'error': 'No bearer token available'}
            
            # Encode ARN for URL
            encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
            agent_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
            
            # Headers for authentication
            headers = {
                'Authorization': f'Bearer {self.bearer_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json, text/event-stream'
            }
            
            # Request payload
            payload = {
                'inputText': input_text,
                'sessionId': f'lambda-session-{hash(agent_arn + input_text)}'[:16]
            }
            
            # Make HTTP request using urllib3
            response = self.http.request(
                'POST',
                agent_url,
                body=json.dumps(payload),
                headers=headers,
                timeout=30
            )
            
            if response.status == 200:
                result = json.loads(response.data.decode('utf-8'))
                return {'success': True, 'data': result}
            else:
                return {'success': False, 'error': f'HTTP {response.status}: {response.data.decode("utf-8")}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # All methods now call ONLY the Ticket Agent
    # The Ticket Agent will internally call Data Agent tools as needed
    
    def validate_ticket_eligibility(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Validate ticket eligibility for upgrade - calls Ticket Agent only"""
        input_text = f"Validate if ticket {ticket_id} is eligible for {upgrade_tier} upgrade"
        return self._call_agent_http(self.ticket_agent_arn, input_text)
    
    def calculate_upgrade_pricing(self, ticket_id: str, upgrade_tier: str, travel_date: str) -> Dict[str, Any]:
        """Calculate upgrade pricing - calls Ticket Agent only"""
        input_text = f"Calculate pricing for ticket {ticket_id} upgrade to {upgrade_tier} on {travel_date}"
        return self._call_agent_http(self.ticket_agent_arn, input_text)
    
    def get_upgrade_recommendations(self, customer_id: str, ticket_id: str) -> Dict[str, Any]:
        """Get upgrade recommendations - calls Ticket Agent only"""
        input_text = f"Get upgrade recommendations for customer {customer_id} with ticket {ticket_id}"
        return self._call_agent_http(self.ticket_agent_arn, input_text)
    
    def get_available_upgrade_tiers(self, ticket_id: str) -> Dict[str, Any]:
        """Get available upgrade tiers - calls Ticket Agent only"""
        input_text = f"Get available upgrade tiers for ticket {ticket_id}"
        return self._call_agent_http(self.ticket_agent_arn, input_text)


def create_client():
    """Create and return an AgentCoreHTTPClient instance"""
    return AgentCoreHTTPClient()