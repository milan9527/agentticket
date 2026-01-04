#!/usr/bin/env python3
"""
Test Lambda function directly to debug the 502 errors
"""

import sys
import os
sys.path.append('backend/lambda')

from agentcore_http_client import create_client

def test_client():
    """Test the AgentCore HTTP client directly"""
    print("🧪 Testing AgentCore HTTP Client Directly")
    print("=" * 50)
    
    try:
        # Create client
        client = create_client()
        print(f"✅ Client created successfully")
        print(f"🎫 Ticket Agent ARN: {client.ticket_agent_arn}")
        print(f"🔑 Bearer Token: {'✅ Available' if client.bearer_token else '❌ Missing'}")
        
        # Test a simple call
        print("\n🔧 Testing ticket validation...")
        result = client.validate_ticket_eligibility("550e8400-e29b-41d4-a716-446655440002", "standard")
        
        print(f"📋 Result: {result}")
        
        if result.get('success'):
            print("✅ AgentCore HTTP client working!")
            return True
        else:
            print(f"❌ AgentCore HTTP client failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing client: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_client()