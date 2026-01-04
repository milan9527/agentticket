#!/usr/bin/env python3
"""
Fix API Gateway Routing

This script updates the API Gateway to route /chat requests to the correct Lambda function.
"""

import boto3
import json

def fix_api_gateway_routing():
    """Fix the API Gateway routing for the chat endpoint"""
    print("🔧 FIXING API GATEWAY ROUTING")
    print("=" * 50)
    
    # API Gateway configuration
    api_id = "qzd3j8cmn2"
    region = "us-west-2"
    account_id = "632930644527"
    
    # Create API Gateway client
    apigateway = boto3.client('apigateway', region_name=region)
    
    print(f"🌐 API Gateway ID: {api_id}")
    print(f"📍 Region: {region}")
    
    # Get current integration
    print(f"\n🔍 Checking current /chat integration...")
    
    try:
        current_integration = apigateway.get_integration(
            restApiId=api_id,
            resourceId='52xzbm',  # /chat resource ID
            httpMethod='POST'
        )
        
        current_uri = current_integration['uri']
        print(f"📋 Current URI: {current_uri}")
        
        if 'chat-handler' in current_uri:
            print("❌ Found the issue: /chat is pointing to old chat-handler function")
            print("✅ Need to update to point to ticket-handler function")
        else:
            print("✅ Integration looks correct")
            return True
            
    except Exception as e:
        print(f"❌ Error checking current integration: {e}")
        return False
    
    # Update integration to point to ticket-handler
    print(f"\n🔄 Updating /chat integration to use ticket-handler...")
    
    new_uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/arn:aws:lambda:{region}:{account_id}:function:ticket-handler/invocations"
    
    try:
        # Update the integration
        response = apigateway.put_integration(
            restApiId=api_id,
            resourceId='52xzbm',
            httpMethod='POST',
            type='AWS_PROXY',
            integrationHttpMethod='POST',
            uri=new_uri
        )
        
        print(f"✅ Integration updated successfully")
        print(f"📋 New URI: {response['uri']}")
        
        # Deploy the changes
        print(f"\n🚀 Deploying API Gateway changes...")
        
        deployment_response = apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod',
            description='Updated /chat endpoint to use ticket-handler function'
        )
        
        print(f"✅ Deployment successful")
        print(f"📋 Deployment ID: {deployment_response['id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating integration: {e}")
        return False

def verify_fix():
    """Verify the fix by checking the integration"""
    print(f"\n🧪 VERIFYING THE FIX")
    print("=" * 30)
    
    apigateway = boto3.client('apigateway', region_name='us-west-2')
    
    try:
        integration = apigateway.get_integration(
            restApiId='qzd3j8cmn2',
            resourceId='52xzbm',
            httpMethod='POST'
        )
        
        uri = integration['uri']
        print(f"📋 Current URI: {uri}")
        
        if 'ticket-handler' in uri:
            print("✅ SUCCESS: /chat now points to ticket-handler")
            return True
        else:
            print("❌ ISSUE: /chat still points to wrong function")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying fix: {e}")
        return False

if __name__ == "__main__":
    print("🎯 API GATEWAY CHAT ROUTING FIX")
    print("=" * 60)
    print("Issue: Frontend /chat calls are going to old chat-handler function")
    print("Solution: Update API Gateway to route /chat to ticket-handler function")
    print()
    
    # Fix the routing
    success = fix_api_gateway_routing()
    
    if success:
        # Verify the fix
        verified = verify_fix()
        
        if verified:
            print(f"\n🎉 API GATEWAY ROUTING FIXED!")
            print("=" * 40)
            print("✅ /chat endpoint now routes to ticket-handler")
            print("✅ Frontend will now get correct responses")
            print("✅ No more validation error messages")
            print()
            print("🧪 Test the fix:")
            print("   1. Refresh your browser")
            print("   2. Try the chat interface again")
            print("   3. Should see success messages now")
        else:
            print(f"\n⚠️ FIX APPLIED BUT VERIFICATION FAILED")
            print("Please check the API Gateway configuration manually")
    else:
        print(f"\n❌ FAILED TO FIX API GATEWAY ROUTING")
        print("Please check the error messages above")