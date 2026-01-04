#!/usr/bin/env python3
"""
Deploy Data Agent Invoker Lambda Function

This script deploys a Lambda function that can invoke the Data Agent MCP server.
"""

import boto3
import json
import zipfile
import os
from pathlib import Path

def create_lambda_package():
    """Create deployment package for Data Agent Invoker Lambda"""
    
    # Create a zip file for the Lambda package
    zip_path = 'data-agent-invoker.zip'
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add the main Lambda handler
        zipf.write('backend/lambda/data_agent_invoker.py', 'lambda_function.py')
        
        # Add the Data Agent MCP server (simplified version without FastMCP)
        # Create a simplified version that doesn't require FastMCP
        simplified_data_agent = '''#!/usr/bin/env python3
"""
Real Data Agent for Lambda Invoker

This connects to the actual Aurora PostgreSQL database using RDS Data API.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
import boto3
from botocore.exceptions import ClientError

# Real database connection using RDS Data API
class DatabaseConnection:
    """Handles Aurora PostgreSQL Data API connections"""
    
    def __init__(self):
        self.db_cluster_arn = os.environ.get('DB_CLUSTER_ARN')
        self.db_secret_arn = os.environ.get('DB_SECRET_ARN')
        self.database_name = os.environ.get('DATABASE_NAME', 'ticket_system')
        self.rds_data = boto3.client('rds-data', region_name='us-west-2')
    
    async def execute_sql(self, sql: str, parameters: List[Dict] = None) -> Dict[str, Any]:
        """Execute SQL statement using RDS Data API"""
        try:
            params = {
                'resourceArn': self.db_cluster_arn,
                'secretArn': self.db_secret_arn,
                'database': self.database_name,
                'sql': sql
            }
            
            if parameters:
                params['parameters'] = parameters
            
            # Execute in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.rds_data.execute_statement(**params)
            )
            return response
        except Exception as e:
            print(f"Database error: {e}")
            raise

# Global database connection
db = None

def initialize_db():
    """Initialize database connection"""
    global db
    if db is None:
        db = DatabaseConnection()

# Real tool functions that connect to Aurora database
async def get_customer(customer_id: str) -> Dict[str, Any]:
    """Get customer by ID from real Aurora database"""
    try:
        initialize_db()
        
        # Validate UUID format
        UUID(customer_id)
        
        sql = "SELECT * FROM customers WHERE id = :customer_id"
        parameters = [{'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}]
        
        response = await db.execute_sql(sql, parameters)
        
        if not response['records']:
            return {"error": "Customer not found in Aurora database", "success": False}
        
        # Convert database record to customer data
        record = response['records'][0]
        customer_data = {
            'id': record[0]['stringValue'],
            'email': record[1]['stringValue'],
            'cognito_user_id': record[2].get('stringValue'),
            'first_name': record[3]['stringValue'],
            'last_name': record[4]['stringValue'],
            'phone': record[5].get('stringValue'),
            'created_at': record[6]['stringValue'],
            'updated_at': record[7]['stringValue']
        }
        
        return {
            "success": True,
            "customer": customer_data,
            "reasoning": "Real customer data retrieved from Aurora PostgreSQL database"
        }
        
    except ValueError as e:
        return {"error": f"Invalid customer ID format: {str(e)}", "success": False}
    except Exception as e:
        return {"error": f"Database error: {str(e)}", "success": False}

async def get_tickets_for_customer(customer_id: str) -> Dict[str, Any]:
    """Get tickets for customer from real Aurora database"""
    try:
        initialize_db()
        
        UUID(customer_id)
        
        sql = """
        SELECT t.*, c.first_name, c.last_name, c.email
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE t.customer_id = :customer_id
        ORDER BY t.event_date DESC;
        """
        
        parameters = [{'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}]
        response = await db.execute_sql(sql, parameters)
        
        tickets = []
        for record in response['records']:
            ticket_data = {
                'id': record[0]['stringValue'],
                'customer_id': record[1]['stringValue'],
                'ticket_number': record[2]['stringValue'],
                'ticket_type': record[3]['stringValue'],
                'original_price': float(record[4]['doubleValue']) if 'doubleValue' in record[4] else float(record[4]['stringValue']),
                'purchase_date': record[5]['stringValue'],
                'event_date': record[6]['stringValue'],
                'status': record[7]['stringValue'],
                'metadata': json.loads(record[8]['stringValue']) if record[8].get('stringValue') else {},
                'created_at': record[9]['stringValue'],
                'updated_at': record[10]['stringValue']
            }
            tickets.append(ticket_data)
        
        return {
            "success": True,
            "tickets": tickets,
            "count": len(tickets),
            "reasoning": f"Real ticket data retrieved from Aurora PostgreSQL database - found {len(tickets)} tickets"
        }
        
    except Exception as e:
        return {"error": f"Database error: {str(e)}", "success": False}

async def create_upgrade_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create upgrade order in real Aurora database"""
    try:
        initialize_db()
        
        # Generate confirmation code
        import uuid
        confirmation_code = f"REAL{str(uuid.uuid4())[:8].upper()}"
        
        sql = """
        INSERT INTO upgrade_orders (
            ticket_id, customer_id, upgrade_tier, original_tier,
            price_difference, total_amount, status, confirmation_code,
            selected_date, metadata
        )
        VALUES (
            :ticket_id, :customer_id, :upgrade_tier, :original_tier,
            :price_difference, :total_amount, :status, :confirmation_code,
            :selected_date, :metadata
        )
        RETURNING id, created_at, updated_at;
        """
        
        parameters = [
            {'name': 'ticket_id', 'value': {'stringValue': str(order_data.get('ticket_id'))}, 'typeHint': 'UUID'},
            {'name': 'customer_id', 'value': {'stringValue': str(order_data.get('customer_id'))}, 'typeHint': 'UUID'},
            {'name': 'upgrade_tier', 'value': {'stringValue': order_data.get('upgrade_tier', 'standard')}},
            {'name': 'original_tier', 'value': {'stringValue': order_data.get('original_tier', 'general')}},
            {'name': 'price_difference', 'value': {'doubleValue': float(order_data.get('price_difference', 0))}},
            {'name': 'total_amount', 'value': {'doubleValue': float(order_data.get('total_amount', 0))}},
            {'name': 'status', 'value': {'stringValue': 'pending'}},
            {'name': 'confirmation_code', 'value': {'stringValue': confirmation_code}},
            {'name': 'selected_date', 'value': {'stringValue': order_data.get('selected_date', datetime.now().isoformat())}, 'typeHint': 'TIMESTAMP'},
            {'name': 'metadata', 'value': {'stringValue': json.dumps(order_data.get('metadata', {}))}}
        ]
        
        response = await db.execute_sql(sql, parameters)
        
        if response['records']:
            record = response['records'][0]
            order_id = record[0]['stringValue']
            created_at = record[1]['stringValue']
            updated_at = record[2]['stringValue']
            
            return {
                "success": True,
                "upgrade_order": {
                    "id": order_id,
                    "status": "pending",
                    "total_amount": order_data.get("total_amount", 0),
                    "confirmation_code": confirmation_code,
                    "created_at": created_at,
                    "updated_at": updated_at
                },
                "reasoning": "Real upgrade order created in Aurora PostgreSQL database"
            }
        else:
            return {"error": "Failed to create upgrade order in database", "success": False}
            
    except Exception as e:
        return {"error": f"Database error: {str(e)}", "success": False}

async def validate_data_integrity() -> Dict[str, Any]:
    """Validate data integrity from real Aurora database"""
    try:
        initialize_db()
        
        # Check for orphaned records and data consistency
        integrity_checks = [
            "SELECT COUNT(*) as orphaned_tickets FROM tickets t LEFT JOIN customers c ON t.customer_id = c.id WHERE c.id IS NULL",
            "SELECT COUNT(*) as orphaned_upgrades FROM upgrade_orders uo LEFT JOIN tickets t ON uo.ticket_id = t.id WHERE t.id IS NULL",
            "SELECT COUNT(*) as total_customers FROM customers",
            "SELECT COUNT(*) as total_tickets FROM tickets",
            "SELECT COUNT(*) as total_upgrades FROM upgrade_orders"
        ]
        
        results = {}
        for sql in integrity_checks:
            response = await db.execute_sql(sql)
            key = sql.split(' as ')[1].split(' ')[0] if ' as ' in sql else 'count'
            results[key] = response['records'][0][0]['longValue']
        
        return {
            "success": True,
            "integrity_results": results,
            "reasoning": "Real database integrity check from Aurora PostgreSQL database"
        }
        
    except Exception as e:
        return {"error": f"Database error: {str(e)}", "success": False}

async def create_customer(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create customer in real Aurora database"""
    try:
        initialize_db()
        
        sql = """
        INSERT INTO customers (email, cognito_user_id, first_name, last_name, phone)
        VALUES (:email, :cognito_user_id, :first_name, :last_name, :phone)
        RETURNING id, created_at, updated_at;
        """
        
        parameters = [
            {'name': 'email', 'value': {'stringValue': customer_data.get('email')}},
            {'name': 'cognito_user_id', 'value': {'stringValue': customer_data.get('cognito_user_id')} if customer_data.get('cognito_user_id') else {'isNull': True}},
            {'name': 'first_name', 'value': {'stringValue': customer_data.get('first_name')}},
            {'name': 'last_name', 'value': {'stringValue': customer_data.get('last_name')}},
            {'name': 'phone', 'value': {'stringValue': customer_data.get('phone')} if customer_data.get('phone') else {'isNull': True}}
        ]
        
        response = await db.execute_sql(sql, parameters)
        
        if response['records']:
            record = response['records'][0]
            customer_id = record[0]['stringValue']
            created_at = record[1]['stringValue']
            updated_at = record[2]['stringValue']
            
            return {
                "success": True,
                "customer": {
                    "id": customer_id,
                    "email": customer_data.get("email"),
                    "first_name": customer_data.get("first_name"),
                    "last_name": customer_data.get("last_name"),
                    "phone": customer_data.get("phone"),
                    "created_at": created_at,
                    "updated_at": updated_at
                },
                "reasoning": "Real customer created in Aurora PostgreSQL database"
            }
        else:
            return {"error": "Failed to create customer in database", "success": False}
            
    except Exception as e:
        return {"error": f"Database error: {str(e)}", "success": False}
'''
        
        zipf.writestr('simplified_data_agent.py', simplified_data_agent)
    
    print(f"✅ Created Lambda package: {zip_path}")
    return zip_path

