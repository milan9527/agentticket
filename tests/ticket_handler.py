#!/usr/bin/env python3
"""
Ticket Operations Lambda Function

Handles ticket-related operations by orchestrating calls to AgentCore agents.
"""

import json
import asyncio
import os
import threading
from typing import Dict, Any
from agentcore_client import create_client
from auth_handler import verify_token


def run_async_in_thread(coro):
    """Run async function in a separate thread to avoid event loop conflicts"""
    result = {}
    exception = {}
    
    def run_in_thread():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result['value'] = loop.run_until_complete(coro)
        except Exception as e:
            exception['error'] = e
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join()
    
    if 'error' in exception:
        raise exception['error']
    
    return result['value']


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for ticket operations
    
    Supported operations:
    - GET /tickets/{customer_id} - Get tickets for customer
    - POST /tickets/{ticket_id}/validate - Validate ticket eligibility
    - POST /tickets/{ticket_id}/pricing - Calculate upgrade pricing
    - GET /tickets/{ticket_id}/recommendations - Get upgrade recommendations
    - GET /tickets/{ticket_id}/tiers - Get tier comparison
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
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Missing or invalid authorization header'})
            }
        
        token = auth_header.replace('Bearer ', '')
        auth_result = verify_token(token)
        if not auth_result['success']:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': 'Invalid token'})
            }
        
        # Parse request
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        
        # Parse body if present
        body = {}
        if event.get('body'):
            body = json.loads(event['body'])
        
        # Route to appropriate handler
        return run_async_in_thread(route_request(http_method, path, path_parameters, query_parameters, body))
        
    except Exception as e:
        print(f"Ticket handler error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }


async def route_request(method: str, path: str, path_params: Dict[str, Any], 
                       query_params: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Route request to appropriate handler"""
    
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        # Create AgentCore client
        client = create_client()
        
        # Route based on path and method
        if method == 'GET' and '/tickets/' in path and path.endswith('/tickets'):
            # GET /tickets/{customer_id}
            customer_id = path_params.get('customer_id')
            if not customer_id:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Customer ID is required'})
                }
            
            result = await client.get_tickets_for_customer(customer_id)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
            }
        
        elif method == 'POST' and '/validate' in path:
            # POST /tickets/{ticket_id}/validate
            ticket_id = path_params.get('ticket_id')
            upgrade_tier = body.get('upgrade_tier', 'Standard')
            
            if not ticket_id:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Ticket ID is required'})
                }
            
            result = await client.validate_ticket_eligibility(ticket_id, upgrade_tier)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
            }
        
        elif method == 'POST' and '/pricing' in path:
            # POST /tickets/{ticket_id}/pricing
            ticket_id = path_params.get('ticket_id')
            upgrade_tier = body.get('upgrade_tier', 'Standard')
            event_date = body.get('event_date', '2026-02-15')
            
            if not ticket_id:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Ticket ID is required'})
                }
            
            result = await client.calculate_upgrade_pricing(ticket_id, upgrade_tier, event_date)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
            }
        
        elif method == 'GET' and '/recommendations' in path:
            # GET /tickets/{ticket_id}/recommendations
            ticket_id = path_params.get('ticket_id')
            customer_id = query_params.get('customer_id')
            
            if not ticket_id or not customer_id:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Ticket ID and Customer ID are required'})
                }
            
            result = await client.get_upgrade_recommendations(customer_id, ticket_id)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
            }
        
        elif method == 'GET' and '/tiers' in path:
            # GET /tickets/{ticket_id}/tiers
            ticket_id = path_params.get('ticket_id')
            
            if not ticket_id:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Ticket ID is required'})
                }
            
            result = await client.get_upgrade_tier_comparison(ticket_id)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
            }
        
        else:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': 'Endpoint not found'})
            }
            
    except Exception as e:
        print(f"Route handler error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }