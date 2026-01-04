#!/usr/bin/env python3
"""
AgentCore-compatible Data Agent for Ticket Auto-Processing System

This agent is configured for deployment to AWS Bedrock AgentCore Runtime.
It handles all database operations and data validation using LLM reasoning.
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from uuid import UUID
import boto3
from botocore.exceptions import ClientError

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models.customer import Customer, CustomerCreate, CustomerUpdate
from models.ticket import Ticket, TicketCreate, TicketUpdate, TicketStatus
from models.upgrade_order import UpgradeOrder, UpgradeOrderCreate, UpgradeOrderUpdate, OrderStatus

# FastMCP imports for AgentCore
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field


class DataAgentConfig(BaseModel):
    """Configuration for the AgentCore Data Agent"""
    
    aws_region: str = Field(default="us-west-2", description="AWS region")
    db_cluster_arn: str = Field(..., description="Aurora cluster ARN")
    db_secret_arn: str = Field(..., description="Database secret ARN")
    database_name: str = Field(default="ticket_system", description="Database name")
    bedrock_model_id: str = Field(..., description="Bedrock model ID for LLM reasoning")


class DatabaseConnection:
    """Handles Aurora PostgreSQL Data API connections"""
    
    def __init__(self, config: DataAgentConfig):
        self.config = config
        self.rds_data = boto3.client('rds-data', region_name=config.aws_region)
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name=config.aws_region)
    
    async def execute_sql(self, sql: str, parameters: List[Dict] = None) -> Dict[str, Any]:
        """Execute SQL statement using RDS Data API"""
        try:
            params = {
                'resourceArn': self.config.db_cluster_arn,
                'secretArn': self.config.db_secret_arn,
                'database': self.config.database_name,
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
    
    async def llm_reason(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Use LLM reasoning for data operations"""
        try:
            # Prepare the reasoning prompt
            system_prompt = """You are a data validation and reasoning agent for a ticket processing system.
            You help validate data operations, suggest corrections, and provide insights about data integrity.
            Always respond with clear, actionable guidance."""
            
            full_prompt = f"{system_prompt}\n\nContext: {json.dumps(context) if context else 'None'}\n\nQuery: {prompt}"
            
            # Call Nova Pro model
            request_body = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": full_prompt}]
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 500,
                    "temperature": 0.1
                }
            }
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.bedrock_runtime.invoke_model(
                    modelId=self.config.bedrock_model_id,
                    body=json.dumps(request_body)
                )
            )
            
            response_body = json.loads(response['body'].read())
            content_list = response_body.get('output', {}).get('message', {}).get('content', [])
            text_block = next((item for item in content_list if "text" in item), None)
            
            if text_block:
                return text_block.get('text', 'No response from LLM')
            else:
                return 'No response from LLM'
                
        except Exception as e:
            print(f"LLM reasoning error: {e}")
            return f"LLM reasoning failed: {str(e)}"


# Initialize FastMCP for AgentCore with stateless HTTP
mcp = FastMCP(host="0.0.0.0", stateless_http=True)

# Global configuration and database connection
config = None
db = None


def load_config() -> DataAgentConfig:
    """Load configuration from AWS Systems Manager Parameter Store"""
    try:
        ssm_client = boto3.client('ssm', region_name='us-west-2')
        
        # Get parameters from Parameter Store
        parameter_names = [
            '/agentcore/data-agent/aws-region',
            '/agentcore/data-agent/db-cluster-arn',
            '/agentcore/data-agent/db-secret-arn',
            '/agentcore/data-agent/database-name',
            '/agentcore/data-agent/bedrock-model-id'
        ]
        
        response = ssm_client.get_parameters(
            Names=parameter_names,
            WithDecryption=True
        )
        
        # Convert to dictionary
        params = {param['Name']: param['Value'] for param in response['Parameters']}
        
        return DataAgentConfig(
            aws_region=params.get('/agentcore/data-agent/aws-region', 'us-west-2'),
            db_cluster_arn=params.get('/agentcore/data-agent/db-cluster-arn'),
            db_secret_arn=params.get('/agentcore/data-agent/db-secret-arn'),
            database_name=params.get('/agentcore/data-agent/database-name', 'ticket_system'),
            bedrock_model_id=params.get('/agentcore/data-agent/bedrock-model-id', 'us.amazon.nova-pro-v1:0')
        )
    except Exception as e:
        print(f"Failed to load config from Parameter Store: {e}")
        # Fallback to environment variables
        return DataAgentConfig(
            aws_region=os.getenv('AWS_REGION', 'us-west-2'),
            db_cluster_arn=os.getenv('DB_CLUSTER_ARN'),
            db_secret_arn=os.getenv('DB_SECRET_ARN'),
            database_name=os.getenv('DATABASE_NAME', 'ticket_system'),
            bedrock_model_id=os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
        )


def initialize_agent():
    """Initialize the agent configuration and database connection"""
    global config, db
    config = load_config()
    
    if not config.db_cluster_arn or not config.db_secret_arn:
        raise ValueError("Missing required database configuration: DB_CLUSTER_ARN and DB_SECRET_ARN must be set")
    
    db = DatabaseConnection(config)