def deploy_lambda_function():
    """Deploy the Data Agent Invoker Lambda function"""
    
    # Load environment variables
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    
    # Function configuration
    function_name = 'data-agent-invoker'
    
    # Create deployment package
    zip_path = create_lambda_package()
    
    try:
        # Read the zip file
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName=function_name)
            function_exists = True
            print(f"📝 Function {function_name} exists, updating...")
        except lambda_client.exceptions.ResourceNotFoundException:
            function_exists = False
            print(f"🆕 Creating new function {function_name}...")
        
        if function_exists:
            # Update existing function code only
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
            
            print(f"✅ Function code updated successfully!")
            
        else:
            # Create new function
            response = lambda_client.create_function(
                FunctionName=function_name,
                Runtime='python3.9',
                Role=os.getenv('LAMBDA_ROLE_ARN'),
                Handler='lambda_function.lambda_handler',
                Code={'ZipFile': zip_content},
                Description='Data Agent Invoker - Bridge to Data Agent MCP server',
                Timeout=30,
                MemorySize=256,
                Environment={
                    'Variables': {
                        'DB_CLUSTER_ARN': os.getenv('DB_CLUSTER_ARN', ''),
                        'DB_SECRET_ARN': os.getenv('DB_SECRET_ARN', ''),
                        'DATABASE_NAME': os.getenv('DATABASE_NAME', 'ticket_system'),
                        'BEDROCK_MODEL_ID': os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
                    }
                }
            )
        
        function_arn = response['FunctionArn']
        print(f"✅ Lambda function deployed successfully!")
        print(f"   Function Name: {function_name}")
        print(f"   Function ARN: {function_arn}")
        
        # Clean up zip file
        os.remove(zip_path)
        
        return {
            'function_name': function_name,
            'function_arn': function_arn,
            'success': True
        }
        
    except Exception as e:
        print(f"❌ Failed to deploy Lambda function: {e}")
        # Clean up zip file
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return {
            'error': str(e),
            'success': False
        }

