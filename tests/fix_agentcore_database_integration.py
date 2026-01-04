#!/usr/bin/env python3
"""
Fix AgentCore Database Integration

This script addresses the issue where the deployed AgentCore Ticket Agent
is still using fallback test data instead of real database data via the
Data Agent Invoker Lambda.

The problem: The deployed AgentCore agent has old code that doesn't call
the Data Agent Invoker Lambda.

Solution: Deploy the updated AgentCore Ticket Agent with Lambda integration.
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def check_current_deployment():
    """Check the current AgentCore deployment status"""
    print("🔍 CHECKING CURRENT AGENTCORE DEPLOYMENT")
    print("="*70)
    
    # Check if the updated agent code exists
    agent_file = Path("backend/agents/agentcore_ticket_agent.py")
    if not agent_file.exists():
        print("❌ AgentCore Ticket Agent file not found")
        return False
    
    # Check if the Lambda integration code is present
    with open(agent_file, 'r') as f:
        content = f.read()
    
    if "data-agent-invoker" in content and "lambda_client.invoke" in content:
        print("✅ Updated AgentCore Ticket Agent code found (with Lambda integration)")
        print("   - Contains Data Agent Invoker Lambda calls")
        print("   - Contains boto3 Lambda client usage")
        print("   - Ready for deployment")
        return True
    else:
        print("❌ AgentCore Ticket Agent code is outdated")
        print("   - Missing Lambda integration")
        print("   - Still using fallback data")
        return False

def deploy_updated_agent():
    """Deploy the updated AgentCore Ticket Agent"""
    print("\n🚀 DEPLOYING UPDATED AGENTCORE TICKET AGENT")
    print("="*70)
    
    try:
        # Change to the agents directory
        os.chdir("backend/agents")
        
        print("📦 Deploying AgentCore Ticket Agent with Lambda integration...")
        
        # Deploy the updated agent
        result = subprocess.run([
            "agentcore", "deploy", 
            "--agent", "agentcore_ticket_agent",
            "--auto-update-on-conflict"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ AgentCore Ticket Agent deployment successful!")
            print(f"   Output: {result.stdout}")
            
            # Extract ARN if available
            if "arn:aws:bedrock-agentcore" in result.stdout:
                lines = result.stdout.split('\n')
                for line in lines:
                    if "arn:aws:bedrock-agentcore" in line:
                        print(f"   Agent ARN: {line.strip()}")
            
            return True
        else:
            print("❌ AgentCore deployment failed!")
            print(f"   Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Deployment error: {e}")
        return False
    finally:
        # Return to original directory
        os.chdir("../..")

def test_updated_deployment():
    """Test the updated deployment to verify Lambda integration"""
    print("\n🧪 TESTING UPDATED DEPLOYMENT")
    print("="*70)
    
    try:
        # Run the AgentCore Lambda integration test
        result = subprocess.run([
            "python", "test_agentcore_lambda_integration.py"
        ], capture_output=True, text=True)
        
        if "✅ Using real database data!" in result.stdout:
            print("✅ Lambda integration working!")
            print("   - AgentCore Ticket Agent successfully calls Data Agent Invoker Lambda")
            print("   - Real database data retrieved")
            return True
        elif "⚠️  Using fallback data" in result.stdout:
            print("❌ Still using fallback data")
            print("   - Lambda integration not working")
            print("   - May need to wait for deployment propagation")
            return False
        else:
            print("⚠️  Test results unclear")
            print(f"   Output: {result.stdout[:500]}...")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def verify_lambda_invoker():
    """Verify the Data Agent Invoker Lambda is working"""
    print("\n🔧 VERIFYING DATA AGENT INVOKER LAMBDA")
    print("="*70)
    
    try:
        # Test the Lambda invoker directly
        result = subprocess.run([
            "python", "test_real_database_with_invoker.py"
        ], capture_output=True, text=True)
        
        if "✅ REAL DATABASE DATA RETRIEVED" in result.stdout:
            print("✅ Data Agent Invoker Lambda working correctly")
            print("   - Successfully connects to Aurora database")
            print("   - Retrieves real customer and ticket data")
            return True
        else:
            print("❌ Data Agent Invoker Lambda issues")
            print(f"   Output: {result.stdout[:500]}...")
            return False
            
    except Exception as e:
        print(f"❌ Lambda test error: {e}")
        return False

def main():
    """Main function to fix the AgentCore database integration"""
    print("🎯 FIXING AGENTCORE DATABASE INTEGRATION")
    print("="*70)
    print("Issue: Deployed AgentCore Ticket Agent using fallback data (TKT-TEST789)")
    print("Solution: Deploy updated agent with Data Agent Invoker Lambda integration")
    print()
    
    # Step 1: Check current deployment
    if not check_current_deployment():
        print("\n❌ CANNOT PROCEED: Updated agent code not found")
        return False
    
    # Step 2: Verify Lambda invoker is working
    if not verify_lambda_invoker():
        print("\n❌ CANNOT PROCEED: Data Agent Invoker Lambda not working")
        return False
    
    # Step 3: Deploy updated agent
    print("\n" + "="*70)
    print("🚀 PROCEEDING WITH DEPLOYMENT")
    
    user_input = input("\nDeploy updated AgentCore Ticket Agent? (y/N): ")
    if user_input.lower() != 'y':
        print("❌ Deployment cancelled by user")
        return False
    
    if not deploy_updated_agent():
        print("\n❌ DEPLOYMENT FAILED")
        return False
    
    # Step 4: Test updated deployment
    print("\n⏳ Waiting 30 seconds for deployment propagation...")
    import time
    time.sleep(30)
    
    if test_updated_deployment():
        print("\n🎉 SUCCESS: AgentCore database integration fixed!")
        print("✅ AgentCore Ticket Agent now uses real database data")
        print("✅ Data Agent Invoker Lambda integration working")
        return True
    else:
        print("\n⚠️  Deployment completed but integration test failed")
        print("💡 May need additional time for propagation")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎯 INTEGRATION FIXED")
        print("The AgentCore Ticket Agent now connects to real Aurora database data")
        print("via the Data Agent Invoker Lambda instead of using fallback test data.")
    else:
        print("\n❌ INTEGRATION NOT FIXED")
        print("Manual intervention may be required to deploy the updated agent.")