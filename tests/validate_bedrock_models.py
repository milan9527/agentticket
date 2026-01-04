#!/usr/bin/env python3
"""
Validate Amazon Bedrock model availability in us-west-2
Check Nova Pro model access and inference profiles
"""

import boto3
import json
import os
from botocore.exceptions import ClientError

def validate_bedrock_models():
    """Validate Bedrock model availability and access"""
    region = 'us-west-2'
    
    print(f"🔍 Validating Amazon Bedrock models in {region}")
    print("=" * 60)
    
    try:
        bedrock = boto3.client('bedrock', region_name=region)
        bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
        
        # List available foundation models
        print("📋 Listing available foundation models...")
        response = bedrock.list_foundation_models()
        
        nova_models = []
        claude_models = []
        other_models = []
        
        for model in response['modelSummaries']:
            model_id = model['modelId']
            model_name = model['modelName']
            provider = model['providerName']
            
            if 'nova' in model_id.lower():
                nova_models.append({
                    'id': model_id,
                    'name': model_name,
                    'provider': provider,
                    'status': model.get('modelLifecycle', {}).get('status', 'ACTIVE')
                })
            elif 'claude' in model_id.lower():
                claude_models.append({
                    'id': model_id,
                    'name': model_name,
                    'provider': provider,
                    'status': model.get('modelLifecycle', {}).get('status', 'ACTIVE')
                })
            else:
                other_models.append({
                    'id': model_id,
                    'name': model_name,
                    'provider': provider
                })
        
        # Display Nova models
        print(f"\n🚀 Amazon Nova Models ({len(nova_models)} found):")
        for model in nova_models:
            status_icon = "✅" if model['status'] == 'ACTIVE' else "⚠️"
            print(f"  {status_icon} {model['id']}")
            print(f"     Name: {model['name']}")
            print(f"     Provider: {model['provider']}")
            print(f"     Status: {model['status']}")
        
        # Display Claude models as backup
        print(f"\n🤖 Anthropic Claude Models ({len(claude_models)} found):")
        for model in claude_models[:3]:  # Show first 3
            status_icon = "✅" if model['status'] == 'ACTIVE' else "⚠️"
            print(f"  {status_icon} {model['id']}")
            print(f"     Name: {model['name']}")
        
        # Check for inference profiles
        print(f"\n🔄 Checking inference profiles...")
        try:
            profiles_response = bedrock.list_inference_profiles()
            inference_profiles = profiles_response.get('inferenceProfileSummaries', [])
            
            nova_profiles = [p for p in inference_profiles if 'nova' in p['inferenceProfileId'].lower()]
            
            if nova_profiles:
                print(f"📊 Nova Inference Profiles ({len(nova_profiles)} found):")
                for profile in nova_profiles:
                    print(f"  ✅ {profile['inferenceProfileId']}")
                    print(f"     Name: {profile.get('inferenceProfileName', 'N/A')}")
                    print(f"     Status: {profile.get('status', 'ACTIVE')}")
            else:
                print("  ℹ️  No Nova inference profiles found")
                
        except Exception as e:
            print(f"  ⚠️  Could not list inference profiles: {e}")
        
        # Test model access
        print(f"\n🧪 Testing model access...")
        
        # Try Nova Pro inference profile first
        nova_pro_profiles = [p for p in inference_profiles if 'nova-pro' in p['inferenceProfileId'].lower()]
        
        if nova_pro_profiles:
            test_profile = nova_pro_profiles[0]['inferenceProfileId']
            print(f"  Testing Nova Pro inference profile: {test_profile}")
            
            try:
                # Test with correct Nova Pro API format
                test_response = bedrock_runtime.invoke_model(
                    modelId=test_profile,
                    body=json.dumps({
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "text": "Hello, this is a test. Please respond with 'Nova Pro access confirmed.'"
                                    }
                                ]
                            }
                        ],
                        "inferenceConfig": {
                            "maxTokens": 50,
                            "temperature": 0.1
                        }
                    })
                )
                
                response_body = json.loads(test_response['body'].read())
                # Extract response text from Nova Pro format
                content_list = response_body.get('output', {}).get('message', {}).get('content', [])
                text_block = next((item for item in content_list if "text" in item), None)
                response_text = text_block.get('text', 'No response') if text_block else 'No text found'
                
                print(f"  ✅ Nova Pro inference profile access confirmed!")
                print(f"  📝 Response: {response_text[:100]}...")
                
                return {
                    'model_id': test_profile,
                    'model_name': 'Nova Pro (Inference Profile)',
                    'access_confirmed': True,
                    'is_inference_profile': True,
                    'inference_profiles': nova_profiles
                }
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                print(f"  ❌ Error testing Nova Pro profile: {error_code}")
                print(f"  Details: {e}")
        
        # Try direct Nova Pro model
        nova_pro_models = [m for m in nova_models if 'pro' in m['name'].lower() and m['status'] == 'ACTIVE']
        
        if nova_pro_models:
            test_model = nova_pro_models[0]['id']
            print(f"  Testing direct Nova Pro model: {test_model}")
            
            try:
                # Test with correct Nova Pro API format
                test_response = bedrock_runtime.invoke_model(
                    modelId=test_model,
                    body=json.dumps({
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "text": "Hello, this is a test. Please respond with 'Model access confirmed.'"
                                    }
                                ]
                            }
                        ],
                        "inferenceConfig": {
                            "maxTokens": 50,
                            "temperature": 0.1
                        }
                    })
                )
                
                response_body = json.loads(test_response['body'].read())
                # Extract response text from Nova Pro format
                content_list = response_body.get('output', {}).get('message', {}).get('content', [])
                text_block = next((item for item in content_list if "text" in item), None)
                response_text = text_block.get('text', 'Model access confirmed') if text_block else 'No text found'
                
                print(f"  ✅ Direct model access confirmed!")
                print(f"  📝 Response: {response_text[:100]}...")
                
                return {
                    'model_id': test_model,
                    'model_name': nova_pro_models[0]['name'],
                    'access_confirmed': True,
                    'inference_profiles': nova_profiles
                }
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'AccessDeniedException':
                    print(f"  ❌ Access denied to {test_model}")
                    print(f"  💡 You may need to request model access in the Bedrock console")
                elif error_code == 'ValidationException':
                    print(f"  ⚠️  Model format validation error")
                else:
                    print(f"  ❌ Error testing model: {e}")
        
        # Try Claude inference profile as fallback
        claude_profiles = [p for p in inference_profiles if 'claude' in p['inferenceProfileId'].lower()]
        
        if claude_profiles:
            claude_profile = claude_profiles[0]['inferenceProfileId']
            print(f"  Testing Claude inference profile as fallback: {claude_profile}")
            
            try:
                # Claude uses different API format - use Anthropic format
                test_response = bedrock_runtime.invoke_model(
                    modelId=claude_profile,
                    body=json.dumps({
                        "messages": [
                            {
                                "role": "user", 
                                "content": "Hello, this is a test. Please respond with 'Claude access confirmed.'"
                            }
                        ],
                        "max_tokens": 50,
                        "anthropic_version": "bedrock-2023-05-31"
                    })
                )
                
                response_body = json.loads(test_response['body'].read())
                print(f"  ✅ Claude inference profile access confirmed!")
                
                return {
                    'model_id': claude_profile,
                    'model_name': 'Claude (Inference Profile)',
                    'access_confirmed': True,
                    'is_fallback': True,
                    'is_inference_profile': True
                }
                
            except Exception as e:
                print(f"  ❌ Error testing Claude profile: {e}")
        
        return {
            'model_id': None,
            'access_confirmed': False,
            'error': 'No accessible models found'
        }
        
    except Exception as e:
        print(f"❌ Error connecting to Bedrock: {e}")
        return {
            'model_id': None,
            'access_confirmed': False,
            'error': str(e)
        }

