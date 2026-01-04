#!/usr/bin/env python3
"""
Deploy Step 1 Validation Fix

This script deploys the fix for Step 1 validation issue where "my ticket" 
was triggering validation logic without proper ticket context.
"""

import boto3
import json
import zipfile
import os

def create_lambda_package():
    """Create deployment package for Lambda function"""
    print("📦 Creating Lambda deployment package...")
    
    # Create zip file
    zip_path = "ticket-handler-step1-validation-fix.zip"
    
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

def main():
    """Main deployment function"""
    print("🔧 DEPLOYING STEP 1 VALIDATION FIX")
    print("Fixing: 'my ticket' triggering validation without proper ticket context")
    print("Change: Only trigger validation MCP tools when hasTicketInfo is true")
    print("=" * 70)
    
    # Create deployment package
    zip_path = create_lambda_package()
    
    # Deploy Lambda function
    if deploy_lambda_function(zip_path):
        print(f"\n🎯 DEPLOYMENT SUCCESSFUL!")
        print(f"   ✅ Lambda function updated with Step 1 validation fix")
        print(f"   ✅ 'I want to upgrade my ticket' should now ask for ticket ID")
        print(f"   ✅ Only triggers validation when ticket context exists")
    else:
        print(f"\n❌ DEPLOYMENT FAILED")
        print(f"   Could not update Lambda function")
    
    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"\n🧹 Cleaned up deployment package")

if __name__ == "__main__":
    main()