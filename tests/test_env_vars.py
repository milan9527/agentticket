#!/usr/bin/env python3
"""
Test environment variables loading
"""

import os

# Load environment variables from .env file
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

print("🔍 Environment Variables:")
print(f"   COGNITO_CLIENT_ID: {os.getenv('COGNITO_CLIENT_ID')}")
print(f"   COGNITO_TEST_USER: {os.getenv('COGNITO_TEST_USER')}")
print(f"   COGNITO_TEST_PASSWORD: {'***' if os.getenv('COGNITO_TEST_PASSWORD') else None}")
print(f"   TICKET_AGENT_ARN: {os.getenv('TICKET_AGENT_ARN')}")
print(f"   API_GATEWAY_URL: {os.getenv('API_GATEWAY_URL')}")