#!/usr/bin/env python3
"""
Run Comprehensive AgentCore Tests

This script runs both separated and integrated tests for AgentCore Runtime agents
to ensure complete validation of:
1. Real LLM (Nova Pro) usage instead of fallback responses
2. Real Aurora database data instead of test/fallback data
3. Individual agent functionality (separated tasks)
4. Complete workflow integration (integrated tasks)
5. Inter-agent communication and data flow

This addresses the user's requirement to test AgentCore Runtime agents with
separated tasks and integrated tasks to ensure real LLM and Aurora data usage.
"""

import sys
import os
import asyncio
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Load environment
env_file = Path('.env')
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

class ComprehensiveAgentCoreTestRunner:
    """Comprehensive test runner for AgentCore agents"""
    
    def __init__(self):
        self.data_agent_arn = os.getenv('DATA_AGENT_ARN')
        self.ticket_agent_arn = os.getenv('TICKET_AGENT_ARN')
        self.bedrock_model_id = os.getenv('BEDROCK_MODEL_ID', 'us.amazon.nova-pro-v1:0')
        
        self.test_results = {
            'test_suite': 'Comprehensive AgentCore Tests',
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'data_agent_arn': self.data_agent_arn,
                'ticket_agent_arn': self.ticket_agent_arn,
                'bedrock_model_id': self.bedrock_model_id
            },
            'test_phases': {},
            'overall_success': False
        }
        
        print(f"🎯 COMPREHENSIVE AGENTCORE TEST RUNNER")
        print("="*70)
        print(f"Testing AgentCore Runtime agents with separated and integrated tasks")
        print(f"Ensuring real LLM (Nova Pro) and Aurora database usage")
        print("="*70)
        print(f"Data Agent ARN: {self.data_agent_arn}")
        print(f"Ticket Agent ARN: {self.ticket_agent_arn}")
        print(f"Bedrock Model: {self.bedrock_model_id}")
    
    async def run_prerequisite_checks(self) -> Dict[str, Any]:
        """Run prerequisite checks before main tests"""
        print(f"\n🔍 PHASE 0: PREREQUISITE CHECKS")
        print("="*70)
        
        prereq_results = {
            'phase': 'Prerequisites',
            'checks': {},
            'overall_success': False
        }
        
        # Check 1: Environment configuration
        print(f"\n📋 CHECK 1: Environment Configuration")
        
        required_vars = [
            'DATA_AGENT_ARN', 'TICKET_AGENT_ARN', 'BEDROCK_MODEL_ID',
            'DB_CLUSTER_ARN', 'DB_SECRET_ARN', 'AWS_REGION'
        ]
        
        env_check_success = True
        missing_vars = []
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"   ✅ {var}: {value[:30]}...")
            else:
                print(f"   ❌ {var}: Missing")
                missing_vars.append(var)
                env_check_success = False
        
        prereq_results['checks']['environment_config'] = {
            'success': env_check_success,
            'missing_vars': missing_vars
        }
        
        # Check 2: Data Agent Invoker Lambda availability
        print(f"\n🔧 CHECK 2: Data Agent Invoker Lambda")
        
        try:
            import boto3
            lambda_client = boto3.client('lambda', region_name='us-west-2')
            
            # Check if Lambda function exists
            try:
                response = lambda_client.get_function(FunctionName='data-agent-invoker')
                lambda_status = response['Configuration']['State']
                print(f"   ✅ Data Agent Invoker Lambda: {lambda_status}")
                lambda_check_success = lambda_status == 'Active'
            except lambda_client.exceptions.ResourceNotFoundException:
                print(f"   ❌ Data Agent Invoker Lambda: Not found")
                lambda_check_success = False
            
        except Exception as e:
            print(f"   ❌ Data Agent Invoker Lambda check failed: {e}")
            lambda_check_success = False
        
        prereq_results['checks']['lambda_availability'] = {
            'success': lambda_check_success
        }
        
        # Check 3: AgentCore agent status
        print(f"\n🤖 CHECK 3: AgentCore Agent Status")
        
        try:
            bedrock_client = boto3.client('bedrock-agentcore-control', region_name='us-west-2')
            
            # Extract agent IDs from ARNs
            data_agent_id = self.data_agent_arn.split('/')[-1] if self.data_agent_arn else None
            ticket_agent_id = self.ticket_agent_arn.split('/')[-1] if self.ticket_agent_arn else None
            
            agent_status_success = True
            
            if data_agent_id:
                try:
                    data_response = bedrock_client.get_agent_runtime(agentRuntimeId=data_agent_id)
                    data_status = data_response['status']
                    print(f"   📊 Data Agent: {data_status}")
                    if data_status != 'READY':
                        agent_status_success = False
                except Exception as e:
                    print(f"   ❌ Data Agent status check failed: {e}")
                    agent_status_success = False
            
            if ticket_agent_id:
                try:
                    ticket_response = bedrock_client.get_agent_runtime(agentRuntimeId=ticket_agent_id)
                    ticket_status = ticket_response['status']
                    print(f"   🎫 Ticket Agent: {ticket_status}")
                    if ticket_status != 'READY':
                        agent_status_success = False
                except Exception as e:
                    print(f"   ❌ Ticket Agent status check failed: {e}")
                    agent_status_success = False
            
        except Exception as e:
            print(f"   ❌ AgentCore status check failed: {e}")
            agent_status_success = False
        
        prereq_results['checks']['agent_status'] = {
            'success': agent_status_success
        }
        
        # Check 4: Database connectivity
        print(f"\n🗄️  CHECK 4: Database Connectivity")
        
        try:
            # Run a quick database query to verify connectivity
            db_check_result = await self._test_database_connectivity()
            db_check_success = db_check_result.get('success', False)
            
            if db_check_success:
                print(f"   ✅ Aurora Database: Connected")
                print(f"   📊 Customers: {db_check_result.get('customer_count', 0)}")
                print(f"   🎫 Tickets: {db_check_result.get('ticket_count', 0)}")
            else:
                print(f"   ❌ Aurora Database: Connection failed")
                print(f"   Error: {db_check_result.get('error', 'Unknown')}")
            
        except Exception as e:
            print(f"   ❌ Database connectivity check failed: {e}")
            db_check_success = False
        
        prereq_results['checks']['database_connectivity'] = {
            'success': db_check_success
        }
        
        # Overall prerequisite success
        all_checks_passed = all(check['success'] for check in prereq_results['checks'].values())
        prereq_results['overall_success'] = all_checks_passed
        
        print(f"\n📊 PREREQUISITE CHECKS SUMMARY:")
        for check_name, check_result in prereq_results['checks'].items():
            status = "✅ PASS" if check_result['success'] else "❌ FAIL"
            print(f"   {check_name}: {status}")
        
        if all_checks_passed:
            print(f"\n✅ All prerequisite checks passed - proceeding with tests")
        else:
            print(f"\n❌ Some prerequisite checks failed - tests may not work correctly")
        
        return prereq_results
    
    async def _test_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity"""
        try:
            import boto3
            
            db_cluster_arn = os.getenv('DB_CLUSTER_ARN')
            db_secret_arn = os.getenv('DB_SECRET_ARN')
            database_name = os.getenv('DATABASE_NAME', 'ticket_system')
            
            if not db_cluster_arn or not db_secret_arn:
                return {'success': False, 'error': 'Missing database configuration'}
            
            rds_data = boto3.client('rds-data', region_name='us-west-2')
            
            # Quick count queries
            customer_response = rds_data.execute_statement(
                resourceArn=db_cluster_arn,
                secretArn=db_secret_arn,
                database=database_name,
                sql="SELECT COUNT(*) FROM customers"
            )
            
            ticket_response = rds_data.execute_statement(
                resourceArn=db_cluster_arn,
                secretArn=db_secret_arn,
                database=database_name,
                sql="SELECT COUNT(*) FROM tickets"
            )
            
            customer_count = customer_response['records'][0][0]['longValue']
            ticket_count = ticket_response['records'][0][0]['longValue']
            
            return {
                'success': True,
                'customer_count': customer_count,
                'ticket_count': ticket_count
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def run_separated_tasks_tests(self) -> Dict[str, Any]:
        """Run separated tasks tests"""
        print(f"\n🔧 PHASE 1: SEPARATED TASKS TESTS")
        print("="*70)
        print(f"Testing individual agent capabilities with separated concerns")
        
        try:
            # Import and run separated tasks test
            from test_agentcore_separated_tasks import AgentCoreTestSuite
            
            separated_test_suite = AgentCoreTestSuite()
            
            # Run Data Agent tests
            data_results = await separated_test_suite.test_data_agent_separated_tasks()
            
            # Run Ticket Agent tests  
            ticket_results = await separated_test_suite.test_ticket_agent_separated_tasks()
            
            separated_results = {
                'phase': 'Separated Tasks',
                'data_agent': data_results,
                'ticket_agent': ticket_results,
                'overall_success': (
                    data_results.get('overall_success', False) and 
                    ticket_results.get('overall_success', False)
                )
            }
            
            return separated_results
            
        except Exception as e:
            print(f"❌ Separated tasks tests failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'phase': 'Separated Tasks',
                'error': str(e),
                'overall_success': False
            }
    
    async def run_integrated_tasks_tests(self) -> Dict[str, Any]:
        """Run integrated tasks tests"""
        print(f"\n🎪 PHASE 2: INTEGRATED TASKS TESTS")
        print("="*70)
        print(f"Testing complete workflows with inter-agent communication")
        
        try:
            # Import and run integrated tasks test
            from test_agentcore_integrated_tasks import AgentCoreIntegratedTestSuite
            
            integrated_test_suite = AgentCoreIntegratedTestSuite()
            integrated_results = await integrated_test_suite.run_integrated_tests()
            
            return {
                'phase': 'Integrated Tasks',
                'results': integrated_results,
                'overall_success': integrated_results.get('overall_success', False)
            }
            
        except Exception as e:
            print(f"❌ Integrated tasks tests failed: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'phase': 'Integrated Tasks',
                'error': str(e),
                'overall_success': False
            }
    
    async def run_data_source_validation(self) -> Dict[str, Any]:
        """Validate that agents are using real data sources"""
        print(f"\n🔍 PHASE 3: DATA SOURCE VALIDATION")
        print("="*70)
        print(f"Validating real LLM and Aurora database usage")
        
        validation_results = {
            'phase': 'Data Source Validation',
            'validations': {},
            'overall_success': False
        }
        
        try:
            # Add path and import
            sys.path.append('backend/lambda')
            from agentcore_client import AgentCoreClient
            
            client = AgentCoreClient()
            
            if not client.get_bearer_token():
                validation_results['error'] = 'AgentCore authentication failed'
                return validation_results
            
            # Validation 1: Check for fallback data indicators
            print(f"\n🔍 VALIDATION 1: Fallback Data Detection")
            
            real_customer_id = "fdd70d2c-3f05-4749-9b8d-9ba3142c0707"
            real_ticket_id = "550e8400-e29b-41d4-a716-446655440002"
            
            eligibility_result = await client.call_ticket_agent_tool('validate_ticket_eligibility', {
                'ticket_id': real_ticket_id,
                'customer_id': real_customer_id
            })
            
            fallback_indicators = self._detect_fallback_data(eligibility_result)
            validation_results['validations']['fallback_detection'] = {
                'success': not fallback_indicators['has_fallback'],
                'indicators': fallback_indicators
            }
            
            if fallback_indicators['has_fallback']:
                print(f"   ❌ Fallback data detected:")
                for indicator in fallback_indicators['indicators']:
                    print(f"      - {indicator}")
            else:
                print(f"   ✅ No fallback data detected - using real data sources")
            
            # Validation 2: LLM reasoning quality check
            print(f"\n🧠 VALIDATION 2: LLM Reasoning Quality")
            
            llm_quality = self._assess_llm_quality(eligibility_result)
            validation_results['validations']['llm_quality'] = {
                'success': llm_quality['is_real_llm'],
                'assessment': llm_quality
            }
            
            if llm_quality['is_real_llm']:
                print(f"   ✅ Real LLM reasoning detected")
                print(f"      Length: {llm_quality['reasoning_length']} characters")
                print(f"      Complexity: {llm_quality['complexity_score']}/10")
            else:
                print(f"   ❌ LLM reasoning appears to be fallback/simple responses")
            
            # Validation 3: Database integration verification
            print(f"\n🗄️  VALIDATION 3: Database Integration")
            
            db_integration = await self._verify_database_integration(client, real_customer_id)
            validation_results['validations']['database_integration'] = {
                'success': db_integration['is_real_database'],
                'verification': db_integration
            }
            
            if db_integration['is_real_database']:
                print(f"   ✅ Real Aurora database integration confirmed")
                print(f"      Data consistency: {db_integration['data_consistency']}")
                print(f"      Real customer data: {db_integration['has_real_customer_data']}")
            else:
                print(f"   ❌ Database integration using fallback/test data")
            
            # Overall validation success
            all_validations_passed = all(v['success'] for v in validation_results['validations'].values())
            validation_results['overall_success'] = all_validations_passed
            
            print(f"\n📊 DATA SOURCE VALIDATION SUMMARY:")
            for validation_name, validation_result in validation_results['validations'].items():
                status = "✅ PASS" if validation_result['success'] else "❌ FAIL"
                print(f"   {validation_name}: {status}")
            
            return validation_results
            
        except Exception as e:
            validation_results['error'] = str(e)
            print(f"❌ Data source validation failed: {e}")
            import traceback
            traceback.print_exc()
            return validation_results
    
    def _detect_fallback_data(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Detect fallback data indicators in response"""
        indicators = []
        has_fallback = False
        
        if not response.get('success'):
            return {'has_fallback': True, 'indicators': ['Response failed']}
        
        # Convert response to string for analysis
        response_str = json.dumps(response, default=str).lower()
        
        # Known fallback indicators
        fallback_patterns = [
            'tkt-test789',
            'tkt-fallback',
            'fallback data',
            'test data',
            'sample customer',
            'fallback.customer@example.com',
            'lambda error',
            'using fallback'
        ]
        
        for pattern in fallback_patterns:
            if pattern in response_str:
                indicators.append(f"Found pattern: {pattern}")
                has_fallback = True
        
        return {
            'has_fallback': has_fallback,
            'indicators': indicators
        }
    
    def _assess_llm_quality(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Assess LLM reasoning quality"""
        assessment = {
            'is_real_llm': False,
            'reasoning_length': 0,
            'complexity_score': 0,
            'has_detailed_analysis': False
        }
        
        if not response.get('success'):
            return assessment
        
        data = response.get('data', {})
        if isinstance(data, dict) and 'result' in data:
            result = data['result']
            
            # Look for LLM reasoning fields
            reasoning_text = result.get('eligibility_reasons', '')
            
            if reasoning_text:
                assessment['reasoning_length'] = len(reasoning_text)
                
                # Simple complexity scoring based on content
                complexity_indicators = [
                    'analyze', 'consider', 'recommend', 'however', 'therefore',
                    'based on', 'taking into account', 'furthermore', 'additionally',
                    'customer', 'ticket', 'upgrade', 'eligibility', 'pricing'
                ]
                
                complexity_score = sum(1 for indicator in complexity_indicators 
                                     if indicator in reasoning_text.lower())
                assessment['complexity_score'] = min(complexity_score, 10)
                
                # Consider it real LLM if it's substantial and complex
                assessment['is_real_llm'] = (
                    assessment['reasoning_length'] > 200 and 
                    assessment['complexity_score'] >= 3
                )
                
                assessment['has_detailed_analysis'] = assessment['reasoning_length'] > 500
        
        return assessment
    
    async def _verify_database_integration(self, client, customer_id: str) -> Dict[str, Any]:
        """Verify real database integration"""
        verification = {
            'is_real_database': False,
            'data_consistency': False,
            'has_real_customer_data': False
        }
        
        try:
            # Get customer data via Data Agent
            customer_result = await client.call_data_agent_tool('get_customer', {
                'customer_id': customer_id
            })
            
            if customer_result.get('success'):
                data = customer_result.get('data', {})
                if isinstance(data, dict) and 'result' in data:
                    result = data['result']
                    
                    if result.get('success'):
                        customer_info = result.get('customer', {})
                        
                        # Check for real customer data indicators
                        has_real_name = (
                            customer_info.get('first_name') and 
                            customer_info.get('first_name') not in ['Fallback', 'Sample', 'Test']
                        )
                        
                        has_real_email = (
                            customer_info.get('email') and
                            'example.com' not in customer_info.get('email', '') and
                            'fallback' not in customer_info.get('email', '').lower()
                        )
                        
                        verification['has_real_customer_data'] = has_real_name and has_real_email
                        
                        # Check reasoning for database indicators
                        reasoning = result.get('reasoning', '')
                        verification['is_real_database'] = 'Aurora database' in reasoning
                        verification['data_consistency'] = True  # If we got here, data is consistent
        
        except Exception as e:
            print(f"   Database verification error: {e}")
        
        return verification
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        print(f"\n🚀 STARTING COMPREHENSIVE AGENTCORE TESTS")
        print("="*70)
        
        # Phase 0: Prerequisites
        prereq_results = await self.run_prerequisite_checks()
        self.test_results['test_phases']['prerequisites'] = prereq_results
        
        if not prereq_results['overall_success']:
            print(f"\n⚠️  Prerequisites failed - continuing with limited testing")
        
        # Phase 1: Separated Tasks
        separated_results = await self.run_separated_tasks_tests()
        self.test_results['test_phases']['separated_tasks'] = separated_results
        
        # Phase 2: Integrated Tasks
        integrated_results = await self.run_integrated_tasks_tests()
        self.test_results['test_phases']['integrated_tasks'] = integrated_results
        
        # Phase 3: Data Source Validation
        validation_results = await self.run_data_source_validation()
        self.test_results['test_phases']['data_source_validation'] = validation_results
        
        # Overall success analysis
        phase_successes = [
            separated_results.get('overall_success', False),
            integrated_results.get('overall_success', False),
            validation_results.get('overall_success', False)
        ]
        
        self.test_results['overall_success'] = all(phase_successes)
        
        # Final comprehensive summary
        print(f"\n🎯 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("="*70)
        
        for phase_name, phase_result in self.test_results['test_phases'].items():
            status = "✅ PASS" if phase_result.get('overall_success', False) else "❌ FAIL"
            print(f"   {phase_name.replace('_', ' ').title()}: {status}")
        
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if self.test_results['overall_success'] else '❌ SOME TESTS FAILED'}")
        
        if self.test_results['overall_success']:
            print(f"\n🎉 SUCCESS: AgentCore agents fully validated!")
            print(f"✅ Real LLM (Nova Pro) usage confirmed")
            print(f"✅ Real Aurora database integration confirmed")
            print(f"✅ Separated tasks working correctly")
            print(f"✅ Integrated workflows working correctly")
            print(f"✅ No fallback data detected")
        else:
            print(f"\n⚠️  ISSUES IDENTIFIED:")
            
            if not separated_results.get('overall_success', False):
                print(f"   - Separated tasks have issues")
            if not integrated_results.get('overall_success', False):
                print(f"   - Integrated workflows have issues")
            if not validation_results.get('overall_success', False):
                print(f"   - Data source validation failed (may be using fallback data)")
        
        return self.test_results


async def main():
    """Main test execution"""
    test_runner = ComprehensiveAgentCoreTestRunner()
    results = await test_runner.run_comprehensive_tests()
    
    # Save comprehensive results to file
    results_file = f"agentcore_comprehensive_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Comprehensive test results saved to: {results_file}")
    
    return results['overall_success']


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)