#!/usr/bin/env python3
"""
Data Agent Invoker Lambda Function

This Lambda function serves as a bridge to invoke the Data Agent MCP server.
It receives MCP tool call requests and forwards them to the Data Agent MCP server.
"""

import json
import os
import sys
import asyncio
import threading
from typing import Dict, Any


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


async def invoke_data_agent_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a tool on the Data Agent MCP server"""
    try:
        # Import the simplified Data Agent tools
        from simplified_data_agent import (
            get_customer, 
            get_tickets_for_customer, 
            create_upgrade_order, 
            validate_data_integrity,
            create_customer
        )
        
        # Map tool names to functions
        tool_map = {
            'get_customer': get_customer,
            'get_tickets_for_customer': get_tickets_for_customer,
            'create_upgrade_order': create_upgrade_order,
            'validate_data_integrity': validate_data_integrity,
            'create_customer': create_customer
        }
        
        if tool_name not in tool_map:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}",
                "data": {}
            }
        
        # Call the appropriate tool function
        tool_function = tool_map[tool_name]
        
        # Handle different argument patterns
        if tool_name == 'get_customer':
            result = await tool_function(arguments.get('customer_id'))
        elif tool_name == 'get_tickets_for_customer':
            result = await tool_function(arguments.get('customer_id'))
        elif tool_name == 'create_upgrade_order':
            result = await tool_function(arguments)
        elif tool_name == 'create_customer':
            result = await tool_function(arguments)
        elif tool_name == 'validate_data_integrity':
            result = await tool_function()
        else:
            result = await tool_function(**arguments)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {}
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for Data Agent tool invocation
    
    Expected event format (MCP tool call):
    {
        "jsonrpc": "2.0",
        "id": "tool-call-123",
        "method": "tools/call",
        "params": {
            "name": "get_customer",
            "arguments": {"customer_id": "123"}
        }
    }
    """
    
    try:
        print(f"📥 Data Agent Invoker received event: {json.dumps(event)}")
        
        # Handle direct tool call format (from AgentCore HTTP client)
        if 'method' in event and event['method'] == 'tools/call':
            tool_name = event['params']['name']
            arguments = event['params']['arguments']
            
            print(f"🔧 Invoking Data Agent tool: {tool_name} with args: {arguments}")
            
            # Invoke the tool
            result = run_async_in_thread(invoke_data_agent_tool(tool_name, arguments))
            
            if result['success']:
                return {
                    "jsonrpc": "2.0",
                    "id": event.get('id', 'unknown'),
                    "result": result['data']
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": event.get('id', 'unknown'),
                    "error": {
                        "code": -32603,
                        "message": result['error']
                    }
                }
        
        # Handle API Gateway format (from customer_handler)
        elif 'httpMethod' in event:
            # Parse body for tool call
            if event.get('body'):
                body = json.loads(event['body'])
                tool_name = body.get('tool_name')
                arguments = body.get('arguments', {})
                
                if not tool_name:
                    return {
                        'statusCode': 400,
                        'headers': {'Content-Type': 'application/json'},
                        'body': json.dumps({'error': 'Missing tool_name'})
                    }
                
                print(f"🔧 API Gateway invoking Data Agent tool: {tool_name} with args: {arguments}")
                
                # Invoke the tool
                result = run_async_in_thread(invoke_data_agent_tool(tool_name, arguments))
                
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps(result)
                }
            else:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({'error': 'Missing request body'})
                }
        
        # Handle direct invocation format
        else:
            tool_name = event.get('tool_name')
            arguments = event.get('arguments', {})
            
            if not tool_name:
                return {
                    'error': 'Missing tool_name in event',
                    'success': False
                }
            
            print(f"🔧 Direct invoking Data Agent tool: {tool_name} with args: {arguments}")
            
            # Invoke the tool
            result = run_async_in_thread(invoke_data_agent_tool(tool_name, arguments))
            
            return result
            
    except Exception as e:
        print(f"❌ Data Agent Invoker error: {e}")
        import traceback
        traceback.print_exc()
        
        # Return appropriate error format based on request type
        if 'method' in event and event['method'] == 'tools/call':
            return {
                "jsonrpc": "2.0",
                "id": event.get('id', 'unknown'),
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
        elif 'httpMethod' in event:
            return {
                'statusCode': 500,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': f'Internal error: {str(e)}'})
            }
        else:
            return {
                'error': f'Internal error: {str(e)}',
                'success': False
            }