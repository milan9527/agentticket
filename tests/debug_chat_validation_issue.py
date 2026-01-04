#!/usr/bin/env python3
"""
Debug Chat Validation Issue

This script investigates why ticket validation is failing in the chat context
but working in direct API calls.
"""

import asyncio
import json
import sys
import os
sys.path.append('backend/lambda')

from agentcore_client import create_client

async def debug_chat_validation_issue():
    """Debug the specific validation issue in chat context"""
    print("🔍 DEBUGGING CHAT VALIDATION ISSUE")
    print("=" * 60)
    
    # Create client
    client = create_client()
    ticket_id = "550e8400-e29b-41d4-a716-446655440002"
    
    print(f"🎫 Testing ticket: {ticket_id}")
    print()
    
    # Test 1: Direct validation call (like API endpoint)
    print("🧪 TEST 1: Direct Validation Call")
    print("-" * 40)
    
    try:
        result = await client.validate_ticket_eligibility(ticket_id, 'standard')
        print(f"✅ Success: {result.get('success', False)}")
        print(f"📊 Data keys: {list(result.get('data', {}).keys()) if result.get('data') else 'None'}")
        
        if result.get('data'):
            data = result.get('data', {})
            print(f"📝 Content length: {len(str(data.get('content', '')))}")
            print(f"🔍 Is error: {data.get('isError', False)}")
            
            # Check if there's structured content
            if 'structuredContent' in data:
                structured = data['structuredContent']
                print(f"📋 Structured content keys: {list(structured.keys()) if isinstance(structured, dict) else 'Not dict'}")
                
                if isinstance(structured, dict):
                    # Look for eligibility info
                    if 'eligible' in structured:
                        print(f"✅ Eligible: {structured['eligible']}")
                    if 'ticket' in structured:
                        ticket_info = structured['ticket']
                        print(f"🎫 Ticket info: {ticket_info}")
                    if 'error' in structured:
                        print(f"❌ Error in structured: {structured['error']}")
            
            # Check raw content for error messages
            content = str(data.get('content', ''))
            if 'validation failed' in content.lower() or 'error' in content.lower():
                print(f"⚠️ Error detected in content:")
                print(f"   {content[:200]}...")
        
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # Test 2: Simulate chat context processing
    print(f"\n🧪 TEST 2: Chat Context Processing")
    print("-" * 40)
    
    try:
        # This is what the chat function does
        result = await client.validate_ticket_eligibility(ticket_id, 'standard')
        
        if result.get('success') and result.get('data'):
            mcp_data = result.get('data', {})
            
            print(f"📊 MCP data keys: {list(mcp_data.keys())}")
            
            # Check if we have structured content (real LLM response)
            if 'content' in mcp_data and len(str(mcp_data['content'])) > 1000:
                print("🎉 Large content detected - should use real LLM response")
                llm_content = str(mcp_data['content'])
                print(f"   Content preview: {llm_content[:100]}...")
            else:
                print("📝 Small/no content - using fallback logic")
                
                # This is the fallback logic that's being used
                eligibility_data = mcp_data
                
                # Check what's actually in the eligibility data
                print(f"🔍 Eligibility data structure:")
                if isinstance(eligibility_data, dict):
                    for key, value in eligibility_data.items():
                        if key == 'content':
                            print(f"   {key}: {str(value)[:100]}...")
                        else:
                            print(f"   {key}: {value}")
                
                # Check for structured content
                if 'structuredContent' in eligibility_data:
                    structured = eligibility_data['structuredContent']
                    print(f"📋 Structured content: {structured}")
                    
                    if isinstance(structured, dict) and 'eligible' in structured:
                        eligible = structured['eligible']
                        print(f"✅ Found eligibility: {eligible}")
                    else:
                        print("⚠️ No eligibility info in structured content")
                else:
                    print("⚠️ No structured content found")
                
                # Check if there's an error in the content
                content = str(eligibility_data.get('content', ''))
                if 'validation failed' in content.lower():
                    print("❌ Validation failed message detected in content")
                    print(f"   Error content: {content}")
        else:
            print(f"❌ MCP call failed: {result}")
    
    except Exception as e:
        print(f"❌ Chat processing exception: {e}")
    
    # Test 3: Check what the error response actually contains
    print(f"\n🧪 TEST 3: Error Response Analysis")
    print("-" * 40)
    
    try:
        # Try with an invalid ticket to see error format
        invalid_result = await client.validate_ticket_eligibility("invalid-ticket-id", 'standard')
        print(f"🔍 Invalid ticket result:")
        print(f"   Success: {invalid_result.get('success', False)}")
        
        if invalid_result.get('data'):
            data = invalid_result.get('data', {})
            content = str(data.get('content', ''))
            print(f"   Content: {content[:200]}...")
            
            if 'structuredContent' in data:
                print(f"   Structured: {data['structuredContent']}")
    
    except Exception as e:
        print(f"❌ Invalid ticket test exception: {e}")

def main():
    """Main function"""
    asyncio.run(debug_chat_validation_issue())

if __name__ == "__main__":
    main()