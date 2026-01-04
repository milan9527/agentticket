#!/usr/bin/env python3
"""
Debug Validation and Pricing MCP Calls

This script tests why validate_ticket_eligibility and calculate_upgrade_pricing
are failing in the chat context but work in other contexts.
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

async def test_validation_call():
    """Test the validate_ticket_eligibility call that's failing in chat"""
    print("🔍 TESTING VALIDATE_TICKET_ELIGIBILITY CALL")
    print("=" * 60)
    
    try:
        client = create_client()
        print(f"✅ Client created successfully")
        
        # Test the exact call that chat is making
        ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        upgrade_tier = "standard"
        
        print(f"🎯 Testing validation call...")
        print(f"   Ticket ID: {ticket_id}")
        print(f"   Upgrade Tier: {upgrade_tier}")
        
        result = await client.validate_ticket_eligibility(ticket_id, upgrade_tier)
        
        print(f"\n📋 Validation Result:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            data = result.get('data', {})
            print(f"   Data Keys: {list(data.keys())}")
            print(f"   Eligible: {data.get('eligible')}")
            print(f"   Data Length: {len(str(data))} characters")
            
            if len(str(data)) > 1000:
                print(f"✅ WORKING: Large response indicates real LLM usage")
                return True
            else:
                print(f"⚠️ SHORT RESPONSE: May be using fallback")
                return False
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Validation call failed: {error}")
            return False
            
    except Exception as e:
        print(f"❌ Error during validation test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_pricing_call():
    """Test the calculate_upgrade_pricing call that's failing in chat"""
    print("\n🔍 TESTING CALCULATE_UPGRADE_PRICING CALL")
    print("=" * 60)
    
    try:
        client = create_client()
        
        # Test the exact call that chat is making
        ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        upgrade_tier = "standard"
        event_date = "2026-02-15"
        
        print(f"🎯 Testing pricing call...")
        print(f"   Ticket ID: {ticket_id}")
        print(f"   Upgrade Tier: {upgrade_tier}")
        print(f"   Event Date: {event_date}")
        
        result = await client.calculate_upgrade_pricing(ticket_id, upgrade_tier, event_date)
        
        print(f"\n📋 Pricing Result:")
        print(f"   Success: {result.get('success')}")
        
        if result.get('success'):
            data = result.get('data', {})
            print(f"   Data Keys: {list(data.keys())}")
            print(f"   Data Length: {len(str(data))} characters")
            
            if len(str(data)) > 500:
                print(f"✅ WORKING: Response indicates real LLM usage")
                return True
            else:
                print(f"⚠️ SHORT RESPONSE: May be using fallback")
                return False
        else:
            error = result.get('error', 'Unknown error')
            print(f"❌ Pricing call failed: {error}")
            return False
            
    except Exception as e:
        print(f"❌ Error during pricing test: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main debugging function"""
    print("🚀 DEBUGGING VALIDATION & PRICING MCP CALLS")
    print("Investigating why these calls fail in chat but work elsewhere")
    print("=" * 80)
    
    # Test validation call
    validation_works = await test_validation_call()
    
    # Test pricing call  
    pricing_works = await test_pricing_call()
    
    # Analysis
    print("\n" + "=" * 80)
    print("🎯 ANALYSIS")
    print("=" * 80)
    
    if validation_works and pricing_works:
        print("✅ BOTH CALLS WORK - Issue may be in Lambda chat logic")
    elif validation_works or pricing_works:
        print("⚠️ PARTIAL SUCCESS - One call works, one doesn't")
    else:
        print("❌ BOTH CALLS FAIL - MCP tool issue")

if __name__ == "__main__":
    asyncio.run(main())