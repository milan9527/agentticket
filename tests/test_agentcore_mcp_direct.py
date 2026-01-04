#!/usr/bin/env python3
"""
Test AgentCore MCP directly with proper format
"""

import boto3
import json
import urllib3

def test_agentcore_mcp_direct():
    """Test AgentCore with proper MCP tool call format"""
    print("🔧 Testing AgentCore MCP Direct")
    print("=" * 50)
    
    try:
        # Get Cognito token
        cognito_client = boto3.client('cognito-idp', region_name='us-west-2')
        
        response = cognito_client.initiate_auth(
            ClientId='11m43vg72idbvlf5pc5d6qhsc4',
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': 'testuser@example.com',
                'PASSWORD': 'TempPass123!'
            }
        )
        
        access_token = response['AuthenticationResult']['AccessToken']
        print(f"✅ Got Cognito token: {access_token[:50]}...")
        
        # Test direct MCP call to Ticket Agent
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        http = urllib3.PoolManager(cert_reqs='CERT_NONE', ca_certs=None)
        
        ticket_agent_arn = 'arn:aws:bedrock-agentcore:us-west-2:632930644527:runtime/agentcore_ticket_agent-zvZNPj28RR'
        encoded_arn = ticket_agent_arn.replace(':', '%3A').replace('/', '%2F')
        agent_url = f"https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{encoded_arn}/invocations?qualifier=DEFAULT"
        
        # Proper MCP tool call format
        mcp_request = {
            "jsonrpc": "2.0",
            "id": "test-tool-call-123",
            "method": "tools/call",
            "params": {
                "name": "validate_ticket_eligibility",
                "arguments": {
                    "ticket_id": "550e8400-e29b-41d4-a716-446655440002",
                    "upgrade_tier": "standard"
                }
            }
        }
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/event-stream'
        }
        
        print(f"\n🔧 Making MCP tool call to Ticket Agent...")
        print(f"   Tool: validate_ticket_eligibility")
        print(f"   Args: ticket_id=550e8400-e29b-41d4-a716-446655440002, upgrade_tier=standard")
        
        response = http.request(
            'POST',
            agent_url,
            body=json.dumps(mcp_request),
            headers=headers,
            timeout=30
        )
        
        print(f"📋 Response Status: {response.status}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.status == 200:
            response_text = response.data.decode('utf-8')
            print(f"📋 Raw Response: {response_text[:500]}...")
            
            if response_text.strip():
                try:
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
                            print(f"❌ Could not parse SSE response")
                            print(f"   Raw response: {response_text}")
                            return False
                    else:
                        # Handle regular JSON response
                        result = json.loads(response_text)
                    
                    print(f"✅ Valid response received (SSE format handled)")
                    
                    if 'error' in result:
                        error = result['error']
                        print(f"❌ MCP Error: {error.get('code')} - {error.get('message')}")
                        return False
                    elif 'result' in result:
                        print(f"✅ MCP Tool call successful!")
                        print(f"   Result type: {type(result['result'])}")
                        return True
                    else:
                        print(f"⚠️ Unexpected response format: {result}")
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    print(f"   Raw response: {response_text}")
                    return False
            else:
                print(f"❌ Empty response from AgentCore")
                return False
                
        elif response.status == 406:
            print(f"❌ 406 Not Acceptable - MCP headers still wrong")
            return False
        else:
            print(f"❌ HTTP Error: {response.status}")
            print(f"   Response: {response.data.decode('utf-8')}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing AgentCore MCP: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agentcore_mcp_direct()
    
    print(f"\n🎯 AGENTCORE MCP TEST RESULTS:")
    print(f"{'✅' if success else '❌'} Direct MCP Call: {'SUCCESS' if success else 'FAILED'}")
    
    if not success:
        print(f"\n🔧 POSSIBLE ISSUES:")
        print(f"   1. AgentCore agent deployment problems")
        print(f"   2. MCP tool not properly registered")
        print(f"   3. Agent runtime configuration errors")
        print(f"   4. Database connectivity issues from AgentCore")