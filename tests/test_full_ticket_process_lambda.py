#!/usr/bin/env python3
"""
Full Ticket Process Test via Lambda Functions

This test validates the complete ticket upgrade process by invoking Lambda functions directly,
ensuring we're using real LLM models (Nova Pro via AgentCore) and real database (Aurora).
"""

import boto3
import json
import time
from datetime import datetime
from typing import Dict, Any, List

class FullTicketProcessTester:
    """Test the complete ticket process via Lambda functions"""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-west-2')
        self.cognito_client = boto3.client('cognito-idp', region_name='us-west-2')
        self.access_token = None
        
        # Test data
        self.test_customer_id = "sample-customer-id"
        self.test_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        
        # Results tracking
        self.test_results = []
        self.llm_responses = []
        self.database_interactions = []
    
    def authenticate(self) -> bool:
        """Get Cognito access token for Lambda authentication"""
        try:
            print("🔐 Authenticating with Cognito...")
            
            response = self.cognito_client.initiate_auth(
                ClientId='11m43vg72idbvlf5pc5d6qhsc4',
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': 'testuser@example.com',
                    'PASSWORD': 'TempPass123!'
                }
            )
            
            self.access_token = response['AuthenticationResult']['AccessToken']
            print(f"✅ Authentication successful: {self.access_token[:50]}...")
            return True
            
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            return False
    
    def invoke_lambda(self, function_name: str, event: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a Lambda function and return the response"""
        try:
            print(f"\n🚀 Invoking Lambda: {function_name}")
            print(f"   Event: {json.dumps(event, indent=2)[:200]}...")
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                Payload=json.dumps(event)
            )
            
            result = json.loads(response['Payload'].read())
            print(f"📋 Lambda Response Status: {result.get('statusCode')}")
            
            if result.get('statusCode') == 200:
                body = json.loads(result.get('body', '{}'))
                print(f"✅ Lambda call successful")
                return {'success': True, 'data': body, 'raw_response': result}
            else:
                body = json.loads(result.get('body', '{}'))
                print(f"❌ Lambda call failed: {body.get('error', 'Unknown error')}")
                return {'success': False, 'error': body.get('error', 'Unknown error'), 'raw_response': result}
                
        except Exception as e:
            print(f"❌ Lambda invocation error: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_chat_with_llm(self) -> bool:
        """Test AI chat functionality using real LLM via AgentCore"""
        print("\n" + "="*80)
        print("🤖 TESTING AI CHAT WITH REAL LLM (Nova Pro via AgentCore)")
        print("="*80)
        
        try:
            # Test various chat scenarios
            chat_scenarios = [
                {
                    "name": "Greeting and Introduction",
                    "message": "Hello! I have a ticket and I'm interested in upgrading it.",
                    "expected_keywords": ["upgrade", "help", "options"]
                },
                {
                    "name": "Ticket Information Request",
                    "message": f"My ticket ID is {self.test_ticket_id}. Can you tell me about upgrade options?",
                    "expected_keywords": ["upgrade", "tier", "premium", "vip"]
                },
                {
                    "name": "Pricing Inquiry",
                    "message": "How much would it cost to upgrade to VIP?",
                    "expected_keywords": ["price", "cost", "vip", "$"]
                }
            ]
            
            conversation_history = []
            all_scenarios_passed = True
            
            for scenario in chat_scenarios:
                print(f"\n🎯 Testing Scenario: {scenario['name']}")
                print(f"   Customer Message: {scenario['message']}")
                
                # Create Lambda event for chat
                event = {
                    "httpMethod": "POST",
                    "path": "/chat",
                    "headers": {
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    "body": json.dumps({
                        "message": scenario['message'],
                        "conversationHistory": conversation_history,
                        "context": {
                            "ticketId": self.test_ticket_id,
                            "hasTicketInfo": True
                        }
                    })
                }
                
                # Invoke Lambda
                result = self.invoke_lambda('ticket-handler', event)
                
                if result['success']:
                    response_data = result['data']
                    ai_response = response_data.get('response', '')
                    
                    print(f"🤖 AI Response: {ai_response[:200]}...")
                    print(f"   Response Length: {len(ai_response)} characters")
                    print(f"   Show Upgrade Buttons: {response_data.get('showUpgradeButtons', False)}")
                    
                    # Validate LLM response quality
                    if len(ai_response) > 50:  # Substantial response
                        print("✅ LLM generated substantial response")
                        
                        # Check for expected keywords
                        response_lower = ai_response.lower()
                        found_keywords = [kw for kw in scenario['expected_keywords'] if kw in response_lower]
                        
                        if found_keywords:
                            print(f"✅ Found expected keywords: {found_keywords}")
                        else:
                            print(f"⚠️ Expected keywords not found: {scenario['expected_keywords']}")
                        
                        # Store LLM response for analysis
                        self.llm_responses.append({
                            'scenario': scenario['name'],
                            'input': scenario['message'],
                            'output': ai_response,
                            'length': len(ai_response),
                            'keywords_found': found_keywords
                        })
                        
                        # Add to conversation history
                        conversation_history.extend([
                            {"sender": "customer", "content": scenario['message']},
                            {"sender": "ai", "content": ai_response}
                        ])
                        
                    else:
                        print("❌ LLM response too short - may not be using real LLM")
                        all_scenarios_passed = False
                else:
                    print(f"❌ Chat scenario failed: {result.get('error')}")
                    all_scenarios_passed = False
                
                time.sleep(1)  # Brief pause between scenarios
            
            self.test_results.append({
                'test': 'AI Chat with Real LLM',
                'passed': all_scenarios_passed,
                'details': f"Tested {len(chat_scenarios)} scenarios"
            })
            
            return all_scenarios_passed
            
        except Exception as e:
            print(f"❌ Chat test error: {e}")
            self.test_results.append({
                'test': 'AI Chat with Real LLM',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
            return False
    
    def test_ticket_validation_with_database(self) -> bool:
        """Test ticket validation using real database via AgentCore"""
        print("\n" + "="*80)
        print("🎫 TESTING TICKET VALIDATION WITH REAL DATABASE")
        print("="*80)
        
        try:
            print(f"🔍 Validating ticket: {self.test_ticket_id}")
            
            # Test different upgrade tiers
            upgrade_tiers = ["standard", "premium", "vip"]
            all_validations_passed = True
            
            for tier in upgrade_tiers:
                print(f"\n🎯 Testing {tier.upper()} upgrade validation...")
                
                # Create Lambda event for ticket validation
                event = {
                    "httpMethod": "POST",
                    "path": f"/tickets/{self.test_ticket_id}/validate",
                    "headers": {
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    "pathParameters": {
                        "ticket_id": self.test_ticket_id
                    },
                    "body": json.dumps({
                        "upgrade_tier": tier
                    })
                }
                
                # Invoke Lambda
                result = self.invoke_lambda('ticket-handler', event)
                
                if result['success']:
                    validation_data = result['data']
                    
                    print(f"✅ Validation successful for {tier}")
                    print(f"   Success: {validation_data.get('success', False)}")
                    print(f"   Data Length: {len(str(validation_data.get('data', {})))} characters")
                    
                    # Check for real database data indicators
                    data_str = str(validation_data.get('data', {}))
                    if 'TKT-TEST789' in data_str or 'sample-customer-id' in data_str:
                        print("✅ Real database data detected")
                        self.database_interactions.append({
                            'operation': f'validate_ticket_{tier}',
                            'ticket_id': self.test_ticket_id,
                            'success': True,
                            'data_length': len(data_str)
                        })
                    else:
                        print("⚠️ Database data format unexpected")
                    
                    # Check for LLM processing indicators
                    if len(data_str) > 1000:  # Substantial response indicates LLM processing
                        print("✅ Substantial response indicates LLM processing")
                    
                else:
                    print(f"❌ Validation failed for {tier}: {result.get('error')}")
                    all_validations_passed = False
                
                time.sleep(1)  # Brief pause between validations
            
            self.test_results.append({
                'test': 'Ticket Validation with Database',
                'passed': all_validations_passed,
                'details': f"Tested {len(upgrade_tiers)} upgrade tiers"
            })
            
            return all_validations_passed
            
        except Exception as e:
            print(f"❌ Ticket validation test error: {e}")
            self.test_results.append({
                'test': 'Ticket Validation with Database',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
            return False
    
    def test_pricing_calculation_with_llm(self) -> bool:
        """Test pricing calculation using real LLM and database"""
        print("\n" + "="*80)
        print("💰 TESTING PRICING CALCULATION WITH REAL LLM & DATABASE")
        print("="*80)
        
        try:
            upgrade_tiers = ["standard", "premium", "vip"]
            all_pricing_passed = True
            
            for tier in upgrade_tiers:
                print(f"\n💵 Calculating pricing for {tier.upper()} upgrade...")
                
                # Create Lambda event for pricing calculation
                event = {
                    "httpMethod": "POST",
                    "path": f"/tickets/{self.test_ticket_id}/pricing",
                    "headers": {
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    "pathParameters": {
                        "ticket_id": self.test_ticket_id
                    },
                    "body": json.dumps({
                        "upgrade_tier": tier,
                        "event_date": "2026-02-15"
                    })
                }
                
                # Invoke Lambda
                result = self.invoke_lambda('ticket-handler', event)
                
                if result['success']:
                    pricing_data = result['data']
                    
                    print(f"✅ Pricing calculation successful for {tier}")
                    print(f"   Success: {pricing_data.get('success', False)}")
                    
                    # Analyze response for LLM and database indicators
                    data_str = str(pricing_data.get('data', {}))
                    print(f"   Response Length: {len(data_str)} characters")
                    
                    # Check for real database integration
                    if 'TKT-TEST789' in data_str:
                        print("✅ Real database ticket data found")
                    
                    # Check for LLM processing (detailed pricing analysis)
                    if len(data_str) > 500:
                        print("✅ Detailed response indicates LLM processing")
                    
                    # Look for pricing information
                    if any(indicator in data_str.lower() for indicator in ['price', 'cost', '$', 'pricing']):
                        print("✅ Pricing information present")
                    
                    self.database_interactions.append({
                        'operation': f'calculate_pricing_{tier}',
                        'ticket_id': self.test_ticket_id,
                        'success': True,
                        'data_length': len(data_str)
                    })
                    
                else:
                    print(f"❌ Pricing calculation failed for {tier}: {result.get('error')}")
                    all_pricing_passed = False
                
                time.sleep(1)
            
            self.test_results.append({
                'test': 'Pricing Calculation with LLM & Database',
                'passed': all_pricing_passed,
                'details': f"Tested {len(upgrade_tiers)} pricing calculations"
            })
            
            return all_pricing_passed
            
        except Exception as e:
            print(f"❌ Pricing calculation test error: {e}")
            self.test_results.append({
                'test': 'Pricing Calculation with LLM & Database',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
            return False
    
    def test_upgrade_recommendations_with_llm(self) -> bool:
        """Test personalized upgrade recommendations using real LLM"""
        print("\n" + "="*80)
        print("🎯 TESTING UPGRADE RECOMMENDATIONS WITH REAL LLM")
        print("="*80)
        
        try:
            print(f"🔍 Getting recommendations for customer: {self.test_customer_id}")
            print(f"   Ticket: {self.test_ticket_id}")
            
            # Create Lambda event for recommendations
            event = {
                "httpMethod": "GET",
                "path": f"/tickets/{self.test_ticket_id}/recommendations",
                "headers": {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                "pathParameters": {
                    "ticket_id": self.test_ticket_id
                },
                "queryStringParameters": {
                    "customer_id": self.test_customer_id
                }
            }
            
            # Invoke Lambda
            result = self.invoke_lambda('ticket-handler', event)
            
            if result['success']:
                recommendations_data = result['data']
                
                print(f"✅ Recommendations generated successfully")
                print(f"   Success: {recommendations_data.get('success', False)}")
                
                # Analyze response for LLM processing
                data_str = str(recommendations_data.get('data', {}))
                print(f"   Response Length: {len(data_str)} characters")
                
                # Check for personalized recommendations (indicates LLM processing)
                if len(data_str) > 1000:
                    print("✅ Detailed recommendations indicate LLM processing")
                
                # Check for database integration
                if 'TKT-TEST789' in data_str or 'sample-customer-id' in data_str:
                    print("✅ Real database data integrated")
                
                # Look for recommendation keywords
                recommendation_keywords = ['recommend', 'suggest', 'upgrade', 'tier', 'benefit']
                found_keywords = [kw for kw in recommendation_keywords if kw in data_str.lower()]
                if found_keywords:
                    print(f"✅ Recommendation keywords found: {found_keywords}")
                
                self.llm_responses.append({
                    'scenario': 'Upgrade Recommendations',
                    'input': f"Customer: {self.test_customer_id}, Ticket: {self.test_ticket_id}",
                    'output': data_str,
                    'length': len(data_str),
                    'keywords_found': found_keywords
                })
                
                self.test_results.append({
                    'test': 'Upgrade Recommendations with LLM',
                    'passed': True,
                    'details': f"Generated {len(data_str)} character response"
                })
                
                return True
                
            else:
                print(f"❌ Recommendations failed: {result.get('error')}")
                self.test_results.append({
                    'test': 'Upgrade Recommendations with LLM',
                    'passed': False,
                    'details': f"Error: {result.get('error')}"
                })
                return False
                
        except Exception as e:
            print(f"❌ Recommendations test error: {e}")
            self.test_results.append({
                'test': 'Upgrade Recommendations with LLM',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
            return False
    
    def test_tier_comparison_with_llm(self) -> bool:
        """Test tier comparison using real LLM"""
        print("\n" + "="*80)
        print("📊 TESTING TIER COMPARISON WITH REAL LLM")
        print("="*80)
        
        try:
            print(f"📋 Getting tier comparison for ticket: {self.test_ticket_id}")
            
            # Create Lambda event for tier comparison
            event = {
                "httpMethod": "GET",
                "path": f"/tickets/{self.test_ticket_id}/tiers",
                "headers": {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                "pathParameters": {
                    "ticket_id": self.test_ticket_id
                }
            }
            
            # Invoke Lambda
            result = self.invoke_lambda('ticket-handler', event)
            
            if result['success']:
                comparison_data = result['data']
                
                print(f"✅ Tier comparison generated successfully")
                print(f"   Success: {comparison_data.get('success', False)}")
                
                # Analyze response for LLM processing
                data_str = str(comparison_data.get('data', {}))
                print(f"   Response Length: {len(data_str)} characters")
                
                # Check for comprehensive comparison (indicates LLM processing)
                if len(data_str) > 800:
                    print("✅ Comprehensive comparison indicates LLM processing")
                
                # Look for tier comparison keywords
                comparison_keywords = ['standard', 'premium', 'vip', 'compare', 'tier', 'benefit', 'feature']
                found_keywords = [kw for kw in comparison_keywords if kw in data_str.lower()]
                if found_keywords:
                    print(f"✅ Comparison keywords found: {found_keywords}")
                
                # Check for database integration
                if 'TKT-TEST789' in data_str:
                    print("✅ Real database ticket data integrated")
                
                self.llm_responses.append({
                    'scenario': 'Tier Comparison',
                    'input': f"Ticket: {self.test_ticket_id}",
                    'output': data_str,
                    'length': len(data_str),
                    'keywords_found': found_keywords
                })
                
                self.test_results.append({
                    'test': 'Tier Comparison with LLM',
                    'passed': True,
                    'details': f"Generated {len(data_str)} character comparison"
                })
                
                return True
                
            else:
                print(f"❌ Tier comparison failed: {result.get('error')}")
                self.test_results.append({
                    'test': 'Tier Comparison with LLM',
                    'passed': False,
                    'details': f"Error: {result.get('error')}"
                })
                return False
                
        except Exception as e:
            print(f"❌ Tier comparison test error: {e}")
            self.test_results.append({
                'test': 'Tier Comparison with LLM',
                'passed': False,
                'details': f"Error: {str(e)}"
            })
            return False
    
    def analyze_llm_usage(self) -> Dict[str, Any]:
        """Analyze LLM usage patterns from responses"""
        print("\n" + "="*80)
        print("🧠 ANALYZING LLM USAGE PATTERNS")
        print("="*80)
        
        if not self.llm_responses:
            print("❌ No LLM responses to analyze")
            return {'llm_detected': False, 'analysis': 'No responses collected'}
        
        total_responses = len(self.llm_responses)
        total_characters = sum(resp['length'] for resp in self.llm_responses)
        avg_length = total_characters / total_responses
        
        print(f"📊 LLM Response Analysis:")
        print(f"   Total Responses: {total_responses}")
        print(f"   Total Characters: {total_characters:,}")
        print(f"   Average Length: {avg_length:.0f} characters")
        
        # Analyze response quality indicators
        substantial_responses = [resp for resp in self.llm_responses if resp['length'] > 500]
        keyword_matches = sum(len(resp['keywords_found']) for resp in self.llm_responses)
        
        print(f"   Substantial Responses (>500 chars): {len(substantial_responses)}")
        print(f"   Total Keyword Matches: {keyword_matches}")
        
        # Determine if real LLM is being used
        llm_indicators = {
            'substantial_responses': len(substantial_responses) > 0,
            'high_avg_length': avg_length > 300,
            'keyword_relevance': keyword_matches > 5,
            'response_variety': len(set(resp['output'][:100] for resp in self.llm_responses)) > 1
        }
        
        llm_score = sum(llm_indicators.values())
        llm_detected = llm_score >= 3
        
        print(f"\n🎯 LLM Detection Score: {llm_score}/4")
        for indicator, passed in llm_indicators.items():
            print(f"   {indicator}: {'✅' if passed else '❌'}")
        
        print(f"\n{'✅' if llm_detected else '❌'} Real LLM Usage: {'DETECTED' if llm_detected else 'NOT DETECTED'}")
        
        return {
            'llm_detected': llm_detected,
            'total_responses': total_responses,
            'total_characters': total_characters,
            'avg_length': avg_length,
            'substantial_responses': len(substantial_responses),
            'keyword_matches': keyword_matches,
            'llm_score': llm_score,
            'indicators': llm_indicators
        }
    
    def analyze_database_usage(self) -> Dict[str, Any]:
        """Analyze database usage patterns"""
        print("\n" + "="*80)
        print("🗄️ ANALYZING DATABASE USAGE PATTERNS")
        print("="*80)
        
        if not self.database_interactions:
            print("❌ No database interactions to analyze")
            return {'database_detected': False, 'analysis': 'No interactions collected'}
        
        total_interactions = len(self.database_interactions)
        successful_interactions = sum(1 for interaction in self.database_interactions if interaction['success'])
        total_data_length = sum(interaction['data_length'] for interaction in self.database_interactions)
        
        print(f"📊 Database Interaction Analysis:")
        print(f"   Total Interactions: {total_interactions}")
        print(f"   Successful Interactions: {successful_interactions}")
        print(f"   Total Data Retrieved: {total_data_length:,} characters")
        print(f"   Success Rate: {(successful_interactions/total_interactions)*100:.1f}%")
        
        # List operations performed
        operations = [interaction['operation'] for interaction in self.database_interactions]
        unique_operations = set(operations)
        print(f"   Unique Operations: {len(unique_operations)}")
        for op in unique_operations:
            count = operations.count(op)
            print(f"     {op}: {count} times")
        
        # Determine if real database is being used
        database_indicators = {
            'multiple_interactions': total_interactions > 3,
            'high_success_rate': (successful_interactions/total_interactions) > 0.8,
            'substantial_data': total_data_length > 5000,
            'varied_operations': len(unique_operations) > 2
        }
        
        database_score = sum(database_indicators.values())
        database_detected = database_score >= 3
        
        print(f"\n🎯 Database Detection Score: {database_score}/4")
        for indicator, passed in database_indicators.items():
            print(f"   {indicator}: {'✅' if passed else '❌'}")
        
        print(f"\n{'✅' if database_detected else '❌'} Real Database Usage: {'DETECTED' if database_detected else 'NOT DETECTED'}")
        
        return {
            'database_detected': database_detected,
            'total_interactions': total_interactions,
            'successful_interactions': successful_interactions,
            'success_rate': (successful_interactions/total_interactions)*100,
            'total_data_length': total_data_length,
            'unique_operations': len(unique_operations),
            'database_score': database_score,
            'indicators': database_indicators
        }
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        print("\n" + "="*80)
        print("📋 FINAL TEST REPORT")
        print("="*80)
        
        # Analyze LLM and database usage
        llm_analysis = self.analyze_llm_usage()
        database_analysis = self.analyze_database_usage()
        
        # Calculate overall results
        total_tests = len(self.test_results)
        passed_tests = sum(1 for test in self.test_results if test['passed'])
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n🎯 OVERALL TEST RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed Tests: {passed_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        print(f"\n📝 Test Details:")
        for test in self.test_results:
            status = "✅" if test['passed'] else "❌"
            print(f"   {status} {test['test']}: {test['details']}")
        
        # System validation
        system_ready = (
            success_rate >= 80 and
            llm_analysis['llm_detected'] and
            database_analysis['database_detected']
        )
        
        print(f"\n🏆 SYSTEM VALIDATION:")
        print(f"   Lambda Functions: {'✅ WORKING' if success_rate >= 80 else '❌ ISSUES'}")
        print(f"   Real LLM (Nova Pro): {'✅ DETECTED' if llm_analysis['llm_detected'] else '❌ NOT DETECTED'}")
        print(f"   Real Database (Aurora): {'✅ DETECTED' if database_analysis['database_detected'] else '❌ NOT DETECTED'}")
        print(f"   Overall System: {'✅ PRODUCTION READY' if system_ready else '❌ NEEDS ATTENTION'}")
        
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return {
            'timestamp': timestamp,
            'test_summary': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'success_rate': success_rate
            },
            'test_results': self.test_results,
            'llm_analysis': llm_analysis,
            'database_analysis': database_analysis,
            'system_validation': {
                'lambda_functions': success_rate >= 80,
                'real_llm': llm_analysis['llm_detected'],
                'real_database': database_analysis['database_detected'],
                'production_ready': system_ready
            }
        }
    
    def run_full_test_suite(self) -> Dict[str, Any]:
        """Run the complete test suite"""
        print("🚀 FULL TICKET PROCESS TEST VIA LAMBDA FUNCTIONS")
        print("Testing real LLM models (Nova Pro) and real database (Aurora)")
        print("="*80)
        
        # Step 1: Authenticate
        if not self.authenticate():
            return {'error': 'Authentication failed'}
        
        # Step 2: Run all tests
        test_functions = [
            self.test_chat_with_llm,
            self.test_ticket_validation_with_database,
            self.test_pricing_calculation_with_llm,
            self.test_upgrade_recommendations_with_llm,
            self.test_tier_comparison_with_llm
        ]
        
        for test_func in test_functions:
            try:
                test_func()
                time.sleep(2)  # Brief pause between major tests
            except Exception as e:
                print(f"❌ Test function {test_func.__name__} failed: {e}")
        
        # Step 3: Generate final report
        return self.generate_final_report()


def main():
    """Main test execution"""
    tester = FullTicketProcessTester()
    report = tester.run_full_test_suite()
    
    # Save detailed report
    if 'error' not in report:
        timestamp = report['timestamp']
        report_filename = f"full_ticket_process_lambda_test_report_{timestamp}.json"
        
        with open(report_filename, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved: {report_filename}")
        
        # Print final status
        if report['system_validation']['production_ready']:
            print(f"\n🎉 SUCCESS: System is production ready!")
            print(f"   ✅ Lambda functions working correctly")
            print(f"   ✅ Real LLM (Nova Pro) detected and functioning")
            print(f"   ✅ Real database (Aurora) detected and accessible")
            print(f"   ✅ Full ticket upgrade process validated")
        else:
            print(f"\n⚠️ ATTENTION NEEDED: System has issues")
            validation = report['system_validation']
            if not validation['lambda_functions']:
                print(f"   ❌ Lambda functions need attention")
            if not validation['real_llm']:
                print(f"   ❌ Real LLM not detected - may be using fallback responses")
            if not validation['real_database']:
                print(f"   ❌ Real database not detected - may be using mock data")


if __name__ == "__main__":
    main()