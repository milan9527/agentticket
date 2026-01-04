#!/usr/bin/env python3
"""
MCP Ticket Agent Lambda Handler

This handler runs the Ticket Agent MCP server in AWS Lambda using the 
run-mcp-servers-with-aws-lambda adapter.
"""

import sys
import os
from mcp.client.stdio import StdioServerParameters
from run_mcp_servers_with_aws_lambda import APIGatewayProxyEventHandler, StdioServerAdapterRequestHandler

# Configure the MCP server parameters to run our ticket agent
server_params = StdioServerParameters(
    command=sys.executable,
    args=[
        "-m", "ticket_agent",  # This will run our ticket_agent.py as a module
    ],
    env={
        **os.environ,
        'AWS_REGION': 'us-west-2',
        'DB_CLUSTER_ARN': os.getenv('DB_CLUSTER_ARN'),
        'DB_SECRET_ARN': os.getenv('DB_SECRET_ARN'),
        'DATABASE_NAME': os.getenv('DATABASE_NAME'),
        'BEDROCK_MODEL_ID': os.getenv('BEDROCK_MODEL_ID'),
    }
)

# Create the request handler and event handler
request_handler = StdioServerAdapterRequestHandler(server_params)
event_handler = APIGatewayProxyEventHandler(request_handler)


def lambda_handler(event, context):
    """Lambda handler function"""
    return event_handler.handle(event, context)