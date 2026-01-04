#!/usr/bin/env python3
"""
CloudFront Deployment Monitor

This script monitors the CloudFront distribution deployment status and tests
accessibility once the distribution is deployed.

Usage:
    python tests/monitor_cloudfront_deployment.py
"""

import boto3
import json
import time
import requests
from pathlib import Path

def load_deployment_info():
    """Load deployment information"""
    info_file = Path('deployment_info.json')
    if not info_file.exists():
        raise FileNotFoundError("❌ deployment_info.json not found. Run deployment script first.")
    
    with open(info_file, 'r') as f:
        return json.load(f)

def check_distribution_status(distribution_id):
    """Check CloudFront distribution status"""
    cloudfront = boto3.client('cloudfront')
    
    try:
        response = cloudfront.get_distribution(Id=distribution_id)
        distribution = response['Distribution']
        status = distribution.get('Status', 'Unknown')
        
        return status
    except Exception as e:
        print(f"❌ Error checking distribution status: {e}")
        return None

def test_frontend_accessibility(frontend_url):
    """Test if frontend is accessible"""
    try:
        print(f"🌐 Testing accessibility: {frontend_url}")
        response = requests.get(frontend_url, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Frontend is accessible (status: {response.status_code})")
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                print(f"✅ Correct content type: {content_type}")
            
            # Check for React indicators
            content = response.text
            if any(indicator in content for indicator in ['<div id="root"', 'react', 'React']):
                print("✅ React application detected")
            
            return True
        else:
            print(f"❌ Frontend not accessible (status: {response.status_code})")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def main():
    """Main monitoring function"""
    try:
        deployment_info = load_deployment_info()
        distribution_id = deployment_info['distribution_id']
        frontend_url = deployment_info['frontend_url']
        
        print("🔍 CloudFront Deployment Monitor")
        print("=" * 50)
        print(f"Distribution ID: {distribution_id}")
        print(f"Frontend URL: {frontend_url}")
        print("=" * 50)
        
        # Monitor deployment status
        max_wait_time = 20 * 60  # 20 minutes
        check_interval = 30  # 30 seconds
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = check_distribution_status(distribution_id)
            
            if status == 'Deployed':
                print(f"✅ Distribution is deployed! Status: {status}")
                
                # Wait a bit more for DNS propagation
                print("⏳ Waiting 30 seconds for DNS propagation...")
                time.sleep(30)
                
                # Test accessibility
                if test_frontend_accessibility(frontend_url):
                    print("\n🎉 Frontend deployment is fully operational!")
                    print(f"🔗 Access your application at: {frontend_url}")
                    return True
                else:
                    print("\n⚠️  Distribution is deployed but frontend not yet accessible.")
                    print("This may take a few more minutes for global DNS propagation.")
                    return False
                    
            elif status == 'InProgress':
                elapsed = int(time.time() - start_time)
                print(f"⏳ Distribution still deploying... Status: {status} (elapsed: {elapsed//60}m {elapsed%60}s)")
                
            else:
                print(f"❓ Unknown status: {status}")
            
            print(f"   Checking again in {check_interval} seconds...")
            time.sleep(check_interval)
        
        print(f"\n⏰ Timeout reached ({max_wait_time//60} minutes)")
        print("CloudFront deployment is taking longer than expected.")
        print("This is normal for initial deployments. Please check again later.")
        return False
        
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)