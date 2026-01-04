#!/usr/bin/env python3
"""
Deploy Upgrade Selection Fix

This script deploys the updated Lambda function that properly handles upgrade selection messages.
"""

import boto3
import json
import zipfile
import os
import time
from pathlib import Path

def create_lambda_package():
    """Create deployment package for Lambda function"""
    print("📦 Creating Lambda deployment package...")
    
    # Create zip file
    zip_path = "ticket-handler-upgrade-fix.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main Lambda files
        lambda_files = [
            'backend/lambda/ticket_handler.py',
            'backend/lambda/agentcore_client.py', 
            'backend/lambda/auth_handler.py'
        ]
        
        for file_path in lambda_files:
            if os.path.exists(file_path):
                # Add to zip with just the filename (no directory structure)
                zipf.write(file_path, os.path.basename(file_path))
                print(f"   ✅ Added {file_path}")
            else:
                print(f"   ⚠️  Missing {file_path}")
    
    print(f"✅ Created deployment package: {zip_path}")
    return zip_path

def deploy_lambda_function(zip_path):
    """Deploy the Lambda function"""
    print("\n🚀 Deploying Lambda function...")
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    try:
        # Read the zip file
        with open(zip_path, 'rb') as zip_file:
            zip_content = zip_file.read()
        
        # Update function code
        response = lambda_client.update_function_code(
            FunctionName='ticket-handler',
            ZipFile=zip_content
        )
        
        print(f"✅ Lambda function updated successfully")
        print(f"   Function ARN: {response.get('FunctionArn')}")
        print(f"   Last Modified: {response.get('LastModified')}")
        print(f"   Code Size: {response.get('CodeSize')} bytes")
        
        # Wait for update to complete
        print("\n⏳ Waiting for function update to complete...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName='ticket-handler')
        print("✅ Function update completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to deploy Lambda function: {e}")
        return False

def test_upgrade_selection():
    """Test the upgrade selection functionality"""
    print("\n🧪 Testing upgrade selection fix...")
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Test payload for upgrade selection
    test_payload = {
        "httpMethod": "POST",
        "path": "/chat",
        "headers": {
            "Authorization": "Bearer test-token",
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "message": "I want to proceed with the Premium Experience upgrade for 150. Please help me complete this upgrade.",
            "conversationHistory": [
                {"role": "assistant", "content": "Here are your upgrade options..."},
                {"role": "user", "content": "I'd like the Premium Experience upgrade"}
            ],
            "context": {
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "hasTicketInfo": True,
                "selectedUpgrade": {
                    "id": "premium",
                    "name": "Premium Experience",
                    "price": 150,
                    "features": ["Premium seating", "Gourmet meal", "Fast track entry", "Lounge access"]
                }
            }
        })
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName='ticket-handler',
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        if response['StatusCode'] == 200:
            result = json.loads(response['Payload'].read())
            
            if result.get('statusCode') == 200:
                body = json.loads(result.get('body', '{}'))
                response_text = body.get('response', '')
                show_buttons = body.get('showUpgradeButtons', False)
                
                print(f"✅ Test successful!")
                print(f"   Response length: {len(response_text)} characters")
                print(f"   Response preview: {response_text[:150]}...")
                print(f"   Show upgrade buttons: {show_buttons}")
                
                # Check if response indicates upgrade processing (not reverting to greeting)
                if any(phrase in response_text.lower() for phrase in ['perfect choice', 'excellent choice', 'processing', 'confirmation email']):
                    print(f"🎉 UPGRADE SELECTION FIX SUCCESSFUL!")
                    print(f"   Response properly handles upgrade selection")
                    print(f"   No longer reverting to initial greeting")
                    return True
                else:
                    print(f"⚠️  Response may still be using fallback logic")
                    return False
            else:
                print(f"❌ Lambda returned error: {result.get('body')}")
                return False
        else:
            print(f"❌ Lambda invocation failed: Status {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🔧 DEPLOYING UPGRADE SELECTION FIX")
    print("Fixing the issue where upgrade button clicks revert to initial greeting")
    print("=" * 70)
    
    # Create deployment package
    zip_path = create_lambda_package()
    
    # Deploy Lambda function
    if deploy_lambda_function(zip_path):
        # Test the fix
        if test_upgrade_selection():
            print(f"\n🎯 DEPLOYMENT SUCCESSFUL!")
            print(f"   ✅ Lambda function updated with upgrade selection handling")
            print(f"   ✅ Upgrade button clicks now properly processed")
            print(f"   ✅ No more reverting to initial AI greeting")
            print(f"   ✅ Customer chat interface ready for upgrade selections")
        else:
            print(f"\n⚠️  DEPLOYMENT COMPLETED BUT NEEDS VERIFICATION")
            print(f"   Lambda function deployed but test results unclear")
            print(f"   Manual testing recommended")
    else:
        print(f"\n❌ DEPLOYMENT FAILED")
        print(f"   Could not update Lambda function")
    
    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"\n🧹 Cleaned up deployment package")

if __name__ == "__main__":
    main()