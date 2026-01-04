#!/usr/bin/env python3
"""
Debug Data Agent Configuration

This script checks the Data Agent configuration and environment variables
to understand why it's failing to initialize properly.
"""

import os
import boto3
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment_variables():
    """Check all required environment variables for Data Agent"""
    print("🔍 CHECKING DATA AGENT ENVIRONMENT VARIABLES")
    print("=" * 60)
    
    required_vars = [
        'AWS_REGION',
        'DB_CLUSTER_ARN', 
        'DB_SECRET_ARN',
        'DATABASE_NAME',
        'BEDROCK_MODEL_ID'
    ]
    
    optional_vars = [
        'COGNITO_CLIENT_ID',
        'COGNITO_TEST_USER',
        'COGNITO_TEST_PASSWORD'
    ]
    
    print("📋 REQUIRED VARIABLES:")
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if 'ARN' in var or 'SECRET' in var:
                display_value = f"{value[:20]}...{value[-10:]}" if len(value) > 30 else value
            else:
                display_value = value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ❌ {var}: NOT SET")
            missing_required.append(var)
    
    print(f"\n📋 OPTIONAL VARIABLES:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            display_value = f"{value[:10]}..." if len(value) > 10 else value
            print(f"   ✅ {var}: {display_value}")
        else:
            print(f"   ⚠️  {var}: NOT SET")
    
    return missing_required

def check_aurora_cluster():
    """Check if Aurora cluster exists and is accessible"""
    print(f"\n🗄️  CHECKING AURORA CLUSTER ACCESS")
    print("=" * 60)
    
    db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
    if not db_cluster_arn:
        print("❌ DB_CLUSTER_ARN not set - cannot check cluster")
        return False
    
    try:
        rds_client = boto3.client('rds', region_name='us-west-2')
        
        # Extract cluster identifier from ARN
        cluster_id = db_cluster_arn.split(':')[-1]
        
        print(f"🔍 Checking cluster: {cluster_id}")
        
        response = rds_client.describe_db_clusters(
            DBClusterIdentifier=cluster_id
        )
        
        if response['DBClusters']:
            cluster = response['DBClusters'][0]
            print(f"✅ Cluster found: {cluster['DBClusterIdentifier']}")
            print(f"   Status: {cluster['Status']}")
            print(f"   Engine: {cluster['Engine']} {cluster.get('EngineVersion', 'Unknown')}")
            print(f"   Endpoint: {cluster.get('Endpoint', 'Not available')}")
            print(f"   Database Name: {cluster.get('DatabaseName', 'Not set')}")
            
            if cluster['Status'] == 'available':
                print(f"✅ Cluster is available and ready")
                return True
            else:
                print(f"⚠️  Cluster status is not 'available': {cluster['Status']}")
                return False
        else:
            print(f"❌ Cluster not found")
            return False
            
    except Exception as e:
        print(f"❌ Error checking cluster: {e}")
        return False

def check_secrets_manager():
    """Check if database secret exists and is accessible"""
    print(f"\n🔐 CHECKING SECRETS MANAGER ACCESS")
    print("=" * 60)
    
    db_secret_arn = os.getenv('DB_SECRET_ARN')
    if not db_secret_arn:
        print("❌ DB_SECRET_ARN not set - cannot check secret")
        return False
    
    try:
        secrets_client = boto3.client('secretsmanager', region_name='us-west-2')
        
        print(f"🔍 Checking secret: {db_secret_arn}")
        
        response = secrets_client.describe_secret(
            SecretId=db_secret_arn
        )
        
        print(f"✅ Secret found: {response['Name']}")
        print(f"   Description: {response.get('Description', 'No description')}")
        print(f"   Last Changed: {response.get('LastChangedDate', 'Unknown')}")
        
        # Try to get the secret value (without printing it)
        try:
            secret_response = secrets_client.get_secret_value(
                SecretId=db_secret_arn
            )
            secret_data = json.loads(secret_response['SecretString'])
            
            print(f"✅ Secret accessible with keys: {list(secret_data.keys())}")
            
            # Check for required database credentials
            required_keys = ['username', 'password', 'host', 'port', 'dbname']
            missing_keys = [key for key in required_keys if key not in secret_data]
            
            if missing_keys:
                print(f"⚠️  Missing secret keys: {missing_keys}")
                return False
            else:
                print(f"✅ All required secret keys present")
                return True
                
        except Exception as e:
            print(f"❌ Cannot access secret value: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking secret: {e}")
        return False

def test_rds_data_api():
    """Test RDS Data API connectivity"""
    print(f"\n🔌 TESTING RDS DATA API CONNECTIVITY")
    print("=" * 60)
    
    db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
    db_secret_arn = os.getenv('DB_SECRET_ARN')
    database_name = os.getenv('DATABASE_NAME', 'ticket_system')
    
    if not db_cluster_arn or not db_secret_arn:
        print("❌ Missing required ARNs for RDS Data API test")
        return False
    
    try:
        rds_data = boto3.client('rds-data', region_name='us-west-2')
        
        print(f"🔍 Testing connection to database: {database_name}")
        
        # Simple test query
        response = rds_data.execute_statement(
            resourceArn=db_cluster_arn,
            secretArn=db_secret_arn,
            database=database_name,
            sql="SELECT 1 as test_value;"
        )
        
        if response['records']:
            test_value = response['records'][0][0]['longValue']
            print(f"✅ RDS Data API working - test query returned: {test_value}")
            
            # Test table existence
            table_check_sql = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('customers', 'tickets', 'upgrade_orders');
            """
            
            table_response = rds_data.execute_statement(
                resourceArn=db_cluster_arn,
                secretArn=db_secret_arn,
                database=database_name,
                sql=table_check_sql
            )
            
            tables = [record[0]['stringValue'] for record in table_response['records']]
            print(f"✅ Found tables: {tables}")
            
            required_tables = ['customers', 'tickets', 'upgrade_orders']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"⚠️  Missing tables: {missing_tables}")
                return False
            else:
                print(f"✅ All required tables present")
                return True
        else:
            print(f"❌ RDS Data API test query failed - no results")
            return False
            
    except Exception as e:
        print(f"❌ RDS Data API test failed: {e}")
        return False

def check_bedrock_access():
    """Check Bedrock model access"""
    print(f"\n🤖 CHECKING BEDROCK MODEL ACCESS")
    print("=" * 60)
    
    bedrock_model_id = os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
    
    try:
        bedrock_runtime = boto3.client('bedrock-runtime', region_name='us-west-2')
        
        print(f"🔍 Testing model: {bedrock_model_id}")
        
        # Simple test request
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": "Hello, this is a test. Please respond with 'Test successful'."}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 50,
                "temperature": 0.1
            }
        }
        
        response = bedrock_runtime.invoke_model(
            modelId=bedrock_model_id,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        content_list = response_body.get('output', {}).get('message', {}).get('content', [])
        text_block = next((item for item in content_list if "text" in item), None)
        
        if text_block:
            response_text = text_block.get('text', 'No response')
            print(f"✅ Bedrock model accessible - response: {response_text}")
            return True
        else:
            print(f"❌ Bedrock model response format unexpected")
            return False
            
    except Exception as e:
        print(f"❌ Bedrock model test failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    print("🔍 DATA AGENT CONFIGURATION DIAGNOSTICS")
    print("Checking all components required for Data Agent operation")
    print("=" * 70)
    
    # Check environment variables
    missing_vars = check_environment_variables()
    
    # Check Aurora cluster
    cluster_ok = check_aurora_cluster()
    
    # Check Secrets Manager
    secrets_ok = check_secrets_manager()
    
    # Test RDS Data API
    rds_api_ok = test_rds_data_api()
    
    # Check Bedrock access
    bedrock_ok = check_bedrock_access()
    
    # Final assessment
    print(f"\n🎯 FINAL DIAGNOSTIC RESULTS")
    print("=" * 60)
    
    all_checks = [
        ("Environment Variables", len(missing_vars) == 0),
        ("Aurora Cluster", cluster_ok),
        ("Secrets Manager", secrets_ok),
        ("RDS Data API", rds_api_ok),
        ("Bedrock Model", bedrock_ok)
    ]
    
    passed_checks = sum(1 for _, status in all_checks if status)
    total_checks = len(all_checks)
    
    for check_name, status in all_checks:
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {check_name}")
    
    print(f"\n📊 OVERALL STATUS: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print(f"🎉 DATA AGENT READY: All components configured correctly")
        print(f"   The Data Agent should be able to access Aurora database")
        print(f"   The 'llm_reason' error should be resolved")
    elif passed_checks >= 3:
        print(f"⚠️  DATA AGENT PARTIALLY READY: Most components working")
        print(f"   Some issues need to be resolved for full functionality")
    else:
        print(f"🚨 DATA AGENT NOT READY: Critical configuration issues")
        print(f"   Multiple components need configuration before Data Agent can work")
    
    if missing_vars:
        print(f"\n🔧 NEXT STEPS:")
        print(f"   1. Set missing environment variables: {', '.join(missing_vars)}")
        print(f"   2. Ensure Aurora cluster is running and accessible")
        print(f"   3. Verify database schema is properly set up")
        print(f"   4. Test Data Agent again after configuration")

if __name__ == "__main__":
    main()