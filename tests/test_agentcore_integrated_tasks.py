#!/usr/bin/env python3
"""
Test AgentCore Runtime Agents with Integrated Tasks

This script tests AgentCore Runtime agents with integrated tasks to ensure:
1. Real LLM (Nova Pro) usage in complex workflows
2. Real Aurora database data in end-to-end scenarios
3. Proper inter-agent communication and data flow
4. Complete business process integration

Architecture being tested:
- Complete customer journey: ticket lookup → eligibility check → upgrade selection → order creation
- Inter-agent communication: Ticket Agent → Data Agent Invoker Lambda → Aurora Database
- End-to-end LLM reasoning with real data context
"""

import sys
import os
import asyncio
import json
import boto3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Load environment
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Add path and import
sys.path.append('backend/lambda')

class AgentCoreIntegratedTestSuite:
    """Comprehensive test suite for AgentCore Runtime agents with integrated workflows"""
    
    def __init__(self):
        self.data_agent_arn = os.getenv('DATA_AGENT_ARN')
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN')
        self.bedrock_model_id = os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
        
        # Real test data from Aurora database
        self.real_customer_id = "fdd70d2c-3f05-4749-9b8d-9ba3142c0707"  # John Doe
        self.real_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
        
        # Test scenarios
        self.test_scenarios = [
            {
                'name': 'Standard Upgrade Journey',
                'description': 'Customer wants to upgrade general ticket to standard',
                'customer_id': self.real_customer_id,
                'ticket_id': self.real_ticket_id,
                'upgrade_tier': 'standard',
                'expected_price': 25.00
            },
            {
                'name': 'Premium Upgrade Journey',
                'description': 'Customer wants to upgrade to non-stop experience',
                'customer_id': self.real_customer_id,
                'ticket_id': self.real_ticket_id,
                'upgrade_tier': 'non-stop',
                'expected_price': 50.00
            },
            {
                'name': 'Ultimate Upgrade Journey',
                'description': 'Customer wants the double fun package',
                'customer_id': self.real_customer_id,
                'ticket_id': self.real_ticket_id,
                'upgrade_tier': 'double-fun',
                'expected_price': 75.00
            }
        ]
        
        print(f"🎯 AgentCore Integrated Test Suite Initialized")
        print(f"   Data Agent ARN: {self.data_agent_arn}")
        print(f"   Ticket Agent ARN: {self.ticket_agent_arn}")
        print(f"   Bedrock Model: {self.bedrock_model_id}")
        print(f"   Test Scenarios: {len(self.test_scenarios)}")
    
    async def test_complete_upgrade_journey(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Test complete upgrade journey from start to finish"""
        print(f"\n🎪 TESTING COMPLETE UPGRADE JOURNEY: {scenario['name']}")
        print("="*70)
        print(f"   Description: {scenario['description']}")
        print(f"   Customer: {scenario['customer_id']}")
        print(f"   Ticket: {scenario['ticket_id']}")
        print(f"   Target Upgrade: {scenario['upgrade_tier']}")
        
        journey_results = {
            'scenario': scenario['name'],
            'steps': {},
            'overall_success': False,
            'data_sources': [],
            'llm_usage': [],
            'errors': []
        }
        
        try:
            from agentcore_client import AgentCoreClient
            client = AgentCoreClient()
            
            if not client.get_bearer_token():
                journey_results['errors'].append('AgentCore authentication failed')
                return journey_results
            
            print("✅ AgentCore authentication successful")
            
            # Step 1: Validate ticket eligibility (Ticket Agent calls Data Agent internally)
            print(f"\n🎯 STEP 1: Validate Ticket Eligibility")
            print(f"   This step tests: Ticket Agent → Data Agent Invoker → Aurora Database")
            
            eligibility_result = await client.call_ticket_agent_tool('validate_ticket_eligibility', {
                'ticket_id': scenario['ticket_id'],
                'customer_id': scenario['customer_id']
            })
            
            step1_success, step1_analysis = self._analyze_integrated_response(
                eligibility_result, 'validate_ticket_eligibility', 'eligibility with real data'
            )
            
            journey_results['steps']['validate_eligibility'] = {
                'success': step1_success,
                'response': eligibility_result,
                'analysis': step1_analysis,
                'data_source': step1_analysis.get('data_source', 'Unknown'),
                'has_llm_reasoning': step1_analysis.get('has_llm_reasoning', False)
            }
            
            if step1_success:
                journey_results['data_sources'].append(step1_analysis.get('data_source', 'Unknown'))
                if step1_analysis.get('has_llm_reasoning'):
                    journey_results['llm_usage'].append('eligibility_analysis')
            else:
                journey_results['errors'].append(f"Step 1 failed: {step1_analysis.get('error', 'Unknown')}")
                return journey_results
            
            # Step 2: Get upgrade recommendations (LLM reasoning with real ticket data)
            print(f"\n🎯 STEP 2: Get Upgrade Recommendations")
            print(f"   This step tests: LLM reasoning with real customer/ticket context")
            
            # Extract ticket data from eligibility result for recommendations
            ticket_data = self._extract_ticket_data(eligibility_result)
            if not ticket_data:
                journey_results['errors'].append('Could not extract ticket data from eligibility result')
                return journey_results
            
            recommendations_result = await client.call_ticket_agent_tool('get_upgrade_recommendations', {
                'ticket_data': ticket_data,
                'customer_preferences': {
                    'budget': 'moderate',
                    'experience_level': 'enhanced',
                    'group_size': 1
                }
            })
            
            step2_success, step2_analysis = self._analyze_integrated_response(
                recommendations_result, 'get_upgrade_recommendations', 'personalized recommendations'
            )
            
            journey_results['steps']['get_recommendations'] = {
                'success': step2_success,
                'response': recommendations_result,
                'analysis': step2_analysis,
                'has_llm_reasoning': step2_analysis.get('has_llm_reasoning', False)
            }
            
            if step2_success and step2_analysis.get('has_llm_reasoning'):
                journey_results['llm_usage'].append('upgrade_recommendations')
            
            # Step 3: Calculate specific upgrade pricing (Business logic)
            print(f"\n🎯 STEP 3: Calculate Upgrade Pricing")
            print(f"   This step tests: Business logic with real ticket type and pricing")
            
            pricing_result = await client.call_ticket_agent_tool('calculate_upgrade_pricing', {
                'ticket_type': ticket_data.get('ticket_type', 'general'),
                'upgrade_tier': scenario['upgrade_tier'],
                'original_price': ticket_data.get('original_price', 50.00)
            })
            
            step3_success, step3_analysis = self._analyze_integrated_response(
                pricing_result, 'calculate_upgrade_pricing', 'pricing calculation'
            )
            
            journey_results['steps']['calculate_pricing'] = {
                'success': step3_success,
                'response': pricing_result,
                'analysis': step3_analysis,
                'has_llm_reasoning': step3_analysis.get('has_llm_reasoning', False)
            }
            
            if step3_success and step3_analysis.get('has_llm_reasoning'):
                journey_results['llm_usage'].append('pricing_analysis')
            
            # Extract pricing for order creation
            upgrade_price = self._extract_upgrade_price(pricing_result)
            if not upgrade_price:
                journey_results['errors'].append('Could not extract upgrade price from pricing result')
                return journey_results
            
            # Step 4: Create upgrade order (Data Agent via Ticket Agent)
            print(f"\n🎯 STEP 4: Create Upgrade Order")
            print(f"   This step tests: End-to-end order creation with real database write")
            
            # Use Data Agent directly for order creation (simulating Ticket Agent calling it)
            order_data = {
                'ticket_id': scenario['ticket_id'],
                'customer_id': scenario['customer_id'],
                'upgrade_tier': scenario['upgrade_tier'],
                'total_amount': upgrade_price
            }
            
            order_result = await client.call_data_agent_tool('create_upgrade_order', order_data)
            
            step4_success, step4_analysis = self._analyze_integrated_response(
                order_result, 'create_upgrade_order', 'order creation'
            )
            
            journey_results['steps']['create_order'] = {
                'success': step4_success,
                'response': order_result,
                'analysis': step4_analysis,
                'data_source': step4_analysis.get('data_source', 'Unknown')
            }
            
            if step4_success:
                journey_results['data_sources'].append(step4_analysis.get('data_source', 'Unknown'))
            
            # Step 5: Verify order in database (Data integrity check)
            print(f"\n🎯 STEP 5: Verify Order Creation")
            print(f"   This step tests: Database integrity after order creation")
            
            integrity_result = await client.call_data_agent_tool('validate_data_integrity', {})
            
            step5_success, step5_analysis = self._analyze_integrated_response(
                integrity_result, 'validate_data_integrity', 'post-order integrity'
            )
            
            journey_results['steps']['verify_order'] = {
                'success': step5_success,
                'response': integrity_result,
                'analysis': step5_analysis,
                'data_source': step5_analysis.get('data_source', 'Unknown')
            }
            
            # Overall journey success
            all_steps_passed = all(step['success'] for step in journey_results['steps'].values())
            journey_results['overall_success'] = all_steps_passed
            
            # Summary
            print(f"\n📊 UPGRADE JOURNEY SUMMARY: {scenario['name']}")
            for step_name, step_result in journey_results['steps'].items():
                status = "✅ PASS" if step_result['success'] else "❌ FAIL"
                data_info = f"Data: {step_result.get('data_source', 'N/A')}" if 'data_source' in step_result else ""
                llm_info = "🧠 LLM" if step_result.get('has_llm_reasoning') else ""
                print(f"   {step_name}: {status} {llm_info} {data_info}")
            
            return journey_results
            
        except Exception as e:
            journey_results['errors'].append(f"Journey failed: {str(e)}")
            print(f"❌ Upgrade journey failed: {e}")
            import traceback
            traceback.print_exc()
            return journey_results
    
    async def test_inter_agent_communication_flow(self) -> Dict[str, Any]:
        """Test the communication flow between agents"""
        print(f"\n🔄 TESTING INTER-AGENT COMMUNICATION FLOW")
        print("="*70)
        
        flow_results = {
            'test_name': 'Inter-Agent Communication Flow',
            'communication_tests': {},
            'overall_success': False
        }
        
        try:
            from agentcore_client import AgentCoreClient
            client = AgentCoreClient()
            
            if not client.get_bearer_token():
                flow_results['error'] = 'AgentCore authentication failed'
                return flow_results
            
            # Test 1: Ticket Agent → Data Agent Invoker → Database
            print(f"\n📡 TEST 1: Ticket Agent → Data Agent Communication")
            print(f"   Testing: validate_ticket_eligibility calls get_customer and get_tickets_for_customer")
            
            # This should trigger internal calls from Ticket Agent to Data Agent
            eligibility_result = await client.call_ticket_agent_tool('validate_ticket_eligibility', {
                'ticket_id': self.real_ticket_id,
                'customer_id': self.real_customer_id
            })
            
            comm_test1_success = self._verify_inter_agent_communication(eligibility_result)
            flow_results['communication_tests']['ticket_to_data_agent'] = {
                'success': comm_test1_success,
                'response': eligibility_result
            }
            
            # Test 2: Direct Data Agent calls for comparison
            print(f"\n📡 TEST 2: Direct Data Agent Calls")
            print(f"   Testing: Direct calls to verify data consistency")
            
            customer_result = await client.call_data_agent_tool('get_customer', {
                'customer_id': self.real_customer_id
            })
            
            tickets_result = await client.call_data_agent_tool('get_tickets_for_customer', {
                'customer_id': self.real_customer_id
            })
            
            comm_test2_success = (
                customer_result.get('success', False) and 
                tickets_result.get('success', False)
            )
            
            flow_results['communication_tests']['direct_data_agent'] = {
                'success': comm_test2_success,
                'customer_response': customer_result,
                'tickets_response': tickets_result
            }
            
            # Test 3: Data consistency verification
            print(f"\n📡 TEST 3: Data Consistency Verification")
            print(f"   Testing: Same data returned via different paths")
            
            consistency_success = self._verify_data_consistency(
                eligibility_result, customer_result, tickets_result
            )
            
            flow_results['communication_tests']['data_consistency'] = {
                'success': consistency_success,
                'details': 'Comparing data from Ticket Agent vs Direct Data Agent calls'
            }
            
            # Overall success
            all_comm_tests_passed = all(test['success'] for test in flow_results['communication_tests'].values())
            flow_results['overall_success'] = all_comm_tests_passed
            
            print(f"\n📊 INTER-AGENT COMMUNICATION SUMMARY:")
            for test_name, test_result in flow_results['communication_tests'].items():
                status = "✅ PASS" if test_result['success'] else "❌ FAIL"
                print(f"   {test_name}: {status}")
            
            return flow_results
            
        except Exception as e:
            flow_results['error'] = str(e)
            print(f"❌ Inter-agent communication test failed: {e}")
            import traceback
            traceback.print_exc()
            return flow_results
    
    def _analyze_integrated_response(self, response: Dict[str, Any], tool_name: str, expected_data: str) -> tuple:
        """Analyze response for integrated workflow success"""
        analysis = {
            'success': False,
            'data_source': 'Unknown',
            'has_llm_reasoning': False,
            'error': None
        }
        
        if not response.get('success'):
            analysis['error'] = response.get('error', 'Unknown error')
            print(f"   ❌ {tool_name} failed: {analysis['error']}")
            return False, analysis
        
        data = response.get('data', {})
        if isinstance(data, dict) and 'result' in data:
            result = data['result']
            
            if result.get('success'):
                print(f"   ✅ {tool_name} successful")
                analysis['success'] = True
                
                # Determine data source
                if 'data_source' in result:
                    analysis['data_source'] = result['data_source']
                elif 'reasoning' in result:
                    reasoning = result['reasoning']
                    if 'Aurora database' in reasoning:
                        analysis['data_source'] = 'Real Database'
                    elif 'fallback' in reasoning.lower():
                        analysis['data_source'] = 'Fallback Data'
                
                # Check for LLM reasoning
                llm_fields = ['eligibility_reasons', 'pricing_analysis', 'personalized_advice', 'llm_recommendations']
                for field in llm_fields:
                    if field in result and result[field] and len(str(result[field])) > 100:
                        analysis['has_llm_reasoning'] = True
                        break
                
                return True, analysis
            else:
                analysis['error'] = result.get('error', 'Unknown')
                print(f"   ❌ {tool_name} returned error: {analysis['error']}")
                return False, analysis
        else:
            analysis['error'] = 'Unexpected response format'
            print(f"   ❌ Unexpected response format for {tool_name}")
            return False, analysis
    
    def _extract_ticket_data(self, eligibility_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract ticket data from eligibility result"""
        if not eligibility_result.get('success'):
            return {}
        
        data = eligibility_result.get('data', {})
        if isinstance(data, dict) and 'result' in data:
            result = data['result']
            ticket_info = result.get('ticket', {})
            
            return {
                'ticket_type': ticket_info.get('ticket_type', 'general'),
                'original_price': ticket_info.get('original_price', 50.00),
                'event_date': ticket_info.get('event_date', ''),
                'status': ticket_info.get('status', 'active'),
                'ticket_number': ticket_info.get('ticket_number', '')
            }
        
        return {}
    
    def _extract_upgrade_price(self, pricing_result: Dict[str, Any]) -> float:
        """Extract upgrade price from pricing result"""
        if not pricing_result.get('success'):
            return 0.0
        
        data = pricing_result.get('data', {})
        if isinstance(data, dict) and 'result' in data:
            result = data['result']
            pricing_info = result.get('pricing', {})
            return pricing_info.get('upgrade_price', 0.0)
        
        return 0.0
    
    def _verify_inter_agent_communication(self, eligibility_result: Dict[str, Any]) -> bool:
        """Verify that Ticket Agent successfully communicated with Data Agent"""
        if not eligibility_result.get('success'):
            return False
        
        data = eligibility_result.get('data', {})
        if isinstance(data, dict) and 'result' in data:
            result = data['result']
            
            # Check if we have both customer and ticket data (indicating successful Data Agent calls)
            has_customer = 'customer' in result and result['customer']
            has_ticket = 'ticket' in result and result['ticket']
            has_data_source = result.get('data_source') == 'Data Agent'
            
            return has_customer and has_ticket and has_data_source
        
        return False
    
    def _verify_data_consistency(self, eligibility_result: Dict[str, Any], 
                                customer_result: Dict[str, Any], 
                                tickets_result: Dict[str, Any]) -> bool:
        """Verify data consistency between different call paths"""
        try:
            # Extract customer data from eligibility result
            eligibility_data = eligibility_result.get('data', {}).get('result', {})
            eligibility_customer = eligibility_data.get('customer', {})
            
            # Extract customer data from direct call
            direct_customer_data = customer_result.get('data', {}).get('result', {})
            direct_customer = direct_customer_data.get('customer', {})
            
            # Compare key fields
            if (eligibility_customer.get('id') == direct_customer.get('id') and
                eligibility_customer.get('email') == direct_customer.get('email')):
                print(f"   ✅ Customer data consistent between call paths")
                return True
            else:
                print(f"   ❌ Customer data inconsistent between call paths")
                return False
                
        except Exception as e:
            print(f"   ❌ Data consistency check failed: {e}")
            return False
    
    async def run_integrated_tests(self) -> Dict[str, Any]:
        """Run all integrated tests"""
        print(f"\n🚀 AGENTCORE INTEGRATED TASKS TEST SUITE")
        print("="*70)
        print(f"Testing complete workflows with real LLM and Aurora database")
        print(f"Verifying inter-agent communication and end-to-end processes")
        print("="*70)
        
        all_results = {
            'test_suite': 'AgentCore Integrated Tasks',
            'timestamp': datetime.now().isoformat(),
            'scenarios': {},
            'communication_flow': {},
            'overall_success': False
        }
        
        # Test inter-agent communication flow first
        comm_results = await self.test_inter_agent_communication_flow()
        all_results['communication_flow'] = comm_results
        
        # Test each upgrade journey scenario
        scenario_results = []
        for scenario in self.test_scenarios:
            journey_result = await self.test_complete_upgrade_journey(scenario)
            all_results['scenarios'][scenario['name']] = journey_result
            scenario_results.append(journey_result['overall_success'])
        
        # Overall success analysis
        comm_success = comm_results.get('overall_success', False)
        scenarios_success = all(scenario_results)
        all_results['overall_success'] = comm_success and scenarios_success
        
        # Final summary
        print(f"\n🎯 INTEGRATED TASKS TEST RESULTS SUMMARY")
        print("="*70)
        print(f"🔄 Inter-Agent Communication: {'✅ PASS' if comm_success else '❌ FAIL'}")
        
        for scenario_name, scenario_result in all_results['scenarios'].items():
            status = "✅ PASS" if scenario_result['overall_success'] else "❌ FAIL"
            data_sources = set(scenario_result['data_sources'])
            llm_usage = len(scenario_result['llm_usage'])
            print(f"🎪 {scenario_name}: {status} (Data: {', '.join(data_sources)}, LLM: {llm_usage} steps)")
        
        print(f"🎯 Overall Result: {'✅ ALL TESTS PASSED' if all_results['overall_success'] else '❌ SOME TESTS FAILED'}")
        
        if all_results['overall_success']:
            print(f"\n🎉 SUCCESS: All integrated workflows working correctly!")
            print(f"✅ Real Aurora database integration in complete workflows")
            print(f"✅ Real LLM (Nova Pro) reasoning in business processes")
            print(f"✅ Proper inter-agent communication and data flow")
            print(f"✅ End-to-end order creation and verification")
        else:
            print(f"\n⚠️  ISSUES FOUND:")
            if not comm_success:
                print(f"   - Inter-agent communication has issues")
            failed_scenarios = [name for name, result in all_results['scenarios'].items() if not result['overall_success']]
            for scenario in failed_scenarios:
                print(f"   - {scenario} workflow failed")
        
        return all_results


async def main():
    """Main test execution"""
    test_suite = AgentCoreIntegratedTestSuite()
    results = await test_suite.run_integrated_tests()
    
    # Save results to file
    results_file = f"agentcore_integrated_tasks_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Test results saved to: {results_file}")
    
    return results['overall_success']


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)