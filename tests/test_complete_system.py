#!/usr/bin/env python3
"""
Complete System Test Suite

This script runs comprehensive tests for the entire Ticket Auto-Processing System:
- Infrastructure tests
- Database tests  
- Agent tests
- API tests
- Frontend tests
- End-to-end integration tests

Usage:
    python tests/test_complete_system.py [component]
    
Components:
    all           - Run all tests (default)
    infrastructure - Test AWS infrastructure
    database      - Test database connectivity and schema
    agents        - Test AgentCore agents
    api           - Test backend API
    frontend      - Test frontend deployment
    integration   - Test end-to-end workflows
    
Examples:
    python tests/test_complete_system.py
    python tests/test_complete_system.py database
    python tests/test_complete_system.py agents
"""

import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

class SystemTestSuite:
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
        
    def log_test_result(self, test_name: str, success: bool, duration: float, details: str = ""):
        """Log a test result"""
        self.test_results.append({
            'test_name': test_name,
            'success': success,
            'duration': duration,
            'details': details
        })
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name} ({duration:.2f}s)")
        if details and not success:
            print(f"    Details: {details}")
    
    def run_script_test(self, script_name: str, test_name: str) -> bool:
        """Run a test script and log results"""
        script_path = Path(__file__).parent / script_name
        
        if not script_path.exists():
            self.log_test_result(test_name, False, 0, f"Script not found: {script_name}")
            return False
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)], 
                check=True, 
                capture_output=True, 
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            self.log_test_result(test_name, True, duration)
            return True
            
        except subprocess.CalledProcessError as e:
            duration = time.time() - start_time
            details = f"Exit code {e.returncode}"
            if e.stderr:
                details += f", Error: {e.stderr[:200]}"
            self.log_test_result(test_name, False, duration, details)
            return False
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, duration, "Test timed out")
            return False
            
        except Exception as e:
            duration = time.time() - start_time
            self.log_test_result(test_name, False, duration, str(e))
            return False
    
    def test_infrastructure(self) -> bool:
        """Test AWS infrastructure setup"""
        print("\n🏗️  Testing AWS Infrastructure...")
        
        # Test infrastructure validation
        success = self.run_script_test("validate_setup.py", "Infrastructure Validation")
        
        return success
    
    def test_database(self) -> bool:
        """Test database connectivity and schema"""
        print("\n🗄️  Testing Database...")
        
        results = []
        
        # Test database schema validation
        results.append(self.run_script_test("../database/validate_schema.py", "Database Schema Validation"))
        
        # Test database connectivity with real data
        results.append(self.run_script_test("../database/test_real_data.py", "Database Real Data Test"))
        
        return all(results)
    
    def test_agents(self) -> bool:
        """Test AgentCore agents"""
        print("\n🤖 Testing AgentCore Agents...")
        
        results = []
        
        # Test data agent
        results.append(self.run_script_test("comprehensive_data_agent_test.py", "Data Agent Comprehensive Test"))
        
        # Test ticket agent
        results.append(self.run_script_test("../backend/agents/test_ticket_agent.py", "Ticket Agent Test"))
        
        # Test multi-agent communication
        results.append(self.run_script_test("test_multi_agent_communication.py", "Multi-Agent Communication Test"))
        
        # Test MCP server
        results.append(self.run_script_test("test_mcp_server.py", "MCP Server Test"))
        
        return all(results)
    
    def test_api(self) -> bool:
        """Test backend API"""
        print("\n🔌 Testing Backend API...")
        
        results = []
        
        # Test Lambda AgentCore integration
        results.append(self.run_script_test("../backend/lambda/test_lambda_agentcore.py", "Lambda AgentCore Integration"))
        
        # Test payment and notifications
        results.append(self.run_script_test("test_payment_and_notifications.py", "Payment and Notifications Test"))
        
        return all(results)
    
    def test_frontend(self) -> bool:
        """Test frontend deployment"""
        print("\n🌐 Testing Frontend Deployment...")
        
        # Test frontend deployment
        success = self.run_script_test("test_frontend_deployment.py", "Frontend Deployment Test")
        
        return success
    
    def test_integration(self) -> bool:
        """Test end-to-end integration"""
        print("\n🔄 Testing End-to-End Integration...")
        
        results = []
        
        # Test full system integration
        results.append(self.run_script_test("test_full_system_integration.py", "Full System Integration Test"))
        
        # Test customer journey simulation
        results.append(self.run_script_test("test_customer_journey_simulation.py", "Customer Journey Simulation"))
        
        # Test natural conversation
        results.append(self.run_script_test("test_natural_conversation.py", "Natural Conversation Test"))
        
        # Demo system capabilities
        results.append(self.run_script_test("demo_system_capabilities.py", "System Capabilities Demo"))
        
        return all(results)
    
    def run_all_tests(self) -> bool:
        """Run all system tests"""
        print("🧪 Running Complete System Test Suite")
        print("=" * 60)
        
        test_components = [
            ("Infrastructure", self.test_infrastructure),
            ("Database", self.test_database),
            ("Agents", self.test_agents),
            ("API", self.test_api),
            ("Frontend", self.test_frontend),
            ("Integration", self.test_integration)
        ]
        
        component_results = []
        
        for component_name, test_func in test_components:
            try:
                print(f"\n{'='*20} {component_name} Tests {'='*20}")
                result = test_func()
                component_results.append((component_name, result))
            except Exception as e:
                print(f"❌ {component_name} tests failed with exception: {e}")
                component_results.append((component_name, False))
        
        return self.generate_test_report(component_results)
    
    def run_component_test(self, component: str) -> bool:
        """Run tests for a specific component"""
        component_map = {
            'infrastructure': ("Infrastructure", self.test_infrastructure),
            'database': ("Database", self.test_database),
            'agents': ("Agents", self.test_agents),
            'api': ("API", self.test_api),
            'frontend': ("Frontend", self.test_frontend),
            'integration': ("Integration", self.test_integration)
        }
        
        if component not in component_map:
            print(f"❌ Unknown component: {component}")
            print(f"Available components: {', '.join(component_map.keys())}")
            return False
        
        component_name, test_func = component_map[component]
        
        print(f"🧪 Running {component_name} Tests")
        print("=" * 60)
        
        try:
            result = test_func()
            component_results = [(component_name, result)]
            return self.generate_test_report(component_results)
        except Exception as e:
            print(f"❌ {component_name} tests failed with exception: {e}")
            return False
    
    def generate_test_report(self, component_results: List[Tuple[str, bool]]) -> bool:
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        
        print("\n" + "=" * 60)
        print("📊 SYSTEM TEST REPORT")
        print("=" * 60)
        
        # Component summary
        print("\n🏷️  Component Results:")
        passed_components = 0
        total_components = len(component_results)
        
        for component_name, result in component_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {status} {component_name}")
            if result:
                passed_components += 1
        
        # Individual test summary
        print(f"\n🔍 Individual Test Results:")
        passed_tests = 0
        total_tests = len(self.test_results)
        
        for test in self.test_results:
            status = "✅ PASS" if test['success'] else "❌ FAIL"
            print(f"  {status} {test['test_name']} ({test['duration']:.2f}s)")
            if test['success']:
                passed_tests += 1
        
        # Statistics
        print(f"\n📈 Statistics:")
        print(f"  Components: {passed_components}/{total_components} passed")
        print(f"  Individual Tests: {passed_tests}/{total_tests} passed")
        print(f"  Total Duration: {total_duration:.2f}s")
        print(f"  Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        # Save detailed report
        report = {
            'timestamp': time.time(),
            'total_duration': total_duration,
            'component_results': [
                {'name': name, 'passed': result} 
                for name, result in component_results
            ],
            'test_results': self.test_results,
            'summary': {
                'components_passed': passed_components,
                'components_total': total_components,
                'tests_passed': passed_tests,
                'tests_total': total_tests,
                'success_rate': passed_tests/total_tests*100 if total_tests > 0 else 0
            }
        }
        
        with open('system_test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Detailed report saved to system_test_report.json")
        
        # Final verdict
        all_passed = passed_components == total_components and passed_tests == total_tests
        
        if all_passed:
            print("\n🎉 ALL TESTS PASSED! System is ready for production.")
        else:
            print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Please review and fix issues.")
        
        return all_passed

def main():
    """Main function"""
    component = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    suite = SystemTestSuite()
    
    if component == "all":
        success = suite.run_all_tests()
    else:
        success = suite.run_component_test(component)
    
    if success:
        print(f"\n✅ System tests completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ System tests failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()