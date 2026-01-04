#!/usr/bin/env python3
"""
Debug Real Frontend Authentication

Compare the authentication flow between test scripts and actual frontend usage
to identify why 401 errors persist.
"""

import requests
import json
import os
import boto3
from datetime import datetime, timedelta
from dotenv import load_dotenv

def debug_real_frontend_auth():
    """Debug authentication differences between test and frontend"""
    
    # Load environment variables
    load_dotenv()
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    print("🔍 DEBUGGING REAL FRONTEND AUTHENTICATION ISSUE")
    print("=" * 60)
    
    # Step 1: Get fresh authentication token (same as frontend would)
    print("📝 Step 1: Getting fresh authentication token")
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return False
    
    auth_data = auth_response.json()
    token = auth_data['tokens']['access_token']
    print(f"✅ Got fresh token: {token[:50]}...{token[-10:]}")
    
    # Step 2: Test the exact same call that frontend makes
    print(f"\n📝 Step 2: Testing exact frontend chat call")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # This is the exact payload the frontend sends
    frontend_payload = {
        'message': '550e8400-e29b-41d4-a716-446655440002',
        'context': {},
        'conversationHistory': []
    }
    
    print(f"Frontend payload: {json.dumps(frontend_payload, indent=2)}")
    print(f"Headers: {headers}")
    
    chat_response = requests.post(f'{api_base_url}/chat', headers=headers, json=frontend_payload)
    
    print(f"Chat response status: {chat_response.status_code}")
    print(f"Chat response: {chat_response.text}")
    
    # Step 3: Check if there are any differences in token format or headers
    print(f"\n📝 Step 3: Analyzing token and headers")
    
    # Check token structure
    try:
        import base64
        # JWT tokens have 3 parts separated by dots
        token_parts = token.split('.')
        print(f"Token parts count: {len(token_parts)}")
        
        if len(token_parts) == 3:
            # Decode header (first part)
            header_padding = '=' * (4 - len(token_parts[0]) % 4)
            header_decoded = base64.b64decode(token_parts[0] + header_padding)
            print(f"Token header: {header_decoded.decode('utf-8')}")
            
            # Decode payload (second part) 
            payload_padding = '=' * (4 - len(token_parts[1]) % 4)
            payload_decoded = base64.b64decode(token_parts[1] + payload_padding)
            payload_json = json.loads(payload_decoded.decode('utf-8'))
            print(f"Token payload exp: {payload_json.get('exp', 'N/A')}")
            print(f"Token payload iat: {payload_json.get('iat', 'N/A')}")
            print(f"Current timestamp: {int(datetime.now().timestamp())}")
            
            # Check if token is expired
            exp_time = payload_json.get('exp', 0)
            current_time = int(datetime.now().timestamp())
            if exp_time < current_time:
                print(f"⚠️ TOKEN IS EXPIRED! Exp: {exp_time}, Current: {current_time}")
            else:
                print(f"✅ Token is valid (expires in {exp_time - current_time} seconds)")
                
    except Exception as e:
        print(f"Could not decode token: {e}")
    
    # Step 4: Test direct ticket handler call with same token
    print(f"\n📝 Step 4: Testing direct ticket handler with same token")
    
    direct_response = requests.post(
        f'{api_base_url}/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
        headers=headers,
        json={'upgrade_tier': 'Standard Upgrade'}
    )
    
    print(f"Direct ticket handler status: {direct_response.status_code}")
    print(f"Direct ticket handler response: {direct_response.text}")
    
    # Step 5: Check recent CloudWatch logs for this specific request
    print(f"\n📝 Step 5: Checking CloudWatch logs for this request")
    
    logs_client = boto3.client('logs', region_name='us-west-2')
    
    try:
        # Check chat handler logs
        chat_log_group = '/aws/lambda/chat-handler'
        
        # Get log events from the last 2 minutes
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=2)
        
        chat_response = logs_client.filter_log_events(
            logGroupName=chat_log_group,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000)
        )
        
        print("Recent chat handler logs:")
        for event in chat_response['events'][-5:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            if any(keyword in message for keyword in ['delegating', 'Auth header', 'response status', '401']):
                print(f"  {timestamp}: {message}")
        
        # Check ticket handler logs
        ticket_log_group = '/aws/lambda/ticket-handler'
        
        ticket_response = logs_client.filter_log_events(
            logGroupName=ticket_log_group,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000)
        )
        
        print("\nRecent ticket handler logs:")
        for event in ticket_response['events'][-5:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            if any(keyword in message for keyword in ['Authorization', 'token', 'auth', '401']):
                print(f"  {timestamp}: {message}")
                
    except Exception as e:
        print(f"Could not check CloudWatch logs: {e}")
    
    # Step 6: Test with different API Gateway URL formats
    print(f"\n📝 Step 6: Testing different URL formats")
    
    # Test if there's a URL mismatch
    test_urls = [
        'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod',
        'https://zno1ww5qr5.execute-api.us-west-2.amazonaws.com/prod'  # Alternative URL from context
    ]
    
    for test_url in test_urls:
        print(f"\nTesting URL: {test_url}")
        try:
            test_response = requests.post(f'{test_url}/chat', headers=headers, json=frontend_payload, timeout=5)
            print(f"  Status: {test_response.status_code}")
            if test_response.status_code != 200:
                print(f"  Error: {test_response.text[:100]}...")
        except Exception as e:
            print(f"  Error: {e}")
    
    return True

if __name__ == "__main__":
    debug_real_frontend_auth()