#!/usr/bin/env python3
"""
Test Auth Header Passing

Test exactly what authentication header the chat handler is sending
to the ticket handler.
"""

import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_auth_header_passing():
    """Test the exact auth header being passed"""
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    print("🔍 TESTING AUTH HEADER PASSING")
    print("=" * 40)
    
    # Get authentication token
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return False
    
    auth_data = auth_response.json()
    token = auth_data['tokens']['access_token']
    full_auth_header = f'Bearer {token}'
    
    print(f"✅ Got token")
    print(f"Full auth header: {full_auth_header[:50]}...{full_auth_header[-20:]}")
    print(f"Auth header length: {len(full_auth_header)}")
    
    # Test what the chat handler would send
    headers = {
        'Authorization': full_auth_header,
        'Content-Type': 'application/json'
    }
    
    print(f"\nTesting direct call with same headers chat handler would use:")
    print(f"Authorization header: {headers['Authorization'][:50]}...{headers['Authorization'][-20:]}")
    
    # Make the exact same call the chat handler makes
    import urllib3
    http = urllib3.PoolManager()
    
    payload = {
        'upgrade_tier': 'Standard Upgrade'
    }
    
    try:
        response = http.request(
            'POST',
            f'{api_base_url}/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
            body=json.dumps(payload),
            headers=headers,
            timeout=10.0
        )
        
        print(f"urllib3 response status: {response.status}")
        if response.status == 200:
            result = json.loads(response.data.decode('utf-8'))
            print(f"✅ urllib3 call successful: {result}")
        else:
            error_data = response.data.decode('utf-8') if response.data else 'No response data'
            print(f"❌ urllib3 call failed: {error_data}")
            
    except Exception as e:
        print(f"❌ urllib3 call exception: {e}")
    
    # Compare with requests library
    print(f"\nTesting with requests library for comparison:")
    
    try:
        requests_response = requests.post(
            f'{api_base_url}/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
            headers=headers,
            json=payload
        )
        
        print(f"requests response status: {requests_response.status_code}")
        if requests_response.status_code == 200:
            print(f"✅ requests call successful: {requests_response.json()}")
        else:
            print(f"❌ requests call failed: {requests_response.text}")
            
    except Exception as e:
        print(f"❌ requests call exception: {e}")
    
    # Test if there are any character encoding issues
    print(f"\nTesting character encoding:")
    print(f"Auth header bytes: {full_auth_header.encode('utf-8')[:50]}...")
    print(f"Auth header repr: {repr(full_auth_header[:50])}...")
    
    return True

if __name__ == "__main__":
    test_auth_header_passing()