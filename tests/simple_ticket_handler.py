#!/usr/bin/env python3
"""
Simplified Ticket Handler Lambda Function

Handles ticket-related operations using simplified AgentCore client.
"""

import json
import asyncio
import os
from typing import Dict, Any
from simple_agentcore_client import create_client
from auth_handler import verify_token


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for ticket operations
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
        
        # Create AgentCore client
        client = create_client()
        
        # Route to appropriate handler
        if '/validate' in path and method == 'POST':
            return handle_validate_ticket(client, path_params, event, headers)
        elif '/pricing' in path and method == 'POST':
            return handle_calculate_pricing(client, path_params, event, headers)
        elif '/recommendations' in path and method == 'GET':
            return handle_get_recommendations(client, path_params, event, headers)
        elif '/tiers' in path and method == 'GET':
            return handle_get_tiers(client, path_params, event, headers)
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        print(f"Ticket handler error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }


def handle_validate_ticket(client, path_params, event, headers):
    """Handle ticket validation"""
    try:
        ticket_id = path_params.get('ticket_id')
        if not ticket_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing ticket_id'})
            }
        
        body = json.loads(event.get('body', '{}'))
        upgrade_tier = body.get('upgrade_tier')
        if not upgrade_tier:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing upgrade_tier'})
            }
        
        # Call AgentCore agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(client.validate_ticket_eligibility(ticket_id, upgrade_tier))
        loop.close()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Validate ticket error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Validation failed'})
        }


def handle_calculate_pricing(client, path_params, event, headers):
    """Handle pricing calculation"""
    try:
        ticket_id = path_params.get('ticket_id')
        if not ticket_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing ticket_id'})
            }
        
        body = json.loads(event.get('body', '{}'))
        upgrade_tier = body.get('upgrade_tier')
        travel_date = body.get('travel_date')
        
        if not upgrade_tier or not travel_date:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing upgrade_tier or travel_date'})
            }
        
        # Call AgentCore agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(client.calculate_upgrade_pricing(ticket_id, upgrade_tier, travel_date))
        loop.close()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Calculate pricing error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Pricing calculation failed'})
        }


def handle_get_recommendations(client, path_params, event, headers):
    """Handle get recommendations"""
    try:
        ticket_id = path_params.get('ticket_id')
        if not ticket_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing ticket_id'})
            }
        
        # Get customer_id from query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        customer_id = query_params.get('customer_id')
        if not customer_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing customer_id query parameter'})
            }
        
        # Call AgentCore agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(client.get_upgrade_recommendations(customer_id, ticket_id))
        loop.close()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Get recommendations error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get recommendations'})
        }


def handle_get_tiers(client, path_params, event, headers):
    """Handle get available tiers"""
    try:
        ticket_id = path_params.get('ticket_id')
        if not ticket_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing ticket_id'})
            }
        
        # Call AgentCore agent
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(client.get_available_upgrade_tiers(ticket_id))
        loop.close()
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        print(f"Get tiers error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Failed to get tiers'})
        }