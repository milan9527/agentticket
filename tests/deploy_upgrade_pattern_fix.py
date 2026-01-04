#!/usr/bin/env python3
"""
Deploy Upgrade Pattern Fix

This script deploys the fix for upgrade selection pattern matching.
"""

import boto3
import json
import zipfile
import os

def create_lambda_package():
    """Create deployment package for Lambda function"""
    print("📦 Creating Lambda deployment package...")
    
    # Create zip file
    zip_path = "ticket-handler-upgrade-pattern-fix.zip"
    
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
    print("🔧 DEPLOYING UPGRADE PATTERN FIX")
    print("Fixing upgrade selection pattern to distinguish between:")
    print("  - General inquiry: 'I want to upgrade'")
    print("  - Specific selection: 'I want the Premium Experience upgrade'")
    print("=" * 70)
    
    # Create deployment package
    zip_path = create_lambda_package()
    
    # Deploy Lambda function
    if deploy_lambda_function(zip_path):
        print(f"\n🎯 DEPLOYMENT SUCCESSFUL!")
        print(f"   ✅ Lambda function updated with improved upgrade pattern matching")
        print(f"   ✅ General upgrade inquiries should now go to validation logic")
        print(f"   ✅ Specific upgrade selections should still work correctly")
    else:
        print(f"\n❌ DEPLOYMENT FAILED")
        print(f"   Could not update Lambda function")
    
    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"\n🧹 Cleaned up deployment package")

if __name__ == "__main__":
    main()