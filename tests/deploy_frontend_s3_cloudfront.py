#!/usr/bin/env python3
"""
Frontend Deployment Script for S3 + CloudFront
Task 10: Deploy frontend to CloudFront and S3

This script handles:
- Task 10.1: Configure S3 bucket for static hosting
- Task 10.2: Set up CloudFront distribution  
- Task 10.3: Deploy React application

Usage:
    python tests/deploy_frontend_s3_cloudfront.py
    
Requirements:
    - AWS CLI configured with appropriate permissions
    - Frontend built (npm run build in frontend directory)
    - .env file with AWS configuration
"""

import boto3
import json
import os
import subprocess
import time
from typing import Dict, Any, Optional
from pathlib import Path

class FrontendDeployment:
    def __init__(self, region: str = 'us-west-2'):
        self.region = region
        self.s3 = boto3.client('s3', region_name=region)
        self.cloudfront = boto3.client('cloudfront', region_name=region)
        self.sts = boto3.client('sts', region_name=region)
        
        # Get account ID
        self.account_id = self.sts.get_caller_identity()['Account']
        
        # Load environment configuration
        self.load_env_config()
        
    def load_env_config(self):
        """Load configuration from .env file"""
        env_path = Path('.env')
        if not env_path.exists():
            raise FileNotFoundError("❌ .env file not found. Run infrastructure/setup_aws.py first.")
        
        self.config = {}
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    self.config[key] = value
        
        print(f"✓ Loaded configuration from .env")
        
    def build_react_app(self) -> bool:
        """Build the React application for production"""
        print("🔨 Building React application for production...")
        
        frontend_dir = Path('frontend')
        if not frontend_dir.exists():
            print("❌ Frontend directory not found")
            return False
        
        try:
            # Check if node_modules exists
            if not (frontend_dir / 'node_modules').exists():
                print("📦 Installing npm dependencies...")
                subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
            
            # Build the application
            print("🏗️  Building production build...")
            result = subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, check=True, capture_output=True, text=True)
            
            # Check if build directory was created
            build_dir = frontend_dir / 'build'
            if build_dir.exists():
                print(f"✅ React app built successfully at {build_dir}")
                return True
            else:
                print("❌ Build directory not found after build")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            if e.stdout:
                print(f"STDOUT: {e.stdout}")
            if e.stderr:
                print(f"STDERR: {e.stderr}")
            return False
        except FileNotFoundError:
            print("❌ npm not found. Please install Node.js and npm")
            return False
    
    def configure_s3_bucket(self) -> str:
        """Task 10.1: Configure S3 bucket for static hosting"""
        print("\n📦 Task 10.1: Configuring S3 bucket for static hosting...")
        
        bucket_name = self.config.get('S3_BUCKET_NAME')
        if not bucket_name:
            bucket_name = f"ticket-system-frontend-{self.account_id}"
            print(f"Using default bucket name: {bucket_name}")
        
        try:
            # Check if bucket exists
            try:
                self.s3.head_bucket(Bucket=bucket_name)
                print(f"✓ S3 bucket {bucket_name} already exists")
            except:
                # Create bucket if it doesn't exist
                print(f"Creating S3 bucket: {bucket_name}")
                if self.region == 'us-east-1':
                    self.s3.create_bucket(Bucket=bucket_name)
                else:
                    self.s3.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={'LocationConstraint': self.region}
                    )
            
            # Ensure public access is blocked (security requirement)
            print("🔒 Blocking public access to S3 bucket...")
            self.s3.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    'BlockPublicAcls': True,
                    'IgnorePublicAcls': True,
                    'BlockPublicPolicy': True,
                    'RestrictPublicBuckets': True
                }
            )
            
            # Configure bucket for static website hosting
            print("🌐 Configuring static website hosting...")
            self.s3.put_bucket_website(
                Bucket=bucket_name,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': 'index.html'},
                    'ErrorDocument': {'Key': 'index.html'}  # SPA routing
                }
            )
            
            print(f"✅ Task 10.1 Complete: S3 bucket configured")
            return bucket_name
            
        except Exception as e:
            print(f"❌ Failed to configure S3 bucket: {e}")
            raise
    
    def create_cloudfront_distribution(self, bucket_name: str) -> Dict[str, str]:
        """Task 10.2: Set up CloudFront distribution with Origin Access Control"""
        print("\n☁️  Task 10.2: Setting up CloudFront distribution...")
        
        try:
            # Create Origin Access Control (OAC) for secure S3 access
            print("🔐 Creating Origin Access Control...")
            
            oac_name = f"ticket-system-oac-{int(time.time())}"
            oac_response = self.cloudfront.create_origin_access_control(
                OriginAccessControlConfig={
                    'Name': oac_name,
                    'Description': 'OAC for Ticket System Frontend',
                    'OriginAccessControlOriginType': 's3',
                    'SigningBehavior': 'always',
                    'SigningProtocol': 'sigv4'
                }
            )
            
            oac_id = oac_response['OriginAccessControl']['Id']
            print(f"✓ Created OAC: {oac_id}")
            
            # Create CloudFront distribution
            print("🌍 Creating CloudFront distribution...")
            
            distribution_config = {
                'CallerReference': f"ticket-system-{int(time.time())}",
                'Comment': 'Ticket System Frontend Distribution',
                'DefaultRootObject': 'index.html',
                'Origins': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'Id': f"{bucket_name}-origin",
                            'DomainName': f"{bucket_name}.s3.{self.region}.amazonaws.com",
                            'S3OriginConfig': {
                                'OriginAccessIdentity': ''  # Empty for OAC
                            },
                            'OriginAccessControlId': oac_id
                        }
                    ]
                },
                'DefaultCacheBehavior': {
                    'TargetOriginId': f"{bucket_name}-origin",
                    'ViewerProtocolPolicy': 'redirect-to-https',
                    'TrustedSigners': {
                        'Enabled': False,
                        'Quantity': 0
                    },
                    'ForwardedValues': {
                        'QueryString': False,
                        'Cookies': {'Forward': 'none'}
                    },
                    'MinTTL': 0,
                    'DefaultTTL': 86400,
                    'MaxTTL': 31536000,
                    'Compress': True
                },
                'CustomErrorResponses': {
                    'Quantity': 1,
                    'Items': [
                        {
                            'ErrorCode': 404,
                            'ResponsePagePath': '/index.html',
                            'ResponseCode': '200',
                            'ErrorCachingMinTTL': 300
                        }
                    ]
                },
                'Enabled': True,
                'PriceClass': 'PriceClass_100'  # Use only North America and Europe
            }
            
            distribution_response = self.cloudfront.create_distribution(
                DistributionConfig=distribution_config
            )
            
            distribution_id = distribution_response['Distribution']['Id']
            domain_name = distribution_response['Distribution']['DomainName']
            
            print(f"✓ Created CloudFront distribution: {distribution_id}")
            print(f"✓ Domain name: {domain_name}")
            
            # Update S3 bucket policy to allow CloudFront OAC access
            print("🔗 Updating S3 bucket policy for CloudFront access...")
            
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowCloudFrontServicePrincipal",
                        "Effect": "Allow",
                        "Principal": {"Service": "cloudfront.amazonaws.com"},
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{bucket_name}/*",
                        "Condition": {
                            "StringEquals": {
                                "AWS:SourceArn": f"arn:aws:cloudfront::{self.account_id}:distribution/{distribution_id}"
                            }
                        }
                    }
                ]
            }
            
            self.s3.put_bucket_policy(
                Bucket=bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            
            print(f"✅ Task 10.2 Complete: CloudFront distribution created")
            
            return {
                'distribution_id': distribution_id,
                'domain_name': domain_name,
                'oac_id': oac_id
            }
            
        except Exception as e:
            print(f"❌ Failed to create CloudFront distribution: {e}")
            raise
    
    def deploy_react_app(self, bucket_name: str) -> bool:
        """Task 10.3: Deploy React application to S3"""
        print("\n🚀 Task 10.3: Deploying React application to S3...")
        
        build_dir = Path('frontend/build')
        if not build_dir.exists():
            print("❌ Build directory not found. Run build first.")
            return False
        
        try:
            # Upload all files from build directory
            print("📤 Uploading files to S3...")
            
            uploaded_files = 0
            for file_path in build_dir.rglob('*'):
                if file_path.is_file():
                    # Calculate S3 key (relative path from build directory)
                    s3_key = str(file_path.relative_to(build_dir)).replace('\\', '/')
                    
                    # Determine content type
                    content_type = self._get_content_type(file_path.suffix)
                    
                    # Upload file
                    self.s3.upload_file(
                        str(file_path),
                        bucket_name,
                        s3_key,
                        ExtraArgs={
                            'ContentType': content_type,
                            'CacheControl': 'max-age=31536000' if s3_key != 'index.html' else 'no-cache'
                        }
                    )
                    
                    uploaded_files += 1
                    if uploaded_files % 10 == 0:
                        print(f"  Uploaded {uploaded_files} files...")
            
            print(f"✅ Task 10.3 Complete: Uploaded {uploaded_files} files to S3")
            return True
            
        except Exception as e:
            print(f"❌ Failed to deploy React app: {e}")
            return False
    
    def _get_content_type(self, file_extension: str) -> str:
        """Get appropriate content type for file extension"""
        content_types = {
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject'
        }
        return content_types.get(file_extension.lower(), 'application/octet-stream')
    
    def invalidate_cloudfront_cache(self, distribution_id: str) -> bool:
        """Invalidate CloudFront cache after deployment"""
        print("🔄 Invalidating CloudFront cache...")
        
        try:
            invalidation_response = self.cloudfront.create_invalidation(
                DistributionId=distribution_id,
                InvalidationBatch={
                    'Paths': {
                        'Quantity': 1,
                        'Items': ['/*']
                    },
                    'CallerReference': f"invalidation-{int(time.time())}"
                }
            )
            
            invalidation_id = invalidation_response['Invalidation']['Id']
            print(f"✓ Created cache invalidation: {invalidation_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to invalidate cache: {e}")
            return False
    
    def deploy_complete_frontend(self) -> Dict[str, Any]:
        """Execute complete frontend deployment (Tasks 10.1, 10.2, 10.3)"""
        print("🚀 Starting complete frontend deployment to S3 + CloudFront")
        print("=" * 70)
        
        try:
            # Build React app
            if not self.build_react_app():
                raise Exception("Failed to build React application")
            
            # Task 10.1: Configure S3 bucket
            bucket_name = self.configure_s3_bucket()
            
            # Task 10.2: Create CloudFront distribution
            cloudfront_info = self.create_cloudfront_distribution(bucket_name)
            
            # Task 10.3: Deploy React application
            if not self.deploy_react_app(bucket_name):
                raise Exception("Failed to deploy React application")
            
            # Invalidate CloudFront cache
            self.invalidate_cloudfront_cache(cloudfront_info['distribution_id'])
            
            # Wait for distribution to be deployed
            print("\n⏳ Waiting for CloudFront distribution to be deployed...")
            print("This may take 10-15 minutes for global propagation...")
            
            deployment_info = {
                'bucket_name': bucket_name,
                'distribution_id': cloudfront_info['distribution_id'],
                'domain_name': cloudfront_info['domain_name'],
                'oac_id': cloudfront_info['oac_id'],
                'frontend_url': f"https://{cloudfront_info['domain_name']}"
            }
            
            print("\n" + "=" * 70)
            print("✅ Frontend deployment completed successfully!")
            print("=" * 70)
            print(f"\n📦 S3 Bucket: {bucket_name}")
            print(f"☁️  CloudFront Distribution: {cloudfront_info['distribution_id']}")
            print(f"🌐 Frontend URL: https://{cloudfront_info['domain_name']}")
            print(f"🔐 Origin Access Control: {cloudfront_info['oac_id']}")
            
            print(f"\n📝 Deployment Summary:")
            print(f"• Task 10.1: ✅ S3 bucket configured with private access")
            print(f"• Task 10.2: ✅ CloudFront distribution with OAC created")
            print(f"• Task 10.3: ✅ React application deployed")
            
            print(f"\n⚠️  Note: CloudFront distribution may take 10-15 minutes to fully propagate globally")
            print(f"🔗 Test your deployment at: https://{cloudfront_info['domain_name']}")
            
            return deployment_info
            
        except Exception as e:
            print(f"\n❌ Deployment failed: {e}")
            raise

def main():
    """Main function to run frontend deployment"""
    try:
        deployment = FrontendDeployment()
        result = deployment.deploy_complete_frontend()
        
        # Save deployment info to file
        with open('deployment_info.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n💾 Deployment info saved to deployment_info.json")
        
    except Exception as e:
        print(f"\n💥 Deployment failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()