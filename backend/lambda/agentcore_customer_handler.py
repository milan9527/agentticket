#!/usr/bin/env python3
"""
AgentCore Customer Handler Lambda Function

Handles customer-related operations by connecting to the existing AgentCore MCP agents.
"""

import json
import os
from typing import Dict, Any
from direct_agent_client import create_client
from auth_handler import verify_token


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for customer operations
    """
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Verify authentication
        auth_header = event.get('headers', {}).get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Missing or invalid authorization header'})
            }
        
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        auth_result = verify_token(token)
        if not auth_result['success']:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid token'})
            }
        
        # Get path and method
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        path_params = event.get('pathParameters', {})
        
        # Create AgentCore MCP client
        client = create_client()
        
        # Route to appropriate handler
        if '/customers/' in path and method == 'GET':
            return handle_get_customer(client, path_params, event, headers)
        elif '/orders' in path and method == 'POST':
            return handle_create_order(client, path_params, event, headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        print(f"Customer handler error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }


def handle_get_customer(client, path_params, event, headers):
    """Handle get customer"""
    try:
        customer_id = path_params.get('customer_id')
        if not customer_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing customer_id'})
            }
        
        # Call AgentCore HTTP agent
        result = client.get_customer(customer_id)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Get customer error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get customer'})
        }


def handle_create_order(client, path_params, event, headers):
    """Handle create order"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        customer_id = body.get('customer_id')
        ticket_id = body.get('ticket_id')
        upgrade_tier = body.get('upgrade_tier')
        travel_date = body.get('travel_date')
        total_amount = body.get('total_amount')
        
        if not all([customer_id, ticket_id, upgrade_tier, travel_date, total_amount]):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing required fields'})
            }
        
        # Call AgentCore HTTP agent
        result = client.create_upgrade_order(
            customer_id, ticket_id, upgrade_tier, travel_date, float(total_amount)
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Create order error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to create order'})
        }