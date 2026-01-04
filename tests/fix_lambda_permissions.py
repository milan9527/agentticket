#!/usr/bin/env python3
"""
Fix Lambda Permissions

Add permission for chat-handler to invoke ticket-handler Lambda.
"""

import boto3
import json

def fix_lambda_permissions():
    """Add Lambda invoke permissions"""
    print("🔧 FIXING LAMBDA PERMISSIONS")
    print("=" * 40)
    
    # Initialize IAM client
    iam_client = boto3.client('iam', region_name='us-west-2')
    
    # Role name for the Lambda execution role
    role_name = 'TicketSystemLambdaExecutionRole'
    
    # Policy to allow Lambda invocation and RDS Data API access
    lambda_invoke_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": [
                    "arn:aws:lambda:us-west-2:632930644527:function:ticket-handler",
                    "arn:aws:lambda:us-west-2:632930644527:function:customer-handler",
                    "arn:aws:lambda:us-west-2:632930644527:function:chat-handler"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "rds-data:ExecuteStatement",
                    "rds-data:BatchExecuteStatement",
                    "rds-data:BeginTransaction",
                    "rds-data:CommitTransaction",
                    "rds-data:RollbackTransaction"
                ],
                "Resource": [
                    "arn:aws:rds:us-west-2:632930644527:cluster:ticket-system-cluster"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret"
                ],
                "Resource": [
                    "arn:aws:secretsmanager:us-west-2:632930644527:secret:ticket-system-db-secret-*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock:InvokeModel"
                ],
                "Resource": "*"
            }
        ]
    }
    
    policy_name = 'LambdaComprehensivePolicy'
    
    try:
        # Try to create the policy
        try:
            response = iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(lambda_invoke_policy),
                Description='Allow Lambda functions to invoke other functions, access RDS Data API, Secrets Manager, and Bedrock'
            )
            policy_arn = response['Policy']['Arn']
            print(f"✅ Created policy: {policy_arn}")
        except iam_client.exceptions.EntityAlreadyExistsException:
            # Policy already exists, get its ARN
            account_id = boto3.client('sts').get_caller_identity()['Account']
            policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
            print(f"📋 Policy already exists: {policy_arn}")
        
        # Attach the policy to the role
        try:
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f"✅ Attached policy to role: {role_name}")
        except iam_client.exceptions.NoSuchEntityException:
            print(f"❌ Role {role_name} not found")
            return
        except Exception as e:
            if "already attached" in str(e):
                print(f"📋 Policy already attached to role: {role_name}")
            else:
                print(f"❌ Error attaching policy: {e}")
                return
        
        print("✅ Lambda permissions fixed successfully!")
        print("🔄 Lambda functions can now invoke each other")
        
    except Exception as e:
        print(f"❌ Error fixing permissions: {e}")

if __name__ == "__main__":
    fix_lambda_permissions()