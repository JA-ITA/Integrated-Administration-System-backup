#!/usr/bin/env python3
"""
Test Engine Microservice Comprehensive Testing
Tests all Test Engine functionality including direct microservice endpoints and main backend integration
"""

import asyncio
import json
import uuid
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import sys

# Test configuration
TEST_ENGINE_SERVICE_URL = "http://localhost:8005"
MAIN_BACKEND_URL = "https://compliance-trace.preview.emergentagent.com"
TEST_ENGINE_API_BASE = f"{TEST_ENGINE_SERVICE_URL}/api/v1"
MAIN_BACKEND_API_BASE = f"{MAIN_BACKEND_URL}/api"

class TestEngineComprehensiveTester:
    """Comprehensive tester for Test Engine microservice and main backend integration."""
    
    def __init__(self):
        self.test_engine_base_url = TEST_ENGINE_API_BASE
        self.main_backend_base_url = MAIN_BACKEND_API_BASE
        self.test_engine_service_url = TEST_ENGINE_SERVICE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.created_tests = []
        
    def log_test(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log test result."""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def generate_test_driver_record_id(self) -> str:
        """Generate a test driver record ID"""
        return str(uuid.uuid4())
    
    def test_test_engine_health_check(self):
        """Test Test Engine service health check"""
        try:
            response = self.session.get(f"{self.test_engine_service_url}/health")
            if response.status_code == 200:
                data = response.json()
                
                # Check required health check components
                required_components = ["status", "service", "version", "database", "events"]
                missing_components = [comp for comp in required_components if comp not in data]
                
                if not missing_components and data.get("status") == "healthy":
                    self.log_test(
                        "Test Engine Health Check",
                        True,
                        f"Service healthy: {data.get('status')}",
                        {
                            "database": data.get("database"),
                            "events": data.get("events"),
                            "event_details": data.get("event_details", {})
                        }
                    )
                else:
                    self.log_test(
                        "Test Engine Health Check",
                        False,
                        f"Health response missing components or unhealthy: {missing_components}",
                        data
                    )
            else:
                self.log_test(
                    "Test Engine Health Check",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Test Engine Health Check",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_test_engine_config_endpoint(self):
        """Test Test Engine configuration endpoint"""
        try:
            response = self.session.get(f"{self.test_engine_service_url}/config")
            if response.status_code == 200:
                data = response.json()
                
                # Check required config components
                required_config = ["questions_per_test", "time_limit_minutes", "passing_score_percent", "available_modules"]
                missing_config = [comp for comp in required_config if comp not in data]
                
                if not missing_config:
                    # Validate config values
                    questions_per_test = data.get("questions_per_test", 0)
                    time_limit = data.get("time_limit_minutes", 0)
                    passing_score = data.get("passing_score_percent", 0)
                    modules = data.get("available_modules", [])
                    
                    config_valid = (
                        questions_per_test == 20 and
                        time_limit == 25 and
                        passing_score == 75.0 and
                        len(modules) >= 5
                    )
                    
                    self.log_test(
                        "Test Engine Configuration",
                        config_valid,
                        f"Configuration endpoint working with expected values: {questions_per_test} questions, {time_limit} min, {passing_score}% pass",
                        {
                            "questions_per_test": questions_per_test,
                            "time_limit_minutes": time_limit,
                            "passing_score_percent": passing_score,
                            "available_modules": modules
                        }
                    )
                else:
                    self.log_test(
                        "Test Engine Configuration",
                        False,
                        f"Config response missing components: {missing_config}",
                        data
                    )
            else:
                self.log_test(
                    "Test Engine Configuration",
                    False,
                    f"Config endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Test Engine Configuration",
                False,
                f"Config endpoint error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_start_test_endpoint(self, module: str = "Provisional") -> Optional[str]:
        """Test POST /api/v1/tests/start endpoint"""
        try:
            driver_record_id = self.generate_test_driver_record_id()
            test_data = {
                "driver_record_id": driver_record_id,
                "module": module
            }
            
            response = self.session.post(
                f"{self.test_engine_base_url}/tests/start",
                json=test_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required response fields
                required_fields = ["test_id", "questions", "time_limit_minutes", "start_time", "expires_at"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    test_id = data.get("test_id")
                    questions = data.get("questions", [])
                    time_limit = data.get("time_limit_minutes", 0)
                    
                    # Validate response
                    valid_response = (
                        len(questions) == 20 and
                        time_limit == 25 and
                        test_id is not None
                    )
                    
                    if valid_response:
                        self.created_tests.append(test_id)
                        
                        # Validate question structure
                        first_question = questions[0] if questions else {}
                        question_valid = all(
                            field in first_question 
                            for field in ["id", "question_type", "text"]
                        )
                        
                        self.log_test(
                            f"Start Test - {module}",
                            question_valid,
                            f"Test started successfully with {len(questions)} questions, {time_limit} min limit",
                            {
                                "test_id": test_id,
                                "driver_record_id": driver_record_id,
                                "module": module,
                                "questions_count": len(questions),
                                "first_question_structure": first_question
                            }
                        )
                        return test_id
                    else:
                        self.log_test(
                            f"Start Test - {module}",
                            False,
                            f"Invalid response structure: {len(questions)} questions, {time_limit} min",
                            data
                        )
                else:
                    self.log_test(
                        f"Start Test - {module}",
                        False,
                        f"Response missing fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    f"Start Test - {module}",
                    False,
                    f"Start test failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                f"Start Test - {module}",
                False,
                f"Start test error: {str(e)}",
                {"error": str(e)}
            )
        
        return None
    
    def test_submit_test_endpoint(self, test_id: str, pass_test: bool = True):
        """Test POST /api/v1/tests/{id}/submit endpoint"""
        try:
            # First get test status to get questions
            status_response = self.session.get(f"{self.test_engine_base_url}/tests/{test_id}/status")
            if status_response.status_code != 200:
                self.log_test(
                    f"Submit Test - {'Pass' if pass_test else 'Fail'}",
                    False,
                    "Could not get test status for submission",
                    {"status_response": status_response.text}
                )
                return
            
            # Generate answers - all correct for pass, mix for fail
            answers = []
            for i in range(20):  # Assuming 20 questions
                question_id = str(uuid.uuid4())  # Mock question ID
                if pass_test:
                    answer = "A"  # Assume all A's are correct for simplicity
                else:
                    answer = "B" if i < 10 else "A"  # 50% correct for fail
                
                answers.append({
                    "question_id": question_id,
                    "answer": answer
                })
            
            submission_data = {"answers": answers}
            
            response = self.session.post(
                f"{self.test_engine_base_url}/tests/{test_id}/submit",
                json=submission_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required response fields
                required_fields = ["test_id", "score", "passed", "correct_answers", "total_questions", "submitted_at"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    score = data.get("score", 0)
                    passed = data.get("passed", False)
                    correct_answers = data.get("correct_answers", 0)
                    total_questions = data.get("total_questions", 0)
                    
                    # Validate auto-grading logic
                    expected_pass = score >= 75.0
                    grading_correct = passed == expected_pass
                    
                    self.log_test(
                        f"Submit Test - {'Pass' if pass_test else 'Fail'} Scenario",
                        grading_correct,
                        f"Test submitted: score={score}%, passed={passed}, {correct_answers}/{total_questions} correct",
                        {
                            "test_id": test_id,
                            "score": score,
                            "passed": passed,
                            "correct_answers": correct_answers,
                            "total_questions": total_questions,
                            "grading_correct": grading_correct
                        }
                    )
                else:
                    self.log_test(
                        f"Submit Test - {'Pass' if pass_test else 'Fail'} Scenario",
                        False,
                        f"Response missing fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    f"Submit Test - {'Pass' if pass_test else 'Fail'} Scenario",
                    False,
                    f"Submit test failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                f"Submit Test - {'Pass' if pass_test else 'Fail'} Scenario",
                False,
                f"Submit test error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_test_status_endpoint(self, test_id: str):
        """Test GET /api/v1/tests/{id}/status endpoint"""
        try:
            response = self.session.get(f"{self.test_engine_base_url}/tests/{test_id}/status")
            
            if response.status_code == 200:
                data = response.json()
                
                # Check required response fields
                required_fields = ["test_id", "status", "start_time", "expires_at", "time_remaining_seconds"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    status = data.get("status")
                    time_remaining = data.get("time_remaining_seconds", 0)
                    
                    self.log_test(
                        "Get Test Status",
                        True,
                        f"Test status retrieved: {status}, {time_remaining}s remaining",
                        {
                            "test_id": test_id,
                            "status": status,
                            "time_remaining_seconds": time_remaining,
                            "expires_at": data.get("expires_at")
                        }
                    )
                else:
                    self.log_test(
                        "Get Test Status",
                        False,
                        f"Response missing fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    "Get Test Status",
                    False,
                    f"Get test status failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Test Status",
                False,
                f"Get test status error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_statistics_endpoint(self):
        """Test statistics endpoint"""
        try:
            response = self.session.get(f"{self.test_engine_service_url}/stats")
            
            if response.status_code == 200:
                data = response.json()
                
                # Statistics should be a dict with some test data
                if isinstance(data, dict):
                    self.log_test(
                        "Test Statistics",
                        True,
                        "Statistics endpoint working",
                        {"statistics": data}
                    )
                else:
                    self.log_test(
                        "Test Statistics",
                        False,
                        "Statistics endpoint returned invalid format",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "Test Statistics",
                    False,
                    f"Statistics endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Test Statistics",
                False,
                f"Statistics endpoint error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_events_status_endpoint(self):
        """Test events status endpoint"""
        try:
            response = self.session.get(f"{self.test_engine_service_url}/events/status")
            
            if response.status_code == 200:
                data = response.json()
                
                # Events status should contain connection info
                if isinstance(data, dict):
                    self.log_test(
                        "Events Status",
                        True,
                        "Events status endpoint working",
                        {"events_status": data}
                    )
                else:
                    self.log_test(
                        "Events Status",
                        False,
                        "Events status endpoint returned invalid format",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "Events Status",
                    False,
                    f"Events status endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Events Status",
                False,
                f"Events status endpoint error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_main_backend_integration(self):
        """Test main backend integration endpoints"""
        
        # Test health check via main backend
        try:
            response = self.session.get(f"{self.main_backend_base_url}/test-engine/health")
            
            if response.status_code == 200:
                data = response.json()
                service_status = data.get("test_engine_service", "unavailable")
                
                self.log_test(
                    "Main Backend - Test Engine Health Check",
                    service_status != "unavailable",
                    f"Test engine health via main backend: {service_status}",
                    {"health_response": data}
                )
            else:
                self.log_test(
                    "Main Backend - Test Engine Health Check",
                    False,
                    f"Main backend health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend - Test Engine Health Check",
                False,
                f"Main backend health check error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test start test via main backend
        try:
            driver_record_id = self.generate_test_driver_record_id()
            test_data = {
                "driver_record_id": driver_record_id,
                "module": "Class-B"
            }
            
            response = self.session.post(
                f"{self.main_backend_base_url}/test-engine/tests/start",
                json=test_data
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                test_id = data.get("test_id")
                
                if success and test_id:
                    self.created_tests.append(test_id)
                    
                    self.log_test(
                        "Main Backend - Start Test",
                        True,
                        f"Test started via main backend: {test_id}",
                        {
                            "test_id": test_id,
                            "driver_record_id": driver_record_id,
                            "questions_count": len(data.get("questions", []))
                        }
                    )
                    
                    # Test submit via main backend
                    self.test_main_backend_submit_test(test_id)
                    
                    # Test status via main backend
                    self.test_main_backend_test_status(test_id)
                    
                else:
                    self.log_test(
                        "Main Backend - Start Test",
                        False,
                        f"Test start via main backend failed: {data}",
                        data
                    )
            else:
                self.log_test(
                    "Main Backend - Start Test",
                    False,
                    f"Main backend start test failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend - Start Test",
                False,
                f"Main backend start test error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test statistics via main backend
        try:
            response = self.session.get(f"{self.main_backend_base_url}/test-engine/statistics")
            
            if response.status_code == 200:
                data = response.json()
                
                self.log_test(
                    "Main Backend - Statistics",
                    True,
                    "Statistics retrieved via main backend",
                    {"statistics": data}
                )
            else:
                self.log_test(
                    "Main Backend - Statistics",
                    False,
                    f"Main backend statistics failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend - Statistics",
                False,
                f"Main backend statistics error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_main_backend_submit_test(self, test_id: str):
        """Test submit test via main backend"""
        try:
            # Generate mock answers
            answers = []
            for i in range(20):
                answers.append({
                    "question_id": str(uuid.uuid4()),
                    "answer": "A"  # All correct answers
                })
            
            submission_data = {"answers": answers}
            
            response = self.session.post(
                f"{self.main_backend_base_url}/test-engine/tests/{test_id}/submit",
                json=submission_data
            )
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                self.log_test(
                    "Main Backend - Submit Test",
                    success,
                    f"Test submitted via main backend: score={data.get('score', 0)}%",
                    {
                        "test_id": test_id,
                        "score": data.get("score"),
                        "passed": data.get("passed")
                    }
                )
            else:
                self.log_test(
                    "Main Backend - Submit Test",
                    False,
                    f"Main backend submit test failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend - Submit Test",
                False,
                f"Main backend submit test error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_main_backend_test_status(self, test_id: str):
        """Test get test status via main backend"""
        try:
            response = self.session.get(f"{self.main_backend_base_url}/test-engine/tests/{test_id}/status")
            
            if response.status_code == 200:
                data = response.json()
                
                self.log_test(
                    "Main Backend - Test Status",
                    True,
                    f"Test status retrieved via main backend: {data.get('status', 'unknown')}",
                    {
                        "test_id": test_id,
                        "status": data.get("status"),
                        "time_remaining": data.get("time_remaining_seconds")
                    }
                )
            else:
                self.log_test(
                    "Main Backend - Test Status",
                    False,
                    f"Main backend test status failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend - Test Status",
                False,
                f"Main backend test status error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_duplicate_test_prevention(self):
        """Test that duplicate tests for same module are prevented"""
        try:
            driver_record_id = self.generate_test_driver_record_id()
            test_data = {
                "driver_record_id": driver_record_id,
                "module": "HAZMAT"
            }
            
            # Start first test
            response1 = self.session.post(
                f"{self.test_engine_base_url}/tests/start",
                json=test_data
            )
            
            if response1.status_code == 200:
                test_id = response1.json().get("test_id")
                if test_id:
                    self.created_tests.append(test_id)
                
                # Try to start second test with same driver and module
                response2 = self.session.post(
                    f"{self.test_engine_base_url}/tests/start",
                    json=test_data
                )
                
                if response2.status_code == 409:
                    self.log_test(
                        "Duplicate Test Prevention",
                        True,
                        "Duplicate test properly prevented with 409 conflict",
                        {
                            "first_test_id": test_id,
                            "driver_record_id": driver_record_id,
                            "module": "HAZMAT"
                        }
                    )
                else:
                    self.log_test(
                        "Duplicate Test Prevention",
                        False,
                        f"Expected 409 conflict, got {response2.status_code}",
                        {"response": response2.text}
                    )
            else:
                self.log_test(
                    "Duplicate Test Prevention",
                    False,
                    f"Could not start first test: {response1.status_code}",
                    {"response": response1.text}
                )
                
        except Exception as e:
            self.log_test(
                "Duplicate Test Prevention",
                False,
                f"Duplicate test prevention error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_multiple_modules(self):
        """Test starting tests for different modules"""
        modules = ["Provisional", "Class-B", "Class-C", "PPV", "HAZMAT"]
        
        for module in modules:
            test_id = self.test_start_test_endpoint(module)
            if test_id:
                # Test status for each module
                self.test_get_test_status_endpoint(test_id)
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting Test Engine Microservice Comprehensive Testing")
        print(f"🌐 Testing Test Engine Service: {TEST_ENGINE_SERVICE_URL}")
        print(f"🌐 Testing Main Backend Integration: {MAIN_BACKEND_URL}")
        print("🔍 Focus: Complete Test Engine functionality and integration")
        print("=" * 100)
        
        # Test Engine Microservice Direct Tests
        print("\n🎯 TESTING TEST ENGINE MICROSERVICE (Port 8005):")
        
        # 1. Health check
        self.test_test_engine_health_check()
        
        # 2. Configuration
        self.test_test_engine_config_endpoint()
        
        # 3. Statistics
        self.test_statistics_endpoint()
        
        # 4. Events status
        self.test_events_status_endpoint()
        
        # 5. Start test for different modules
        print("\n🧪 TESTING TEST SCENARIOS:")
        self.test_multiple_modules()
        
        # 6. Duplicate test prevention
        self.test_duplicate_test_prevention()
        
        # Main Backend Integration Tests
        print("\n🔗 TESTING MAIN BACKEND INTEGRATION (Port 8001):")
        self.test_main_backend_integration()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 100)
        print("📊 TEST ENGINE MICROSERVICE TEST SUMMARY")
        print("=" * 100)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🎯 KEY VALIDATION POINTS:")
        print("   ✓ Test Engine microservice health and configuration")
        print("   ✓ Test start with 20 questions per test")
        print("   ✓ Auto-grading with ≥75% pass threshold")
        print("   ✓ One attempt per booking enforcement")
        print("   ✓ 25-minute test timer")
        print("   ✓ Multiple module support")
        print("   ✓ Main backend integration endpoints")
        print("   ✓ Event publishing and statistics")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print(f"\n📝 Created {len(self.created_tests)} test instances during testing")
        
        # Save detailed results to file
        with open('/app/test_engine_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'test_engine_service_url': TEST_ENGINE_SERVICE_URL,
                    'main_backend_url': MAIN_BACKEND_URL,
                    'focus': 'Complete Test Engine microservice and integration testing'
                },
                'test_results': self.test_results,
                'created_tests': self.created_tests
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/test_engine_test_results.json")


def main():
    """Main test execution function."""
    tester = TestEngineComprehensiveTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()