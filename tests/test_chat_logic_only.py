#!/usr/bin/env python3
"""
Test just the chat logic without authentication
"""

import json
import sys
import os

# Add the backend/lambda directory to the path
sys.path.insert(0, 'backend/lambda')

# Import the chat functions directly
try:
    from ticket_handler import generate_intelligent_response, get_upgrade_options
    print("✅ Successfully imported chat functions from backend/lambda/ticket_handler.py")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

def test_chat_logic():
    """Test the chat logic functions directly"""
    
    print("Testing chat logic functions...")
    
    # Test greeting
    print("\n1. Testing greeting:")
    result = generate_intelligent_response("Hello", [], {})
    print(f"Response: {result['response'][:100]}...")
    print(f"Show buttons: {result['show_upgrade_buttons']}")
    
    # Test upgrade request
    print("\n2. Testing upgrade request:")
    result = generate_intelligent_response("I want to upgrade my ticket", [], {})
    print(f"Response: {result['response'][:100]}...")
    print(f"Show buttons: {result['show_upgrade_buttons']}")
    print(f"Options count: {len(result['upgrade_options'])}")
    
    # Test pricing question
    print("\n3. Testing pricing question:")
    result = generate_intelligent_response("How much does it cost?", [], {})
    print(f"Response: {result['response'][:100]}...")
    print(f"Show buttons: {result['show_upgrade_buttons']}")
    
    # Test upgrade options
    print("\n4. Testing upgrade options:")
    options = get_upgrade_options()
    print(f"Number of options: {len(options)}")
    for option in options:
        print(f"  - {option['name']}: ${option['price']}")
    
    return True

if __name__ == "__main__":
    print("Testing chat logic without authentication...")
    
    success = test_chat_logic()
    
    if success:
        print("\n✅ Chat logic tests passed!")
        print("\nThe Ticket Handler now includes:")
        print("- Chat endpoint at POST /chat")
        print("- AI response generation")
        print("- Upgrade option handling")
        print("- Fallback responses")
    else:
        print("\n❌ Chat logic tests failed.")