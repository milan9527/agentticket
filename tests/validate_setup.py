#!/usr/bin/env python3
"""
Validation script to check if the infrastructure setup is ready to run

This script validates the setup without actually creating AWS resources
"""

import os
import sys
from pathlib import Path

def validate_file_structure():
    """Validate that all required files and directories exist"""
    print("🔍 Validating project structure...")
    
    required_files = [
        'README.md',
        '.env.example',
        'requirements.txt',
        'setup.py',
        'infrastructure/setup_aws.py',
        'database/setup_schema.py',
        'backend/shared/__init__.py',
        'backend/agents/__init__.py',
        'backend/lambda/__init__.py',
        'tests/__init__.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files present")
    return True

def validate_scripts():
    """Validate that setup scripts are executable and syntactically correct"""
    print("\n🔍 Validating setup scripts...")
    
    scripts = [
        'setup.py',
        'infrastructure/setup_aws.py',
        'database/setup_schema.py'
    ]
    
    for script in scripts:
        # Check if file is executable
        if not os.access(script, os.X_OK):
            print(f"⚠️  {script} is not executable")
        else:
            print(f"✅ {script} is executable")
        
        # Check syntax
        try:
            with open(script, 'r') as f:
                compile(f.read(), script, 'exec')
            print(f"✅ {script} syntax is valid")
        except SyntaxError as e:
            print(f"❌ {script} has syntax error: {e}")
            return False
    
    return True

def validate_requirements():
    """Validate requirements.txt format"""
    print("\n🔍 Validating requirements.txt...")
    
    try:
        with open('requirements.txt', 'r') as f:
            lines = f.readlines()
        
        required_packages = [
            'boto3',
            'bedrock-agentcore-starter-toolkit',
            'strands-agents',
            'fastmcp',
            'pydantic',
            'pytest',
            'hypothesis'
        ]
        
        content = ''.join(lines)
        missing_packages = []
        
        for package in required_packages:
            if package not in content:
                missing_packages.append(package)
            else:
                print(f"✅ {package} found in requirements")
        
        if missing_packages:
            print(f"❌ Missing required packages: {missing_packages}")
            return False
        
        print("✅ All required packages present in requirements.txt")
        return True
        
    except FileNotFoundError:
        print("❌ requirements.txt not found")
        return False

def validate_env_example():
    """Validate .env.example has required variables"""
    print("\n🔍 Validating .env.example...")
    
    required_vars = [
        'AWS_REGION',
        'DB_CLUSTER_ARN',
        'DB_SECRET_ARN',
        'DATABASE_NAME',
        'AGENTCORE_ENDPOINT',
        'MCP_PORT',
        'COGNITO_USER_POOL_ID'
    ]
    
    try:
        with open('.env.example', 'r') as f:
            content = f.read()
        
        missing_vars = []
        for var in required_vars:
            if var not in content:
                missing_vars.append(var)
            else:
                print(f"✅ {var} found in .env.example")
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
            return False
        
        print("✅ All required environment variables present")
        return True
        
    except FileNotFoundError:
        print("❌ .env.example not found")
        return False

def main():
    """Main validation function"""
    print("🔍 Validating Ticket Auto-Processing System Setup")
    print("=" * 60)
    
    all_valid = True
    
    # Run all validations
    validations = [
        validate_file_structure,
        validate_scripts,
        validate_requirements,
        validate_env_example
    ]
    
    for validation in validations:
        if not validation():
            all_valid = False
    
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ All validations passed!")
        print("🚀 Infrastructure setup is ready to run")
        print("\nTo proceed with actual AWS setup:")
        print("1. Configure AWS credentials: aws configure")
        print("2. Run setup: python setup.py")
    else:
        print("❌ Some validations failed")
        print("Please fix the issues above before proceeding")
        sys.exit(1)

if __name__ == "__main__":
    main()