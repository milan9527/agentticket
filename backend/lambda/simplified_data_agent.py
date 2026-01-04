#!/usr/bin/env python3
"""
Simplified Data Agent Functions for Lambda Invoker

This module provides simplified functions that directly access the Aurora database
for use by the Data Agent Invoker Lambda function.
"""

import os
import json
import boto3
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Load environment
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Database configuration
DB_CLUSTER_ARN = os.getenv('DB_CLUSTER_ARN')
DB_SECRET_ARN = os.getenv('DB_SECRET_ARN')
DATABASE_NAME = os.getenv('DATABASE_NAME', 'ticket_system')
AWS_REGION = os.getenv('AWS_REGION', 'us-west-2')

# Initialize RDS Data API client
rds_data = boto3.client('rds-data', region_name=AWS_REGION)


async def get_customer(customer_id: str) -> Dict[str, Any]:
    """Get customer data from Aurora database"""
    try:
        print(f"🔍 Getting customer: {customer_id}")
        
        sql = "SELECT id, email, phone, first_name, last_name, created_at, updated_at FROM customers WHERE id = :customer_id"
        
        response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql=sql,
            parameters=[
                {'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}
            ]
        )
        
        if response['records']:
            record = response['records'][0]
            customer = {
                'id': record[0]['stringValue'],
                'email': record[1]['stringValue'],
                'phone': record[2]['stringValue'] if record[2].get('stringValue') else None,
                'first_name': record[3]['stringValue'],
                'last_name': record[4]['stringValue'],
                'created_at': record[5]['stringValue'],
                'updated_at': record[6]['stringValue']
            }
            
            print(f"✅ Customer found: {customer['first_name']} {customer['last_name']}")
            
            return {
                'success': True,
                'customer': customer,
                'reasoning': f"Customer {customer['first_name']} {customer['last_name']} retrieved from Aurora database"
            }
        else:
            print(f"❌ Customer not found: {customer_id}")
            return {
                'success': False,
                'error': f'Customer {customer_id} not found',
                'reasoning': 'Customer ID not found in Aurora database'
            }
            
    except Exception as e:
        print(f"❌ Error getting customer {customer_id}: {e}")
        return {
            'success': False,
            'error': f'Database error: {str(e)}',
            'reasoning': 'Failed to query Aurora database for customer data'
        }


async def get_tickets_for_customer(customer_id: str) -> Dict[str, Any]:
    """Get all tickets for a customer from Aurora database"""
    try:
        print(f"🎫 Getting tickets for customer: {customer_id}")
        
        sql = """
        SELECT id, customer_id, ticket_number, ticket_type, original_price, 
               purchase_date, event_date, status, metadata, created_at, updated_at 
        FROM tickets 
        WHERE customer_id = :customer_id
        ORDER BY created_at DESC
        """
        
        response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql=sql,
            parameters=[
                {'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'}
            ]
        )
        
        tickets = []
        for record in response['records']:
            ticket = {
                'id': record[0]['stringValue'],
                'customer_id': record[1]['stringValue'],
                'ticket_number': record[2]['stringValue'],
                'ticket_type': record[3]['stringValue'],
                'original_price': float(record[4]['doubleValue']) if record[4].get('doubleValue') is not None else 0.0,
                'purchase_date': record[5]['stringValue'],
                'event_date': record[6]['stringValue'],
                'status': record[7]['stringValue'],
                'metadata': json.loads(record[8]['stringValue']) if record[8].get('stringValue') else {},
                'created_at': record[9]['stringValue'],
                'updated_at': record[10]['stringValue']
            }
            tickets.append(ticket)
        
        print(f"✅ Found {len(tickets)} tickets for customer {customer_id}")
        
        return {
            'success': True,
            'data': {'tickets': tickets},
            'tickets': tickets,  # Also provide direct access
            'count': len(tickets),
            'reasoning': f"Retrieved {len(tickets)} tickets from Aurora database for customer {customer_id}"
        }
        
    except Exception as e:
        print(f"❌ Error getting tickets for customer {customer_id}: {e}")
        return {
            'success': False,
            'error': f'Database error: {str(e)}',
            'data': {'tickets': []},
            'tickets': [],
            'count': 0,
            'reasoning': 'Failed to query Aurora database for ticket data'
        }


