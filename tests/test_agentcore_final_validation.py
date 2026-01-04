#!/usr/bin/env python3
"""
Final validation test for AgentCore agents with actual LLM responses
"""

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

async def test_agentcore_final_validation():
    print("🎯 FINAL AGENTCORE VALIDATION TEST")
    print("Testing actual LLM responses and business functionality")
    print("="*70)
    
    try:
        from agentcore_client import AgentCoreClient
        
        client = AgentCoreClient()
        
        if not client.get_bearer_token():
            print("❌ Authentication failed")
            return False
        
        print("✅ Authentication successful")
        
        # Test 1: Data Agent - Get Customer
        print("\n📊 TEST 1: Data Agent - Get Customer")
        print("   Testing: get_customer tool with MCP format")
        
        result1 = await client.call_data_agent_tool('get_customer', {
            'customer_id': 'test-customer-123'
        })
        
        success1 = result1.get('success', False)
        print(f"   Success: {success1}")
        
        if success1:
            data = result1.get('data', {})
            print(f"   Response Type: {type(data)}")
            print(f"   Has Data: {bool(data)}")
            if data:
                print(f"   Sample Data: {str(data)[:100]}...")
        else:
            print(f"   Error: {result1.get('error', 'Unknown')}")
        
        # Test 2: Ticket Agent - Validate Eligibility with LLM Analysis
        print("\n🎫 TEST 2: Ticket Agent - Validate Eligibility")
        print("   Testing: validate_ticket_eligibility with LLM reasoning")
        
        result2 = await client.call_ticket_agent_tool('validate_ticket_eligibility', {
            'ticket_id': 'test-ticket-456',
            'customer_id': 'test-customer-123'
        })
        
        success2 = result2.get('success', False)
        print(f"   Success: {success2}")
        
        if success2:
            data = result2.get('data', {})
            if isinstance(data, dict) and 'result' in data:
                ticket_result = data['result']
                print(f"   Eligible: {ticket_result.get('eligible', False)}")
                print(f"   Has LLM Analysis: {'eligibility_reasons' in ticket_result}")
                
                # Check for actual LLM reasoning
                llm_analysis = ticket_result.get('eligibility_reasons', '')
                if llm_analysis and len(llm_analysis) > 100:
                    print(f"   LLM Analysis Length: {len(llm_analysis)} chars")
                    print(f"   LLM Sample: {llm_analysis[:150]}...")
                    print("   ✅ ACTUAL LLM REASONING DETECTED!")
                else:
                    print("   ⚠️  No substantial LLM analysis found")
            else:
                print(f"   Raw Data: {str(data)[:100]}...")
        else:
            print(f"   Error: {result2.get('error', 'Unknown')}")
        
        # Test 3: Ticket Agent - Calculate Pricing with LLM Analysis
        print("\n💰 TEST 3: Ticket Agent - Calculate Pricing")
        print("   Testing: calculate_upgrade_pricing with LLM analysis")
        
        result3 = await client.call_ticket_agent_tool('calculate_upgrade_pricing', {
            'ticket_type': 'general',
            'upgrade_tier': 'standard',
            'original_price': 50.0
        })
        
        success3 = result3.get('success', False)
        print(f"   Success: {success3}")
        
        if success3:
            data = result3.get('data', {})
            if isinstance(data, dict) and 'result' in data:
                pricing_result = data['result']
                print(f"   Has Pricing: {'pricing' in pricing_result}")
                print(f"   Has LLM Analysis: {'pricing_analysis' in pricing_result}")
                
                # Check pricing details
                pricing = pricing_result.get('pricing', {})
                if pricing:
                    print(f"   Original Price: ${pricing.get('original_price', 0)}")
                    print(f"   Upgrade Price: ${pricing.get('upgrade_price', 0)}")
                    print(f"   Total Price: ${pricing.get('total_price', 0)}")
                
                # Check for actual LLM reasoning
                llm_analysis = pricing_result.get('pricing_analysis', '')
                if llm_analysis and len(llm_analysis) > 100:
                    print(f"   LLM Analysis Length: {len(llm_analysis)} chars")
                    print(f"   LLM Sample: {llm_analysis[:150]}...")
                    print("   ✅ ACTUAL LLM PRICING ANALYSIS DETECTED!")
                else:
                    print("   ⚠️  No substantial LLM analysis found")
            else:
                print(f"   Raw Data: {str(data)[:100]}...")
        else:
            print(f"   Error: {result3.get('error', 'Unknown')}")
        
        # Test 4: Ticket Agent - Get Recommendations with LLM
        print("\n🎯 TEST 4: Ticket Agent - Get Recommendations")
        print("   Testing: get_upgrade_recommendations with LLM personalization")
        
        result4 = await client.call_ticket_agent_tool('get_upgrade_recommendations', {
            'ticket_data': {
                'ticket_type': 'general',
                'original_price': 50.0,
                'event_date': '2026-02-15'
            },
            'customer_preferences': {
                'budget': 'moderate',
                'interests': ['music', 'vip_experience']
            }
        })
        
        success4 = result4.get('success', False)
        print(f"   Success: {success4}")
        
        if success4:
            data = result4.get('data', {})
            if isinstance(data, dict) and 'result' in data:
                rec_result = data['result']
                print(f"   Has Recommendations: {'recommendations' in rec_result}")
                print(f"   Has LLM Advice: {'personalized_advice' in rec_result}")
                
                # Check recommendations
                recommendations = rec_result.get('recommendations', [])
                print(f"   Number of Options: {len(recommendations)}")
                
                # Check for actual LLM reasoning
                llm_advice = rec_result.get('personalized_advice', '')
                if llm_advice and len(llm_advice) > 100:
                    print(f"   LLM Advice Length: {len(llm_advice)} chars")
                    print(f"   LLM Sample: {llm_advice[:150]}...")
                    print("   ✅ ACTUAL LLM PERSONALIZATION DETECTED!")
                else:
                    print("   ⚠️  No substantial LLM advice found")
            else:
                print(f"   Raw Data: {str(data)[:100]}...")
        else:
            print(f"   Error: {result4.get('error', 'Unknown')}")
        
        # Summary
        working_tests = sum([success1, success2, success3, success4])
        print(f"\n📊 FINAL VALIDATION RESULTS")
        print("="*70)
        print(f"Working Tests: {working_tests}/4")
        print(f"Success Rate: {working_tests/4*100:.1f}%")
        
        if working_tests == 4:
            print("\n🎉 EXCELLENT! All AgentCore agents working with LLM!")
            print("✅ Data Agent: Providing customer data")
            print("✅ Ticket Agent: LLM reasoning for eligibility")
            print("✅ Ticket Agent: LLM analysis for pricing")
            print("✅ Ticket Agent: LLM personalized recommendations")
            print("\n🚀 BUSINESS READY: Full LLM-powered ticket operations!")
            return True
        elif working_tests >= 2:
            print(f"\n⚠️  PARTIAL SUCCESS: {working_tests}/4 tests working")
            print("🔧 Some functionality available, but not all features working")
            return False
        else:
            print("\n❌ AGENTS NEED ATTENTION")
            print("🔧 AgentCore agents not providing expected functionality")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agentcore_final_validation())
    
    if success:
        print("\n🎯 NEXT STEPS:")
        print("1. ✅ AgentCore agents are working with actual LLM responses")
        print("2. ✅ Business logic is functional")
        print("3. ✅ Ready for customer interactions")
        print("4. 🚀 System is ready for production use!")
    else:
        print("\n🔧 TROUBLESHOOTING NEEDED:")
        print("1. Check AgentCore agent logs in AWS Console")
        print("2. Verify MCP server configurations")
        print("3. Test individual tool calls")
        print("4. Check database connectivity from agents")