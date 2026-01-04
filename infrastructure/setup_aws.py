#!/usr/bin/env python3
"""
AWS Infrastructure Setup Script for Ticket Auto-Processing System

This script creates the necessary AWS resources:
- Aurora PostgreSQL Serverless cluster with Data API
- AWS Secrets Manager for database credentials
- IAM roles for Lambda, AgentCore, and database access
- S3 bucket for frontend deployment (private access only)
"""

import boto3
import json
import time
import os
from typing import Dict, Any

class AWSInfrastructureSetup:
    def __init__(self, region: str = 'us-west-2'):
        self.region = region
        self.rds = boto3.client('rds', region_name=region)
        self.secretsmanager = boto3.client('secretsmanager', region_name=region)
        self.iam = boto3.client('iam', region_name=region)
        self.s3 = boto3.client('s3', region_name=region)
        self.sts = boto3.client('sts', region_name=region)
        
        # Get account ID for ARN construction
        self.account_id = self.sts.get_caller_identity()['Account']
        
    def create_database_secret(self) -> str:
        """Create database credentials in AWS Secrets Manager"""
        print("Creating database secret in AWS Secrets Manager...")
        
        secret_name = "ticket-system-db-secret"
        secret_value = {
            "username": "ticket_admin",
            "password": "TicketSystem2024!",  # In production, use a secure random password
            "engine": "postgres",
            "host": "",  # Will be updated after cluster creation
            "port": 5432,
            "dbname": "ticket_system"
        }
        
        try:
            response = self.secretsmanager.create_secret(
                Name=secret_name,
                Description="Database credentials for Ticket Auto-Processing System",
                SecretString=json.dumps(secret_value)
            )
            print(f"✓ Created secret: {response['ARN']}")
            return response['ARN']
        except self.secretsmanager.exceptions.ResourceExistsException:
            print(f"✓ Secret {secret_name} already exists")
            response = self.secretsmanager.describe_secret(SecretId=secret_name)
            return response['ARN']
    
    def create_aurora_cluster(self, secret_arn: str) -> Dict[str, str]:
        """Create Aurora PostgreSQL Serverless cluster with Data API enabled"""
        print("Creating Aurora PostgreSQL Serverless cluster...")
        
        cluster_identifier = "ticket-system-cluster"
        
        try:
            response = self.rds.create_db_cluster(
                DBClusterIdentifier=cluster_identifier,
                Engine='aurora-postgresql',
                EngineMode='provisioned',
                EngineVersion='15.4',
                MasterUsername='ticket_admin',
                MasterUserPassword='TicketSystem2024!',  # Use direct password for simplicity
                DatabaseName='ticket_system',
                ServerlessV2ScalingConfiguration={
                    'MinCapacity': 0.5,
                    'MaxCapacity': 2.0
                },
                EnableHttpEndpoint=True,  # Enable Data API
                DeletionProtection=False,  # Set to True in production
                BackupRetentionPeriod=7,
                PreferredBackupWindow='03:00-04:00',
                PreferredMaintenanceWindow='sun:04:00-sun:05:00',
                Tags=[
                    {'Key': 'Project', 'Value': 'TicketAutoProcessing'},
                    {'Key': 'Environment', 'Value': 'Development'}
                ]
            )
            
            cluster_arn = response['DBCluster']['DBClusterArn']
            print(f"✓ Created Aurora cluster: {cluster_arn}")
            
            # Wait for cluster to be available
            print("Waiting for cluster to be available...")
            waiter = self.rds.get_waiter('db_cluster_available')
            waiter.wait(DBClusterIdentifier=cluster_identifier)
            
            # Create a serverless v2 instance
            print("Creating Aurora Serverless v2 instance...")
            self.rds.create_db_instance(
                DBInstanceIdentifier=f"{cluster_identifier}-instance-1",
                DBClusterIdentifier=cluster_identifier,
                DBInstanceClass='db.serverless',
                Engine='aurora-postgresql'
            )
            
            return {
                'cluster_arn': cluster_arn,
                'cluster_identifier': cluster_identifier
            }
            
        except self.rds.exceptions.DBClusterAlreadyExistsFault:
            print(f"✓ Aurora cluster {cluster_identifier} already exists")
            response = self.rds.describe_db_clusters(DBClusterIdentifier=cluster_identifier)
            cluster_arn = response['DBClusters'][0]['DBClusterArn']
            return {
                'cluster_arn': cluster_arn,
                'cluster_identifier': cluster_identifier
            }
    
    def create_iam_roles(self) -> Dict[str, str]:
        """Create IAM roles for Lambda, AgentCore, and database access"""
        print("Creating IAM roles...")
        
        roles = {}
        
        # Lambda execution role
        lambda_role_name = "TicketSystemLambdaRole"
        lambda_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "lambda.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        lambda_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "rds-data:BatchExecuteStatement",
                        "rds-data:BeginTransaction",
                        "rds-data:CommitTransaction",
                        "rds-data:ExecuteStatement",
                        "rds-data:RollbackTransaction"
                    ],
                    "Resource": f"arn:aws:rds:{self.region}:{self.account_id}:cluster:ticket-system-cluster"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue",
                        "secretsmanager:DescribeSecret"
                    ],
                    "Resource": f"arn:aws:secretsmanager:{self.region}:{self.account_id}:secret:ticket-system-db-secret*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:*"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        try:
            self.iam.create_role(
                RoleName=lambda_role_name,
                AssumeRolePolicyDocument=json.dumps(lambda_trust_policy),
                Description="IAM role for Ticket System Lambda functions"
            )
            
            self.iam.put_role_policy(
                RoleName=lambda_role_name,
                PolicyName="TicketSystemLambdaPolicy",
                PolicyDocument=json.dumps(lambda_policy)
            )
            
            roles['lambda_role'] = f"arn:aws:iam::{self.account_id}:role/{lambda_role_name}"
            print(f"✓ Created Lambda role: {roles['lambda_role']}")
            
        except self.iam.exceptions.EntityAlreadyExistsException:
            roles['lambda_role'] = f"arn:aws:iam::{self.account_id}:role/{lambda_role_name}"
            print(f"✓ Lambda role already exists: {roles['lambda_role']}")
        
        # AgentCore execution role
        agentcore_role_name = "TicketSystemAgentCoreRole"
        agentcore_trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            self.iam.create_role(
                RoleName=agentcore_role_name,
                AssumeRolePolicyDocument=json.dumps(agentcore_trust_policy),
                Description="IAM role for AgentCore Runtime"
            )
            
            # Create custom policy for AgentCore instead of managed policy
            agentcore_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "bedrock:InvokeModel",
                            "bedrock:InvokeModelWithResponseStream"
                        ],
                        "Resource": "*"
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "logs:CreateLogGroup",
                            "logs:CreateLogStream",
                            "logs:PutLogEvents"
                        ],
                        "Resource": "arn:aws:logs:*:*:*"
                    }
                ]
            }
            
            self.iam.put_role_policy(
                RoleName=agentcore_role_name,
                PolicyName="TicketSystemAgentCorePolicy",
                PolicyDocument=json.dumps(agentcore_policy)
            )
            
            roles['agentcore_role'] = f"arn:aws:iam::{self.account_id}:role/{agentcore_role_name}"
            print(f"✓ Created AgentCore role: {roles['agentcore_role']}")
            
        except self.iam.exceptions.EntityAlreadyExistsException:
            roles['agentcore_role'] = f"arn:aws:iam::{self.account_id}:role/{agentcore_role_name}"
            print(f"✓ AgentCore role already exists: {roles['agentcore_role']}")
        
        return roles
    
    def create_s3_bucket(self) -> str:
        """Create S3 bucket for frontend deployment (private access only)"""
        print("Creating S3 bucket for frontend deployment...")
        
        bucket_name = f"ticket-system-frontend-{self.account_id}"
        
        try:
            if self.region == 'us-east-1':
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            # Block all public access
            self.s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            # Add bucket policy for CloudFront access
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowCloudFrontServicePrincipal",
                        "Effect": "Allow",
                        "Principal": {"Service": "cloudfront.amazonaws.com"},
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*"
                    }
                ]
            }
            
            self.s3.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            
            print(f"✓ Created S3 bucket: {bucket_name}")
            return bucket_name
            
        except self.s3.exceptions.BucketAlreadyExists:
            print(f"✓ S3 bucket {bucket_name} already exists")
            return bucket_name
        except self.s3.exceptions.BucketAlreadyOwnedByYou:
            print(f"✓ S3 bucket {bucket_name} already owned by you")
            return bucket_name
    
    def setup_infrastructure(self) -> Dict[str, Any]:
        """Set up all AWS infrastructure components"""
        print("🚀 Setting up AWS infrastructure for Ticket Auto-Processing System")
        print(f"Region: {self.region}")
        print(f"Account ID: {self.account_id}")
        print("-" * 60)
        
        # Create database secret
        secret_arn = self.create_database_secret()
        
        # Create Aurora cluster
        cluster_info = self.create_aurora_cluster(secret_arn)
        
        # Create IAM roles
        roles = self.create_iam_roles()
        
        # Create S3 bucket
        bucket_name = self.create_s3_bucket()
        
        # Generate .env file
        env_config = {
            'AWS_REGION': self.region,
            'DB_CLUSTER_ARN': cluster_info['cluster_arn'],
            'DB_SECRET_ARN': secret_arn,
            'DATABASE_NAME': 'ticket_system',
            'LAMBDA_ROLE_ARN': roles['lambda_role'],
            'AGENTCORE_ROLE_ARN': roles['agentcore_role'],
            'S3_BUCKET_NAME': bucket_name
        }
        
        print("\n" + "=" * 60)
        print("✅ Infrastructure setup completed successfully!")
        print("=" * 60)
        print("\nCreated resources:")
        print(f"• Aurora Cluster: {cluster_info['cluster_identifier']}")
        print(f"• Database Secret: {secret_arn}")
        print(f"• Lambda Role: {roles['lambda_role']}")
        print(f"• AgentCore Role: {roles['agentcore_role']}")
        print(f"• S3 Bucket: {bucket_name}")
        
        print(f"\n📝 Environment configuration:")
        for key, value in env_config.items():
            print(f"{key}={value}")
        
        return env_config

def main():
    """Main function to run infrastructure setup"""
    setup = AWSInfrastructureSetup()
    config = setup.setup_infrastructure()
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write("# AWS Infrastructure Configuration\n")
        f.write("# Generated by setup_aws.py\n\n")
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    print(f"\n💾 Configuration saved to .env file")
    print("\n🎉 Ready to proceed with development!")
    print("\nNext steps:")
    print("1. Review the .env file and add any missing configuration")
    print("2. Run database schema setup: python database/setup_schema.py")
    print("3. Install AgentCore CLI: pip install bedrock-agentcore-starter-toolkit")

if __name__ == "__main__":
    main()