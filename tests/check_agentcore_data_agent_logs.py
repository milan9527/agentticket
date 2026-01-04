#!/usr/bin/env python3
"""
Check AgentCore Data Agent Logs

This script checks the CloudWatch logs for the AgentCore Data Agent to see
if it's properly accessing Aurora database and handling requests.
"""

import boto3
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_agentcore_log_groups():
    """Get all AgentCore-related log groups"""
    try:
        logs_client = boto3.client('logs', region_name='us-west-2')
        
        # Get log groups with AgentCore pattern
        response = logs_client.describe_log_groups(
            logGroupNamePrefix='/aws/bedrock-agentcore'
        )
        
        log_groups = response.get('logGroups', [])
        
        print("🔍 AGENTCORE LOG GROUPS FOUND:")
        print("=" * 60)
        
        for log_group in log_groups:
            name = log_group['logGroupName']
            creation_time = datetime.fromtimestamp(log_group['creationTime'] / 1000)
            size_bytes = log_group.get('storedBytes', 0)
            
            print(f"📋 Log Group: {name}")
            print(f"   Created: {creation_time}")
            print(f"   Size: {size_bytes} bytes")
            
            # Check if this is a data agent log group
            if 'data' in name.lower():
                print(f"   🎯 DATA AGENT LOG GROUP FOUND!")
        
        return log_groups
        
    except Exception as e:
        print(f"❌ Failed to get log groups: {e}")
        return []

def get_recent_logs(log_group_name, hours=2):
    """Get recent logs from a specific log group"""
    try:
        logs_client = boto3.client('logs', region_name='us-west-2')
        
        # Calculate time range (last 2 hours)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        
        print(f"\n📊 RECENT LOGS FROM: {log_group_name}")
        print(f"   Time Range: {start_time} to {end_time}")
        print("=" * 80)
        
        # Get log streams
        streams_response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        log_streams = streams_response.get('logStreams', [])
        
        if not log_streams:
            print("   ⚠️  No log streams found")
            return []
        
        all_events = []
        
        for stream in log_streams:
            stream_name = stream['logStreamName']
            print(f"\n📝 Log Stream: {stream_name}")
            
            try:
                # Get events from this stream
                events_response = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream_name,
                    startTime=start_timestamp,
                    endTime=end_timestamp,
                    limit=50
                )
                
                events = events_response.get('events', [])
                
                if events:
                    print(f"   📈 Found {len(events)} events")
                    
                    for event in events[-10:]:  # Show last 10 events
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        message = event['message'].strip()
                        
                        print(f"   {timestamp}: {message[:200]}...")
                        
                        # Look for specific patterns
                        if 'aurora' in message.lower() or 'database' in message.lower():
                            print(f"      🎯 DATABASE ACTIVITY DETECTED!")
                        
                        if 'error' in message.lower() or 'exception' in message.lower():
                            print(f"      🚨 ERROR DETECTED!")
                        
                        if 'mcp' in message.lower():
                            print(f"      🔧 MCP ACTIVITY DETECTED!")
                    
                    all_events.extend(events)
                else:
                    print(f"   📭 No events in time range")
                    
            except Exception as e:
                print(f"   ❌ Failed to get events from stream {stream_name}: {e}")
        
        return all_events
        
    except Exception as e:
        print(f"❌ Failed to get logs from {log_group_name}: {e}")
        return []

def analyze_data_agent_activity(events):
    """Analyze Data Agent activity from log events"""
    print(f"\n🔍 DATA AGENT ACTIVITY ANALYSIS")
    print("=" * 60)
    
    if not events:
        print("❌ No events to analyze")
        return
    
    # Count different types of activities
    database_calls = 0
    mcp_calls = 0
    errors = 0
    aurora_mentions = 0
    
    recent_activities = []
    
    for event in events:
        message = event['message'].lower()
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        
        if 'aurora' in message or 'rds' in message:
            aurora_mentions += 1
            recent_activities.append(f"{timestamp}: Aurora/RDS activity")
        
        if 'database' in message or 'sql' in message:
            database_calls += 1
            recent_activities.append(f"{timestamp}: Database activity")
        
        if 'mcp' in message:
            mcp_calls += 1
            recent_activities.append(f"{timestamp}: MCP activity")
        
        if 'error' in message or 'exception' in message or 'failed' in message:
            errors += 1
            recent_activities.append(f"{timestamp}: ERROR - {event['message'][:100]}")
    
    print(f"📊 ACTIVITY SUMMARY:")
    print(f"   Total Events: {len(events)}")
    print(f"   Aurora Mentions: {aurora_mentions}")
    print(f"   Database Calls: {database_calls}")
    print(f"   MCP Calls: {mcp_calls}")
    print(f"   Errors: {errors}")
    
    if recent_activities:
        print(f"\n📋 RECENT ACTIVITIES (Last 10):")
        for activity in recent_activities[-10:]:
            print(f"   {activity}")
    
    # Assessment
    if aurora_mentions > 0:
        print(f"\n✅ AURORA ACCESS: Data Agent is accessing Aurora database")
    else:
        print(f"\n⚠️  NO AURORA ACCESS: Data Agent may not be connecting to Aurora")
    
    if database_calls > 0:
        print(f"✅ DATABASE ACTIVITY: Data Agent is performing database operations")
    else:
        print(f"⚠️  NO DATABASE ACTIVITY: Data Agent may not be querying database")
    
    if errors > 0:
        print(f"🚨 ERRORS DETECTED: {errors} errors found - investigation needed")
    else:
        print(f"✅ NO ERRORS: Data Agent operating without errors")

