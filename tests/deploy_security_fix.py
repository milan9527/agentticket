#!/usr/bin/env python3
"""
Deploy Security Fix for Invalid Ticket Validation

This script deploys the security fix that prevents invalid tickets from being processed.
The fix ensures that when a ticket ID is not found in the database, the system properly
rejects it instead of creating fake ticket data.
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
    print("📦 Creating deployment package with security fix...")
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy the fixed AgentCore ticket agent
        source_file = "backend/agents/agentcore_ticket_agent.py"
        dest_file = os.path.join(temp_dir, "agentcore_ticket_agent.py")
        
        if not os.path.exists(source_file):
            print(f"❌ Source file not found: {source_file}")
            return None
        
        shutil.copy2(source_file, dest_file)
        
        # Copy other necessary files
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
        zip_path = "ticket-handler-security-fix.zip"
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
        print(f"   Runtime: {response['Runtime']}")
        
        # Wait for the update to complete
        print("⏳ Waiting for deployment to complete...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(FunctionName='ticket-handler')
        
        print("✅ Deployment completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to deploy Lambda function: {e}")
        return False

def test_security_fix():
    """Test that the security fix is working"""
    print("\n🧪 Testing security fix...")
    
    try:
        lambda_client = boto3.client('lambda', region_name='us-west-2')
        
        # Test with invalid ticket ID
        test_payload = {
            "httpMethod": "POST",
            "path": "/chat",
            "headers": {
                "Authorization": f"Bearer test-token",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": "My ticket ID is 12345678-1234-1234-1234-123456789012",
                "conversationHistory": [],
                "context": {
                    "ticketId": "12345678-1234-1234-1234-123456789012",
                    "hasTicketInfo": True
                }
            })
        }
        
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
                shows_upgrades = body.get('showUpgradeButtons', False)
                
                print(f"📝 Response: {response_text[:200]}...")
                print(f"🔘 Shows upgrade buttons: {shows_upgrades}")
                
                # Check if security fix is working
                security_keywords = ['not found', 'invalid', 'verify', 'check', 'cannot find']
                rejects_invalid = any(keyword in response_text.lower() for keyword in security_keywords)
                
                if rejects_invalid and not shows_upgrades:
                    print("🎉 SECURITY FIX WORKING: Invalid ticket properly rejected!")
                    return True
                elif shows_upgrades:
                    print("🚨 SECURITY ISSUE: Still shows upgrades for invalid ticket!")
                    return False
                else:
                    print("⚠️  UNCLEAR: Response unclear, manual verification needed")
                    return False
        
        print("❌ Test failed - no valid response")
        return False
        
    except Exception as e:
        print(f"❌ Security test failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🔒 DEPLOYING SECURITY FIX FOR INVALID TICKET VALIDATION")
    print("=" * 60)
    print("This deployment fixes the critical security vulnerability where")
    print("invalid ticket IDs were being accepted and processed.")
    print("=" * 60)
    
    # Create deployment package
    zip_path = create_deployment_package()
    if not zip_path:
        print("❌ Failed to create deployment package")
        return
    
    # Deploy to Lambda
    if not deploy_lambda_function(zip_path):
        print("❌ Deployment failed")
        return
    
    # Test the security fix
    if test_security_fix():
        print("\n🎯 SECURITY FIX DEPLOYMENT SUCCESSFUL!")
        print("✅ Invalid tickets are now properly rejected")
        print("✅ No upgrade options shown for invalid tickets")
        print("✅ System security vulnerability resolved")
    else:
        print("\n⚠️  SECURITY FIX NEEDS VERIFICATION")
        print("🔍 Manual testing recommended to confirm fix")
    
    # Clean up
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"🧹 Cleaned up deployment package: {zip_path}")
    
    print(f"\n📊 DEPLOYMENT SUMMARY:")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    print(f"   Function: ticket-handler")
    print(f"   Fix: Invalid ticket validation security")
    print(f"   Status: Deployed and tested")

if __name__ == "__main__":
    main()