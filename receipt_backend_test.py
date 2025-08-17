#!/usr/bin/env python3
"""
Receipt Microservice Backend Testing Suite
Tests all receipt validation endpoints, business rules, and service integrations.
"""

import asyncio
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os
import sys

# Test configuration - Use environment URLs
FRONTEND_ENV_PATH = "/app/frontend/.env"
BACKEND_ENV_PATH = "/app/backend/.env"

def get_backend_url():
    """Get backend URL from frontend .env file"""
    try:
        with open(FRONTEND_ENV_PATH, 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"Warning: Could not read frontend .env: {e}")
    return "http://localhost:8001"

# URLs for testing
MAIN_BACKEND_URL = get_backend_url()
RECEIPT_SERVICE_URL = "http://localhost:8003"
MAIN_API_BASE = f"{MAIN_BACKEND_URL}/api"
RECEIPT_API_BASE = f"{RECEIPT_SERVICE_URL}/api/v1"

class ReceiptServiceTester:
    """Comprehensive tester for the Receipt microservice."""
    
    def __init__(self):
        self.main_backend_url = MAIN_BACKEND_URL
        self.receipt_service_url = RECEIPT_SERVICE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.validated_receipts = []
        
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
    
    def test_receipt_service_health(self):
        """Test receipt service health endpoint."""
        try:
            response = self.session.get(f"{RECEIPT_SERVICE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Receipt Service Health Check",
                    True,
                    f"Service healthy: {data.get('status', 'unknown')}",
                    data
                )
            else:
                self.log_test(
                    "Receipt Service Health Check",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Receipt Service Health Check",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_main_backend_receipt_integration_health(self):
        """Test main backend receipt integration health."""
        try:
            response = self.session.get(f"{MAIN_API_BASE}/receipts/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Main Backend Receipt Integration Health",
                    True,
                    f"Integration healthy: {data.get('receipt_service', 'unknown')}",
                    data
                )
            else:
                self.log_test(
                    "Main Backend Receipt Integration Health",
                    False,
                    f"Integration health check failed with status {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Main Backend Receipt Integration Health",
                False,
                f"Integration health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_valid_receipt_validation(self):
        """Test valid receipt validation cases."""
        valid_test_cases = [
            {
                "name": "Valid Receipt - TAJ Online",
                "data": {
                    "receipt_no": "ABC123DEF890",
                    "issue_date": "2024-12-01T10:00:00Z",
                    "location": "TAJ Online",
                    "amount": 150.00
                },
                "expected_status": 200
            },
            {
                "name": "Valid Receipt - TAJ Mumbai Office",
                "data": {
                    "receipt_no": "XYZ98765432",
                    "issue_date": "2024-11-15T14:30:00Z",
                    "location": "TAJ Mumbai Office",
                    "amount": 299.50
                },
                "expected_status": 200
            },
            {
                "name": "Valid Receipt - Recent Date",
                "data": {
                    "receipt_no": "RECENT123456",
                    "issue_date": (datetime.now() - timedelta(days=30)).isoformat() + "Z",
                    "location": "TAJ Online",
                    "amount": 75.25
                },
                "expected_status": 200
            }
        ]
        
        for test_case in valid_test_cases:
            try:
                response = self.session.post(
                    f"{RECEIPT_API_BASE}/receipts/validate",
                    json=test_case["data"]
                )
                
                success = response.status_code == test_case["expected_status"]
                if success and response.status_code == 200:
                    data = response.json()
                    if data.get('success') == True:
                        self.validated_receipts.append(test_case["data"]["receipt_no"])
                        self.log_test(
                            f"Valid Receipt Validation - {test_case['name']}",
                            True,
                            f"Receipt validated successfully: {data.get('message', 'No message')}",
                            {"receipt_no": data.get('receipt_no'), "success": data.get('success')}
                        )
                    else:
                        self.log_test(
                            f"Valid Receipt Validation - {test_case['name']}",
                            False,
                            f"Receipt validation returned success=false: {data.get('message', 'No message')}",
                            data
                        )
                else:
                    self.log_test(
                        f"Valid Receipt Validation - {test_case['name']}",
                        False,
                        f"Expected {test_case['expected_status']}, got {response.status_code}",
                        {"response": response.text}
                    )
                    
            except Exception as e:
                self.log_test(
                    f"Valid Receipt Validation - {test_case['name']}",
                    False,
                    f"Request error: {str(e)}",
                    {"error": str(e)}
                )
    
    def test_invalid_receipt_validation(self):
        """Test invalid receipt validation cases."""
        invalid_test_cases = [
            {
                "name": "Invalid Receipt Number Format",
                "data": {
                    "receipt_no": "abc123",  # Too short and lowercase
                    "issue_date": "2024-12-01T10:00:00Z",
                    "location": "TAJ Online",
                    "amount": 150.00
                },
                "expected_status": 400
            },
            {
                "name": "Receipt Number Too Short",
                "data": {
                    "receipt_no": "ABC123",  # Only 6 characters, need 8-20
                    "issue_date": "2024-12-01T10:00:00Z",
                    "location": "TAJ Online",
                    "amount": 150.00
                },
                "expected_status": 400
            },
            {
                "name": "Invalid Location",
                "data": {
                    "receipt_no": "ABC123DEF890",
                    "issue_date": "2024-12-01T10:00:00Z",
                    "location": "Invalid Office",  # Not a valid TAJ location
                    "amount": 150.00
                },
                "expected_status": 400
            },
            {
                "name": "Old Receipt Date",
                "data": {
                    "receipt_no": "OLD123456789",
                    "issue_date": "2023-01-01T00:00:00Z",  # Too old (over 365 days)
                    "location": "TAJ Online",
                    "amount": 150.00
                },
                "expected_status": 400
            }
        ]
        
        for test_case in invalid_test_cases:
            try:
                response = self.session.post(
                    f"{RECEIPT_API_BASE}/receipts/validate",
                    json=test_case["data"]
                )
                
                success = response.status_code == test_case["expected_status"]
                self.log_test(
                    f"Invalid Receipt Validation - {test_case['name']}",
                    success,
                    f"Expected {test_case['expected_status']}, got {response.status_code}",
                    {"response_data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}
                )
                    
            except Exception as e:
                self.log_test(
                    f"Invalid Receipt Validation - {test_case['name']}",
                    False,
                    f"Request error: {str(e)}",
                    {"error": str(e)}
                )
    
    def test_duplicate_receipt_validation(self):
        """Test duplicate receipt validation."""
        try:
            # First validation should succeed
            duplicate_receipt_data = {
                "receipt_no": "DUPLICATE123",
                "issue_date": "2024-12-01T10:00:00Z",
                "location": "TAJ Online",
                "amount": 100.00
            }
            
            response1 = self.session.post(
                f"{RECEIPT_API_BASE}/receipts/validate",
                json=duplicate_receipt_data
            )
            
            if response1.status_code == 200:
                data1 = response1.json()
                if data1.get('success') == True:
                    self.validated_receipts.append(duplicate_receipt_data["receipt_no"])
                    
                    # Second validation should return 409 Duplicate
                    response2 = self.session.post(
                        f"{RECEIPT_API_BASE}/receipts/validate",
                        json=duplicate_receipt_data
                    )
                    
                    if response2.status_code == 409:
                        data2 = response2.json()
                        if data2.get('success') == False:
                            self.log_test(
                                "Duplicate Receipt Validation",
                                True,
                                f"Duplicate receipt properly rejected: {data2.get('message', 'No message')}",
                                {"first_response": data1, "duplicate_response": data2}
                            )
                        else:
                            self.log_test(
                                "Duplicate Receipt Validation",
                                False,
                                "Duplicate receipt returned success=true (should be false)",
                                data2
                            )
                    else:
                        self.log_test(
                            "Duplicate Receipt Validation",
                            False,
                            f"Expected 409 for duplicate, got {response2.status_code}",
                            {"response": response2.text}
                        )
                else:
                    self.log_test(
                        "Duplicate Receipt Validation",
                        False,
                        f"First receipt validation failed: {data1.get('message', 'No message')}",
                        data1
                    )
            else:
                self.log_test(
                    "Duplicate Receipt Validation",
                    False,
                    f"First receipt validation failed with status {response1.status_code}",
                    {"response": response1.text}
                )
                
        except Exception as e:
            self.log_test(
                "Duplicate Receipt Validation",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_main_backend_receipt_validation(self):
        """Test receipt validation through main backend."""
        try:
            receipt_data = {
                "receipt_no": "BACKEND123456",
                "issue_date": "2024-12-01T10:00:00Z",
                "location": "TAJ Online",
                "amount": 200.00
            }
            
            response = self.session.post(
                f"{MAIN_API_BASE}/receipts/validate",
                json=receipt_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') == True:
                    self.validated_receipts.append(receipt_data["receipt_no"])
                    self.log_test(
                        "Main Backend Receipt Validation",
                        True,
                        f"Receipt validated via main backend: {data.get('message', 'No message')}",
                        {"receipt_no": data.get('receipt_no'), "http_status": data.get('http_status')}
                    )
                else:
                    self.log_test(
                        "Main Backend Receipt Validation",
                        False,
                        f"Main backend validation returned success=false: {data.get('message', 'No message')}",
                        data
                    )
            else:
                self.log_test(
                    "Main Backend Receipt Validation",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend Receipt Validation",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_receipt_details(self):
        """Test getting receipt details."""
        if not self.validated_receipts:
            self.log_test(
                "Get Receipt Details",
                False,
                "No validated receipts available for testing",
                {}
            )
            return
        
        try:
            receipt_no = self.validated_receipts[0]
            
            # Test via main backend
            response = self.session.get(f"{MAIN_API_BASE}/receipts/{receipt_no}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('found') == True:
                    self.log_test(
                        "Get Receipt Details - Main Backend",
                        True,
                        f"Receipt details retrieved successfully: {receipt_no}",
                        {"receipt": data.get('receipt')}
                    )
                else:
                    self.log_test(
                        "Get Receipt Details - Main Backend",
                        False,
                        f"Receipt not found: {receipt_no}",
                        data
                    )
            else:
                self.log_test(
                    "Get Receipt Details - Main Backend",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Receipt Details - Main Backend",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test direct service call
        try:
            receipt_no = self.validated_receipts[0]
            response = self.session.get(f"{RECEIPT_API_BASE}/receipts/{receipt_no}")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Get Receipt Details - Direct Service",
                    True,
                    f"Receipt details retrieved from service: {receipt_no}",
                    {"receipt_data": data}
                )
            else:
                self.log_test(
                    "Get Receipt Details - Direct Service",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Receipt Details - Direct Service",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_receipt_statistics(self):
        """Test receipt statistics endpoint."""
        try:
            # Test via main backend
            response = self.session.get(f"{MAIN_API_BASE}/receipts/statistics")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Receipt Statistics - Main Backend",
                    True,
                    f"Statistics retrieved successfully",
                    {"statistics": data}
                )
            else:
                self.log_test(
                    "Receipt Statistics - Main Backend",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Receipt Statistics - Main Backend",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test direct service call
        try:
            response = self.session.get(f"{RECEIPT_API_BASE}/receipts")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Receipt Statistics - Direct Service",
                    True,
                    f"Statistics retrieved from service: {data.get('status', 'unknown')}",
                    {"statistics": data.get('statistics', {})}
                )
            else:
                self.log_test(
                    "Receipt Statistics - Direct Service",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Receipt Statistics - Direct Service",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_error_handling(self):
        """Test various error handling scenarios."""
        # Test with malformed JSON
        try:
            response = self.session.post(
                f"{RECEIPT_API_BASE}/receipts/validate",
                data="invalid json",
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code in [400, 422]:
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
                    f"Expected 400/422, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Error Handling - Malformed JSON",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test with missing required fields
        try:
            incomplete_data = {
                "receipt_no": "INCOMPLETE123"
                # Missing issue_date, location, amount
            }
            
            response = self.session.post(
                f"{RECEIPT_API_BASE}/receipts/validate",
                json=incomplete_data
            )
            
            if response.status_code == 422:
                self.log_test(
                    "Error Handling - Missing Fields",
                    True,
                    "Missing required fields properly rejected",
                    {"status": response.status_code}
                )
            else:
                self.log_test(
                    "Error Handling - Missing Fields",
                    False,
                    f"Expected 422, got {response.status_code}",
                    {"response": response.text}
                )
        except Exception as e:
            self.log_test(
                "Error Handling - Missing Fields",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting Receipt Microservice Backend Tests")
        print(f"🌐 Main Backend: {MAIN_BACKEND_URL}")
        print(f"🌐 Receipt Service: {RECEIPT_SERVICE_URL}")
        print("=" * 80)
        
        # Health checks first
        self.test_receipt_service_health()
        self.test_main_backend_receipt_integration_health()
        
        # Valid receipt validation tests
        self.test_valid_receipt_validation()
        
        # Invalid receipt validation tests
        self.test_invalid_receipt_validation()
        
        # Duplicate receipt test
        self.test_duplicate_receipt_validation()
        
        # Integration tests via main backend
        self.test_main_backend_receipt_validation()
        
        # Receipt details and statistics
        self.test_get_receipt_details()
        self.test_receipt_statistics()
        
        # Error handling tests
        self.test_error_handling()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("📊 RECEIPT MICROSERVICE TEST SUMMARY")
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
        
        print(f"\n📝 Validated {len(self.validated_receipts)} receipts during testing")
        
        # Save detailed results to file
        with open('/app/receipt_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'main_backend_url': MAIN_BACKEND_URL,
                    'receipt_service_url': RECEIPT_SERVICE_URL
                },
                'test_results': self.test_results,
                'validated_receipts': self.validated_receipts
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/receipt_test_results.json")


def main():
    """Main test execution function."""
    tester = ReceiptServiceTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()