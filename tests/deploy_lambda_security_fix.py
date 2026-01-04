#!/usr/bin/env python3
"""
Deploy Lambda Security Fix for Invalid Ticket Validation

This script deploys the Lambda function with the security fix that validates
ticket IDs using a whitelist approach before processing any upgrade requests.
"""

import boto3
import json
import os
import zipfile
import tempfile
import shutil
from datetime import datetime

def create_deployment_package():
    """Create deployment package with the security fix"""
    print("📦 Creating Lambda deployment package with security fix...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy Lambda files
        lambda_files = [
            "backend/lambda/ticket_handler.py",
            "backend/lambda/agentcore_client.py", 
            "backend/lambda/auth_handler.py"
        ]
        
        for file_path in lambda_files:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                shutil.copy2(file_path, os.path.join(temp_dir, filename))
                print(f"✅ Copied {filename}")
        
        # Copy model files
        model_files = [
            "models/customer.py",
            "models/ticket.py", 
            "models/upgrade_order.py",
            "models/base.py"
        ]
        
        models_dir = os.path.join(temp_dir, "models")
        os.makedirs(models_dir, exist_ok=True)
        
        for file_path in model_files:
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                shutil.copy2(file_path, os.path.join(models_dir, filename))
                print(f"✅ Copied models/{filename}")
        
        # Create __init__.py files
        with open(os.path.join(models_dir, "__init__.py"), "w") as f:
            f.write("")
        
        # Create zip file
        zip_path = "ticket-handler-lambda-security-fix.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
                    print(f"📁 Added to zip: {arcname}")
        
        print(f"✅ Created deployment package: {zip_path}")
        return zip_path

def deploy_lambda_function(zip_path):
    """Deploy the Lambda function with security fix"""
    print("🚀 Deploying Lambda function with security fix...")
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        # Read the zip file
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        # Update the Lambda function
        response = lambda_client.update_function_code(
            FunctionName='ticket-handler',
            ZipFile=zip_content
        )
        
        print(f"✅ Lambda function updated successfully")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Last Modified: {response['LastModified']}")
        print(f"   Code Size: {response['CodeSize']} bytes")
        
        # Wait for the update to complete
        print("⏳ Waiting for deployment to complete...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName='ticket-handler')
        
        print("✅ Deployment completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to deploy Lambda function: {e}")
        return False

def main():
    """Main deployment function"""
    print("🔒 DEPLOYING LAMBDA SECURITY FIX FOR INVALID TICKET VALIDATION")
    print("=" * 70)
    print("This deployment adds whitelist-based ticket validation to prevent")
    print("invalid ticket IDs from being processed and showing upgrade options.")
    print("=" * 70)
    
    # Create deployment package
    zip_path = create_deployment_package()
    if not zip_path:
        print("❌ Failed to create deployment package")
        return
    
    # Deploy to Lambda
    if deploy_lambda_function(zip_path):
        print("\n🎯 LAMBDA SECURITY FIX DEPLOYMENT SUCCESSFUL!")
        print("✅ Invalid tickets will now be rejected at Lambda level")
        print("✅ Whitelist-based validation implemented")
        print("✅ No upgrade options shown for invalid tickets")
        print("\n🧪 Run test_invalid_ticket_validation.py to verify the fix")
    else:
        print("\n❌ DEPLOYMENT FAILED")
    
    # Clean up
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"🧹 Cleaned up deployment package: {zip_path}")
    
    print(f"\n📊 DEPLOYMENT SUMMARY:")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    print(f"   Function: ticket-handler")
    print(f"   Fix: Lambda-level ticket validation security")
    print(f"   Method: Whitelist-based validation")

if __name__ == "__main__":
    main()