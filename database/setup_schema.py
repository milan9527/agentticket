#!/usr/bin/env python3
"""
Database Schema Setup for Ticket Auto-Processing System

This script creates the PostgreSQL schema and tables for the ticket system:
- customers table
- tickets table  
- upgrade_orders table
- sample data for development and testing
"""

import boto3
import json
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid

class DatabaseSetup:
    def __init__(self):
        self.region = os.getenv('AWS_REGION', 'us-west-2')
        self.cluster_arn = os.getenv('DB_CLUSTER_ARN')
        self.secret_arn = os.getenv('DB_SECRET_ARN')
        self.database_name = os.getenv('DATABASE_NAME', 'ticket_system')
        
        if not self.cluster_arn or not self.secret_arn:
            raise ValueError("DB_CLUSTER_ARN and DB_SECRET_ARN must be set in environment")
        
        self.rds_data = boto3.client('rds-data', region_name=self.region)
    
    def execute_sql(self, sql: str, parameters: List[Dict] = None) -> Dict[str, Any]:
        """Execute SQL statement using RDS Data API"""
        try:
            params = {
                'resourceArn': self.cluster_arn,
                'secretArn': self.secret_arn,
                'database': self.database_name,
                'sql': sql
            }
            
            if parameters:
                params['parameters'] = parameters
            
            response = self.rds_data.execute_statement(**params)
            return response
        except Exception as e:
            print(f"Error executing SQL: {e}")
            print(f"SQL: {sql}")
            raise
    
    def create_tables(self):
        """Create all database tables"""
        print("Creating database tables...")
        
        # Enable UUID extension first
        uuid_extension_sql = 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'
        self.execute_sql(uuid_extension_sql)
        print("✓ Enabled UUID extension")
        
        # Create customers table
        customers_sql = """
        CREATE TABLE IF NOT EXISTS customers (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            email VARCHAR(255) UNIQUE NOT NULL,
            cognito_user_id VARCHAR(255) UNIQUE,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            phone VARCHAR(20),
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        # Create tickets table
        tickets_sql = """
        CREATE TABLE IF NOT EXISTS tickets (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
            ticket_number VARCHAR(50) UNIQUE NOT NULL,
            ticket_type VARCHAR(50) NOT NULL,
            original_price DECIMAL(10,2) NOT NULL,
            purchase_date TIMESTAMP DEFAULT NOW(),
            event_date TIMESTAMP NOT NULL,
            status VARCHAR(50) DEFAULT 'active',
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        """
        
        # Create upgrade_orders table (without foreign keys initially)
        upgrade_orders_sql = """
        CREATE TABLE IF NOT EXISTS upgrade_orders (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            ticket_id UUID NOT NULL,
            customer_id UUID NOT NULL,
            upgrade_tier VARCHAR(50) NOT NULL,
            original_tier VARCHAR(50) NOT NULL,
            price_difference DECIMAL(10,2) NOT NULL,
            total_amount DECIMAL(10,2) NOT NULL,
            status VARCHAR(50) DEFAULT 'pending',
            payment_intent_id VARCHAR(255),
            confirmation_code VARCHAR(20) UNIQUE,
            selected_date TIMESTAMP,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            completed_at TIMESTAMP
        );
        """
        
        # Create indexes for better performance
        indexes_sql = [
            "CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);",
            "CREATE INDEX IF NOT EXISTS idx_customers_cognito_id ON customers(cognito_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_tickets_customer_id ON tickets(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_tickets_number ON tickets(ticket_number);",
            "CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);",
            "CREATE INDEX IF NOT EXISTS idx_upgrade_orders_ticket_id ON upgrade_orders(ticket_id);",
            "CREATE INDEX IF NOT EXISTS idx_upgrade_orders_customer_id ON upgrade_orders(customer_id);",
            "CREATE INDEX IF NOT EXISTS idx_upgrade_orders_status ON upgrade_orders(status);",
            "CREATE INDEX IF NOT EXISTS idx_upgrade_orders_confirmation ON upgrade_orders(confirmation_code);"
        ]
        
        # Execute table creation
        self.execute_sql(customers_sql)
        print("✓ Created customers table")
        
        self.execute_sql(tickets_sql)
        print("✓ Created tickets table")
        
        self.execute_sql(upgrade_orders_sql)
        print("✓ Created upgrade_orders table")
        
        # Add foreign key constraints after all tables are created
        fk_constraints = [
            "ALTER TABLE upgrade_orders ADD CONSTRAINT fk_upgrade_orders_ticket_id FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE;",
            "ALTER TABLE upgrade_orders ADD CONSTRAINT fk_upgrade_orders_customer_id FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE;"
        ]
        
        for constraint_sql in fk_constraints:
            try:
                self.execute_sql(constraint_sql)
            except Exception as e:
                if "already exists" in str(e):
                    print(f"✓ Foreign key constraint already exists")
                else:
                    print(f"Warning: Could not add constraint: {e}")
        
        print("✓ Added foreign key constraints")
        
        # Create indexes
        for index_sql in indexes_sql:
            self.execute_sql(index_sql)
        print("✓ Created database indexes")
    
    def generate_sample_data(self):
        """Generate sample data for development and testing"""
        print("Generating sample data...")
        
        # Sample customers
        customers_data = [
            {
                'email': 'john.doe@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone': '+1-555-0101'
            },
            {
                'email': 'jane.smith@example.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'phone': '+1-555-0102'
            },
            {
                'email': 'bob.johnson@example.com',
                'first_name': 'Bob',
                'last_name': 'Johnson',
                'phone': '+1-555-0103'
            },
            {
                'email': 'alice.brown@example.com',
                'first_name': 'Alice',
                'last_name': 'Brown',
                'phone': '+1-555-0104'
            },
            {
                'email': 'charlie.wilson@example.com',
                'first_name': 'Charlie',
                'last_name': 'Wilson',
                'phone': '+1-555-0105'
            }
        ]
        
        # Insert customers
        for customer in customers_data:
            insert_customer_sql = """
            INSERT INTO customers (email, first_name, last_name, phone)
            VALUES (:email, :first_name, :last_name, :phone)
            ON CONFLICT (email) DO NOTHING
            RETURNING id;
            """
            
            parameters = [
                {'name': 'email', 'value': {'stringValue': customer['email']}},
                {'name': 'first_name', 'value': {'stringValue': customer['first_name']}},
                {'name': 'last_name', 'value': {'stringValue': customer['last_name']}},
                {'name': 'phone', 'value': {'stringValue': customer['phone']}}
            ]
            
            self.execute_sql(insert_customer_sql, parameters)
        
        print("✓ Inserted sample customers")
        
        # Get customer IDs for ticket creation
        get_customers_sql = "SELECT id, email FROM customers ORDER BY created_at LIMIT 5;"
        response = self.execute_sql(get_customers_sql)
        customer_ids = [record[0]['stringValue'] for record in response['records']]
        
        # Sample tickets
        ticket_types = ['general', 'vip', 'premium', 'standard']
        base_date = datetime.now() + timedelta(days=30)
        
        for i, customer_id in enumerate(customer_ids):
            for j in range(2):  # 2 tickets per customer
                ticket_number = f"TKT-{2024}{(i+1):02d}{(j+1):02d}"
                ticket_type = ticket_types[j % len(ticket_types)]
                original_price = 50.00 + (j * 25.00)
                event_date = base_date + timedelta(days=j*7)
                
                insert_ticket_sql = """
                INSERT INTO tickets (customer_id, ticket_number, ticket_type, original_price, event_date)
                VALUES (:customer_id, :ticket_number, :ticket_type, :original_price, :event_date)
                ON CONFLICT (ticket_number) DO NOTHING;
                """
                
                # Format timestamp properly for Aurora
                event_date_str = event_date.strftime('%Y-%m-%d %H:%M:%S')
                
                parameters = [
                    {'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'},
                    {'name': 'ticket_number', 'value': {'stringValue': ticket_number}},
                    {'name': 'ticket_type', 'value': {'stringValue': ticket_type}},
                    {'name': 'original_price', 'value': {'doubleValue': original_price}},
                    {'name': 'event_date', 'value': {'stringValue': event_date_str}, 'typeHint': 'TIMESTAMP'}
                ]
                
                self.execute_sql(insert_ticket_sql, parameters)
        
        print("✓ Inserted sample tickets")
        
        # Sample upgrade orders (some completed, some pending)
        get_tickets_sql = "SELECT id, customer_id, original_price FROM tickets LIMIT 3;"
        response = self.execute_sql(get_tickets_sql)
        
        upgrade_tiers = ['standard', 'non-stop', 'double-fun']
        upgrade_prices = [25.00, 50.00, 75.00]
        
        for i, ticket_record in enumerate(response['records']):
            ticket_id = ticket_record[0]['stringValue']
            customer_id = ticket_record[1]['stringValue']
            # Handle different possible formats for the price field
            price_field = ticket_record[2]
            if 'doubleValue' in price_field:
                original_price = float(price_field['doubleValue'])
            elif 'stringValue' in price_field:
                original_price = float(price_field['stringValue'])
            else:
                original_price = 50.0  # Default fallback
            
            upgrade_tier = upgrade_tiers[i % len(upgrade_tiers)]
            price_difference = upgrade_prices[i % len(upgrade_prices)]
            total_amount = original_price + price_difference
            confirmation_code = f"CONF{str(uuid.uuid4())[:8].upper()}"
            
            status = 'completed' if i < 2 else 'pending'
            completed_at = datetime.now() if status == 'completed' else None
            
            completed_at_str = completed_at.strftime('%Y-%m-%d %H:%M:%S') if completed_at else None
            
            parameters = [
                {'name': 'ticket_id', 'value': {'stringValue': ticket_id}, 'typeHint': 'UUID'},
                {'name': 'customer_id', 'value': {'stringValue': customer_id}, 'typeHint': 'UUID'},
                {'name': 'upgrade_tier', 'value': {'stringValue': upgrade_tier}},
                {'name': 'original_tier', 'value': {'stringValue': 'general'}},
                {'name': 'price_difference', 'value': {'doubleValue': price_difference}},
                {'name': 'total_amount', 'value': {'doubleValue': total_amount}},
                {'name': 'status', 'value': {'stringValue': status}},
                {'name': 'confirmation_code', 'value': {'stringValue': confirmation_code}}
            ]
            
            # Add completed_at only if it's not None
            if completed_at_str:
                parameters.append({'name': 'completed_at', 'value': {'stringValue': completed_at_str}, 'typeHint': 'TIMESTAMP'})
                insert_upgrade_sql = """
                INSERT INTO upgrade_orders (
                    ticket_id, customer_id, upgrade_tier, original_tier, 
                    price_difference, total_amount, status, confirmation_code, completed_at
                )
                VALUES (
                    :ticket_id, :customer_id, :upgrade_tier, :original_tier,
                    :price_difference, :total_amount, :status, :confirmation_code, :completed_at
                );
                """
            else:
                insert_upgrade_sql = """
                INSERT INTO upgrade_orders (
                    ticket_id, customer_id, upgrade_tier, original_tier, 
                    price_difference, total_amount, status, confirmation_code
                )
                VALUES (
                    :ticket_id, :customer_id, :upgrade_tier, :original_tier,
                    :price_difference, :total_amount, :status, :confirmation_code
                );
                """
            
            self.execute_sql(insert_upgrade_sql, parameters)
        
        print("✓ Inserted sample upgrade orders")
    
    def verify_setup(self):
        """Verify database setup by running test queries"""
        print("Verifying database setup...")
        
        # Count records in each table
        tables = ['customers', 'tickets', 'upgrade_orders']
        
        for table in tables:
            count_sql = f"SELECT COUNT(*) FROM {table};"
            response = self.execute_sql(count_sql)
            count = response['records'][0][0]['longValue']
            print(f"✓ {table}: {count} records")
        
        # Test a join query
        join_sql = """
        SELECT 
            c.first_name, c.last_name, c.email,
            t.ticket_number, t.ticket_type,
            uo.upgrade_tier, uo.status, uo.total_amount
        FROM customers c
        JOIN tickets t ON c.id = t.customer_id
        LEFT JOIN upgrade_orders uo ON t.id = uo.ticket_id
        ORDER BY c.created_at
        LIMIT 5;
        """
        
        response = self.execute_sql(join_sql)
        print(f"✓ Join query successful: {len(response['records'])} results")
    
    def setup_database(self):
        """Run complete database setup"""
        print("🗄️  Setting up database schema for Ticket Auto-Processing System")
        print(f"Cluster: {self.cluster_arn}")
        print(f"Database: {self.database_name}")
        print("-" * 60)
        
        try:
            self.create_tables()
            self.generate_sample_data()
            self.verify_setup()
            
            print("\n" + "=" * 60)
            print("✅ Database setup completed successfully!")
            print("=" * 60)
            print("\nDatabase schema created with:")
            print("• customers table (5 sample records)")
            print("• tickets table (10 sample records)")
            print("• upgrade_orders table (3 sample records)")
            print("• Proper indexes for performance")
            print("\n🎉 Ready for agent development!")
            
        except Exception as e:
            print(f"\n❌ Database setup failed: {e}")
            raise

def main():
    """Main function to run database setup"""
    # Load environment variables from .env file if it exists
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    setup = DatabaseSetup()
    setup.setup_database()

if __name__ == "__main__":
    main()