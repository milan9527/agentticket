#!/usr/bin/env python3
"""
Check Lambda Function Logs

Check the CloudWatch logs for the chat handler to debug the 502 errors.
"""

import boto3
import time
from datetime import datetime, timedelta

def check_lambda_logs():
    """Check Lambda function logs"""
    print("📋 CHECKING LAMBDA LOGS")
    print("=" * 40)
    
    # Initialize CloudWatch Logs client
    logs_client = boto3.client('logs', region_name='us-west-2')
    
    # Log group name for Lambda function
    log_group_name = '/aws/lambda/chat-handler'
    
    try:
        # Get recent log events (last 10 minutes)
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)
        
        print(f"🔍 Checking logs from {start_time.strftime('%H:%M:%S')} to {end_time.strftime('%H:%M:%S')}")
        
        response = logs_client.filter_log_events(
            logGroupName=log_group_name,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000)
        )
        
        events = response.get('events', [])
        
        if not events:
            print("ℹ️ No recent log events found")
            return
        
        print(f"📝 Found {len(events)} log events:")
        print("-" * 60)
        
        for event in events[-20:]:  # Show last 20 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            
            # Color code different types of messages
            if 'ERROR' in message or 'Exception' in message or 'Traceback' in message:
                print(f"❌ {timestamp.strftime('%H:%M:%S')} - {message}")
            elif 'START' in message or 'END' in message or 'REPORT' in message:
                print(f"ℹ️ {timestamp.strftime('%H:%M:%S')} - {message}")
            else:
                print(f"📝 {timestamp.strftime('%H:%M:%S')} - {message}")
        
        print("-" * 60)
        
    except Exception as e:
        print(f"❌ Failed to check logs: {e}")

if __name__ == "__main__":
    check_lambda_logs()