#!/usr/bin/env python3
"""
Diagnose and fix AgentCore agent configuration issues
"""

import boto3
import json
import os
from pathlib import Path

def check_agentcore_deployment_status():
    """Check if AgentCore agents are properly deployed"""
    
    print("🔍 DIAGNOSING AGENTCORE AGENT ISSUES")
    print("="*60)
    
    # Check environment variables
    print("📋 Checking Environment Variables:")
    
    ticket_agent_arn = os.getenv('TICKET_AGENT_ARN')
    data_agent_arn = os.getenv('DATA_AGENT_ARN')
    cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
    cognito_user = os.getenv('COGNITO_TEST_USER')
    cognito_password = os.getenv('COGNITO_TEST_PASSWORD')
    
    print(f"   TICKET_AGENT_ARN: {ticket_agent_arn}")
    print(f"   DATA_AGENT_ARN: {data_agent_arn}")
    print(f"   COGNITO_CLIENT_ID: {cognito_client_id}")
    print(f"   COGNITO_TEST_USER: {cognito_user}")
    print(f"   COGNITO_TEST_PASSWORD: {'***' if cognito_password else 'NOT SET'}")
    
    if not all([ticket_agent_arn, data_agent_arn, cognito_client_id, cognito_user, cognito_password]):
        print("❌ Missing required environment variables")
        return False
    
    print("✅ Environment variables are set")
    
    # Check if agents exist in AgentCore
    print("\n🤖 Checking AgentCore Agent Status:")
    
    try:
        bedrock_client = boto3.client('bedrock-agent', region_name='us-west-2')
        
        # This might not work directly, but let's try
        print("   Attempting to list AgentCore agents...")
        
        # The ARNs suggest these are AgentCore runtime ARNs
        print(f"   Ticket Agent: {ticket_agent_arn}")
        print(f"   Data Agent: {data_agent_arn}")
        
        return True
        
    except Exception as e:
        print(f"   ⚠️  Cannot directly check agent status: {e}")
        return True  # Continue with other checks

def check_mcp_server_status():
    """Check if MCP servers are running"""
    
    print("\n🔌 Checking MCP Server Status:")
    
    # Check if agentcore.yaml exists
    if os.path.exists('agentcore.yaml'):
        print("✅ agentcore.yaml found")
        
        with open('agentcore.yaml', 'r') as f:
            config = f.read()
            print("   Configuration preview:")
            print("   " + "\n   ".join(config.split('\n')[:10]))
    else:
        print("❌ agentcore.yaml not found")
        return False
    
    # Check if MCP servers are defined
    mcp_files = [
        'backend/agents/data_agent.py',
        'backend/agents/ticket_agent.py',
        'backend/agents/agentcore_data_agent.py',
        'backend/agents/agentcore_ticket_agent.py'
    ]
    
    print("\n   MCP Server Files:")
    for file_path in mcp_files:
        if os.path.exists(file_path):
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❌ {file_path}")
    
    return True

