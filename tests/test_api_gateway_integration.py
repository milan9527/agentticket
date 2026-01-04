#!/usr/bin/env python3
"""
Test API Gateway Integration with AgentCore

This script tests the deployed API Gateway endpoints to ensure they properly
communicate with the AgentCore agents through Lambda functions.
"""

import asyncio
import json
import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class APIGatewayTester:
    def __init__(self):
        self.api_url = os.getenv('API_GATEWAY_URL', 'https://5yh987mdt2.execute-api.us-west-2.amazonaws.com/prod')
        self.test_user = os.getenv('COGNITO_TEST_USER', 'testuser@example.com')
        self.test_password = os.getenv('COGNITO_TEST_PASSWORD', 'TempPass123!')
        self.access_token = None
        
        # Test data
        self.test_customer_id = "550e8400-e29b-41d4-a716-446655440001"
        self.test_ticket_id = "550e8400-e29b-41d4-a716-446655440002"

    def test_authentication(self):
        """Test authentication endpoint"""
        print("🔐 Testing Authentication Endpoint")
        print("=" * 50)
        
        url = f"{self.api_url}/auth"
        payload = {
            'email': self.test_user,
            'password': self.test_password
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'tokens' in data:
                    self.access_token = data['tokens']['access_token']
                    print("✅ Authentication successful")
                    print(f"📋 Access token received: {self.access_token[:20]}...")
                    return True
                else:
                    print(f"❌ Authentication failed: {data}")
                    return False
            else:
                print(f"❌ Authentication failed with status {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication test failed: {e}")
            return False

    def test_customer_endpoint(self):
        """Test customer endpoint"""
        print("\n👤 Testing Customer Endpoint")
        print("=" * 50)
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        url = f"{self.api_url}/customers/{self.test_customer_id}"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Customer endpoint successful")
                print(f"📋 Customer data: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Customer endpoint failed with status {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Customer endpoint test failed: {e}")
            return False

    def test_ticket_validation_endpoint(self):
        """Test ticket validation endpoint"""
        print("\n🎫 Testing Ticket Validation Endpoint")
        print("=" * 50)
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        url = f"{self.api_url}/tickets/{self.test_ticket_id}/validate"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        payload = {'upgrade_tier': 'Standard'}
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Ticket validation endpoint successful")
                print(f"📋 Validation result: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Ticket validation failed with status {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ticket validation test failed: {e}")
            return False

    def test_ticket_pricing_endpoint(self):
        """Test ticket pricing endpoint"""
        print("\n💰 Testing Ticket Pricing Endpoint")
        print("=" * 50)
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        url = f"{self.api_url}/tickets/{self.test_ticket_id}/pricing"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        payload = {
            'upgrade_tier': 'Standard',
            'travel_date': '2026-02-15'
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Ticket pricing endpoint successful")
                print(f"📋 Pricing result: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Ticket pricing failed with status {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ticket pricing test failed: {e}")
            return False

    def test_ticket_recommendations_endpoint(self):
        """Test ticket recommendations endpoint"""
        print("\n🎯 Testing Ticket Recommendations Endpoint")
        print("=" * 50)
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        url = f"{self.api_url}/tickets/{self.test_ticket_id}/recommendations?customer_id={self.test_customer_id}"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Ticket recommendations endpoint successful")
                print(f"📋 Recommendations: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Ticket recommendations failed with status {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ticket recommendations test failed: {e}")
            return False

    def test_ticket_tiers_endpoint(self):
        """Test ticket tiers endpoint"""
        print("\n🏆 Testing Ticket Tiers Endpoint")
        print("=" * 50)
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        url = f"{self.api_url}/tickets/{self.test_ticket_id}/tiers"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Ticket tiers endpoint successful")
                print(f"📋 Available tiers: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Ticket tiers failed with status {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ticket tiers test failed: {e}")
            return False

    def test_order_endpoint(self):
        """Test order creation endpoint"""
        print("\n📦 Testing Order Creation Endpoint")
        print("=" * 50)
        
        if not self.access_token:
            print("❌ No access token available")
            return False
        
        url = f"{self.api_url}/orders"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        payload = {
            'customer_id': self.test_customer_id,
            'ticket_id': self.test_ticket_id,
            'upgrade_tier': 'Standard',
            'travel_date': '2026-02-15',
            'total_amount': 150.00
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                print("✅ Order creation endpoint successful")
                print(f"📋 Order result: {json.dumps(data, indent=2)}")
                return True
            else:
                print(f"❌ Order creation failed with status {response.status_code}")
                print(f"📋 Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Order creation test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 API GATEWAY INTEGRATION TEST")
        print("=" * 70)
        print(f"🔗 API URL: {self.api_url}")
        print(f"👤 Test User: {self.test_user}")
        print(f"🎫 Test Ticket: {self.test_ticket_id}")
        print(f"👤 Test Customer: {self.test_customer_id}")
        
        # Run tests
        results = {}
        
        # Authentication test (required for other tests)
        results['Authentication'] = self.test_authentication()
        
        if results['Authentication']:
            # Only run other tests if authentication succeeds
            results['Customer Endpoint'] = self.test_customer_endpoint()
            results['Ticket Validation'] = self.test_ticket_validation_endpoint()
            results['Ticket Pricing'] = self.test_ticket_pricing_endpoint()
            results['Ticket Recommendations'] = self.test_ticket_recommendations_endpoint()
            results['Ticket Tiers'] = self.test_ticket_tiers_endpoint()
            results['Order Creation'] = self.test_order_endpoint()
        else:
            print("\n⚠️ Skipping other tests due to authentication failure")
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 API GATEWAY INTEGRATION TEST RESULTS")
        print("=" * 70)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        overall_success = all(results.values())
        
        if overall_success:
            print("\n🎉 ALL API TESTS PASSED!")
            print("✅ API Gateway successfully integrates with AgentCore")
            print("✅ Authentication working with Cognito")
            print("✅ All endpoints properly routing to Lambda functions")
            print("✅ Lambda functions successfully communicating with AgentCore agents")
            print("✅ Backend API is ready for frontend integration")
        else:
            failed_tests = [name for name, success in results.items() if not success]
            print(f"\n⚠️ {len(failed_tests)} test(s) failed: {', '.join(failed_tests)}")
        
        return overall_success


def main():
    """Main test function"""
    tester = APIGatewayTester()
    return tester.run_all_tests()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)