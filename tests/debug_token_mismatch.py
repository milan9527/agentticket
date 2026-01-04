#!/usr/bin/env python3
"""
Debug Token Mismatch Issue

The issue appears to be that the frontend is using a different/expired token
than what our test scripts generate. Let's investigate this.
"""

import requests
import json
import os
import boto3
from datetime import datetime, timedelta
from dotenv import load_dotenv

def debug_token_mismatch():
    """Debug token mismatch between frontend and backend"""
    
    # Load environment variables
    load_dotenv()
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    print("🔍 DEBUGGING TOKEN MISMATCH ISSUE")
    print("=" * 50)
    
    # Step 1: Check what the CloudWatch logs show for recent 401 errors
    print("📝 Step 1: Analyzing recent 401 errors from CloudWatch")
    
    logs_client = boto3.client('logs', region_name='us-west-2')
    
    try:
        log_group = '/aws/lambda/chat-handler'
        
        # Get log events from the last 30 minutes
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=30)
        
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000),
            filterPattern='Auth header'
        )
        
        print("Recent auth headers from failed requests:")
        for event in response['events'][-5:]:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            if 'Auth header:' in message:
                # Extract the token part
                auth_part = message.split('Auth header: Bearer ')[-1]
                token_start = auth_part[:50] if len(auth_part) > 50 else auth_part
                print(f"  {timestamp}: {token_start}...")
                
    except Exception as e:
        print(f"Could not check CloudWatch logs: {e}")
    
    # Step 2: Generate a fresh token and compare
    print(f"\n📝 Step 2: Generating fresh token for comparison")
    
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return False
    
    auth_data = auth_response.json()
    fresh_token = auth_data['tokens']['access_token']
    print(f"Fresh token start: {fresh_token[:50]}...")
    
    # Step 3: Test the fresh token
    print(f"\n📝 Step 3: Testing fresh token")
    
    headers = {
        'Authorization': f'Bearer {fresh_token}',
        'Content-Type': 'application/json'
    }
    
    test_response = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': '550e8400-e29b-41d4-a716-446655440002',
        'context': {},
        'conversationHistory': []
    })
    
    print(f"Fresh token test status: {test_response.status_code}")
    if test_response.status_code == 200:
        print("✅ Fresh token works")
    else:
        print(f"❌ Fresh token failed: {test_response.text}")
    
    # Step 4: Check if there are multiple tokens being generated
    print(f"\n📝 Step 4: Checking for token generation patterns")
    
    # Generate multiple tokens to see if they're different
    tokens = []
    for i in range(3):
        auth_resp = requests.post(f'{api_base_url}/auth', json={
            'email': 'testuser@example.com',
            'password': 'TempPass123!'
        })
        if auth_resp.status_code == 200:
            token = auth_resp.json()['tokens']['access_token']
            tokens.append(token[:50])
            print(f"Token {i+1}: {token[:50]}...")
    
    # Check if tokens are the same or different
    if len(set(tokens)) == 1:
        print("✅ All tokens are identical (good)")
    else:
        print("⚠️ Tokens are different each time (this could cause issues)")
    
    # Step 5: Check token expiration times
    print(f"\n📝 Step 5: Checking token expiration")
    
    try:
        import base64
        
        # Decode the fresh token
        token_parts = fresh_token.split('.')
        if len(token_parts) == 3:
            payload_padding = '=' * (4 - len(token_parts[1]) % 4)
            payload_decoded = base64.b64decode(token_parts[1] + payload_padding)
            payload_json = json.loads(payload_decoded.decode('utf-8'))
            
            exp_time = payload_json.get('exp', 0)
            iat_time = payload_json.get('iat', 0)
            current_time = int(datetime.now().timestamp())
            
            print(f"Token issued at: {datetime.fromtimestamp(iat_time)}")
            print(f"Token expires at: {datetime.fromtimestamp(exp_time)}")
            print(f"Current time: {datetime.fromtimestamp(current_time)}")
            print(f"Token valid for: {exp_time - current_time} seconds")
            
            if exp_time < current_time:
                print("❌ TOKEN IS EXPIRED!")
            else:
                print("✅ Token is still valid")
                
    except Exception as e:
        print(f"Could not decode token: {e}")
    
    # Step 6: Provide solution recommendations
    print(f"\n📝 Step 6: Solution Recommendations")
    print("=" * 50)
    
    print("LIKELY CAUSES OF 401 ERRORS:")
    print("1. Frontend using expired token from localStorage")
    print("2. Frontend using different token than expected")
    print("3. Token refresh not working properly")
    print("4. Race condition between token generation and usage")
    
    print("\nRECOMMENDED SOLUTIONS:")
    print("1. Clear localStorage and re-authenticate")
    print("2. Add token expiration checking in frontend")
    print("3. Implement automatic token refresh")
    print("4. Add better error handling for 401 responses")
    
    return True

if __name__ == "__main__":
    debug_token_mismatch()