# MCP Tools for AgentCore
@mcp.tool()
async def get_customer(customer_id: str) -> Dict[str, Any]:
    """Get customer by ID with LLM validation"""
    try:
        # Validate UUID format
        UUID(customer_id)
        
        sql = "SELECT * FROM customers WHERE id = :customer_id"
        parameters = [{'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}]
        
        response = await db.execute_sql(sql, parameters)
        
        if not response['records']:
            reasoning = await db.llm_reason(
                f"Customer with ID {customer_id} not found. What should we do?",
                {"operation": "get_customer", "customer_id": customer_id}
            )
            return {"error": "Customer not found", "reasoning": reasoning}
        
        # Convert database record to Customer model
        record = response['records'][0]
        customer_data = {
            'id': record[0]['stringValue'],
            'email': record[1]['stringValue'],
            'cognito_user_id': record[2].get('stringValue'),
            'first_name': record[3]['stringValue'],
            'last_name': record[4]['stringValue'],
            'phone': record[5].get('stringValue'),
            'created_at': datetime.fromisoformat(record[6]['stringValue']),
            'updated_at': datetime.fromisoformat(record[7]['stringValue'])
        }
        
        customer = Customer(**customer_data)
        return {"success": True, "customer": customer.model_dump()}
        
    except ValueError as e:
        reasoning = await db.llm_reason(
            f"Invalid customer ID format: {customer_id}. Error: {str(e)}",
            {"operation": "get_customer", "error": str(e)}
        )
        return {"error": "Invalid customer ID format", "reasoning": reasoning}
    except Exception as e:
        reasoning = await db.llm_reason(
            f"Database error while getting customer: {str(e)}",
            {"operation": "get_customer", "error": str(e)}
        )
        return {"error": str(e), "reasoning": reasoning}


@mcp.tool()
async def create_customer(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new customer with LLM validation"""
    try:
        # Use LLM to validate customer data
        reasoning = await db.llm_reason(
            f"Validate this customer data for creation: {json.dumps(customer_data)}",
            {"operation": "create_customer", "data": customer_data}
        )
        
        # Create and validate customer model
        customer_create = CustomerCreate(**customer_data)
        
        sql = """
        INSERT INTO customers (email, cognito_user_id, first_name, last_name, phone)
        VALUES (:email, :cognito_user_id, :first_name, :last_name, :phone)
        RETURNING id, created_at, updated_at;
        """
        
        parameters = [
            {'name': 'email', 'value': {'stringValue': customer_create.email}},
            {'name': 'cognito_user_id', 'value': {'stringValue': customer_create.cognito_user_id} if customer_create.cognito_user_id else {'isNull': True}},
            {'name': 'first_name', 'value': {'stringValue': customer_create.first_name}},
            {'name': 'last_name', 'value': {'stringValue': customer_create.last_name}},
            {'name': 'phone', 'value': {'stringValue': customer_create.phone} if customer_create.phone else {'isNull': True}}
        ]
        
        response = await db.execute_sql(sql, parameters)
        
        if response['records']:
            record = response['records'][0]
            customer_id = record[0]['stringValue']
            created_at = datetime.fromisoformat(record[1]['stringValue'])
            updated_at = datetime.fromisoformat(record[2]['stringValue'])
            
            # Create full customer object
            customer = Customer(
                id=customer_id,
                email=customer_create.email,
                cognito_user_id=customer_create.cognito_user_id,
                first_name=customer_create.first_name,
                last_name=customer_create.last_name,
                phone=customer_create.phone,
                created_at=created_at,
                updated_at=updated_at
            )
            
            return {
                "success": True, 
                "customer": customer.model_dump(),
                "reasoning": reasoning
            }
        else:
            return {"error": "Failed to create customer", "reasoning": reasoning}
            
    except Exception as e:
        reasoning = await db.llm_reason(
            f"Error creating customer: {str(e)}. Data: {json.dumps(customer_data)}",
            {"operation": "create_customer", "error": str(e), "data": customer_data}
        )
        return {"error": str(e), "reasoning": reasoning}


@mcp.tool()
async def get_tickets_for_customer(customer_id: str) -> Dict[str, Any]:
    """Get all tickets for a customer with upgrade eligibility analysis"""
    try:
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
                'purchase_date': datetime.fromisoformat(record[5]['stringValue']),
                'event_date': datetime.fromisoformat(record[6]['stringValue']),
                'status': record[7]['stringValue'],
                'metadata': json.loads(record[8]['stringValue']) if record[8].get('stringValue') else {},
                'created_at': datetime.fromisoformat(record[9]['stringValue']),
                'updated_at': datetime.fromisoformat(record[10]['stringValue'])
            }
            
            ticket = Ticket(**ticket_data)
            tickets.append(ticket.model_dump())
        
        # Use LLM to analyze upgrade opportunities
        reasoning = await db.llm_reason(
            f"Analyze upgrade opportunities for customer {customer_id} with {len(tickets)} tickets",
            {"operation": "get_tickets", "customer_id": customer_id, "ticket_count": len(tickets)}
        )
        
        return {
            "success": True,
            "tickets": tickets,
            "count": len(tickets),
            "reasoning": reasoning
        }
        
    except Exception as e:
        reasoning = await db.llm_reason(
            f"Error getting tickets for customer: {str(e)}",
            {"operation": "get_tickets", "error": str(e)}
        )
        return {"error": str(e), "reasoning": reasoning}


@mcp.tool()
async def create_upgrade_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create new upgrade order with LLM validation"""
    try:
        # Use LLM to validate upgrade order data
        reasoning = await db.llm_reason(
            f"Validate this upgrade order data: {json.dumps(order_data)}",
            {"operation": "create_upgrade_order", "data": order_data}
        )
        
        # Create and validate upgrade order model
        upgrade_create = UpgradeOrderCreate(**order_data)
        
        # Generate confirmation code
        import uuid
        confirmation_code = f"CONF{str(uuid.uuid4())[:8].upper()}"
        
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
            {'name': 'ticket_id', 'value': {'stringValue': str(upgrade_create.ticket_id)}, 'typeHint': 'UUID'},
            {'name': 'customer_id', 'value': {'stringValue': str(upgrade_create.customer_id)}, 'typeHint': 'UUID'},
            {'name': 'upgrade_tier', 'value': {'stringValue': upgrade_create.upgrade_tier.value}},
            {'name': 'original_tier', 'value': {'stringValue': upgrade_create.original_tier}},
            {'name': 'price_difference', 'value': {'doubleValue': float(upgrade_create.price_difference)}},
            {'name': 'total_amount', 'value': {'doubleValue': float(upgrade_create.total_amount)}},
            {'name': 'status', 'value': {'stringValue': upgrade_create.status.value}},
            {'name': 'confirmation_code', 'value': {'stringValue': confirmation_code}},
            {'name': 'selected_date', 'value': {'stringValue': upgrade_create.selected_date.isoformat()} if upgrade_create.selected_date else {'isNull': True}, 'typeHint': 'TIMESTAMP'},
            {'name': 'metadata', 'value': {'stringValue': json.dumps(upgrade_create.metadata)}}
        ]
        
        response = await db.execute_sql(sql, parameters)
        
        if response['records']:
            record = response['records'][0]
            order_id = record[0]['stringValue']
            created_at = datetime.fromisoformat(record[1]['stringValue'])
            updated_at = datetime.fromisoformat(record[2]['stringValue'])
            
            # Create full upgrade order object
            upgrade_order = UpgradeOrder(
                id=order_id,
                ticket_id=upgrade_create.ticket_id,
                customer_id=upgrade_create.customer_id,
                upgrade_tier=upgrade_create.upgrade_tier,
                original_tier=upgrade_create.original_tier,
                price_difference=upgrade_create.price_difference,
                total_amount=upgrade_create.total_amount,
                status=upgrade_create.status,
                confirmation_code=confirmation_code,
                selected_date=upgrade_create.selected_date,
                metadata=upgrade_create.metadata,
                created_at=created_at,
                updated_at=updated_at
            )
            
            return {
                "success": True,
                "upgrade_order": upgrade_order.model_dump(),
                "reasoning": reasoning
            }
        else:
            return {"error": "Failed to create upgrade order", "reasoning": reasoning}
            
    except Exception as e:
        reasoning = await db.llm_reason(
            f"Error creating upgrade order: {str(e)}. Data: {json.dumps(order_data)}",
            {"operation": "create_upgrade_order", "error": str(e), "data": order_data}
        )
        return {"error": str(e), "reasoning": reasoning}


@mcp.tool()
async def validate_data_integrity() -> Dict[str, Any]:
    """Validate overall data integrity with LLM analysis"""
    try:
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
        
        # Use LLM to analyze integrity results
        reasoning = await db.llm_reason(
            f"Analyze data integrity results: {json.dumps(results)}",
            {"operation": "validate_integrity", "results": results}
        )
        
        return {
            "success": True,
            "integrity_results": results,
            "reasoning": reasoning
        }
        
    except Exception as e:
        reasoning = await db.llm_reason(
            f"Error validating data integrity: {str(e)}",
            {"operation": "validate_integrity", "error": str(e)}
        )
        return {"error": str(e), "reasoning": reasoning}


# Initialize the agent when the module is loaded
try:
    initialize_agent()
    print("✅ AgentCore Data Agent initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize AgentCore Data Agent: {e}")


if __name__ == "__main__":
    # Run the MCP server for AgentCore
    print("🤖 Starting AgentCore Data Agent MCP server on 0.0.0.0:8000")
    print("📊 Available tools:")
    print("  - get_customer: Retrieve customer by ID")
    print("  - create_customer: Create new customer")
    print("  - get_tickets_for_customer: Get customer tickets with upgrade analysis")
    print("  - create_upgrade_order: Create new upgrade order")
    print("  - validate_data_integrity: Check database integrity")
    
    # For AgentCore, use streamable-http transport as required by AWS
    mcp.run(transport="streamable-http")