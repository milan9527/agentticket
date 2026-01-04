#!/usr/bin/env python3
"""
Test Ticket Handler Lambda Directly

Test the ticket handler Lambda function directly to see what's happening.
"""

import boto3
import json

def test_ticket_handler_direct():
    """Test ticket handler Lambda directly"""
    print("🧪 TESTING TICKET HANDLER LAMBDA DIRECTLY")
    print("=" * 50)
    
    # Initialize Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Test ticket validation
    test_ticket_id = '550e8400-e29b-41d4-a716-446655440002'
    
    # Prepare payload for ticket validation
    validation_payload = {
        'httpMethod': 'POST',
        'path': f'/tickets/{test_ticket_id}/validate',
        'pathParameters': {'ticket_id': test_ticket_id},
        'headers': {'Authorization': 'Bearer dummy-token'},
        'body': json.dumps({'upgrade_tier': 'Standard Upgrade'})
    }
    
    print(f"🎫 Testing ticket validation for: {test_ticket_id}")
    print(f"📋 Payload: {json.dumps(validation_payload, indent=2)}")
    
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
        print(f"📋 Response Body: {json.dumps(json.loads(response_payload.get('body', '{}')), indent=2)}")
        
        if response_payload.get('statusCode') == 200:
            print("✅ Ticket handler responded successfully")
        else:
            print("❌ Ticket handler returned error")
            
    except Exception as e:
        print(f"❌ Error calling ticket handler: {e}")

if __name__ == "__main__":
    test_ticket_handler_direct()