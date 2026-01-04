#!/usr/bin/env python3
"""
Bedrock AgentCore Client for Lambda

This client directly invokes AgentCore agents using the Bedrock AgentCore service.
"""

import json
import boto3
import os
from typing import Dict, Any, Optional


class BedrockAgentCoreClient:
    """Client for invoking AgentCore agents via Bedrock AgentCore service"""
    
    def __init__(self):
        self.data_agent_arn = os.getenv('DATA_AGENT_ARN', 
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_data_agent-mNwb8TETc3')
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN',
            'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR')
        
        # Initialize Bedrock AgentCore client
        self.bedrock_agentcore = boto3.client('bedrock-agentcore', region_name='us-west-2')
    
    def invoke_agent(self, agent_arn: str, input_text: str, session_id: str = None) -> Dict[str, Any]:
        """Invoke AgentCore agent using Bedrock AgentCore service"""
        try:
            if not session_id:
                session_id = f'lambda-session-{hash(agent_arn + input_text)}'[:16]
            
            # Invoke the agent
            response = self.bedrock_agentcore.invoke_agent(
                agentRuntimeId=agent_arn,
                inputText=input_text,
                sessionId=session_id
            )
            
            # Parse response
            if 'completion' in response:
                try:
                    # Try to parse as JSON first
                    result = json.loads(response['completion'])
                    return {'success': True, 'data': result}
                except json.JSONDecodeError:
                    # If not JSON, return as text
                    return {'success': True, 'data': {'result': response['completion']}}
            else:
                return {'success': False, 'error': 'No completion in response'}
                
        except Exception as e:
            print(f"Agent invocation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    # Data Agent methods
    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get customer by ID"""
        input_text = f"Get customer with ID: {customer_id}"
        return self.invoke_agent(self.data_agent_arn, input_text)
    
    def get_tickets_for_customer(self, customer_id: str) -> Dict[str, Any]:
        """Get tickets for customer"""
        input_text = f"Get all tickets for customer ID: {customer_id}"
        return self.invoke_agent(self.data_agent_arn, input_text)
    
    def create_upgrade_order(self, customer_id: str, ticket_id: str, upgrade_tier: str, 
                           travel_date: str, total_amount: float) -> Dict[str, Any]:
        """Create upgrade order"""
        input_text = f"Create upgrade order for customer {customer_id}, ticket {ticket_id}, tier {upgrade_tier}, date {travel_date}, amount ${total_amount}"
        return self.invoke_agent(self.data_agent_arn, input_text)
    
    # Ticket Agent methods
    def validate_ticket_eligibility(self, ticket_id: str, upgrade_tier: str) -> Dict[str, Any]:
        """Validate ticket eligibility for upgrade"""
        input_text = f"Validate if ticket {ticket_id} is eligible for {upgrade_tier} upgrade"
        return self.invoke_agent(self.ticket_agent_arn, input_text)
    
    def calculate_upgrade_pricing(self, ticket_id: str, upgrade_tier: str, travel_date: str) -> Dict[str, Any]:
        """Calculate upgrade pricing"""
        input_text = f"Calculate pricing for ticket {ticket_id} upgrade to {upgrade_tier} on {travel_date}"
        return self.invoke_agent(self.ticket_agent_arn, input_text)
    
    def get_upgrade_recommendations(self, customer_id: str, ticket_id: str) -> Dict[str, Any]:
        """Get upgrade recommendations"""
        input_text = f"Get upgrade recommendations for customer {customer_id} with ticket {ticket_id}"
        return self.invoke_agent(self.ticket_agent_arn, input_text)
    
    def get_available_upgrade_tiers(self, ticket_id: str) -> Dict[str, Any]:
        """Get available upgrade tiers"""
        input_text = f"Get available upgrade tiers for ticket {ticket_id}"
        return self.invoke_agent(self.ticket_agent_arn, input_text)


def create_client():
    """Create and return a BedrockAgentCoreClient instance"""
    return BedrockAgentCoreClient()