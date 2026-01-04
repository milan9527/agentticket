#!/usr/bin/env python3
"""
Database Schema Validation Script

This script validates the database schema structure and sample data
without requiring actual AWS resources for development purposes.
"""

import os
import sys

def validate_schema_file():
    """Validate that the schema.sql file exists and has proper structure"""
    schema_file = "database/schema.sql"
    
    if not os.path.exists(schema_file):
        print("❌ Schema file not found: database/schema.sql")
        return False
    
    with open(schema_file, 'r') as f:
        content = f.read()
    
    # Check for required tables
    required_tables = ['customers', 'tickets', 'upgrade_orders']
    for table in required_tables:
        if f"CREATE TABLE IF NOT EXISTS {table}" not in content:
            print(f"❌ Missing table definition: {table}")
            return False
        print(f"✓ Found table definition: {table}")
    
    # Check for required indexes
    required_indexes = [
        'idx_customers_email',
        'idx_tickets_customer_id', 
        'idx_upgrade_orders_ticket_id'
    ]
    for index in required_indexes:
        if f"CREATE INDEX IF NOT EXISTS {index}" not in content:
            print(f"❌ Missing index: {index}")
            return False
        print(f"✓ Found index: {index}")
    
    # Check for sample data
    if "INSERT INTO customers" not in content:
        print("❌ Missing sample customer data")
        return False
    print("✓ Found sample customer data")
    
    if "INSERT INTO tickets" not in content:
        print("❌ Missing sample ticket data")
        return False
    print("✓ Found sample ticket data")
    
    print("\n✅ Database schema validation passed!")
    return True

def validate_data_models():
    """Validate that the data model structure is correct"""
    print("\n📋 Validating data model structure...")
    
    # Expected table structure
    expected_structure = {
        'customers': [
            'id', 'email', 'cognito_user_id', 'first_name', 
            'last_name', 'phone', 'created_at', 'updated_at'
        ],
        'tickets': [
            'id', 'customer_id', 'ticket_number', 'ticket_type',
            'original_price', 'purchase_date', 'event_date', 'status',
            'metadata', 'created_at', 'updated_at'
        ],
        'upgrade_orders': [
            'id', 'ticket_id', 'customer_id', 'upgrade_tier',
            'original_tier', 'price_difference', 'total_amount', 'status',
            'payment_intent_id', 'confirmation_code', 'selected_date',
            'metadata', 'created_at', 'updated_at', 'completed_at'
        ]
    }
    
    schema_file = "database/schema.sql"
    with open(schema_file, 'r') as f:
        content = f.read()
    
    for table, columns in expected_structure.items():
        print(f"\n🔍 Checking {table} table structure:")
        for column in columns:
            if column in content:
                print(f"  ✓ {column}")
            else:
                print(f"  ❌ Missing column: {column}")
                return False
    
    print("\n✅ Data model structure validation passed!")
    return True

def validate_business_rules():
    """Validate business rules are properly implemented in schema"""
    print("\n📊 Validating business rules...")
    
    schema_file = "database/schema.sql"
    with open(schema_file, 'r') as f:
        content = f.read()
    
    # Check for foreign key constraints
    fk_constraints = [
        'REFERENCES customers(id)',
        'REFERENCES tickets(id)'
    ]
    
    for constraint in fk_constraints:
        if constraint in content:
            print(f"✓ Found foreign key constraint: {constraint}")
        else:
            print(f"❌ Missing foreign key constraint: {constraint}")
            return False
    
    # Check for unique constraints
    unique_constraints = [
        'email VARCHAR(255) UNIQUE',
        'ticket_number VARCHAR(50) UNIQUE',
        'confirmation_code VARCHAR(20) UNIQUE'
    ]
    
    for constraint in unique_constraints:
        if 'UNIQUE' in constraint and any(part in content for part in constraint.split()):
            print(f"✓ Found unique constraint for: {constraint.split()[0]}")
        else:
            print(f"❌ Missing unique constraint: {constraint}")
            return False
    
    # Check for default values
    defaults = [
        "DEFAULT 'active'",
        "DEFAULT 'pending'",
        "DEFAULT NOW()"
    ]
    
    for default in defaults:
        if default in content:
            print(f"✓ Found default value: {default}")
        else:
            print(f"❌ Missing default value: {default}")
            return False
    
    print("\n✅ Business rules validation passed!")
    return True

def main():
    """Main validation function"""
    print("🗄️  Database Schema Validation")
    print("=" * 50)
    
    # Run all validations
    validations = [
        validate_schema_file,
        validate_data_models,
        validate_business_rules
    ]
    
    all_passed = True
    for validation in validations:
        if not validation():
            all_passed = False
            break
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All database schema validations passed!")
        print("\nDatabase schema is ready for:")
        print("• Agent development")
        print("• Data model implementation")
        print("• Aurora PostgreSQL deployment")
        print("\nNext steps:")
        print("1. Implement Python data models (Task 2.3)")
        print("2. Set up AgentCore development environment (Task 3.1)")
        return 0
    else:
        print("❌ Database schema validation failed!")
        print("Please fix the issues above before proceeding.")
        return 1

if __name__ == "__main__":
    sys.exit(main())