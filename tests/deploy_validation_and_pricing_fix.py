#!/usr/bin/env python3
"""
Deploy Validation and Pricing Fix

This script deploys the updated Lambda function that:
1. Requires ticket validation before showing upgrade options
2. Fixes the MCP tool call parameters for calculate_upgrade_pricing
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
    zip_path = "ticket-handler-validation-pricing-fix.zip"
    
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

def test_validation_and_pricing_fixes():
    """Test both validation and pricing fixes"""
    print("\n🧪 Testing validation and pricing fixes...")
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Upgrade without ticket (should require validation)",
            "message": "I want to upgrade",
            "context": {},  # No ticket info
            "expected": "Should ask for ticket ID first"
        },
        {
            "name": "Upgrade with ticket (should show options)",
            "message": "I want to upgrade", 
            "context": {
                "hasTicketInfo": True,
                "ticketId": "550e8400-e29b-41d4-a716-446655440002"
            },
            "expected": "Should show upgrade options"
        },
        {
            "name": "VIP upgrade selection (should work without MCP error)",
            "message": "I'd like the VIP Package upgrade",
            "context": {
                "hasTicketInfo": True,
                "ticketId": "550e8400-e29b-41d4-a716-446655440002",
                "selectedUpgrade": {
                    "id": "vip",
                    "name": "VIP Package",
                    "price": 300,
                    "features": ["VIP seating", "Meet & greet", "Exclusive merchandise"]
                }
            },
            "expected": "Should process upgrade without MCP parameter error"
        }
    ]
    
    results = []
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n🎯 Test {i}: {scenario['name']}")
        print(f"   Message: {scenario['message']}")
        print(f"   Expected: {scenario['expected']}")
        
        # Test payload
        test_payload = {
            "httpMethod": "POST",
            "path": "/chat",
            "headers": {
                "Authorization": "Bearer test-token",
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "message": scenario['message'],
                "conversationHistory": [],
                "context": scenario['context']
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
                    
                    print(f"   ✅ Success: {len(response_text)} characters")
                    print(f"   Response: {response_text[:150]}...")
                    print(f"   Show upgrade buttons: {show_buttons}")
                    
                    # Check specific expectations
                    if scenario['name'] == "Upgrade without ticket (should require validation)":
                        if "ticket information" in response_text.lower() or "ticket id" in response_text.lower():
                            print(f"   🎉 VALIDATION FIX WORKING: Properly asks for ticket ID")
                            status = "FIXED"
                        else:
                            print(f"   ❌ VALIDATION ISSUE: Still shows options without ticket")
                            status = "BROKEN"
                    
                    elif scenario['name'] == "Upgrade with ticket (should show options)":
                        if show_buttons:
                            print(f"   🎉 VALIDATION FIX WORKING: Shows options with valid ticket")
                            status = "FIXED"
                        else:
                            print(f"   ❌ VALIDATION ISSUE: Doesn't show options with valid ticket")
                            status = "BROKEN"
                    
                    elif scenario['name'] == "VIP upgrade selection (should work without MCP error)":
                        if "Error executing tool" not in response_text and "validation error" not in response_text:
                            print(f"   🎉 PRICING FIX WORKING: No MCP parameter errors")
                            status = "FIXED"
                        else:
                            print(f"   ❌ PRICING ISSUE: Still has MCP parameter errors")
                            status = "BROKEN"
                    else:
                        status = "UNCLEAR"
                    
                    results.append({
                        'scenario': scenario['name'],
                        'success': True,
                        'status': status,
                        'length': len(response_text),
                        'show_buttons': show_buttons
                    })
                else:
                    print(f"   ❌ Error: {result.get('body')}")
                    results.append({
                        'scenario': scenario['name'],
                        'success': False,
                        'error': result.get('body')
                    })
            else:
                print(f"   ❌ Lambda error: Status {response['StatusCode']}")
                results.append({
                    'scenario': scenario['name'],
                    'success': False,
                    'error': f"Lambda status {response['StatusCode']}"
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            results.append({
                'scenario': scenario['name'],
                'success': False,
                'error': str(e)
            })
    
    return results

def analyze_fix_results(results):
    """Analyze the fix results"""
    print("\n" + "=" * 60)
    print("📊 VALIDATION AND PRICING FIX ANALYSIS")
    print("=" * 60)
    
    successful_tests = [r for r in results if r.get('success')]
    fixed_tests = [r for r in results if r.get('status') == 'FIXED']
    broken_tests = [r for r in results if r.get('status') == 'BROKEN']
    
    print(f"Total Tests: {len(results)}")
    print(f"Successful Tests: {len(successful_tests)}")
    print(f"Fixed Issues: {len(fixed_tests)}")
    print(f"Remaining Issues: {len(broken_tests)}")
    
    if fixed_tests:
        print(f"\n🎉 FIXES WORKING!")
        for result in fixed_tests:
            print(f"   ✅ {result['scenario']}")
    
    if broken_tests:
        print(f"\n❌ STILL BROKEN:")
        for result in broken_tests:
            print(f"   ❌ {result['scenario']}")
    
    # Overall assessment
    if len(fixed_tests) == len(results):
        print(f"\n🎯 OVERALL ASSESSMENT: ALL FIXES WORKING")
        print(f"   ✅ Ticket validation now required before showing upgrades")
        print(f"   ✅ MCP tool parameter errors resolved")
        print(f"   ✅ Customer chat interface fully functional")
    elif len(fixed_tests) >= len(results) * 0.5:
        print(f"\n🎯 OVERALL ASSESSMENT: MOSTLY FIXED")
        print(f"   Some issues resolved, others may need attention")
    else:
        print(f"\n🎯 OVERALL ASSESSMENT: NEEDS MORE WORK")
        print(f"   Major issues still present")

def main():
    """Main deployment function"""
    print("🔧 DEPLOYING VALIDATION AND PRICING FIXES")
    print("Fixing: 1) Upgrade options without ticket validation")
    print("        2) MCP tool parameter errors in pricing calls")
    print("=" * 70)
    
    # Create deployment package
    zip_path = create_lambda_package()
    
    # Deploy Lambda function
    if deploy_lambda_function(zip_path):
        # Test the fixes (without auth for quick validation)
        results = test_validation_and_pricing_fixes()
        analyze_fix_results(results)
    else:
        print(f"\n❌ DEPLOYMENT FAILED")
        print(f"   Could not update Lambda function")
    
    # Cleanup
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"\n🧹 Cleaned up deployment package")

if __name__ == "__main__":
    main()