def update_env_file(model_info):
    """Update .env file with validated model information"""
    print(f"\n📝 Updating .env file with model configuration...")
    
    # Read current .env file
    env_lines = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_lines = f.readlines()
    
    # Update or add model configuration
    model_config_added = False
    updated_lines = []
    
    for line in env_lines:
        if line.startswith('BEDROCK_MODEL_ID='):
            updated_lines.append(f"BEDROCK_MODEL_ID={model_info['model_id']}\n")
            model_config_added = True
        elif line.startswith('BEDROCK_MODEL_NAME='):
            updated_lines.append(f"BEDROCK_MODEL_NAME={model_info['model_name']}\n")
        elif line.startswith('BEDROCK_REGION='):
            updated_lines.append(f"BEDROCK_REGION=us-west-2\n")
        else:
            updated_lines.append(line)
    
    # Add model configuration if not present
    if not model_config_added:
        updated_lines.append(f"\n# Amazon Bedrock Model Configuration\n")
        updated_lines.append(f"BEDROCK_MODEL_ID={model_info['model_id']}\n")
        updated_lines.append(f"BEDROCK_MODEL_NAME={model_info['model_name']}\n")
        updated_lines.append(f"BEDROCK_REGION=us-west-2\n")
        
        if model_info.get('is_inference_profile'):
            updated_lines.append(f"# Using inference profile for optimized access\n")
        
        if model_info.get('is_fallback'):
            updated_lines.append(f"# Note: Using Claude as fallback - Nova Pro access may need to be requested\n")
    
    # Write updated .env file
    with open('.env', 'w') as f:
        f.writelines(updated_lines)
    
    print(f"✅ Updated .env file with:")
    print(f"   BEDROCK_MODEL_ID={model_info['model_id']}")
    print(f"   BEDROCK_MODEL_NAME={model_info['model_name']}")
    print(f"   BEDROCK_REGION=us-west-2")

def main():
    """Main validation function"""
    print("🚀 Amazon Bedrock Model Validation")
    print("Checking Nova Pro availability in us-west-2")
    
    model_info = validate_bedrock_models()
    
    print("\n" + "=" * 60)
    
    if model_info['access_confirmed']:
        print("✅ Bedrock model validation successful!")
        
        if model_info.get('is_fallback'):
            print("⚠️  Using Claude as fallback model")
            print("💡 Consider requesting Nova Pro access in AWS Bedrock console")
        else:
            print("🎉 Nova Pro model access confirmed!")
        
        update_env_file(model_info)
        
        print(f"\n📋 Next steps:")
        print(f"1. Review model configuration in .env file")
        print(f"2. Proceed with AgentCore development (Task 3.1)")
        print(f"3. Test agents with the configured model")
        
    else:
        print("❌ Bedrock model validation failed!")
        print(f"Error: {model_info.get('error', 'Unknown error')}")
        print(f"\n🔧 Troubleshooting steps:")
        print(f"1. Check AWS credentials and permissions")
        print(f"2. Request model access in AWS Bedrock console")
        print(f"3. Verify region availability (us-west-2)")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())