def test_data_agent_directly():
    """Test the Data Agent directly to see if it responds"""
    print(f"\n🧪 TESTING DATA AGENT DIRECTLY")
    print("=" * 60)
    
    try:
        # Import the AgentCore client
        import sys
        sys.path.insert(0, 'backend/lambda')
        from agentcore_client import create_client
        
        print(f"🔧 Creating AgentCore client...")
        client = create_client()
        
        print(f"🎯 Testing Data Agent MCP tool...")
        
        # Test the data agent
        import asyncio
        
        async def test_data_agent():
            result = await client.call_data_agent_tool('get_customer', {
                'customer_id': 'test-customer-123'
            })
            return result
        
        result = asyncio.run(test_data_agent())
        
        print(f"📋 Data Agent Test Result:")
        print(f"   Success: {result.get('success')}")
        print(f"   Data: {json.dumps(result.get('data', {}), indent=2)[:500]}...")
        
        if result.get('success'):
            print(f"✅ DATA AGENT RESPONDING: Agent is accessible and responding")
        else:
            print(f"❌ DATA AGENT ISSUE: {result.get('error', 'Unknown error')}")
        
        return result.get('success', False)
        
    except Exception as e:
        print(f"❌ Data Agent test failed: {e}")
        return False

def main():
    """Main function to check Data Agent logs and status"""
    print("🔍 AGENTCORE DATA AGENT LOG ANALYSIS")
    print("Checking if Data Agent is properly accessing Aurora database")
    print("=" * 70)
    
    # Get all AgentCore log groups
    log_groups = get_agentcore_log_groups()
    
    if not log_groups:
        print("❌ No AgentCore log groups found")
        return
    
    # Look for Data Agent specific log groups
    data_agent_logs = []
    for log_group in log_groups:
        name = log_group['logGroupName']
        if 'data' in name.lower() or 'agentcore_data_agent' in name:
            data_agent_logs.append(name)
    
    if data_agent_logs:
        print(f"\n🎯 FOUND {len(data_agent_logs)} DATA AGENT LOG GROUPS:")
        for log_name in data_agent_logs:
            print(f"   📋 {log_name}")
        
        # Get recent logs from each Data Agent log group
        all_events = []
        for log_name in data_agent_logs:
            events = get_recent_logs(log_name, hours=4)  # Check last 4 hours
            all_events.extend(events)
        
        # Analyze the collected events
        analyze_data_agent_activity(all_events)
    else:
        print(f"\n⚠️  NO DATA AGENT LOG GROUPS FOUND")
        print(f"   This could mean:")
        print(f"   - Data Agent hasn't been invoked recently")
        print(f"   - Data Agent is not deployed")
        print(f"   - Log group naming is different")
    
    # Test Data Agent directly
    agent_working = test_data_agent_directly()
    
    # Final assessment
    print(f"\n🎯 FINAL ASSESSMENT:")
    if data_agent_logs and agent_working:
        print(f"✅ DATA AGENT STATUS: OPERATIONAL")
        print(f"   - Log groups exist and accessible")
        print(f"   - Agent responds to direct calls")
        print(f"   - Ready for Aurora database access")
    elif agent_working:
        print(f"⚠️  DATA AGENT STATUS: WORKING BUT LIMITED LOGS")
        print(f"   - Agent responds to direct calls")
        print(f"   - May not have recent activity or different log location")
    else:
        print(f"🚨 DATA AGENT STATUS: ISSUES DETECTED")
        print(f"   - Agent may not be properly deployed")
        print(f"   - Database access may be impaired")
        print(f"   - Investigation required")

if __name__ == "__main__":
    main()