#!/usr/bin/env python3
"""
Frontend Deployment Test Script

This script validates the frontend deployment to S3 + CloudFront:
- Tests S3 bucket configuration and security
- Tests CloudFront distribution setup
- Tests frontend accessibility and functionality
- Validates Origin Access Control (OAC) security

Usage:
    python tests/test_frontend_deployment.py
    
Requirements:
    - deployment_info.json (created by deploy_frontend_s3_cloudfront.py)
    - AWS CLI configured with appropriate permissions
"""

import boto3
import json
import requests
import time
from pathlib import Path
from typing import Dict, Any, List

class FrontendDeploymentTest:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.cloudfront = boto3.client('cloudfront')
        
        # Load deployment info
        self.deployment_info = self.load_deployment_info()
        
    def load_deployment_info(self) -> Dict[str, Any]:
        """Load deployment information from JSON file"""
        info_file = Path('deployment_info.json')
        if not info_file.exists():
            raise FileNotFoundError("❌ deployment_info.json not found. Run deployment script first.")
        
        with open(info_file, 'r') as f:
            info = json.load(f)
        
        print(f"✓ Loaded deployment info for distribution: {info['distribution_id']}")
        return info
    
    def test_s3_bucket_security(self) -> bool:
        """Test S3 bucket security configuration"""
        print("\n🔒 Testing S3 bucket security configuration...")
        
        bucket_name = self.deployment_info['bucket_name']
        
        try:
            # Test 1: Verify public access is blocked
            print("  Testing public access block...")
            response = self.s3.get_public_access_block(Bucket=bucket_name)
            config = response['PublicAccessBlockConfiguration']
            
            security_checks = [
                ('BlockPublicAcls', config.get('BlockPublicAcls', False)),
                ('IgnorePublicAcls', config.get('IgnorePublicAcls', False)),
                ('BlockPublicPolicy', config.get('BlockPublicPolicy', False)),
                ('RestrictPublicBuckets', config.get('RestrictPublicBuckets', False))
            ]
            
            all_blocked = all(check[1] for check in security_checks)
            
            for check_name, is_blocked in security_checks:
                status = "✅" if is_blocked else "❌"
                print(f"    {status} {check_name}: {is_blocked}")
            
            if not all_blocked:
                print("  ❌ S3 bucket is not properly secured!")
                return False
            
            # Test 2: Verify bucket policy allows only CloudFront
            print("  Testing bucket policy...")
            try:
                policy_response = self.s3.get_bucket_policy(Bucket=bucket_name)
                policy = json.loads(policy_response['Policy'])
                
                # Check if policy allows CloudFront service principal
                cloudfront_allowed = False
                for statement in policy.get('Statement', []):
                    principal = statement.get('Principal', {})
                    if isinstance(principal, dict) and principal.get('Service') == 'cloudfront.amazonaws.com':
                        cloudfront_allowed = True
                        break
                
                if cloudfront_allowed:
                    print("    ✅ Bucket policy allows CloudFront access")
                else:
                    print("    ❌ Bucket policy does not properly allow CloudFront")
                    return False
                    
            except self.s3.exceptions.NoSuchBucketPolicy:
                print("    ❌ No bucket policy found")
                return False
            
            # Test 3: Try direct S3 access (should fail)
            print("  Testing direct S3 access (should be blocked)...")
            s3_url = f"https://{bucket_name}.s3.amazonaws.com/index.html"
            
            try:
                response = requests.get(s3_url, timeout=10)
                if response.status_code == 403:
                    print("    ✅ Direct S3 access properly blocked (403 Forbidden)")
                else:
                    print(f"    ❌ Direct S3 access not blocked (status: {response.status_code})")
                    return False
            except requests.exceptions.RequestException:
                print("    ✅ Direct S3 access blocked (connection failed)")
            
            print("✅ S3 bucket security tests passed")
            return True
            
        except Exception as e:
            print(f"❌ S3 security test failed: {e}")
            return False
    
    def test_cloudfront_distribution(self) -> bool:
        """Test CloudFront distribution configuration"""
        print("\n☁️  Testing CloudFront distribution configuration...")
        
        distribution_id = self.deployment_info['distribution_id']
        
        try:
            # Get distribution configuration
            response = self.cloudfront.get_distribution(Id=distribution_id)
            distribution = response['Distribution']
            config = distribution['DistributionConfig']
            
            # Test 1: Verify distribution is enabled
            if config.get('Enabled', False):
                print("  ✅ Distribution is enabled")
            else:
                print("  ❌ Distribution is not enabled")
                return False
            
            # Test 2: Verify HTTPS redirect
            default_behavior = config.get('DefaultCacheBehavior', {})
            viewer_protocol = default_behavior.get('ViewerProtocolPolicy', '')
            
            if viewer_protocol == 'redirect-to-https':
                print("  ✅ HTTPS redirect is configured")
            else:
                print(f"  ❌ HTTPS redirect not configured (policy: {viewer_protocol})")
                return False
            
            # Test 3: Verify Origin Access Control
            origins = config.get('Origins', {}).get('Items', [])
            if origins:
                origin = origins[0]
                oac_id = origin.get('OriginAccessControlId', '')
                if oac_id:
                    print(f"  ✅ Origin Access Control configured: {oac_id}")
                else:
                    print("  ❌ Origin Access Control not configured")
                    return False
            
            # Test 4: Verify custom error pages for SPA
            error_responses = config.get('CustomErrorResponses', {}).get('Items', [])
            spa_routing_configured = False
            
            for error_response in error_responses:
                if (error_response.get('ErrorCode') == 404 and 
                    error_response.get('ResponsePagePath') == '/index.html' and
                    error_response.get('ResponseCode') == '200'):
                    spa_routing_configured = True
                    break
            
            if spa_routing_configured:
                print("  ✅ SPA routing (404 -> index.html) configured")
            else:
                print("  ❌ SPA routing not properly configured")
                return False
            
            # Test 5: Check distribution status
            status = distribution.get('Status', '')
            if status == 'Deployed':
                print("  ✅ Distribution is deployed")
            else:
                print(f"  ⏳ Distribution status: {status} (may still be deploying)")
            
            print("✅ CloudFront distribution tests passed")
            return True
            
        except Exception as e:
            print(f"❌ CloudFront test failed: {e}")
            return False
    
    def test_frontend_accessibility(self) -> bool:
        """Test frontend accessibility through CloudFront"""
        print("\n🌐 Testing frontend accessibility...")
        
        frontend_url = self.deployment_info['frontend_url']
        
        try:
            # Test 1: Basic connectivity
            print(f"  Testing connectivity to {frontend_url}...")
            response = requests.get(frontend_url, timeout=30)
            
            if response.status_code == 200:
                print("  ✅ Frontend is accessible")
            else:
                print(f"  ❌ Frontend not accessible (status: {response.status_code})")
                return False
            
            # Test 2: Content type
            content_type = response.headers.get('content-type', '')
            if 'text/html' in content_type:
                print("  ✅ Correct content type (HTML)")
            else:
                print(f"  ❌ Incorrect content type: {content_type}")
                return False
            
            # Test 3: Check for React app indicators
            content = response.text
            react_indicators = [
                '<div id="root"',
                'react',
                'React'
            ]
            
            react_found = any(indicator in content for indicator in react_indicators)
            if react_found:
                print("  ✅ React application detected")
            else:
                print("  ⚠️  React application indicators not found (may be minified)")
            
            # Test 4: HTTPS enforcement
            if frontend_url.startswith('https://'):
                print("  ✅ HTTPS URL confirmed")
            else:
                print("  ❌ Not using HTTPS")
                return False
            
            # Test 5: Test SPA routing (404 handling)
            print("  Testing SPA routing...")
            spa_test_url = f"{frontend_url}/nonexistent-route"
            spa_response = requests.get(spa_test_url, timeout=30)
            
            if spa_response.status_code == 200:
                print("  ✅ SPA routing works (404 -> 200)")
            else:
                print(f"  ❌ SPA routing failed (status: {spa_response.status_code})")
                return False
            
            print("✅ Frontend accessibility tests passed")
            return True
            
        except requests.exceptions.Timeout:
            print("  ❌ Request timeout - distribution may still be deploying")
            return False
        except requests.exceptions.RequestException as e:
            print(f"  ❌ Request failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Frontend accessibility test failed: {e}")
            return False
    
    def test_performance_and_caching(self) -> bool:
        """Test performance and caching configuration"""
        print("\n⚡ Testing performance and caching...")
        
        frontend_url = self.deployment_info['frontend_url']
        
        try:
            # Test 1: Response time
            start_time = time.time()
            response = requests.get(frontend_url, timeout=30)
            response_time = time.time() - start_time
            
            print(f"  Response time: {response_time:.2f}s")
            if response_time < 5.0:
                print("  ✅ Good response time")
            else:
                print("  ⚠️  Slow response time (may improve after cache warm-up)")
            
            # Test 2: Compression
            encoding = response.headers.get('content-encoding', '')
            if 'gzip' in encoding or 'br' in encoding:
                print(f"  ✅ Content compression enabled: {encoding}")
            else:
                print("  ⚠️  Content compression not detected")
            
            # Test 3: Cache headers
            cache_control = response.headers.get('cache-control', '')
            if cache_control:
                print(f"  ✅ Cache control headers present: {cache_control}")
            else:
                print("  ⚠️  No cache control headers")
            
            # Test 4: CloudFront headers
            cf_headers = [
                'x-amz-cf-pop',
                'x-amz-cf-id',
                'x-cache'
            ]
            
            cf_detected = False
            for header in cf_headers:
                if header in response.headers:
                    cf_detected = True
                    print(f"  ✅ CloudFront header detected: {header}")
                    break
            
            if not cf_detected:
                print("  ⚠️  CloudFront headers not detected")
            
            print("✅ Performance and caching tests completed")
            return True
            
        except Exception as e:
            print(f"❌ Performance test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """Run all deployment tests"""
        print("🧪 Running Frontend Deployment Tests")
        print("=" * 50)
        
        test_results = []
        
        # Run all tests
        tests = [
            ("S3 Bucket Security", self.test_s3_bucket_security),
            ("CloudFront Distribution", self.test_cloudfront_distribution),
            ("Frontend Accessibility", self.test_frontend_accessibility),
            ("Performance & Caching", self.test_performance_and_caching)
        ]
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                test_results.append((test_name, result))
            except Exception as e:
                print(f"❌ {test_name} test failed with exception: {e}")
                test_results.append((test_name, False))
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Results Summary")
        print("=" * 50)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {test_name}")
            if result:
                passed += 1
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Frontend deployment is successful.")
            print(f"\n🔗 Your frontend is live at: {self.deployment_info['frontend_url']}")
            return True
        else:
            print("⚠️  Some tests failed. Please review the issues above.")
            return False

def main():
    """Main function to run deployment tests"""
    try:
        tester = FrontendDeploymentTest()
        success = tester.run_all_tests()
        
        if success:
            print("\n✅ Frontend deployment validation completed successfully!")
        else:
            print("\n❌ Frontend deployment validation failed!")
            exit(1)
            
    except Exception as e:
        print(f"\n💥 Test execution failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()