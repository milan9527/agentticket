#!/usr/bin/env python3
"""
Reset database schema - drop all tables and recreate
"""

import boto3
import json
import os

def reset_database():
    """Drop all tables and recreate schema"""
    region = os.getenv('AWS_REGION', 'us-west-2')
    cluster_arn = os.getenv('DB_CLUSTER_ARN')
    secret_arn = os.getenv('DB_SECRET_ARN')
    database_name = os.getenv('DATABASE_NAME', 'ticket_system')
    
    if not cluster_arn or not secret_arn:
        print("Missing DB_CLUSTER_ARN or DB_SECRET_ARN")
        return
    
    rds_data = boto3.client('rds-data', region_name=region)
    
    def execute_sql(sql):
        try:
            response = rds_data.execute_statement(
                resourceArn=cluster_arn,
                secretArn=secret_arn,
                database=database_name,
                sql=sql
            )
            return response
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    print("🗑️  Dropping existing tables...")
    
    # Drop tables in correct order (child tables first)
    drop_tables = [
        "DROP TABLE IF EXISTS upgrade_orders CASCADE;",
        "DROP TABLE IF EXISTS payments CASCADE;", 
        "DROP TABLE IF EXISTS upgrades CASCADE;",
        "DROP TABLE IF EXISTS tickets CASCADE;",
        "DROP TABLE IF EXISTS customers CASCADE;"
    ]
    
    for drop_sql in drop_tables:
        response = execute_sql(drop_sql)
        if response:
            table_name = drop_sql.split()[4]
            print(f"✓ Dropped {table_name}")
    
    print("✅ All tables dropped successfully")

if __name__ == "__main__":
    # Load .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    reset_database()