async def create_upgrade_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create an upgrade order in Aurora database"""
    try:
        print(f"📝 Creating upgrade order: {order_data}")
        
        # Generate order ID and confirmation code
        import uuid
        order_id = str(uuid.uuid4())
        confirmation_code = f"CONF{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        sql = """
        INSERT INTO upgrade_orders (id, ticket_id, customer_id, upgrade_tier, total_amount, 
                                  status, confirmation_code, created_at, updated_at)
        VALUES (:id, :ticket_id, :customer_id, :upgrade_tier, :total_amount, 
                :status, :confirmation_code, :created_at, :updated_at)
        """
        
        now = datetime.now().isoformat()
        
        response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql=sql,
            parameters=[
                {'name': 'id', 'value': {'stringValue': order_id}, 'typeHint': 'UUID'},
                {'name': 'ticket_id', 'value': {'stringValue': order_data.get('ticket_id', '')}, 'typeHint': 'UUID'},
                {'name': 'customer_id', 'value': {'stringValue': order_data.get('customer_id', '')}, 'typeHint': 'UUID'},
                {'name': 'upgrade_tier', 'value': {'stringValue': order_data.get('upgrade_tier', 'standard')}},
                {'name': 'total_amount', 'value': {'doubleValue': float(order_data.get('total_amount', 0))}},
                {'name': 'status', 'value': {'stringValue': 'pending'}},
                {'name': 'confirmation_code', 'value': {'stringValue': confirmation_code}},
                {'name': 'created_at', 'value': {'stringValue': now}},
                {'name': 'updated_at', 'value': {'stringValue': now}}
            ]
        )
        
        upgrade_order = {
            'id': order_id,
            'ticket_id': order_data.get('ticket_id'),
            'customer_id': order_data.get('customer_id'),
            'upgrade_tier': order_data.get('upgrade_tier', 'standard'),
            'total_amount': float(order_data.get('total_amount', 0)),
            'status': 'pending',
            'confirmation_code': confirmation_code,
            'created_at': now,
            'updated_at': now
        }
        
        print(f"✅ Upgrade order created: {order_id}")
        
        return {
            'success': True,
            'upgrade_order': upgrade_order,
            'reasoning': f"Upgrade order {order_id} created successfully in Aurora database"
        }
        
    except Exception as e:
        print(f"❌ Error creating upgrade order: {e}")
        return {
            'success': False,
            'error': f'Database error: {str(e)}',
            'reasoning': 'Failed to create upgrade order in Aurora database'
        }


async def create_customer(customer_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new customer in Aurora database"""
    try:
        print(f"👤 Creating customer: {customer_data}")
        
        import uuid
        customer_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        sql = """
        INSERT INTO customers (id, email, phone, first_name, last_name, created_at, updated_at)
        VALUES (:id, :email, :phone, :first_name, :last_name, :created_at, :updated_at)
        """
        
        response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql=sql,
            parameters=[
                {'name': 'id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'},
                {'name': 'email', 'value': {'stringValue': customer_data.get('email', '')}},
                {'name': 'phone', 'value': {'stringValue': customer_data.get('phone', '')}},
                {'name': 'first_name', 'value': {'stringValue': customer_data.get('first_name', '')}},
                {'name': 'last_name', 'value': {'stringValue': customer_data.get('last_name', '')}},
                {'name': 'created_at', 'value': {'stringValue': now}},
                {'name': 'updated_at', 'value': {'stringValue': now}}
            ]
        )
        
        customer = {
            'id': customer_id,
            'email': customer_data.get('email', ''),
            'phone': customer_data.get('phone', ''),
            'first_name': customer_data.get('first_name', ''),
            'last_name': customer_data.get('last_name', ''),
            'created_at': now,
            'updated_at': now
        }
        
        print(f"✅ Customer created: {customer_id}")
        
        return {
            'success': True,
            'customer': customer,
            'reasoning': f"Customer {customer['first_name']} {customer['last_name']} created successfully in Aurora database"
        }
        
    except Exception as e:
        print(f"❌ Error creating customer: {e}")
        return {
            'success': False,
            'error': f'Database error: {str(e)}',
            'reasoning': 'Failed to create customer in Aurora database'
        }


async def validate_data_integrity() -> Dict[str, Any]:
    """Validate data integrity in Aurora database"""
    try:
        print("🔍 Validating data integrity")
        
        # Count customers
        customers_response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql="SELECT COUNT(*) FROM customers"
        )
        total_customers = customers_response['records'][0][0]['longValue']
        
        # Count tickets
        tickets_response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql="SELECT COUNT(*) FROM tickets"
        )
        total_tickets = tickets_response['records'][0][0]['longValue']
        
        # Count upgrade orders
        upgrades_response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql="SELECT COUNT(*) FROM upgrade_orders"
        )
        total_upgrades = upgrades_response['records'][0][0]['longValue']
        
        # Check for orphaned tickets (tickets without valid customers)
        orphaned_tickets_response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql="""
            SELECT COUNT(*) FROM tickets t 
            LEFT JOIN customers c ON t.customer_id = c.id 
            WHERE c.id IS NULL
            """
        )
        orphaned_tickets = orphaned_tickets_response['records'][0][0]['longValue']
        
        # Check for orphaned upgrade orders
        orphaned_upgrades_response = rds_data.execute_statement(
            resourceArn=DB_CLUSTER_ARN,
            secretArn=DB_SECRET_ARN,
            database=DATABASE_NAME,
            sql="""
            SELECT COUNT(*) FROM upgrade_orders u 
            LEFT JOIN tickets t ON u.ticket_id = t.id 
            WHERE t.id IS NULL
            """
        )
        orphaned_upgrades = orphaned_upgrades_response['records'][0][0]['longValue']
        
        integrity_results = {
            'total_customers': total_customers,
            'total_tickets': total_tickets,
            'total_upgrades': total_upgrades,
            'orphaned_tickets': orphaned_tickets,
            'orphaned_upgrades': orphaned_upgrades
        }
        
        print(f"✅ Data integrity check complete: {integrity_results}")
        
        return {
            'success': True,
            'integrity_results': integrity_results,
            'reasoning': f"Database integrity validated: {total_customers} customers, {total_tickets} tickets, {total_upgrades} upgrades"
        }
        
    except Exception as e:
        print(f"❌ Error validating data integrity: {e}")
        return {
            'success': False,
            'error': f'Database error: {str(e)}',
            'reasoning': 'Failed to validate data integrity in Aurora database'
        }