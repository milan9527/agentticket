#!/usr/bin/env python3
"""
Test Pricing Endpoint

Test the pricing endpoint that's causing CORS issues.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_pricing_endpoint():
    """Test the pricing endpoint"""
    print("💰 TESTING PRICING ENDPOINT")
    print("=" * 50)
    
    # API configuration
    api_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    test_user = os.getenv('COGNITO_TEST_USER', 'testuser@example.com')
    test_password = os.getenv('COGNITO_TEST_PASSWORD', 'TempPass123!')
    
    print(f"🌐 API URL: {api_url}")
    print(f"👤 Test User: {test_user}")
    
    # Step 1: Authenticate
    print("\n🔐 Testing Authentication...")
    auth_response = requests.post(
        f"{api_url}/auth",
        json={
            "email": test_user,
            "password": test_password
        },
        headers={'Content-Type': 'application/json'}
    )
    
    if auth_response.status_code == 200:
        auth_data = auth_response.json()
        if auth_data.get('success'):
            access_token = auth_data['tokens']['access_token']
            print("✅ Authentication successful")
        else:
            print(f"❌ Authentication failed: {auth_data}")
            return
    else:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return
    
    # Step 2: Test Pricing Endpoint
    print("\n💰 Testing Pricing Endpoint...")
    
    ticket_id = "550e8400-e29b-41d4-a716-446655440002"
    upgrade_tier = "premium"
    travel_date = "2024-12-31"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    print(f"📋 Ticket ID: {ticket_id}")
    print(f"📋 Upgrade Tier: {upgrade_tier}")
    print(f"📋 Travel Date: {travel_date}")
    
    pricing_response = requests.post(
        f"{api_url}/tickets/{ticket_id}/pricing",
        json={
            "upgrade_tier": upgrade_tier,
            "travel_date": travel_date
        },
        headers=headers
    )
    
    print(f"\n📋 Status Code: {pricing_response.status_code}")
    print(f"📋 Response Headers:")
    for key, value in pricing_response.headers.items():
        if 'cors' in key.lower() or 'access-control' in key.lower():
            print(f"  {key}: {value}")
    
    if pricing_response.status_code == 200:
        pricing_data = pricing_response.json()
        print(f"✅ Pricing successful")
        print(f"💰 Response: {json.dumps(pricing_data, indent=2)}")
    else:
        print(f"❌ Pricing request failed: {pricing_response.status_code}")
        print(f"Response: {pricing_response.text}")
    
    # Step 3: Test Other Endpoints
    print("\n🎫 Testing Other Ticket Endpoints...")
    
    endpoints_to_test = [
        ("validate", "POST", {"upgrade_tier": "standard"}),
        ("tiers", "GET", None),
        ("recommendations", "GET", None)
    ]
    
    for endpoint, method, payload in endpoints_to_test:
        print(f"\n📝 Testing {endpoint} endpoint...")
        
        if endpoint == "recommendations":
            url = f"{api_url}/tickets/{ticket_id}/{endpoint}?customer_id=test-customer"
        else:
            url = f"{api_url}/tickets/{ticket_id}/{endpoint}"
        
        if method == "POST":
            response = requests.post(url, json=payload, headers=headers)
        else:
            response = requests.get(url, headers=headers)
        
        print(f"📋 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ {endpoint} successful")
        else:
            print(f"❌ {endpoint} failed: {response.status_code}")
            print(f"Response: {response.text}")


if __name__ == "__main__":
    test_pricing_endpoint()