#!/usr/bin/env python3
"""
Test AgentCore agents with proper environment variables loaded
"""

import os
import sys
import json
import urllib3
import boto3
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    print("📋 Loading environment variables from .env file...")
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
    
    # Verify key variables are loaded
    required_vars = [
        'TICKET_AGENT_ARN',
        'DATA_AGENT_ARN', 
        'COGNITO_CLIENT_ID',
        'COGNITO_TEST_USER',
        'COGNITO_TEST_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
        else:
            print(f"   ✅ {var}: {os.getenv(var)}")
    
    if missing_vars:
        print(f"❌ Missing variables: {missing_vars}")
        return False
    
    print("✅ All required environment variables loaded")
    return True

def test_agentcore_authentication():
    """Test AgentCore authentication"""
    
    print("\n🔐 Testing AgentCore Authentication...")
    
    try:
        cognito_client = boto3.client('cognito-idp', region_name='us-west-2')
        
        response = cognito_client.initiate_auth(
            ClientId=os.getenv('COGNITO_CLIENT_ID'),
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': os.getenv('COGNITO_TEST_USER'),
                'PASSWORD': os.getenv('COGNITO_TEST_PASSWORD')
            }
        )
        
        bearer_token = response['AuthenticationResult']['AccessToken']
        print("✅ Successfully obtained bearer token")
        return bearer_token
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return None