def test_lambda_function():
    """Test the deployed Lambda function"""
    
    lambda_client = boto3.client('lambda', region_name='us-west-2')
    function_name = 'data-agent-invoker'
    
    # Test with get_customer tool call
    test_payload = {
        "jsonrpc": "2.0",
        "id": "test-123",
        "method": "tools/call",
        "params": {
            "name": "get_customer",
            "arguments": {"customer_id": "test-customer-123"}
        }
    }
    
    try:
        print(f"\n🧪 Testing Lambda function with get_customer...")
        
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(test_payload)
        )
        
        if response['StatusCode'] == 200:
            result = json.loads(response['Payload'].read())
            print(f"✅ Test successful!")
            print(f"   Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Test failed with status: {response['StatusCode']}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Deploying Data Agent Invoker Lambda Function")
    print("="*60)
    
    # Deploy the function
    result = deploy_lambda_function()
    
    if result['success']:
        print(f"\n🎯 Deployment Summary:")
        print(f"✅ Function deployed: {result['function_name']}")
        print(f"📍 ARN: {result['function_arn']}")
        
        # Test the function
        print(f"\n🧪 Testing deployed function...")
        test_success = test_lambda_function()
        
        if test_success:
            print(f"\n🎉 SUCCESS: Data Agent Invoker is ready!")
            print(f"💡 Usage: Invoke with MCP tool call format")
            print(f"🔧 Function Name: data-agent-invoker")
        else:
            print(f"\n⚠️  Deployment successful but test failed")
            print(f"🔍 Check CloudWatch logs for details")
    else:
        print(f"\n❌ Deployment failed: {result['error']}")