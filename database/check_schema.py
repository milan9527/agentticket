#!/usr/bin/env python3
"""
Check existing database schema
"""

import boto3
import json
import os

def check_database():
    """Check what exists in the database"""
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
    
    # Check what tables exist
    print("Checking existing tables...")
    response = execute_sql("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    if response:
        tables = [record[0]['stringValue'] for record in response['records']]
        print(f"Existing tables: {tables}")
        
        # Check structure of each table
        for table in tables:
            print(f"\nStructure of {table}:")
            response = execute_sql(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}';")
            if response:
                for record in response['records']:
                    column_name = record[0]['stringValue']
                    data_type = record[1]['stringValue']
                    print(f"  {column_name}: {data_type}")
    else:
        print("No tables found or error occurred")

if __name__ == "__main__":
    # Load .env file
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    
    check_database()