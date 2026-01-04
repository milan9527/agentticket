#!/usr/bin/env python3
"""
Test API Gateway Integration with Real Database Data

This script tests the complete API workflow using actual customer and ticket data
from the Aurora PostgreSQL database.
"""

import requests
import json
import os
import boto3
from typing import Dict, Any, List, Optional


class APITesterWithRealData:
    """Test API Gateway endpoints with real database data"""
    
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
        
        # Database connection for getting real data
        self.region = os.getenv('AWS_REGION', 'us-west-2')
        self.cluster_arn = os.getenv('DB_CLUSTER_ARN')
        self.secret_arn = os.getenv('DB_SECRET_ARN')
        self.database_name = os.getenv('DATABASE_NAME', 'ticket_system')
        
        self.rds_data = boto3.client('rds-data', region_name=self.region)
        self.access_token = None
        
        if not all([self.api_url, self.cognito_client_id, self.test_user, self.test_password]):
            raise ValueError("Missing required environment variables")
    
    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """Execute SQL statement using RDS Data API"""
        try:
            response = self.rds_data.execute_statement(
                resourceArn=self.cluster_arn,
                secretArn=self.secret_arn,
                database=self.database_name,
                sql=sql
            )
            return response
        except Exception as e:
            print(f"Database error: {e}")
            raise
    
    def get_real_customers(self) -> List[Dict[str, Any]]:
        """Get real customer data from database"""
        sql = "SELECT id, email, first_name, last_name FROM customers LIMIT 5;"
        response = self.execute_sql(sql)
        
        customers = []
        for record in response['records']:
            customers.append({
                'id': record[0]['stringValue'],
                'email': record[1]['stringValue'],
                'first_name': record[2]['stringValue'],
                'last_name': record[3]['stringValue']
            })
        return customers
    
    def get_real_tickets(self) -> List[Dict[str, Any]]:
        """Get real ticket data from database"""
        sql = """
        SELECT t.id, t.customer_id, t.ticket_number, t.ticket_type, t.original_price, 
               t.event_date, t.status, c.first_name, c.last_name
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE t.status = 'active'
        LIMIT 5;
        """
        response = self.execute_sql(sql)
        
        tickets = []
        for record in response['records']:
            # Handle different price formats
            price_field = record[4]
            if 'doubleValue' in price_field:
                price = price_field['doubleValue']
            elif 'stringValue' in price_field:
                price = float(price_field['stringValue'])
            else:
                price = 0.0
            
            tickets.append({
                'id': record[0]['stringValue'],
                'customer_id': record[1]['stringValue'],
                'ticket_number': record[2]['stringValue'],
                'ticket_type': record[3]['stringValue'],
                'original_price': price,
                'event_date': record[5]['stringValue'],
                'status': record[6]['stringValue'],
                'customer_name': f"{record[7]['stringValue']} {record[8]['stringValue']}"
            })
        return tickets
    
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
    
    def test_customer_endpoint(self, customer: Dict[str, Any]) -> bool:
        """Test customer endpoint with real customer data"""
        print(f"\n👤 Testing Customer Endpoint: {customer['first_name']} {customer['last_name']}")
        print("=" * 60)
        
        customer_url = f"{self.api_url}/customers/{customer['id']}"
        
        try:
            response = requests.get(customer_url, headers=self.get_headers())
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Customer endpoint working with real data")
                    return True
                else:
                    print(f"⚠️ Customer endpoint returned success=false: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Customer endpoint failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Customer endpoint error: {e}")
            return False
    
    def test_ticket_validation(self, ticket: Dict[str, Any]) -> bool:
        """Test ticket validation with real ticket data"""
        print(f"\n🎫 Testing Ticket Validation: {ticket['ticket_number']} ({ticket['customer_name']})")
        print("=" * 60)
        
        validation_url = f"{self.api_url}/tickets/{ticket['id']}/validate"
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
                    print("✅ Ticket validation working with real data")
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
    
    def test_pricing_calculation(self, ticket: Dict[str, Any]) -> bool:
        """Test pricing calculation with real ticket data"""
        print(f"\n💰 Testing Pricing Calculation: {ticket['ticket_number']}")
        print("=" * 60)
        
        pricing_url = f"{self.api_url}/tickets/{ticket['id']}/pricing"
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
                    print("✅ Pricing calculation working with real data")
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
    
    def test_recommendations(self, ticket: Dict[str, Any]) -> bool:
        """Test recommendations with real ticket data"""
        print(f"\n🎯 Testing Recommendations: {ticket['ticket_number']}")
        print("=" * 60)
        
        recommendations_url = f"{self.api_url}/tickets/{ticket['id']}/recommendations?customer_id={ticket['customer_id']}"
        
        try:
            response = requests.get(recommendations_url, headers=self.get_headers())
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Recommendations working with real data")
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
    
    def test_upgrade_tiers(self, ticket: Dict[str, Any]) -> bool:
        """Test upgrade tiers with real ticket data"""
        print(f"\n🏆 Testing Upgrade Tiers: {ticket['ticket_number']}")
        print("=" * 60)
        
        tiers_url = f"{self.api_url}/tickets/{ticket['id']}/tiers"
        
        try:
            response = requests.get(tiers_url, headers=self.get_headers())
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Upgrade tiers working with real data")
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
    
    def test_order_creation(self, ticket: Dict[str, Any]) -> bool:
        """Test order creation with real ticket data"""
        print(f"\n📦 Testing Order Creation: {ticket['ticket_number']}")
        print("=" * 60)
        
        orders_url = f"{self.api_url}/orders"
        payload = {
            "customer_id": ticket['customer_id'],
            "ticket_id": ticket['id'],
            "upgrade_tier": "standard",
            "travel_date": "2026-02-15",
            "total_amount": ticket['original_price'] + 25.00
        }
        
        try:
            response = requests.post(orders_url, json=payload, headers=self.get_headers())
            
            print(f"📋 Response Status: {response.status_code}")
            print(f"📋 Response Data: {json.dumps(response.json(), indent=2)}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    print("✅ Order creation working with real data")
                    return True
                else:
                    print(f"⚠️ Order creation returned success=false: {data.get('error', 'Unknown error')}")
                    return False
            else:
                print(f"❌ Order creation failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Order creation error: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run comprehensive test with real data"""
        print("🚀 API GATEWAY INTEGRATION TEST WITH REAL DATA")
        print("=" * 70)
        print(f"🔗 API URL: {self.api_url}")
        
        # Step 1: Authenticate
        if not self.authenticate():
            return False
        
        # Step 2: Get real data from database
        print("\n📊 Fetching Real Data from Database...")
        customers = self.get_real_customers()
        tickets = self.get_real_tickets()
        
        print(f"👥 Found {len(customers)} customers")
        print(f"🎫 Found {len(tickets)} active tickets")
        
        if not customers or not tickets:
            print("❌ No real data found in database!")
            return False
        
        # Step 3: Test endpoints with real data
        results = []
        
        # Test customer endpoint
        test_customer = customers[0]
        results.append(("Customer Endpoint", self.test_customer_endpoint(test_customer)))
        
        # Test ticket endpoints with first ticket
        test_ticket = tickets[0]
        results.append(("Ticket Validation", self.test_ticket_validation(test_ticket)))
        results.append(("Pricing Calculation", self.test_pricing_calculation(test_ticket)))
        results.append(("Recommendations", self.test_recommendations(test_ticket)))
        results.append(("Upgrade Tiers", self.test_upgrade_tiers(test_ticket)))
        results.append(("Order Creation", self.test_order_creation(test_ticket)))
        
        # Step 4: Summary
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE API TEST RESULTS WITH REAL DATA")
        print("=" * 70)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        print(f"\n📈 Overall Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 ALL API TESTS PASSED WITH REAL DATA!")
            print("✅ API Gateway successfully integrates with AgentCore using real database data")
            print("✅ Complete ticket upgrade workflow functional")
            print("✅ Backend API is ready for frontend integration")
            print("\n🚀 SYSTEM READY FOR PRODUCTION!")
        else:
            failed_tests = [name for name, result in results if not result]
            print(f"\n⚠️ {len(failed_tests)} test(s) failed:")
            for test_name in failed_tests:
                print(f"   - {test_name}")
        
        return passed == total


def main():
    """Main function"""
    try:
        tester = APITesterWithRealData()
        success = tester.run_comprehensive_test()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())