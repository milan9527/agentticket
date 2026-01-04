#!/usr/bin/env python3
"""
Setup AgentCore development environment for Ticket Auto-Processing System
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description, check=True):
    """Run a command and handle errors"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"   {result.stdout.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Error: {e}")
        if e.stderr:
            print(f"   {e.stderr.strip()}")
        return False


def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"   ✅ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check AgentCore CLI
    if not run_command("agentcore --help > /dev/null 2>&1", "Checking AgentCore CLI", check=False):
        print("❌ AgentCore CLI not found. Please install bedrock-agentcore-starter-toolkit")
        return False
    print("   ✅ AgentCore CLI available")
    
    # Check AWS credentials
    if not run_command("aws sts get-caller-identity > /dev/null 2>&1", "Checking AWS credentials", check=False):
        print("❌ AWS credentials not configured")
        return False
    print("   ✅ AWS credentials configured")
    
    return True


def setup_environment():
    """Set up the development environment"""
    print("\n🛠️  Setting up AgentCore development environment...")
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found. Please ensure database configuration is set up.")
        return False
    
    # Load environment variables
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                env_vars[key] = value
    
    required_vars = ['DB_CLUSTER_ARN', 'DB_SECRET_ARN', 'BEDROCK_MODEL_ID']
    missing_vars = [var for var in required_vars if var not in env_vars]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    print("   ✅ Environment variables configured")
    
    # Create agents directory if it doesn't exist
    agents_dir = Path("backend/agents")
    agents_dir.mkdir(parents=True, exist_ok=True)
    
    print("   ✅ Agent directory structure ready")
    
    return True


def test_data_agent():
    """Test the Data Agent"""
    print("\n🧪 Testing Data Agent...")
    
    if not run_command("python backend/agents/test_data_agent.py", "Running Data Agent tests"):
        print("❌ Data Agent tests failed")
        return False
    
    print("   ✅ Data Agent tests passed")
    return True


def create_dev_scripts():
    """Create development helper scripts"""
    print("\n📝 Creating development scripts...")
    
    # Create start script for Data Agent
    start_data_agent = """#!/bin/bash
# Start Data Agent MCP Server
echo "🚀 Starting Data Agent MCP Server..."
python backend/agents/run_data_agent.py
"""
    
    with open("start_data_agent.sh", "w") as f:
        f.write(start_data_agent)
    
    os.chmod("start_data_agent.sh", 0o755)
    print("   ✅ Created start_data_agent.sh")
    
    # Create AgentCore dev script
    agentcore_dev = """#!/bin/bash
# Start AgentCore development server
echo "🚀 Starting AgentCore development server..."
agentcore dev --config agentcore.yaml
"""
    
    with open("start_agentcore_dev.sh", "w") as f:
        f.write(agentcore_dev)
    
    os.chmod("start_agentcore_dev.sh", 0o755)
    print("   ✅ Created start_agentcore_dev.sh")
    
    return True


def main():
    """Main setup function"""
    print("🚀 AgentCore Development Environment Setup")
    print("=" * 50)
    
    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites check failed")
        return 1
    
    # Setup environment
    if not setup_environment():
        print("\n❌ Environment setup failed")
        return 1
    
    # Test Data Agent
    if not test_data_agent():
        print("\n❌ Data Agent testing failed")
        return 1
    
    # Create development scripts
    if not create_dev_scripts():
        print("\n❌ Failed to create development scripts")
        return 1
    
    print("\n" + "=" * 50)
    print("✅ AgentCore development environment setup complete!")
    print("\n📋 Next steps:")
    print("1. Start Data Agent MCP server:")
    print("   ./start_data_agent.sh")
    print("\n2. In another terminal, start AgentCore dev server:")
    print("   ./start_agentcore_dev.sh")
    print("\n3. Test the agents:")
    print("   agentcore invoke --agent data-agent --tool get_customer")
    print("\n🎉 Ready for Task 3.2: Implement Data Agent with fastMCP")
    
    return 0


if __name__ == "__main__":
    exit(main())