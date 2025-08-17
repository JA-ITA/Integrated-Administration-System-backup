#!/usr/bin/env python3
"""
Backend Testing Suite for ITADIAS Identity Microservice
Tests all REST API endpoints, database operations, and service integrations.
"""

import asyncio
import json
import uuid
import requests
import time
from datetime import datetime, date
from typing import Dict, Any, Optional
import os
import sys

# Test configuration
BACKEND_URL = "https://identity-service.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

class IdentityServiceTester:
    """Comprehensive tester for the Identity microservice."""
    
    def __init__(self):
        self.base_url = API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.created_candidates = []
        
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
    
    def generate_test_candidate_data(self, suffix: str = None) -> Dict[str, Any]:
        """Generate realistic test candidate data."""
        if suffix is None:
            suffix = str(int(time.time()))[-6:]
        
        return {
            "email": f"candidate.{suffix}@bermuda.bm",
            "first_name": "Maria",
            "last_name": "Santos",
            "phone": f"441555{suffix[-4:]}",
            "date_of_birth": "1995-03-15",
            "national_id": f"BM{suffix}789",
            "passport_number": f"P{suffix}456",
            "street_address": "45 Front Street",
            "city": "Hamilton",
            "postal_code": "HM11",
            "country": "Bermuda",
            "preferred_language": "en",
            "timezone": "Atlantic/Bermuda"
        }
    
    def test_health_check(self):
        """Test health check endpoints."""
        try:
            # Test main health endpoint
            response = self.session.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Health Check - Main",
                    True,
                    f"Service healthy: {data.get('status', 'unknown')}",
                    data
                )
            else:
                self.log_test(
                    "Health Check - Main",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
            
            # Test identity module health endpoint
            response = self.session.get(f"{self.base_url}/identity/v1/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Health Check - Identity Module",
                    True,
                    f"Identity module healthy: {data.get('status', 'unknown')}",
                    data
                )
            else:
                self.log_test(
                    "Health Check - Identity Module",
                    False,
                    f"Identity health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Health Check",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_candidate_success(self):
        """Test successful candidate creation."""
        try:
            candidate_data = self.generate_test_candidate_data()
            
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates",
                json=candidate_data,
                headers={"X-Correlation-ID": f"test-{uuid.uuid4()}"}
            )
            
            if response.status_code == 201:
                data = response.json()
                candidate_id = data.get('candidate', {}).get('id')
                
                if candidate_id:
                    self.created_candidates.append(candidate_id)
                
                # Validate response structure
                required_fields = ['candidate', 'otp_sent', 'message', 'next_steps']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    candidate = data['candidate']
                    otp_sent = data['otp_sent']
                    
                    self.log_test(
                        "Create Candidate - Success",
                        True,
                        f"Candidate created successfully: {candidate.get('email')}",
                        {
                            "candidate_id": candidate_id,
                            "email_otp_sent": otp_sent.get('email'),
                            "phone_otp_sent": otp_sent.get('phone'),
                            "status": candidate.get('status')
                        }
                    )
                    return candidate_id
                else:
                    self.log_test(
                        "Create Candidate - Success",
                        False,
                        f"Response missing required fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    "Create Candidate - Success",
                    False,
                    f"Expected 201, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Candidate - Success",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        return None
    
    def test_create_candidate_validation_errors(self):
        """Test candidate creation with various validation errors."""
        test_cases = [
            {
                "name": "Invalid Email",
                "data": {"email": "invalid-email", "first_name": "Test", "last_name": "User", "phone": "4415551234"},
                "expected_status": 422
            },
            {
                "name": "Missing Required Fields",
                "data": {"email": "test@example.com"},
                "expected_status": 422
            },
            {
                "name": "Invalid Phone Format",
                "data": {"email": "test@example.com", "first_name": "Test", "last_name": "User", "phone": "123"},
                "expected_status": 422
            },
            {
                "name": "Underage Candidate",
                "data": {
                    "email": "young@example.com",
                    "first_name": "Young",
                    "last_name": "Person",
                    "phone": "4415551234",
                    "date_of_birth": "2010-01-01"  # Too young
                },
                "expected_status": 422
            }
        ]
        
        for test_case in test_cases:
            try:
                response = self.session.post(
                    f"{self.base_url}/identity/v1/candidates",
                    json=test_case["data"]
                )
                
                success = response.status_code == test_case["expected_status"]
                self.log_test(
                    f"Create Candidate - {test_case['name']}",
                    success,
                    f"Expected {test_case['expected_status']}, got {response.status_code}",
                    {"response_data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}
                )
                
            except Exception as e:
                self.log_test(
                    f"Create Candidate - {test_case['name']}",
                    False,
                    f"Request error: {str(e)}",
                    {"error": str(e)}
                )
    
    def test_create_duplicate_candidate(self):
        """Test creating duplicate candidate."""
        try:
            # Create first candidate
            candidate_data = self.generate_test_candidate_data("duplicate")
            
            response1 = self.session.post(
                f"{self.base_url}/identity/v1/candidates",
                json=candidate_data
            )
            
            if response1.status_code == 201:
                candidate_id = response1.json().get('candidate', {}).get('id')
                if candidate_id:
                    self.created_candidates.append(candidate_id)
                
                # Try to create duplicate
                response2 = self.session.post(
                    f"{self.base_url}/identity/v1/candidates",
                    json=candidate_data
                )
                
                if response2.status_code == 400:
                    data = response2.json()
                    if "already exists" in data.get('detail', {}).get('message', '').lower():
                        self.log_test(
                            "Create Candidate - Duplicate Prevention",
                            True,
                            "Duplicate candidate properly rejected",
                            data
                        )
                    else:
                        self.log_test(
                            "Create Candidate - Duplicate Prevention",
                            False,
                            "Wrong error message for duplicate",
                            data
                        )
                else:
                    self.log_test(
                        "Create Candidate - Duplicate Prevention",
                        False,
                        f"Expected 400, got {response2.status_code}",
                        {"response": response2.text}
                    )
            else:
                self.log_test(
                    "Create Candidate - Duplicate Prevention",
                    False,
                    f"Failed to create first candidate: {response1.status_code}",
                    {"response": response1.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Candidate - Duplicate Prevention",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_candidate_success(self, candidate_id: str):
        """Test successful candidate retrieval."""
        if not candidate_id:
            self.log_test(
                "Get Candidate - Success",
                False,
                "No candidate ID provided",
                {}
            )
            return
        
        try:
            response = self.session.get(
                f"{self.base_url}/identity/v1/candidates/{candidate_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = ['id', 'email', 'first_name', 'last_name', 'status']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test(
                        "Get Candidate - Success",
                        True,
                        f"Candidate retrieved successfully: {data.get('email')}",
                        {
                            "candidate_id": data.get('id'),
                            "status": data.get('status'),
                            "is_email_verified": data.get('is_email_verified'),
                            "is_phone_verified": data.get('is_phone_verified')
                        }
                    )
                else:
                    self.log_test(
                        "Get Candidate - Success",
                        False,
                        f"Response missing required fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    "Get Candidate - Success",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Candidate - Success",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_candidate_not_found(self):
        """Test candidate retrieval with non-existent ID."""
        try:
            fake_id = str(uuid.uuid4())
            response = self.session.get(
                f"{self.base_url}/identity/v1/candidates/{fake_id}"
            )
            
            if response.status_code == 404:
                data = response.json()
                if data.get('detail', {}).get('error') == 'not_found':
                    self.log_test(
                        "Get Candidate - Not Found",
                        True,
                        "Non-existent candidate properly returns 404",
                        data
                    )
                else:
                    self.log_test(
                        "Get Candidate - Not Found",
                        False,
                        "Wrong error format for 404",
                        data
                    )
            else:
                self.log_test(
                    "Get Candidate - Not Found",
                    False,
                    f"Expected 404, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Candidate - Not Found",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_candidate_invalid_uuid(self):
        """Test candidate retrieval with invalid UUID format."""
        try:
            invalid_id = "not-a-valid-uuid"
            response = self.session.get(
                f"{self.base_url}/identity/v1/candidates/{invalid_id}"
            )
            
            # Should return 422 for invalid UUID format or 404
            if response.status_code in [422, 404, 400]:
                self.log_test(
                    "Get Candidate - Invalid UUID",
                    True,
                    f"Invalid UUID properly handled with status {response.status_code}",
                    {"response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}
                )
            else:
                self.log_test(
                    "Get Candidate - Invalid UUID",
                    False,
                    f"Expected 422/404/400, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Candidate - Invalid UUID",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_otp_verification_flow(self, candidate_id: str):
        """Test OTP verification functionality."""
        if not candidate_id:
            self.log_test(
                "OTP Verification Flow",
                False,
                "No candidate ID provided",
                {}
            )
            return
        
        # Test OTP status check
        try:
            response = self.session.get(
                f"{self.base_url}/identity/v1/candidates/{candidate_id}/otp-status"
            )
            
            if response.status_code == 200:
                status_data = response.json()
                self.log_test(
                    "OTP Status Check",
                    True,
                    f"OTP status retrieved successfully",
                    {
                        "email_otp_status": status_data.get('email_otp_status'),
                        "phone_otp_status": status_data.get('phone_otp_status'),
                        "can_set_password": status_data.get('can_set_password')
                    }
                )
            else:
                self.log_test(
                    "OTP Status Check",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "OTP Status Check",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test OTP verification with invalid code
        try:
            otp_data = {
                "candidate_id": candidate_id,
                "otp_type": "email",
                "otp_code": "000000"  # Invalid code
            }
            
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates/{candidate_id}/verify-otp",
                json=otp_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get('success', True):  # Should fail
                    self.log_test(
                        "OTP Verification - Invalid Code",
                        True,
                        f"Invalid OTP properly rejected: {data.get('message')}",
                        data
                    )
                else:
                    self.log_test(
                        "OTP Verification - Invalid Code",
                        False,
                        "Invalid OTP was accepted (should fail)",
                        data
                    )
            else:
                self.log_test(
                    "OTP Verification - Invalid Code",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "OTP Verification - Invalid Code",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test OTP resend
        try:
            resend_data = {
                "candidate_id": candidate_id,
                "otp_type": "email"
            }
            
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates/{candidate_id}/resend-otp",
                json=resend_data
            )
            
            if response.status_code in [200, 400]:  # 400 might be cooldown
                data = response.json()
                if response.status_code == 200:
                    self.log_test(
                        "OTP Resend",
                        True,
                        f"OTP resend successful: {data.get('message')}",
                        data
                    )
                else:  # 400 - might be cooldown
                    if "wait" in data.get('detail', {}).get('message', '').lower():
                        self.log_test(
                            "OTP Resend - Cooldown",
                            True,
                            f"OTP resend cooldown properly enforced: {data.get('detail', {}).get('message')}",
                            data
                        )
                    else:
                        self.log_test(
                            "OTP Resend",
                            False,
                            f"Unexpected error: {data}",
                            data
                        )
            else:
                self.log_test(
                    "OTP Resend",
                    False,
                    f"Expected 200/400, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "OTP Resend",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_password_setting_flow(self, candidate_id: str):
        """Test password setting functionality."""
        if not candidate_id:
            self.log_test(
                "Password Setting Flow",
                False,
                "No candidate ID provided",
                {}
            )
            return
        
        # Test password setting with weak password
        try:
            weak_password_data = {
                "candidate_id": candidate_id,
                "password": "weak",
                "confirm_password": "weak"
            }
            
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates/{candidate_id}/set-password",
                json=weak_password_data
            )
            
            if response.status_code == 422:
                self.log_test(
                    "Password Setting - Weak Password",
                    True,
                    "Weak password properly rejected",
                    {"response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}
                )
            else:
                self.log_test(
                    "Password Setting - Weak Password",
                    False,
                    f"Expected 422, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Password Setting - Weak Password",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test password setting with mismatched passwords
        try:
            mismatch_data = {
                "candidate_id": candidate_id,
                "password": "StrongPass123!",
                "confirm_password": "DifferentPass123!"
            }
            
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates/{candidate_id}/set-password",
                json=mismatch_data
            )
            
            if response.status_code == 422:
                self.log_test(
                    "Password Setting - Mismatch",
                    True,
                    "Password mismatch properly rejected",
                    {"response": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}
                )
            else:
                self.log_test(
                    "Password Setting - Mismatch",
                    False,
                    f"Expected 422, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Password Setting - Mismatch",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test password setting without verification (should fail)
        try:
            valid_password_data = {
                "candidate_id": candidate_id,
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!"
            }
            
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates/{candidate_id}/set-password",
                json=valid_password_data
            )
            
            # Should fail because candidate is not verified
            if response.status_code == 400:
                data = response.json()
                if "verification" in data.get('detail', {}).get('message', '').lower():
                    self.log_test(
                        "Password Setting - Unverified Candidate",
                        True,
                        f"Unverified candidate properly rejected: {data.get('detail', {}).get('message')}",
                        data
                    )
                else:
                    self.log_test(
                        "Password Setting - Unverified Candidate",
                        False,
                        f"Wrong error message: {data}",
                        data
                    )
            else:
                self.log_test(
                    "Password Setting - Unverified Candidate",
                    False,
                    f"Expected 400, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Password Setting - Unverified Candidate",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_error_handling(self):
        """Test various error handling scenarios."""
        # Test with malformed JSON
        try:
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates",
                data="invalid json",
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 422:
                self.log_test(
                    "Error Handling - Malformed JSON",
                    True,
                    "Malformed JSON properly rejected",
                    {"status": response.status_code}
                )
            else:
                self.log_test(
                    "Error Handling - Malformed JSON",
                    False,
                    f"Expected 422, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Error Handling - Malformed JSON",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test with missing Content-Type
        try:
            candidate_data = self.generate_test_candidate_data("error_test")
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates",
                json=candidate_data,
                headers={'Content-Type': 'text/plain'}  # Wrong content type
            )
            
            # Should handle gracefully
            if response.status_code in [400, 422, 415]:
                self.log_test(
                    "Error Handling - Wrong Content Type",
                    True,
                    f"Wrong content type handled with status {response.status_code}",
                    {"status": response.status_code}
                )
            else:
                self.log_test(
                    "Error Handling - Wrong Content Type",
                    False,
                    f"Unexpected status {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Error Handling - Wrong Content Type",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_correlation_id_handling(self):
        """Test correlation ID handling."""
        try:
            candidate_data = self.generate_test_candidate_data("correlation")
            correlation_id = f"test-correlation-{uuid.uuid4()}"
            
            response = self.session.post(
                f"{self.base_url}/identity/v1/candidates",
                json=candidate_data,
                headers={"X-Correlation-ID": correlation_id}
            )
            
            if response.status_code == 201:
                candidate_id = response.json().get('candidate', {}).get('id')
                if candidate_id:
                    self.created_candidates.append(candidate_id)
                
                self.log_test(
                    "Correlation ID Handling",
                    True,
                    f"Request with correlation ID processed successfully",
                    {"correlation_id": correlation_id, "candidate_id": candidate_id}
                )
            else:
                self.log_test(
                    "Correlation ID Handling",
                    False,
                    f"Expected 201, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Correlation ID Handling",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting ITADIAS Identity Microservice Backend Tests")
        print(f"🌐 Testing against: {BACKEND_URL}")
        print("=" * 80)
        
        # Health checks first
        self.test_health_check()
        
        # Create a candidate for subsequent tests
        candidate_id = self.test_create_candidate_success()
        
        # Validation tests
        self.test_create_candidate_validation_errors()
        self.test_create_duplicate_candidate()
        
        # Candidate retrieval tests
        self.test_get_candidate_success(candidate_id)
        self.test_get_candidate_not_found()
        self.test_get_candidate_invalid_uuid()
        
        # OTP and verification tests
        self.test_otp_verification_flow(candidate_id)
        
        # Password setting tests
        self.test_password_setting_flow(candidate_id)
        
        # Error handling tests
        self.test_error_handling()
        
        # Correlation ID tests
        self.test_correlation_id_handling()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print(f"\n📝 Created {len(self.created_candidates)} test candidates during testing")
        
        # Save detailed results to file
        with open('/app/backend_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'backend_url': BACKEND_URL
                },
                'test_results': self.test_results,
                'created_candidates': self.created_candidates
            }, indent=2)
        
        print(f"📄 Detailed results saved to: /app/backend_test_results.json")


def main():
    """Main test execution function."""
    tester = IdentityServiceTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()