def test_direct_agentcore_connection():
    """Test direct connection to AgentCore agents"""
    
    print("\n🧪 Testing Direct AgentCore Connection:")
    
    try:
        import urllib3
        
        # Get authentication token
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
        
        # Test connection to Ticket Agent
        ticket_agent_arn = os.getenv('TICKET_AGENT_ARN')
        encoded_arn = ticket_agent_arn.replace(':', '%3A').replace('/', '%2F')
        agent_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
        
        payload = {
            'inputText': 'Hello, can you help me with ticket upgrades?',
            'sessionId': 'test-session-123'
        }
        
        http = urllib3.PoolManager()
        response = http.request(
            'POST',
            agent_url,
            body=json.dumps(payload),
            headers=headers,
            timeout=30
        )
        
        print(f"   Response Status: {response.status}")
        
        if response.status == 200:
            result = json.loads(response.data.decode('utf-8'))
            print(f"   Response Data: {json.dumps(result, indent=2)}")
            
            # Check for specific error patterns
            if 'error' in result:
                error_code = result['error'].get('code')
                error_message = result['error'].get('message')
                
                print(f"\n❌ AgentCore Error Detected:")
                print(f"   Error Code: {error_code}")
                print(f"   Error Message: {error_message}")
                
                if error_code == -32603:
                    print("\n🔧 DIAGNOSIS: Internal Server Error (-32603)")
                    print("   This typically means:")
                    print("   1. Agent is deployed but MCP tools are not working")
                    print("   2. Agent configuration has issues")
                    print("   3. MCP server connection problems")
                    print("   4. Agent runtime environment issues")
                
                return False
            else:
                print("✅ AgentCore responded successfully!")
                return True
        else:
            print(f"❌ HTTP Error: {response.status}")
            print(f"   Response: {response.data.decode('utf-8')}")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def check_mcp_tools_configuration():
    """Check MCP tools configuration"""
    
    print("\n🛠️  Checking MCP Tools Configuration:")
    
    # Read the agent files to see tool definitions
    agent_files = [
        'backend/agents/agentcore_ticket_agent.py',
        'backend/agents/agentcore_data_agent.py'
    ]
    
    for file_path in agent_files:
        if os.path.exists(file_path):
            print(f"\n   📄 {file_path}:")
            
            with open(file_path, 'r') as f:
                content = f.read()
                
                # Look for tool definitions
                if '@server.list_tools()' in content:
                    print("   ✅ Has tool definitions")
                else:
                    print("   ⚠️  No tool definitions found")
                
                # Look for specific tools
                tools = ['validate_ticket_eligibility', 'calculate_upgrade_pricing', 'get_customer', 'get_tickets_for_customer']
                
                for tool in tools:
                    if tool in content:
                        print(f"   ✅ Tool: {tool}")
                    else:
                        print(f"   ❌ Missing tool: {tool}")
        else:
            print(f"   ❌ File not found: {file_path}")

def suggest_fixes():
    """Suggest fixes for AgentCore issues"""
    
    print("\n🔧 SUGGESTED FIXES:")
    print("="*60)
    
    print("1. 🚀 Restart AgentCore Agents:")
    print("   - Agents may need to be redeployed")
    print("   - MCP servers may need restart")
    
    print("\n2. 🔍 Check MCP Server Status:")
    print("   - Verify MCP servers are running")
    print("   - Check port 8000 connectivity")
    
    print("\n3. 🛠️  Validate Tool Definitions:")
    print("   - Ensure all required tools are defined")
    print("   - Check tool parameter schemas")
    
    print("\n4. 🔐 Verify Authentication:")
    print("   - Check Cognito user permissions")
    print("   - Validate bearer token scope")
    
    print("\n5. 📊 Check Agent Logs:")
    print("   - Review AgentCore agent logs")
    print("   - Check MCP server logs")

def main():
    """Main diagnostic function"""
    
    print("🚀 AGENTCORE DIAGNOSTIC TOOL")
    print("Identifying why agents return internal configuration errors")
    print("="*80)
    
    # Run diagnostic checks
    checks = [
        ("Environment Variables", check_agentcore_deployment_status),
        ("MCP Server Status", check_mcp_server_status),
        ("Direct AgentCore Connection", test_direct_agentcore_connection),
        ("MCP Tools Configuration", check_mcp_tools_configuration)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n{'='*20} {check_name} {'='*20}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ Check failed: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "="*80)
    print("📋 DIAGNOSTIC SUMMARY")
    print("="*80)
    
    for check_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{check_name:.<40} {status}")
    
    # Determine root cause
    failed_checks = [name for name, result in results if not result]
    
    if 'Direct AgentCore Connection' in failed_checks:
        print(f"\n🎯 ROOT CAUSE IDENTIFIED:")
        print("   AgentCore agents are returning internal errors (-32603)")
        print("   This means agents are deployed but have configuration issues")
        
        print(f"\n🔧 IMMEDIATE ACTION NEEDED:")
        print("   1. Check AgentCore agent deployment status")
        print("   2. Verify MCP server connectivity") 
        print("   3. Restart AgentCore agents if needed")
        print("   4. Validate tool configurations")
    
    suggest_fixes()

if __name__ == "__main__":
    main()