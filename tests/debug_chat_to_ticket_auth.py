#!/usr/bin/env python3
"""
Debug Chat to Ticket Authentication

Deep dive into the authentication flow between chat handler and ticket handler
to identify why 401 errors are occurring.
"""

import requests
import json
import os
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def debug_chat_to_ticket_auth():
    """Debug the specific authentication issue between chat and ticket handler"""
    
    api_base_url = os.getenv('API_GATEWAY_URL', 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod')
    
    print("🔍 DEBUGGING CHAT → TICKET HANDLER AUTHENTICATION")
    print("=" * 60)
    
    # Step 1: Get authentication token
    print("📝 Step 1: Getting authentication token")
    auth_response = requests.post(f'{api_base_url}/auth', json={
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    })
    
    if auth_response.status_code != 200:
        print(f"❌ Authentication failed: {auth_response.status_code}")
        return False
    
    auth_data = auth_response.json()
    token = auth_data['tokens']['access_token']
    print(f"✅ Got token: {token[:50]}...{token[-10:]}")
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Step 2: Test direct ticket handler call
    print(f"\n📝 Step 2: Testing direct ticket handler call")
    direct_url = f'{api_base_url}/tickets/550e8400-e29b-41d4-a716-446655440002/validate'
    print(f"Direct URL: {direct_url}")
    
    direct_response = requests.post(
        direct_url,
        headers=headers,
        json={'upgrade_tier': 'Standard Upgrade'}
    )
    
    print(f"Direct call status: {direct_response.status_code}")
    if direct_response.status_code == 200:
        print("✅ Direct ticket handler call works")
        print(f"Response: {direct_response.json()}")
    else:
        print(f"❌ Direct ticket handler call failed")
        print(f"Response: {direct_response.text}")
        return False
    
    # Step 3: Check Lambda environment variables
    print(f"\n📝 Step 3: Checking chat handler Lambda environment")
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    try:
        function_config = lambda_client.get_function_configuration(FunctionName='chat-handler')
        env_vars = function_config.get('Environment', {}).get('Variables', {})
        
        print("Chat handler environment variables:")
        for key, value in env_vars.items():
            if 'URL' in key:
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {'***' if 'SECRET' in key or 'ARN' in key else value}")
        
        chat_api_url = env_vars.get('API_GATEWAY_URL', 'NOT SET')
        print(f"\nChat handler will use URL: {chat_api_url}")
        
        if chat_api_url != api_base_url:
            print(f"⚠️ URL MISMATCH!")
            print(f"  Test script using: {api_base_url}")
            print(f"  Chat handler using: {chat_api_url}")
        else:
            print(f"✅ URLs match")
            
    except Exception as e:
        print(f"❌ Could not check Lambda config: {e}")
    
    # Step 4: Test chat handler call and trace the delegation
    print(f"\n📝 Step 4: Testing chat handler call with tracing")
    chat_response = requests.post(f'{api_base_url}/chat', headers=headers, json={
        'message': '550e8400-e29b-41d4-a716-446655440002',
        'context': {},
        'conversationHistory': []
    })
    
    print(f"Chat handler status: {chat_response.status_code}")
    if chat_response.status_code == 200:
        chat_data = chat_response.json()
        print(f"Chat response: {chat_data['response'][:200]}...")
        
        if '401' in chat_data['response']:
            print("❌ Chat handler is getting 401 when calling ticket handler")
            print("This means the chat handler's internal call is failing")
        else:
            print("✅ Chat handler call successful")
    else:
        print(f"❌ Chat handler call failed: {chat_response.status_code}")
        print(f"Response: {chat_response.text}")
    
    # Step 5: Check CloudWatch logs for chat handler
    print(f"\n📝 Step 5: Checking recent CloudWatch logs")
    logs_client = boto3.client('logs', region_name='us-west-2')
    
    try:
        log_group = '/aws/lambda/chat-handler'
        
        # Get recent log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=3
        )
        
        print("Recent log streams:")
        for stream in streams_response['logStreams']:
            stream_name = stream['logStreamName']
            print(f"  {stream_name}")
            
            # Get recent events from this stream
            try:
                events_response = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    limit=10,
                    startFromHead=False
                )
                
                print(f"    Recent events:")
                for event in events_response['events'][-5:]:  # Last 5 events
                    message = event['message'].strip()
                    if any(keyword in message for keyword in ['401', 'error', 'failed', 'delegating']):
                        print(f"      {message}")
                        
            except Exception as e:
                print(f"    Could not read events: {e}")
                
    except Exception as e:
        print(f"❌ Could not check CloudWatch logs: {e}")
    
    # Step 6: Test with different authentication approaches
    print(f"\n📝 Step 6: Testing different authentication scenarios")
    
    # Test if the issue is with token format
    test_scenarios = [
        ("Original token", f'Bearer {token}'),
        ("Token without Bearer", token),
        ("Different format", f'bearer {token}')
    ]
    
    for scenario_name, auth_value in test_scenarios:
        print(f"\nTesting {scenario_name}:")
        test_headers = {
            'Authorization': auth_value,
            'Content-Type': 'application/json'
        }
        
        test_response = requests.post(
            f'{api_base_url}/tickets/550e8400-e29b-41d4-a716-446655440002/validate',
            headers=test_headers,
            json={'upgrade_tier': 'Standard Upgrade'}
        )
        
        print(f"  Status: {test_response.status_code}")
        if test_response.status_code != 200:
            print(f"  Error: {test_response.text[:100]}...")
    
    return True

if __name__ == "__main__":
    debug_chat_to_ticket_auth()