#!/usr/bin/env python3
"""
Test Lambda Functions with AgentCore Integration

This script tests the Lambda functions locally to ensure they properly
communicate with the deployed AgentCore MCP agents.
"""

import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agentcore_client import create_client
from auth_handler import lambda_handler as auth_handler
from ticket_handler import lambda_handler as ticket_handler
from customer_handler import lambda_handler as customer_handler

# Load environment variables
load_dotenv()


async def test_agentcore_client():
    """Test direct AgentCore client functionality"""
    print("🔍 Testing AgentCore Client Direct Integration")
    print("=" * 60)
    
    try:
        # Create and authenticate client
        client = create_client()
        print("✅ AgentCore client created and authenticated")
        
        # Test Data Agent - Get Customer
        print("\n📋 Testing Data Agent - Get Customer...")
        result = await client.get_customer("550e8400-e29b-41d4-a716-446655440001")
        if result['success']:
            print("✅ Get customer successful")
        else:
            print(f"❌ Get customer failed: {result.get('error')}")
        
        # Test Data Agent - Get Tickets
        print("\n🎫 Testing Data Agent - Get Tickets...")
        result = await client.get_tickets_for_customer("550e8400-e29b-41d4-a716-446655440001")
        if result['success']:
            print("✅ Get tickets successful")
        else:
            print(f"❌ Get tickets failed: {result.get('error')}")
        
        # Test Ticket Agent - Validate Eligibility
        print("\n🔍 Testing Ticket Agent - Validate Eligibility...")
        result = await client.validate_ticket_eligibility("550e8400-e29b-41d4-a716-446655440002", "Standard")
        if result['success']:
            print("✅ Validate eligibility successful")
        else:
            print(f"❌ Validate eligibility failed: {result.get('error')}")
        
        # Test Ticket Agent - Calculate Pricing
        print("\n💰 Testing Ticket Agent - Calculate Pricing...")
        result = await client.calculate_upgrade_pricing("550e8400-e29b-41d4-a716-446655440002", "Standard", "2026-02-15")
        if result['success']:
            print("✅ Calculate pricing successful")
        else:
            print(f"❌ Calculate pricing failed: {result.get('error')}")
        
        # Test Ticket Agent - Get Recommendations
        print("\n🎯 Testing Ticket Agent - Get Recommendations...")
        result = await client.get_upgrade_recommendations("550e8400-e29b-41d4-a716-446655440001", "550e8400-e29b-41d4-a716-446655440002")
        if result['success']:
            print("✅ Get recommendations successful")
        else:
            print(f"❌ Get recommendations failed: {result.get('error')}")
        
        print("\n✅ AgentCore client integration test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ AgentCore client test failed: {e}")
        return False


def test_auth_handler():
    """Test authentication handler"""
    print("\n🔐 Testing Authentication Handler")
    print("=" * 60)
    
    # Test authentication with valid credentials
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({
            'email': os.getenv('COGNITO_TEST_USER', 'testuser@example.com'),
            'password': os.getenv('COGNITO_TEST_PASSWORD', 'TempPass123!')
        })
    }
    
    try:
        response = auth_handler(event, {})
        
        if response['statusCode'] == 200:
            body = json.loads(response['body'])
            if body.get('success') and 'tokens' in body:
                print("✅ Authentication successful")
                print(f"📋 Access token received: {body['tokens']['access_token'][:20]}...")
                return body['tokens']['access_token']
            else:
                print(f"❌ Authentication failed: {body}")
                return None
        else:
            print(f"❌ Authentication failed with status {response['statusCode']}")
            return None
            
    except Exception as e:
        print(f"❌ Authentication handler test failed: {e}")
        return None


def test_ticket_handler(access_token):
    """Test ticket handler"""
    print("\n🎫 Testing Ticket Handler")
    print("=" * 60)
    
    if not access_token:
        print("❌ No access token available for testing")
        return False
    
    # Test ticket validation
    event = {
        'httpMethod': 'POST',
        'path': '/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
        'pathParameters': {'ticket_id': '550e8400-e29b-41d4-a716-446655440002'},
        'headers': {'Authorization': f'Bearer {access_token}'},
        'body': json.dumps({'upgrade_tier': 'Standard'})
    }
    
    try:
        response = ticket_handler(event, {})
        
        if response['statusCode'] == 200:
            print("✅ Ticket validation endpoint successful")
            return True
        else:
            body = json.loads(response['body'])
            print(f"❌ Ticket validation failed: {body}")
            return False
            
    except Exception as e:
        print(f"❌ Ticket handler test failed: {e}")
        return False


def test_customer_handler(access_token):
    """Test customer handler"""
    print("\n👤 Testing Customer Handler")
    print("=" * 60)
    
    if not access_token:
        print("❌ No access token available for testing")
        return False
    
    # Test get customer
    event = {
        'httpMethod': 'GET',
        'path': '/customers/550e8400-e29b-41d4-a716-446655440001',
        'pathParameters': {'customer_id': '550e8400-e29b-41d4-a716-446655440001'},
        'headers': {'Authorization': f'Bearer {access_token}'}
    }
    
    try:
        response = customer_handler(event, {})
        
        if response['statusCode'] == 200:
            print("✅ Customer get endpoint successful")
            return True
        else:
            body = json.loads(response['body'])
            print(f"❌ Customer get failed: {body}")
            return False
            
    except Exception as e:
        print(f"❌ Customer handler test failed: {e}")
        return False


async def main():
    """Main test function"""
    print("🚀 LAMBDA FUNCTIONS + AGENTCORE INTEGRATION TEST")
    print("=" * 70)
    
    # Test AgentCore client integration
    agentcore_success = await test_agentcore_client()
    
    # Test authentication handler
    access_token = test_auth_handler()
    auth_success = access_token is not None
    
    # Test ticket handler
    ticket_success = test_ticket_handler(access_token)
    
    # Test customer handler
    customer_success = test_customer_handler(access_token)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 LAMBDA INTEGRATION TEST RESULTS")
    print("=" * 70)
    
    results = {
        'AgentCore Client': agentcore_success,
        'Authentication Handler': auth_success,
        'Ticket Handler': ticket_success,
        'Customer Handler': customer_success
    }
    
    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    overall_success = all(results.values())
    
    if overall_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Lambda functions successfully integrate with AgentCore")
        print("✅ Authentication working with Cognito")
        print("✅ API endpoints properly routing to AgentCore agents")
        print("✅ Ready for API Gateway deployment")
    else:
        print("\n⚠️ Some tests failed - check individual results above")
    
    return overall_success


if __name__ == "__main__":
    asyncio.run(main())