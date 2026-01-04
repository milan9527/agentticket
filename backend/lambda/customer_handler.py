#!/usr/bin/env python3
"""
Customer Operations Lambda Function

Handles customer-related operations by orchestrating calls to AgentCore agents.
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
    Lambda handler for customer operations
    
    Supported operations:
    - GET /customers/{customer_id} - Get customer information
    - POST /customers - Create new customer
    - POST /orders - Create upgrade order
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
        print(f"Customer handler error: {e}")
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
        if method == 'GET' and '/customers/' in path:
            # GET /customers/{customer_id}
            customer_id = path_params.get('customer_id')
            if not customer_id:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Customer ID is required'})
                }
            
            result = await client.get_customer(customer_id)
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(result)
            }
        
        elif method == 'POST' and path.endswith('/customers'):
            # POST /customers - Create new customer
            required_fields = ['first_name', 'last_name', 'email']
            missing_fields = [field for field in required_fields if field not in body]
            
            if missing_fields:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': f'Missing required fields: {", ".join(missing_fields)}'})
                }
            
            # Note: This would need to be implemented in the Data Agent
            # For now, return a placeholder response
            return {
                'statusCode': 501,
                'headers': headers,
                'body': json.dumps({'error': 'Customer creation not yet implemented'})
            }
        
        elif method == 'POST' and path.endswith('/orders'):
            # POST /orders - Create upgrade order
            required_fields = ['customer_id', 'ticket_id', 'upgrade_tier', 'upgrade_price']
            missing_fields = [field for field in required_fields if field not in body]
            
            if missing_fields:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': f'Missing required fields: {", ".join(missing_fields)}'})
                }
            
            result = await client.create_upgrade_order(
                customer_id=body['customer_id'],
                ticket_id=body['ticket_id'],
                upgrade_tier=body['upgrade_tier'],
                upgrade_price=float(body['upgrade_price']),
                payment_method=body.get('payment_method', 'credit_card')
            )
            
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