#!/usr/bin/env python3
"""
Test script to validate AgentCore agent locally
"""

import os
import sys
import asyncio
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

async def test_agent_initialization():
    """Test if the agent can initialize properly"""
    try:
        print("🔍 Testing AgentCore Data Agent initialization...")
        
        # Check environment variables
        required_vars = ['DB_CLUSTER_ARN', 'DB_SECRET_ARN', 'BEDROCK_MODEL_ID']
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: {value[:50]}...")
            else:
                print(f"❌ {var}: Not set")
        
        # Try to import and initialize the agent
        from backend.agents.agentcore_data_agent import config, db, mcp
        
        print(f"✅ Agent configuration loaded:")
        print(f"   - AWS Region: {config.aws_region}")
        print(f"   - Database: {config.database_name}")
        print(f"   - Model: {config.bedrock_model_id}")
        
        # Test database connection
        print("🔍 Testing database connection...")
        response = await db.execute_sql("SELECT 1 as test")
        print(f"✅ Database connection successful: {response}")
        
        # Test LLM reasoning
        print("🔍 Testing LLM reasoning...")
        reasoning = await db.llm_reason("Test prompt for agent validation")
        print(f"✅ LLM reasoning successful: {reasoning[:100]}...")
        
        # Check MCP tools
        print("🔍 Checking MCP tools...")
        tools = mcp.list_tools()
        print(f"✅ MCP tools available: {len(tools)} tools")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        print("🎉 Agent initialization test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_agent_initialization())
    sys.exit(0 if success else 1)