#!/usr/bin/env python3
"""
Test AgentCore MCP servers using OAuth Bearer token authentication
Based on AWS AgentCore MCP documentation
"""

import asyncio
import os
import boto3
import json
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Load environment variables from .env file
load_dotenv()


def get_bearer_token():
    """Get Bearer token from Cognito"""
    try:
        # Load configuration from .env
        cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
        test_user = os.getenv('COGNITO_TEST_USER')
        test_password = os.getenv('COGNITO_TEST_PASSWORD')
        aws_region = os.getenv('AWS_REGION', 'us-west-2')
        
        print(f"🔍 Debug - Environment variables:")
        print(f"   COGNITO_CLIENT_ID: {cognito_client_id}")
        print(f"   COGNITO_TEST_USER: {test_user}")
        print(f"   COGNITO_TEST_PASSWORD: {'***' if test_password else None}")
        print(f"   AWS_REGION: {aws_region}")
        
        if not all([cognito_client_id, test_user, test_password]):
            print("❌ Missing Cognito configuration in .env file")
            return None
        
        print(f"🔐 Authenticating with Cognito...")
        print(f"   Client ID: {cognito_client_id}")
        print(f"   User: {test_user}")
        
        # Initialize Cognito client
        cognito_client = boto3.client('cognito-idp', region_name=aws_region)
        
        # Authenticate user
        response = cognito_client.initiate_auth(
            ClientId=cognito_client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': test_user,
                'PASSWORD': test_password
            }
        )
        
        access_token = response['AuthenticationResult']['AccessToken']
        print("✅ Successfully obtained Bearer token")
        return access_token
        
    except Exception as e:
        print(f"❌ Failed to get Bearer token: {e}")
        return None


async def test_agent_with_oauth(agent_name, agent_arn, bearer_token):
    """Test an AgentCore agent using OAuth Bearer token"""
    print(f"\n🔍 Testing {agent_name} with OAuth Bearer token...")
    
    try:
        # Encode ARN for URL
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        
        # Construct MCP URL
        mcp_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        # Create headers with Bearer token
        headers = {
            "authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        print(f"🔗 Connecting to: {mcp_url}")
        print(f"📋 Using OAuth Bearer token authentication")
        
        async with streamablehttp_client(mcp_url, headers, timeout=120, terminate_on_close=False) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                print("🤝 Initializing MCP session...")
                await session.initialize()
                print("✅ Session initialized successfully!")
                
                # List tools
                print("📋 Listing available tools...")
                tool_result = await session.list_tools()
                print(f"✅ Found {len(tool_result.tools)} tools:")
                for tool in tool_result.tools:
                    print(f"   - {tool.name}: {tool.description}")
                
                # Test a tool call if tools are available
                if tool_result.tools:
                    print(f"\n🔧 Testing tool: {tool_result.tools[0].name}")
                    
                    # Use appropriate test arguments based on agent type
                    if "data" in agent_name.lower():
                        test_args = {"customer_id": "550e8400-e29b-41d4-a716-446655440001"}
                    else:  # ticket agent
                        test_args = {
                            "ticket_id": "550e8400-e29b-41d4-a716-446655440002",
                            "upgrade_tier": "Standard"
                        }
                    
                    result = await session.call_tool(
                        tool_result.tools[0].name,
                        test_args
                    )
                    print(f"✅ Tool result: {result}")
                
                return True
                
    except Exception as e:
        print(f"❌ {agent_name} OAuth test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_both_agents_oauth():
    """Test both AgentCore agents using OAuth authentication"""
    print("🚀 Testing AgentCore MCP Agents with OAuth Authentication")
    print("=" * 70)
    
    # Get Bearer token
    bearer_token = get_bearer_token()
    if not bearer_token:
        print("❌ Cannot proceed without Bearer token")
        return
    
    # Agent ARNs (updated after MCP deployment)
    data_agent_arn = "arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_data_agent-mNwb8TETc3"
    ticket_agent_arn = "arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR"
    
    print("\n" + "=" * 70)
    
    # Test Data Agent
    data_success = await test_agent_with_oauth("Data Agent", data_agent_arn, bearer_token)
    
    print("\n" + "=" * 70)
    
    # Test Ticket Agent
    ticket_success = await test_agent_with_oauth("Ticket Agent", ticket_agent_arn, bearer_token)
    
    print("\n" + "=" * 70)
    print("📊 OAuth Test Results Summary:")
    print(f"   Data Agent: {'✅ PASS' if data_success else '❌ FAIL'}")
    print(f"   Ticket Agent: {'✅ PASS' if ticket_success else '❌ FAIL'}")
    
    if data_success and ticket_success:
        print("\n🎉 Both AgentCore agents working with OAuth MCP protocol!")
        print("✅ Ready for production use!")
    else:
        print("\n⚠️ Some agents failed OAuth MCP tests")
        print("🔧 Check agent runtime status and logs")


def check_agent_status():
    """Check current agent status"""
    print("📊 Checking Agent Runtime Status...")
    
    try:
        client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
        
        # Check Data Agent (new ID)
        try:
            data_response = client.get_agent_runtime(agentRuntimeId='agentcore_data_agent-mNwb8TETc3')
            print(f"📈 Data Agent Status: {data_response['status']}")
        except Exception as e:
            print(f"❌ Data Agent status check failed: {e}")
        
        # Check Ticket Agent (new ID)
        try:
            ticket_response = client.get_agent_runtime(agentRuntimeId='agentcore_ticket_agent-zvZNPj28RR')
            print(f"🎫 Ticket Agent Status: {ticket_response['status']}")
        except Exception as e:
            print(f"❌ Ticket Agent status check failed: {e}")
        
    except Exception as e:
        print(f"❌ Status check failed: {e}")


async def main():
    """Main test function"""
    # Check agent status first
    check_agent_status()
    
    print("\n" + "=" * 70)
    
    # Run OAuth tests
    await test_both_agents_oauth()


if __name__ == "__main__":
    asyncio.run(main())