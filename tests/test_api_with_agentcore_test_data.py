#!/usr/bin/env python3
"""
Test API Gateway Integration with AgentCore Test Data

This script tests the complete API workflow using the test data that AgentCore agents provide.
Since the agents are working with realistic test data, we can validate the complete workflow.
"""

import requests
import json
import os
from typing import Dict, Any


class APITesterWithAgentCoreData:
    """Test API Gateway endpoints with AgentCore test data"""
    
    def __init__(self):
        # Load environment variables
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        os.environ[key] = value
        
        self.api_url = os.getenv('API_GATEWAY_URL')
        self.cognito_client_id = os.getenv('COGNITO_CLIENT_ID')
        self.test_user = os.getenv('COGNITO_TEST_USER')
        self.test_password = os.getenv('COGNITO_TEST_PASSWORD')
        
        self.access_token = None
        
        if not all([self.api_url, self.cognito_client_id, self.test_user, self.test_password]):
            raise ValueError("Missing required environment variables")
    
    def authenticate(self) -> bool:
        """Authenticate with the API and get access token"""
        print("🔐 Authenticating with API...")
        
        auth_url = f"{self.api_url}/auth"
        payload = {
            "email": self.test_user,
            "password": self.test_password
        }
        
        try:
            response = requests.post(auth_url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data['tokens']['access_token']
                print("✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def test_ticket_validation(self) -> bool:
        """Test ticket validation with AgentCore test data"""
        print(f"\n🎫 Testing Ticket Validation with AgentCore Test Data")
        print("=" * 60)
        
        # Use a test ticket ID that AgentCore agents will recognize
        test_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        validation_url = f"{self.api_url}/tickets/{test_ticket_id}/validate"
        payload = {
            "upgrade_tier": "standard"
        }
        
        try:
            response = requests.post(validation_url, json=payload, headers=self.get_headers())
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Ticket validation working with AgentCore test data")
                    return True
                else:
                    print(f"⚠️ Ticket validation returned success=false: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Ticket validation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ticket validation error: {e}")
            return False
    
    def test_pricing_calculation(self) -> bool:
        """Test pricing calculation with AgentCore test data"""
        print(f"\n💰 Testing Pricing Calculation with AgentCore Test Data")
        print("=" * 60)
        
        test_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        pricing_url = f"{self.api_url}/tickets/{test_ticket_id}/pricing"
        payload = {
            "upgrade_tier": "standard",
            "travel_date": "2026-02-15"
        }
        
        try:
            response = requests.post(pricing_url, json=payload, headers=self.get_headers())
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Pricing calculation working with AgentCore test data")
                    return True
                else:
                    print(f"⚠️ Pricing calculation returned success=false: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Pricing calculation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Pricing calculation error: {e}")
            return False
    
    def test_recommendations(self) -> bool:
        """Test recommendations with AgentCore test data"""
        print(f"\n🎯 Testing Recommendations with AgentCore Test Data")
        print("=" * 60)
        
        test_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        test_customer_id = "sample-customer-id"
        recommendations_url = f"{self.api_url}/tickets/{test_ticket_id}/recommendations?customer_id={test_customer_id}"
        
        try:
            response = requests.get(recommendations_url, headers=self.get_headers())
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Recommendations working with AgentCore test data")
                    return True
                else:
                    print(f"⚠️ Recommendations returned success=false: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Recommendations failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Recommendations error: {e}")
            return False
    
    def test_upgrade_tiers(self) -> bool:
        """Test upgrade tiers with AgentCore test data"""
        print(f"\n🏆 Testing Upgrade Tiers with AgentCore Test Data")
        print("=" * 60)
        
        test_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        tiers_url = f"{self.api_url}/tickets/{test_ticket_id}/tiers"
        
        try:
            response = requests.get(tiers_url, headers=self.get_headers())
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Upgrade tiers working with AgentCore test data")
                    return True
                else:
                    print(f"⚠️ Upgrade tiers returned success=false: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Upgrade tiers failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Upgrade tiers error: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test with AgentCore test data"""
        print("🚀 API GATEWAY INTEGRATION TEST WITH AGENTCORE TEST DATA")
        print("=" * 70)
        print(f"🔗 API URL: {self.api_url}")
        print("📊 Testing with AgentCore's realistic test data")
        
        # Step 1: Authenticate
        if not self.authenticate():
            return False
        
        # Step 2: Test endpoints with AgentCore test data
        results = []
        
        results.append(("Ticket Validation", self.test_ticket_validation()))
        results.append(("Pricing Calculation", self.test_pricing_calculation()))
        results.append(("Recommendations", self.test_recommendations()))
        results.append(("Upgrade Tiers", self.test_upgrade_tiers()))
        
        # Step 3: Summary
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE API TEST RESULTS WITH AGENTCORE TEST DATA")
        print("=" * 70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        print(f"\n📈 Overall Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL API TESTS PASSED WITH AGENTCORE TEST DATA!")
            print("✅ API Gateway successfully integrates with AgentCore agents")
            print("✅ Complete ticket upgrade workflow functional")
            print("✅ AgentCore agents providing realistic business responses")
            print("✅ Lambda → AgentCore → Response architecture working")
            print("\n🚀 SYSTEM ARCHITECTURE VALIDATED!")
            print("\n📋 Next Steps:")
            print("   1. ✅ AgentCore agents deployed and working")
            print("   2. ✅ API Gateway integration functional")
            print("   3. ✅ Authentication and authorization working")
            print("   4. ✅ Business logic and LLM reasoning operational")
            print("   5. 🔄 Ready for frontend development")
        else:
            failed_tests = [name for name, result in results if not result]
            print(f"\n⚠️ {len(failed_tests)} test(s) failed:")
            for test_name in failed_tests:
                print(f"   - {test_name}")
        
        return passed == total


def main():
    """Main function"""
    try:
        tester = APITesterWithAgentCoreData()
        success = tester.run_comprehensive_test()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())