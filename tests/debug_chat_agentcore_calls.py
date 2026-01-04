#!/usr/bin/env python3
"""
Debug Chat AgentCore Calls

This script specifically tests why the chat functionality is falling back to 
pattern matching instead of using the real AgentCore LLM.
"""

import boto3
import json
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend/lambda directory to the path so we can import the client
sys.path.insert(0, 'backend/lambda')

from agentcore_client import create_client

async def test_chat_agentcore_call():
    """Test the exact AgentCore call that the chat functionality makes"""
    print("🔍 DEBUGGING CHAT AGENTCORE CALLS")
    print("=" * 60)
    
    try:
        # Create the same client that the Lambda function uses
        print("🔧 Creating AgentCore client...")
        client = create_client()
        print(f"✅ Client created successfully")
        print(f"   Ticket Agent ARN: {client.ticket_agent_arn}")
        print(f"   Bearer Token: {client.bearer_token[:50] if client.bearer_token else 'None'}...")
        
        # Test the exact call that the chat functionality makes
        test_message = "Hello! I have a ticket and I'm interested in upgrading it."
        context_summary = " Customer ticket ID: 550e8400-e29b-41d4-a716-446655440002 Customer has provided ticket information."
        
        full_prompt = f"Customer message: {test_message}\n{context_summary}\n\nPlease provide a helpful response about ticket upgrades."
        
        print(f"\n🎯 Testing AgentCore HTTP call...")
        print(f"   Message: {test_message}")
        print(f"   Full Prompt: {full_prompt[:100]}...")
        
        # Make the exact same call as the chat handler
        result = await client.call_agent_http(
            client.ticket_agent_arn,
            full_prompt
        )
        
        print(f"\n📋 AgentCore Response:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            data = result.get('data')
            print(f"   Data Type: {type(data)}")
            print(f"   Data Length: {len(str(data))} characters")
            print(f"   Data Preview: {str(data)[:200]}...")
            
            # Check if this would trigger the fallback
            if data and len(str(data)) > 50:
                print(f"✅ AgentCore call successful - should NOT use fallback")
                return True
            else:
                print(f"⚠️ AgentCore response too short - would trigger fallback")
                return False
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ AgentCore call failed: {error}")
            print(f"   Error Code: {result.get('error_code', 'N/A')}")
            print(f"   Raw Response: {result.get('raw_response', 'N/A')}")
            return False
            
    except Exception as e:
        print(f"❌ Error during AgentCore call test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_multiple_chat_scenarios():
    """Test multiple chat scenarios to see which ones work"""
    print("\n" + "=" * 60)
    print("🧪 TESTING MULTIPLE CHAT SCENARIOS")
    print("=" * 60)
    
    scenarios = [
        "Hello! I have a ticket and I'm interested in upgrading it.",
        "My ticket ID is 550e8400-e29b-41d4-a716-446655440002. Can you tell me about upgrade options?",
        "How much would it cost to upgrade to VIP?",
        "What are the benefits of upgrading my ticket?",
        "I want to upgrade my ticket to premium"
    ]
    
    try:
        client = create_client()
        results = []
        
        for i, message in enumerate(scenarios, 1):
            print(f"\n🎯 Scenario {i}: {message[:50]}...")
            
            # Build the same prompt as the chat handler
            context_summary = " Customer ticket ID: 550e8400-e29b-41d4-a716-446655440002 Customer has provided ticket information."
            full_prompt = f"Customer message: {message}\n{context_summary}\n\nPlease provide a helpful response about ticket upgrades."
            
            result = await client.call_agent_http(
                client.ticket_agent_arn,
                full_prompt
            )
            
            success = result.get('success', False)
            data_length = len(str(result.get('data', ''))) if success else 0
            
            print(f"   Success: {success}")
            print(f"   Response Length: {data_length} characters")
            
            if success and data_length > 100:
                print(f"   ✅ Would use AgentCore response")
            else:
                print(f"   ❌ Would use fallback response")
                if not success:
                    print(f"   Error: {result.get('error', 'Unknown')}")
            
            results.append({
                'scenario': message,
                'success': success,
                'length': data_length,
                'would_use_agentcore': success and data_length > 100
            })
        
        # Summary
        successful_scenarios = sum(1 for r in results if r['would_use_agentcore'])
        print(f"\n📊 SUMMARY:")
        print(f"   Total Scenarios: {len(scenarios)}")
        print(f"   Successful AgentCore Calls: {successful_scenarios}")
        print(f"   Fallback Usage: {len(scenarios) - successful_scenarios}")
        
        if successful_scenarios == 0:
            print(f"\n❌ ALL SCENARIOS USING FALLBACK - AgentCore chat calls are failing")
        elif successful_scenarios < len(scenarios):
            print(f"\n⚠️ PARTIAL SUCCESS - Some scenarios using fallback")
        else:
            print(f"\n✅ ALL SCENARIOS USING AGENTCORE - Chat should work with real LLM")
        
        return results
        
    except Exception as e:
        print(f"❌ Error during scenario testing: {e}")
        return []

async def compare_mcp_vs_chat_calls():
    """Compare MCP tool calls (which work) vs chat calls (which don't)"""
    print("\n" + "=" * 60)
    print("🔬 COMPARING MCP TOOL CALLS VS CHAT CALLS")
    print("=" * 60)
    
    try:
        client = create_client()
        
        # Test MCP tool call (we know this works)
        print("🔧 Testing MCP Tool Call (validate_ticket_eligibility)...")
        mcp_result = await client.validate_ticket_eligibility(
            "550e8400-e29b-41d4-a716-446655440002", 
            "standard"
        )
        
        print(f"   MCP Success: {mcp_result.get('success')}")
        print(f"   MCP Data Length: {len(str(mcp_result.get('data', '')))} characters")
        
        # Test chat call (this is failing)
        print("\n🔧 Testing Chat Call (call_agent_http)...")
        chat_result = await client.call_agent_http(
            client.ticket_agent_arn,
            "Customer message: Hello! I have a ticket and I'm interested in upgrading it.\n Customer ticket ID: 550e8400-e29b-41d4-a716-446655440002\n\nPlease provide a helpful response about ticket upgrades."
        )
        
        print(f"   Chat Success: {chat_result.get('success')}")
        print(f"   Chat Data Length: {len(str(chat_result.get('data', '')))} characters")
        
        # Compare the results
        print(f"\n📊 COMPARISON:")
        if mcp_result.get('success') and not chat_result.get('success'):
            print(f"   ✅ MCP calls work, ❌ Chat calls fail")
            print(f"   Issue: Chat HTTP calls to AgentCore are failing")
            print(f"   Chat Error: {chat_result.get('error', 'Unknown')}")
        elif mcp_result.get('success') and chat_result.get('success'):
            print(f"   ✅ Both MCP and Chat calls work")
            print(f"   Issue: May be in the Lambda function logic")
        else:
            print(f"   ❌ Both MCP and Chat calls have issues")
        
        return {
            'mcp_works': mcp_result.get('success', False),
            'chat_works': chat_result.get('success', False),
            'mcp_data_length': len(str(mcp_result.get('data', ''))),
            'chat_data_length': len(str(chat_result.get('data', ''))),
            'chat_error': chat_result.get('error') if not chat_result.get('success') else None
        }
        
    except Exception as e:
        print(f"❌ Error during comparison: {e}")
        return {}

async def main():
    """Main debugging function"""
    print("🚀 CHAT AGENTCORE DEBUGGING")
    print("Investigating why chat uses fallback instead of real LLM")
    print("=" * 80)
    
    # Test 1: Basic AgentCore chat call
    basic_test = await test_chat_agentcore_call()
    
    # Test 2: Multiple scenarios
    scenario_results = await test_multiple_chat_scenarios()
    
    # Test 3: Compare MCP vs Chat
    comparison = await compare_mcp_vs_chat_calls()
    
    # Final analysis
    print("\n" + "=" * 80)
    print("🎯 FINAL ANALYSIS")
    print("=" * 80)
    
    if comparison.get('mcp_works') and not comparison.get('chat_works'):
        print("🔍 ROOT CAUSE IDENTIFIED:")
        print("   ✅ MCP tool calls work (using real LLM)")
        print("   ❌ Chat HTTP calls fail")
        print("   🔧 SOLUTION: Fix chat HTTP call implementation")
        print(f"   📋 Chat Error: {comparison.get('chat_error', 'Unknown')}")
        
        print("\n💡 LIKELY ISSUES:")
        print("   1. Different request format between MCP and chat calls")
        print("   2. AgentCore agent not configured for conversational HTTP calls")
        print("   3. Different authentication or headers needed")
        print("   4. Session ID or payload format issues")
        
    elif not basic_test:
        print("🔍 ISSUE CONFIRMED:")
        print("   ❌ AgentCore chat calls are failing")
        print("   ✅ System correctly falls back to pattern matching")
        print("   🔧 SOLUTION: Fix AgentCore chat call implementation")
    else:
        print("🤔 UNEXPECTED RESULT:")
        print("   ✅ AgentCore chat calls appear to work in testing")
        print("   ❌ But Lambda function still uses fallback")
        print("   🔧 SOLUTION: Check Lambda function error handling logic")

if __name__ == "__main__":
    asyncio.run(main())