#!/usr/bin/env python3
"""
Test the HTTP-based AgentCore client for actual LLM responses
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.lambda.agentcore_client import create_client
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

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
    
    print("✅ Environment variables loaded")
    return True

async def test_http_client():
    """Test the HTTP-based AgentCore client"""
    
    print("🚀 TESTING HTTP-BASED AGENTCORE CLIENT")
    print("Testing actual LLM agent responses via HTTP")
    print("="*80)
    
    # Load environment
    if not load_env_file():
        print("❌ Cannot proceed without environment variables")
        return
    
    try:
        # Create client
        print("🔐 Creating AgentCore HTTP client...")
        client = create_client()
        print("✅ Client created and authenticated")
        
        # Test cases for both agents
        test_cases = [
            {
                'agent_name': 'Ticket Agent',
                'agent_arn': client.ticket_agent_arn,
                'test_message': 'Help me validate ticket 550e8400-e29b-41d4-a716-446655440002 for Premium upgrade'
            },
            {
                'agent_name': 'Data Agent', 
                'agent_arn': client.data_agent_arn,
                'test_message': 'Get customer information for customer ID cust_123'
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\n🤖 Testing {test_case['agent_name']}...")
            print(f"   ARN: {test_case['agent_arn']}")
            print(f"   Message: {test_case['test_message']}")
            
            # Call agent via HTTP
            result = await client.call_agent_http(
                test_case['agent_arn'], 
                test_case['test_message']
            )
            
            if result['success']:
                print(f"   ✅ {test_case['agent_name']} responded successfully!")
                print(f"   Response: {str(result.get('data', ''))[:200]}...")
                results.append((test_case['agent_name'], True))
            else:
                print(f"   ❌ {test_case['agent_name']} failed:")
                print(f"   Error: {result['error']}")
                if 'error_code' in result:
                    print(f"   Error Code: {result['error_code']}")
                results.append((test_case['agent_name'], False))
        
        # Test specific tool calls
        print(f"\n🔧 Testing specific tool calls...")
        
        # Test Data Agent tool
        print(f"   Testing Data Agent get_customer tool...")
        data_result = await client.get_customer("test-customer-123")
        if data_result['success']:
            print(f"   ✅ Data Agent tool call successful")
        else:
            print(f"   ❌ Data Agent tool call failed: {data_result['error']}")
        
        # Test Ticket Agent tool
        print(f"   Testing Ticket Agent validate_ticket_eligibility tool...")
        ticket_result = await client.validate_ticket_eligibility("test-ticket-456", "standard")
        if ticket_result['success']:
            print(f"   ✅ Ticket Agent tool call successful")
        else:
            print(f"   ❌ Ticket Agent tool call failed: {ticket_result['error']}")
        
        # Summary
        print("\n" + "="*80)
        print("📋 HTTP CLIENT TEST RESULTS")
        print("="*80)
        
        working_agents = sum(1 for _, success in results if success)
        total_agents = len(results)
        
        for agent_name, success in results:
            status = "✅ WORKING" if success else "❌ NEEDS FIX"
            print(f"{agent_name}:........................ {status}")
        
        if working_agents == total_agents:
            print(f"\n🎉 EXCELLENT! All AgentCore agents working via HTTP!")
            print("✅ Full LLM business functionality is available")
            print("✅ Lambda can now get actual AI responses")
            print("✅ Customer chat will use real agent intelligence")
            
        elif working_agents > 0:
            print(f"\n⚠️  PARTIAL SUCCESS: {working_agents}/{total_agents} agents working")
            print("🔧 Some agents need attention")
            
        else:
            print(f"\n❌ AGENTS STILL NEED FIXES")
            print("🔧 HTTP client created but agents have configuration issues")
            print("💡 Check AgentCore agent logs and MCP configurations")
        
        print(f"\n📊 Business Readiness: {'✅ READY' if working_agents == total_agents else '🔧 NEEDS WORK'}")
        
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_http_client())