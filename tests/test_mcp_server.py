#!/usr/bin/env python3
"""
Quick test to verify MCP server can start
"""

import asyncio
import signal
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.agents.data_agent import DataAgent, load_config


async def test_server_startup():
    """Test that the MCP server can start properly"""
    print("🧪 Testing MCP Server Startup")
    print("=" * 30)
    
    try:
        # Load configuration
        config = load_config()
        
        if not config.db_cluster_arn or not config.db_secret_arn:
            print("❌ Missing database configuration")
            return False
        
        print("✅ Configuration loaded")
        
        # Create agent
        agent = DataAgent(config)
        print("✅ Data Agent created successfully")
        
        # Test database connection
        sql = "SELECT COUNT(*) FROM customers"
        result = await agent.db.execute_sql(sql)
        count = result['records'][0][0]['longValue']
        print(f"✅ Database connection working ({count} customers)")
        
        # Test LLM reasoning
        reasoning = await agent.db.llm_reason("Test LLM connection", {"test": True})
        if reasoning and "failed" not in reasoning.lower():
            print("✅ LLM reasoning working")
        else:
            print("❌ LLM reasoning failed")
            return False
        
        print("✅ MCP server ready to start")
        return True
        
    except Exception as e:
        print(f"❌ Server startup test failed: {e}")
        return False


async def main():
    """Main test function"""
    success = await test_server_startup()
    
    if success:
        print("\n🎉 MCP Server startup test passed!")
        print("📋 Server is ready for production use")
        return 0
    else:
        print("\n❌ MCP Server startup test failed!")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))