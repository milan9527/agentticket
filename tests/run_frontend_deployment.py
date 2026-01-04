#!/usr/bin/env python3
"""
Simple Frontend Deployment Runner

This script provides a simple interface to deploy and test the frontend.

Usage:
    python tests/run_frontend_deployment.py [action]
    
Actions:
    deploy    - Deploy frontend to S3 + CloudFront (default)
    test      - Test existing deployment
    both      - Deploy and then test
    
Examples:
    python tests/run_frontend_deployment.py
    python tests/run_frontend_deployment.py deploy
    python tests/run_frontend_deployment.py test
    python tests/run_frontend_deployment.py both
"""

import sys
import subprocess
from pathlib import Path

def run_deployment():
    """Run the frontend deployment"""
    print("🚀 Starting frontend deployment...")
    
    script_path = Path(__file__).parent / "deploy_frontend_s3_cloudfront.py"
    
    try:
        result = subprocess.run([sys.executable, str(script_path)], check=True)
        print("✅ Deployment completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Deployment failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        return False

def run_tests():
    """Run the deployment tests"""
    print("🧪 Starting deployment tests...")
    
    script_path = Path(__file__).parent / "test_frontend_deployment.py"
    
    try:
        result = subprocess.run([sys.executable, str(script_path)], check=True)
        print("✅ Tests completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Tests failed: {e}")
        return False

def main():
    """Main function"""
    action = sys.argv[1] if len(sys.argv) > 1 else "deploy"
    
    print(f"Frontend Deployment Runner - Action: {action}")
    print("=" * 50)
    
    if action == "deploy":
        success = run_deployment()
    elif action == "test":
        success = run_tests()
    elif action == "both":
        print("Running deployment followed by tests...\n")
        deploy_success = run_deployment()
        if deploy_success:
            print("\n" + "="*50)
            test_success = run_tests()
            success = deploy_success and test_success
        else:
            success = False
    else:
        print(f"❌ Unknown action: {action}")
        print("Valid actions: deploy, test, both")
        sys.exit(1)
    
    if success:
        print(f"\n🎉 Action '{action}' completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 Action '{action}' failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()