import sys
import os
import asyncio
from pathlib import Path

# Load environment
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Add path and import
sys.path.append('backend/lambda')

async def test():
    print("🚀 Testing HTTP AgentCore Client")
    
    try:
        from agentcore_client_fixed import AgentCoreClient
        
        client = AgentCoreClient()
        
        if client.get_bearer_token():
            print("✅ Authentication successful")
            
            # Test direct HTTP call to Ticket Agent
            print("\n🎫 Testing Ticket Agent...")
            result = await client.call_agent_http(
                client.ticket_agent_arn,
                "Help me validate ticket 550e8400-e29b-41d4-a716-446655440002 for Premium upgrade"
            )
            
            if result['success']:
                print("✅ Ticket Agent HTTP call successful!")
                print(f"Response: {str(result.get('data', ''))[:200]}...")
            else:
                print(f"❌ Ticket Agent failed: {result['error']}")
                if 'error_code' in result:
                    print(f"Error Code: {result['error_code']}")
            
            # Test direct HTTP call to Data Agent
            print("\n📊 Testing Data Agent...")
            result2 = await client.call_agent_http(
                client.data_agent_arn,
                "Get customer information for customer ID cust_123"
            )
            
            if result2['success']:
                print("✅ Data Agent HTTP call successful!")
                print(f"Response: {str(result2.get('data', ''))[:200]}...")
            else:
                print(f"❌ Data Agent failed: {result2['error']}")
                if 'error_code' in result2:
                    print(f"Error Code: {result2['error_code']}")
            
            # Summary
            working_agents = sum([result['success'], result2['success']])
            print(f"\n📊 Results: {working_agents}/2 agents working via HTTP")
            
            if working_agents == 2:
                print("🎉 EXCELLENT! Both AgentCore agents working via HTTP!")
                print("✅ Lambda can now get actual LLM responses")
                print("✅ Full business functionality available")
            elif working_agents == 1:
                print("⚠️  PARTIAL SUCCESS: One agent working")
            else:
                print("❌ Both agents need fixes")
                
        else:
            print("❌ Authentication failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())