def test_agentcore_agent_direct(agent_arn, agent_name, bearer_token, test_message):
    """Test direct connection to an AgentCore agent"""
    
    print(f"\n🤖 Testing {agent_name} Agent...")
    print(f"   ARN: {agent_arn}")
    print(f"   Test Message: {test_message}")
    
    try:
        # Encode ARN for URL
        encoded_arn = agent_arn.replace(':', '%3A').replace('/', '%2F')
        agent_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
        
        payload = {
            'inputText': test_message,
            'sessionId': f'test-session-{hash(agent_arn)}'[:16]
        }
        
        http = urllib3.PoolManager()
        response = http.request(
            'POST',
            agent_url,
            body=json.dumps(payload),
            headers=headers,
            timeout=30
        )
        
        print(f"   HTTP Status: {response.status}")
        
        if response.status == 200:
            response_text = response.data.decode('utf-8')
            
            # Handle Server-Sent Events (SSE) format
            if response_text.startswith('event:'):
                # Parse SSE format: extract JSON from data: lines
                lines = response_text.strip().split('\n')
                result = None
                
                for line in lines:
                    if line.startswith('data: '):
                        json_str = line[6:]  # Remove 'data: ' prefix
                        try:
                            result = json.loads(json_str)
                            break
                        except json.JSONDecodeError:
                            continue
                
                if not result:
                    print(f"   ❌ Could not parse SSE response")
                    return False
            else:
                # Handle regular JSON response
                result = json.loads(response_text)
            
            print(f"   Response Structure: {list(result.keys())}")
            
            # Check for errors
            if 'error' in result:
                error = result['error']
                print(f"   ❌ Agent Error:")
                print(f"      Code: {error.get('code')}")
                print(f"      Message: {error.get('message')}")
                
                # Analyze error type
                if error.get('code') == -32603:
                    print(f"   🔍 Analysis: Internal server error - agent configuration issue")
                elif error.get('code') == -32601:
                    print(f"   🔍 Analysis: Method not found - missing tool definitions")
                elif error.get('code') == -32602:
                    print(f"   🔍 Analysis: Invalid parameters - tool parameter mismatch")
                
                return False
            
            # Check for successful response
            elif 'result' in result or 'output' in result:
                print(f"   ✅ Agent responded successfully!")
                
                # Print response content
                if 'result' in result:
                    print(f"   Response: {result['result']}")
                elif 'output' in result:
                    print(f"   Output: {result['output']}")
                
                return True
            
            else:
                print(f"   ⚠️  Unexpected response format: {json.dumps(result, indent=2)}")
                return False
        
        else:
            print(f"   ❌ HTTP Error: {response.status}")
            print(f"   Response: {response.data.decode('utf-8')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False

def test_mcp_server_locally():
    """Test if MCP servers can be started locally"""
    
    print("\n🔌 Testing Local MCP Server Startup...")
    
    # Check if we can import MCP libraries
    try:
        from mcp import server
        print("✅ MCP libraries available")
    except ImportError as e:
        print(f"❌ MCP libraries not available: {e}")
        return False
    
    # Check agent files
    agent_files = [
        'backend/agents/agentcore_ticket_agent.py',
        'backend/agents/agentcore_data_agent.py'
    ]
    
    for agent_file in agent_files:
        if os.path.exists(agent_file):
            print(f"✅ Agent file exists: {agent_file}")
            
            # Try to import the agent
            try:
                # Add the directory to Python path
                sys.path.insert(0, 'backend/agents')
                
                if 'ticket_agent' in agent_file:
                    import agentcore_ticket_agent
                    print("   ✅ Ticket agent imports successfully")
                elif 'data_agent' in agent_file:
                    import agentcore_data_agent  
                    print("   ✅ Data agent imports successfully")
                    
            except Exception as e:
                print(f"   ❌ Import failed: {e}")
                
        else:
            print(f"❌ Agent file missing: {agent_file}")
    
    return True

def suggest_agentcore_fixes():
    """Suggest specific fixes for AgentCore issues"""
    
    print("\n🔧 AGENTCORE TROUBLESHOOTING GUIDE")
    print("="*60)
    
    print("🎯 MOST LIKELY ISSUES:")
    print("1. AgentCore agents are deployed but MCP servers are not running")
    print("2. MCP tool definitions have errors")
    print("3. Agent runtime environment issues")
    print("4. Database connectivity problems from agents")
    
    print("\n🚀 IMMEDIATE FIXES TO TRY:")
    
    print("\n1. Restart AgentCore Development Environment:")
    print("   cd backend/agents")
    print("   python run_data_agent.py")
    print("   # In another terminal:")
    print("   python agentcore_ticket_agent.py")
    
    print("\n2. Check AgentCore Agent Status:")
    print("   python setup_agentcore_dev.py")
    
    print("\n3. Test MCP Servers Directly:")
    print("   python test_data_agent.py")
    print("   python test_ticket_agent.py")
    
    print("\n4. Redeploy Agents if Needed:")
    print("   # Follow AgentCore deployment guide")
    print("   # Ensure MCP servers are properly configured")
    
    print("\n🔍 DEBUGGING STEPS:")
    print("1. Check AgentCore agent logs in AWS Console")
    print("2. Verify MCP server port 8000 is accessible")
    print("3. Test database connectivity from agent environment")
    print("4. Validate tool parameter schemas")

def main():
    """Main testing function"""
    
    print("🚀 AGENTCORE AGENT TESTING WITH PROPER ENVIRONMENT")
    print("Testing actual LLM agents for full business functionality")
    print("="*80)
    
    # Step 1: Load environment
    if not load_env_file():
        print("❌ Cannot proceed without environment variables")
        return
    
    # Step 2: Test authentication
    bearer_token = test_agentcore_authentication()
    if not bearer_token:
        print("❌ Cannot proceed without authentication")
        return
    
    # Step 3: Test both agents
    test_cases = [
        {
            'agent_arn': os.getenv('TICKET_AGENT_ARN'),
            'agent_name': 'Ticket',
            'test_message': 'Help me validate ticket 550e8400-e29b-41d4-a716-446655440002 for Premium upgrade'
        },
        {
            'agent_arn': os.getenv('DATA_AGENT_ARN'),
            'agent_name': 'Data',
            'test_message': 'Get customer information for customer ID cust_123'
        }
    ]
    
    agent_results = []
    
    for test_case in test_cases:
        result = test_agentcore_agent_direct(
            test_case['agent_arn'],
            test_case['agent_name'],
            bearer_token,
            test_case['test_message']
        )
        agent_results.append((test_case['agent_name'], result))
    
    # Step 4: Test local MCP servers
    mcp_result = test_mcp_server_locally()
    
    # Summary
    print("\n" + "="*80)
    print("📋 AGENTCORE TESTING RESULTS")
    print("="*80)
    
    for agent_name, result in agent_results:
        status = "✅ WORKING" if result else "❌ NEEDS FIX"
        print(f"{agent_name} Agent:........................ {status}")
    
    mcp_status = "✅ AVAILABLE" if mcp_result else "❌ ISSUES"
    print(f"Local MCP Servers:.................. {mcp_status}")
    
    # Determine overall status
    working_agents = sum(1 for _, result in agent_results if result)
    total_agents = len(agent_results)
    
    if working_agents == total_agents:
        print(f"\n🎉 EXCELLENT! All AgentCore agents are working!")
        print("✅ Full LLM business functionality is available")
        print("✅ Customers can get real AI responses")
        print("✅ Ticket operations will use actual agent intelligence")
        
    elif working_agents > 0:
        print(f"\n⚠️  PARTIAL SUCCESS: {working_agents}/{total_agents} agents working")
        print("🔧 Some agents need attention for full functionality")
        
    else:
        print(f"\n❌ AGENTS NEED ATTENTION")
        print("🔧 AgentCore agents are not responding properly")
        print("💡 This explains the internal configuration errors")
        
        suggest_agentcore_fixes()
    
    print(f"\n📊 Business Readiness: {'✅ READY' if working_agents == total_agents else '🔧 NEEDS WORK'}")

if __name__ == "__main__":
    main()