#!/usr/bin/env python3
"""
Authentication Handler Lambda Function

Handles user authentication with Cognito and returns JWT tokens.
"""

import json
import boto3
import os
from typing import Dict, Any


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for authentication
    
    Expected event structure:
    {
        "httpMethod": "POST",
        "body": "{\"email\": \"user@example.com\", \"password\": \"password\"}"
    }
    """
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    try:
        # Handle preflight OPTIONS request
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight'})
            }
        
        # Parse request body
        if 'body' not in event or not event['body']:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing request body'})
            }
        
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')
        
        if not email or not password:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Email and password are required'})
            }
        
        # Get Cognito configuration
        cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
        aws_region = os.getenv('AWS_REGION', 'us-west-2')
        
        if not cognito_client_id:
            return {
                'statusCode': 500,
                'headers': headers,
                'body': json.dumps({'error': 'Cognito configuration missing'})
            }
        
        # Initialize Cognito client
        cognito_client = boto3.client('cognito-idp', region_name=aws_region)
        
        # Authenticate user
        response = cognito_client.initiate_auth(
            ClientId=cognito_client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': password
            }
        )
        
        # Extract tokens
        auth_result = response['AuthenticationResult']
        access_token = auth_result['AccessToken']
        id_token = auth_result['IdToken']
        refresh_token = auth_result.get('RefreshToken')
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'tokens': {
                    'access_token': access_token,
                    'id_token': id_token,
                    'refresh_token': refresh_token
                },
                'expires_in': auth_result.get('ExpiresIn', 3600)
            })
        }
        
    except cognito_client.exceptions.NotAuthorizedException:
        return {
            'statusCode': 401,
            'headers': headers,
            'body': json.dumps({'error': 'Invalid email or password'})
        }
    except cognito_client.exceptions.UserNotFoundException:
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': 'User not found'})
        }
    except Exception as e:
        print(f"Authentication error: {e}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': 'Internal server error'})
        }


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token with Cognito
    
    Returns user information if token is valid
    """
    try:
        cognito_client = boto3.client('cognito-idp', region_name=os.getenv('AWS_REGION', 'us-west-2'))
        
        response = cognito_client.get_user(AccessToken=token)
        
        # Extract user attributes
        user_attributes = {}
        for attr in response.get('UserAttributes', []):
            user_attributes[attr['Name']] = attr['Value']
        
        return {
            'success': True,
            'username': response.get('Username'),
            'attributes': user_attributes
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }