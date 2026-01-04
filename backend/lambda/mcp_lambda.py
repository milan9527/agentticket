#!/usr/bin/env python3
"""
MCP Lambda Adapter

This module provides the necessary components to run MCP servers in AWS Lambda
based on the AWS Labs implementation pattern.
"""

import json
import subprocess
import asyncio
import sys
import os
from typing import Dict, Any, Optional
from mcp.client.stdio import StdioServerParameters
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client


class StdioServerAdapterRequestHandler:
    """Handles requests to MCP servers via stdio"""
    
    def __init__(self, server_params: StdioServerParameters):
        self.server_params = server_params
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request via stdio"""
        try:
            # Start the MCP server process
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Extract tool call information
                    tool_name = request.get('tool')
                    arguments = request.get('arguments', {})
                    
                    if not tool_name:
                        return {'error': 'Missing tool name'}
                    
                    # List available tools
                    tools_result = await session.list_tools()
                    
                    # Find the requested tool
                    tool = None
                    for t in tools_result.tools:
                        if t.name == tool_name:
                            tool = t
                            break
                    
                    if not tool:
                        return {'error': f'Tool {tool_name} not found'}
                    
                    # Call the tool
                    result = await session.call_tool(tool_name, arguments)
                    
                    # Return the result
                    if result.isError:
                        return {'error': result.content[0].text if result.content else 'Tool execution failed'}
                    else:
                        return {'success': True, 'result': result.content[0].text if result.content else 'Success'}
                        
        except Exception as e:
            return {'error': str(e)}


class APIGatewayProxyEventHandler:
    """Handles API Gateway proxy events for MCP servers"""
    
    def __init__(self, request_handler: StdioServerAdapterRequestHandler):
        self.request_handler = request_handler
    
    def handle(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Handle API Gateway proxy event"""
        
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
            
            # Parse request body
            if 'body' not in event or not event['body']:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Missing request body'})
                }
            
            try:
                request_data = json.loads(event['body'])
            except json.JSONDecodeError:
                return {
                    'statusCode': 400,
                    'headers': headers,
                    'body': json.dumps({'error': 'Invalid JSON in request body'})
                }
            
            # Handle the MCP request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self.request_handler.handle_request(request_data))
                
                return {
                    'statusCode': 200,
                    'headers': headers,
                    'body': json.dumps(result)
                }
            finally:
                loop.close()
                
        except Exception as e:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': f'Internal server error: {str(e)}'})
            }