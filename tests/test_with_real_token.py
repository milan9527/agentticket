#!/usr/bin/env python3
"""
Test Ticket Handler with Real Token

Get a real authentication token and test the ticket handler.
"""

import boto3
import json
import requests

# API Configuration
API_BASE_URL = 'https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod'

def get_real_token():
    """Get a real authentication token"""
    auth_data = {
        'email': 'testuser@example.com',
        'password': 'TempPass123!'
    }
    
    response = requests.post(f'{API_BASE_URL}/auth', json=auth_data)
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            return result['tokens']['access_token']
    return None

def test_ticket_handler_with_real_token():
    """Test ticket handler Lambda with real token"""
    print("🧪 TESTING TICKET HANDLER WITH REAL TOKEN")
    print("=" * 50)
    
    # Get real token
    token = get_real_token()
    if not token:
        print("❌ Failed to get authentication token")
        return
    
    print("✅ Got real authentication token")
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Test ticket validation
    test_ticket_id = '550e8400-e29b-41d4-a716-446655440002'
    
    # Prepare payload for ticket validation
    validation_payload = {
        'httpMethod': 'POST',
        'path': f'/tickets/{test_ticket_id}/validate',
        'pathParameters': {'ticket_id': test_ticket_id},
        'headers': {'Authorization': f'Bearer {token}'},
        'body': json.dumps({'upgrade_tier': 'Standard Upgrade'})
    }
    
    print(f"🎫 Testing ticket validation for: {test_ticket_id}")
    
    try:
        # Invoke ticket handler Lambda
        response = lambda_client.invoke(
            FunctionName='ticket-handler',
            InvocationType='RequestResponse',
            Payload=json.dumps(validation_payload)
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        print(f"\n📊 Response Status Code: {response_payload.get('statusCode')}")
        
        if response_payload.get('body'):
            body = json.loads(response_payload.get('body', '{}'))
            print(f"📋 Response Body: {json.dumps(body, indent=2)}")
        
        if response_payload.get('statusCode') == 200:
            print("✅ Ticket handler responded successfully")
        else:
            print("❌ Ticket handler returned error")
            
    except Exception as e:
        print(f"❌ Error calling ticket handler: {e}")

if __name__ == "__main__":
    test_ticket_handler_with_real_token()