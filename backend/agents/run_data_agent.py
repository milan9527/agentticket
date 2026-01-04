#!/usr/bin/env python3
"""
Run Data Agent as FastMCP server for development and testing
"""

import asyncio
import signal
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.agents.data_agent import DataAgent, load_config


class DataAgentServer:
    """Data Agent MCP Server wrapper"""
    
    def __init__(self):
        self.agent = None
        self.running = False
    
    async def start(self, host: str = "localhost", port: int = 8001):
        """Start the Data Agent MCP server"""
        try:
            print("🚀 Starting Data Agent MCP Server")
            print("=" * 40)
            
            # Load configuration
            config = load_config()
            
            if not config.db_cluster_arn or not config.db_secret_arn:
                print("❌ Missing required database configuration:")
                print("   DB_CLUSTER_ARN and DB_SECRET_ARN must be set in .env")
                return 1
            
            print(f"✅ Configuration loaded:")
            print(f"   Region: {config.aws_region}")
            print(f"   Database: {config.database_name}")
            print(f"   Model: {config.bedrock_model_id}")
            print(f"   Server: {host}:{port}")
            
            # Create and start agent
            self.agent = DataAgent(config)
            self.running = True
            
            print(f"\n🤖 Data Agent MCP Tools:")
            print(f"   📊 get_customer - Retrieve customer by ID")
            print(f"   👤 create_customer - Create new customer")
            print(f"   🎫 get_tickets_for_customer - Get customer tickets")
            print(f"   🔍 validate_data_integrity - Check database integrity")
            
            print(f"\n🌐 Server starting on http://{host}:{port}")
            print(f"💡 Use Ctrl+C to stop the server")
            print("=" * 40)
            
            # Start the FastMCP server
            await self.agent.start_server(host=host, port=port)
            
        except KeyboardInterrupt:
            print(f"\n👋 Shutting down Data Agent MCP Server...")
            self.running = False
            return 0
        except Exception as e:
            print(f"❌ Error starting Data Agent: {e}")
            import traceback
            traceback.print_exc()
            return 1
    
    def stop(self):
        """Stop the server"""
        self.running = False


async def main():
    """Main function"""
    server = DataAgentServer()
    
    # Handle shutdown signals
    def signal_handler(signum, frame):
        print(f"\n🛑 Received signal {signum}, shutting down...")
        server.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start server
    return await server.start()


if __name__ == "__main__":
    try:
        exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n👋 Data Agent MCP Server stopped")
        exit(0)