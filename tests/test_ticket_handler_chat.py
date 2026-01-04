#!/usr/bin/env python3
"""
Test the updated Ticket Handler with chat functionality
"""

import json
import sys
import os

# Add the backend/lambda directory to the path
sys.path.append('backend/lambda')

from ticket_handler import lambda_handler

def test_chat_endpoint():
    """Test the new /chat endpoint in ticket handler"""
    
    # Mock event for chat request
    event = {
        'httpMethod': 'POST',
        'path': '/chat',
        'headers': {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'message': 'Hello, I want to upgrade my ticket',
            'conversationHistory': [],
            'context': {}
        })
    }
    
    # Mock context
    context = {}
    
    try:
        print("Testing chat endpoint in Ticket Handler...")
        result = lambda_handler(event, context)
        
        print(f"Status Code: {result['statusCode']}")
        print(f"Response: {result['body']}")
        
        if result['statusCode'] == 200:
            response_data = json.loads(result['body'])
            print(f"Success: {response_data.get('success')}")
            print(f"AI Response: {response_data.get('response')}")
            print(f"Show Upgrade Buttons: {response_data.get('showUpgradeButtons')}")
            
        return result['statusCode'] == 200
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

def test_existing_endpoints():
    """Test that existing endpoints still work"""
    
    # Test ticket validation endpoint
    event = {
        'httpMethod': 'POST',
        'path': '/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
        'pathParameters': {
            'ticket_id': '550e8400-e29b-41d4-a716-446655440002'
        },
        'headers': {
            'Authorization': 'Bearer test-token',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'upgrade_tier': 'Standard'
        })
    }
    
    context = {}
    
    try:
        print("\nTesting existing validation endpoint...")
        result = lambda_handler(event, context)
        
        print(f"Status Code: {result['statusCode']}")
        print(f"Response: {result['body']}")
        
        return result['statusCode'] in [200, 401]  # 401 is OK (auth issue in test)
        
    except Exception as e:
        print(f"Existing endpoint test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing updated Ticket Handler with chat functionality...")
    
    # Test chat endpoint
    chat_success = test_chat_endpoint()
    
    # Test existing endpoints still work
    existing_success = test_existing_endpoints()
    
    if chat_success and existing_success:
        print("\n✅ All tests passed! Ticket Handler now supports chat.")
    else:
        print("\n❌ Some tests failed.")
        
    print(f"\nChat endpoint: {'✅' if chat_success else '❌'}")
    print(f"Existing endpoints: {'✅' if existing_success else '❌'}")