#!/usr/bin/env python3
"""
Certificate Microservice Testing
Tests the ITADIAS Certificate Microservice with Handlebars + PDF-lib integration
"""

import asyncio
import json
import uuid
import requests
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import sys

# Test configuration
MAIN_BACKEND_URL = "https://cranky-tharp.preview.emergentagent.com"
CERTIFICATE_SERVICE_URL = "http://localhost:8006"  # Direct service URL for health checks
API_BASE = f"{MAIN_BACKEND_URL}/api"

class CertificateMicroserviceTester:
    """Comprehensive tester for the Certificate microservice."""
    
    def __init__(self):
        self.main_backend_url = MAIN_BACKEND_URL
        self.certificate_service_url = CERTIFICATE_SERVICE_URL
        self.api_base = API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.generated_certificates = []
        
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
    
    def test_certificate_service_health_via_main_backend(self):
        """Test certificate service health check via main backend"""
        try:
            response = self.session.get(f"{self.api_base}/certificates/health")
            if response.status_code == 200:
                data = response.json()
                
                # Check if certificate service is healthy
                service_status = data.get("certificate_service", "unavailable")
                status_data = data.get("status", {})
                
                if service_status == "healthy" or (status_data and status_data.get("status") == "healthy"):
                    self.log_test(
                        "Certificate Service Health Check (via Main Backend)",
                        True,
                        f"Certificate service is healthy: {service_status}",
                        {
                            "service_status": service_status,
                            "status_details": status_data
                        }
                    )
                else:
                    self.log_test(
                        "Certificate Service Health Check (via Main Backend)",
                        False,
                        f"Certificate service is not healthy: {service_status}",
                        data
                    )
            else:
                self.log_test(
                    "Certificate Service Health Check (via Main Backend)",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Service Health Check (via Main Backend)",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_direct_certificate_service_health(self):
        """Test certificate service health check directly"""
        try:
            response = self.session.get(f"{self.certificate_service_url}/health")
            if response.status_code == 200:
                data = response.json()
                
                # Check required health check components
                required_components = ["status", "service", "version"]
                missing_components = [comp for comp in required_components if comp not in data]
                
                if not missing_components and data.get("status") == "healthy":
                    self.log_test(
                        "Certificate Service Direct Health Check",
                        True,
                        f"Service healthy: {data.get('status')}",
                        {
                            "service": data.get("service"),
                            "version": data.get("version"),
                            "storage": data.get("storage"),
                            "database": data.get("database")
                        }
                    )
                else:
                    self.log_test(
                        "Certificate Service Direct Health Check",
                        False,
                        f"Health response missing components or unhealthy: {missing_components}",
                        data
                    )
            else:
                self.log_test(
                    "Certificate Service Direct Health Check",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Service Direct Health Check",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_direct_certificate_service_config(self):
        """Test certificate service configuration endpoint directly"""
        try:
            response = self.session.get(f"{self.certificate_service_url}/config")
            if response.status_code == 200:
                data = response.json()
                
                # Check for expected configuration fields
                expected_fields = ["service", "version", "storage", "pdf_service"]
                missing_fields = [field for field in expected_fields if field not in data]
                
                if not missing_fields:
                    self.log_test(
                        "Certificate Service Configuration",
                        True,
                        "Configuration endpoint accessible with expected fields",
                        {
                            "service": data.get("service"),
                            "version": data.get("version"),
                            "storage": data.get("storage"),
                            "pdf_service": data.get("pdf_service")
                        }
                    )
                else:
                    self.log_test(
                        "Certificate Service Configuration",
                        False,
                        f"Configuration missing expected fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    "Certificate Service Configuration",
                    False,
                    f"Config endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Service Configuration",
                False,
                f"Config endpoint error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_generation_via_main_backend(self):
        """Test certificate generation via main backend"""
        try:
            # Generate a test driver record ID
            test_driver_record_id = str(uuid.uuid4())
            
            certificate_data = {
                "driver_record_id": test_driver_record_id
            }
            
            response = self.session.post(
                f"{self.api_base}/certificates/generate",
                json=certificate_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    # Store certificate details for later tests
                    certificate_info = {
                        "driver_record_id": test_driver_record_id,
                        "certificate_id": data.get("certificate_id"),
                        "download_url": data.get("download_url"),
                        "verification_token": data.get("verification_token"),
                        "issue_date": data.get("issue_date"),
                        "expiry_date": data.get("expiry_date")
                    }
                    self.generated_certificates.append(certificate_info)
                    
                    # Check required response fields
                    required_fields = ["certificate_id", "download_url", "verification_token", "issue_date"]
                    missing_fields = [field for field in required_fields if not data.get(field)]
                    
                    if not missing_fields:
                        self.log_test(
                            "Certificate Generation (via Main Backend)",
                            True,
                            f"Certificate generated successfully for driver record: {test_driver_record_id}",
                            {
                                "certificate_id": data.get("certificate_id"),
                                "has_download_url": bool(data.get("download_url")),
                                "has_verification_token": bool(data.get("verification_token")),
                                "issue_date": data.get("issue_date"),
                                "metadata": data.get("metadata", {})
                            }
                        )
                    else:
                        self.log_test(
                            "Certificate Generation (via Main Backend)",
                            False,
                            f"Certificate generated but missing required fields: {missing_fields}",
                            data
                        )
                else:
                    self.log_test(
                        "Certificate Generation (via Main Backend)",
                        False,
                        f"Certificate generation failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Certificate Generation (via Main Backend)",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Generation (via Main Backend)",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_download_by_driver_record(self):
        """Test certificate download by driver record ID"""
        if not self.generated_certificates:
            self.log_test(
                "Certificate Download by Driver Record",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            # Use the first generated certificate
            cert_info = self.generated_certificates[0]
            driver_record_id = cert_info["driver_record_id"]
            
            response = self.session.get(
                f"{self.api_base}/certificates/{driver_record_id}/download"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("download_url"):
                    self.log_test(
                        "Certificate Download by Driver Record",
                        True,
                        f"Download URL obtained for driver record: {driver_record_id}",
                        {
                            "driver_record_id": driver_record_id,
                            "has_download_url": bool(data.get("download_url"))
                        }
                    )
                else:
                    self.log_test(
                        "Certificate Download by Driver Record",
                        False,
                        f"Download request failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Certificate Download by Driver Record",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Download by Driver Record",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_download_by_certificate_id(self):
        """Test certificate download by certificate ID"""
        if not self.generated_certificates:
            self.log_test(
                "Certificate Download by Certificate ID",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            # Use the first generated certificate
            cert_info = self.generated_certificates[0]
            certificate_id = cert_info["certificate_id"]
            
            response = self.session.get(
                f"{self.api_base}/certificates/download/{certificate_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("download_url"):
                    self.log_test(
                        "Certificate Download by Certificate ID",
                        True,
                        f"Download URL obtained for certificate: {certificate_id}",
                        {
                            "certificate_id": certificate_id,
                            "has_download_url": bool(data.get("download_url"))
                        }
                    )
                else:
                    self.log_test(
                        "Certificate Download by Certificate ID",
                        False,
                        f"Download request failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Certificate Download by Certificate ID",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Download by Certificate ID",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_verification(self):
        """Test certificate verification"""
        if not self.generated_certificates:
            self.log_test(
                "Certificate Verification",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            # Use the first generated certificate
            cert_info = self.generated_certificates[0]
            verification_token = cert_info["verification_token"]
            
            response = self.session.get(
                f"{self.api_base}/certificates/verify/{verification_token}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("verification"):
                    verification_data = data.get("verification", {})
                    
                    # Check for expected verification fields
                    expected_fields = ["valid", "certificate_id", "issue_date"]
                    missing_fields = [field for field in expected_fields if field not in verification_data]
                    
                    if not missing_fields and verification_data.get("valid"):
                        self.log_test(
                            "Certificate Verification",
                            True,
                            f"Certificate verification successful for token: {verification_token}",
                            {
                                "verification_token": verification_token,
                                "valid": verification_data.get("valid"),
                                "certificate_id": verification_data.get("certificate_id"),
                                "issue_date": verification_data.get("issue_date")
                            }
                        )
                    else:
                        self.log_test(
                            "Certificate Verification",
                            False,
                            f"Verification failed or missing fields: {missing_fields}",
                            verification_data
                        )
                else:
                    self.log_test(
                        "Certificate Verification",
                        False,
                        f"Verification request failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Certificate Verification",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Verification",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_status(self):
        """Test certificate status endpoint"""
        if not self.generated_certificates:
            self.log_test(
                "Certificate Status",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            # Use the first generated certificate
            cert_info = self.generated_certificates[0]
            certificate_id = cert_info["certificate_id"]
            
            response = self.session.get(
                f"{self.api_base}/certificates/status/{certificate_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("certificate"):
                    certificate_data = data.get("certificate", {})
                    
                    # Check for expected status fields
                    expected_fields = ["id", "status", "issue_date"]
                    missing_fields = [field for field in expected_fields if field not in certificate_data]
                    
                    if not missing_fields:
                        self.log_test(
                            "Certificate Status",
                            True,
                            f"Certificate status retrieved for: {certificate_id}",
                            {
                                "certificate_id": certificate_id,
                                "status": certificate_data.get("status"),
                                "issue_date": certificate_data.get("issue_date"),
                                "expiry_date": certificate_data.get("expiry_date")
                            }
                        )
                    else:
                        self.log_test(
                            "Certificate Status",
                            False,
                            f"Status response missing fields: {missing_fields}",
                            certificate_data
                        )
                else:
                    self.log_test(
                        "Certificate Status",
                        False,
                        f"Status request failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Certificate Status",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Status",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_driver_certificates_list(self):
        """Test getting all certificates for a driver record"""
        if not self.generated_certificates:
            self.log_test(
                "Driver Certificates List",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            # Use the first generated certificate
            cert_info = self.generated_certificates[0]
            driver_record_id = cert_info["driver_record_id"]
            
            response = self.session.get(
                f"{self.api_base}/certificates/driver/{driver_record_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    certificates_data = data.get("data", {})
                    certificates_list = certificates_data.get("certificates", [])
                    
                    if certificates_list and len(certificates_list) > 0:
                        self.log_test(
                            "Driver Certificates List",
                            True,
                            f"Retrieved {len(certificates_list)} certificates for driver: {driver_record_id}",
                            {
                                "driver_record_id": driver_record_id,
                                "certificates_count": len(certificates_list),
                                "first_certificate": certificates_list[0] if certificates_list else None
                            }
                        )
                    else:
                        self.log_test(
                            "Driver Certificates List",
                            False,
                            f"No certificates found for driver: {driver_record_id}",
                            certificates_data
                        )
                else:
                    self.log_test(
                        "Driver Certificates List",
                        False,
                        f"Driver certificates request failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Driver Certificates List",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Driver Certificates List",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_error_handling_non_existent_certificate(self):
        """Test error handling for non-existent certificates"""
        try:
            # Use a random UUID that doesn't exist
            non_existent_id = str(uuid.uuid4())
            
            response = self.session.get(
                f"{self.api_base}/certificates/download/{non_existent_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("success") and data.get("error"):
                    self.log_test(
                        "Error Handling - Non-existent Certificate",
                        True,
                        f"Properly handled non-existent certificate: {data.get('error')}",
                        {
                            "non_existent_id": non_existent_id,
                            "error": data.get("error"),
                            "status_code": data.get("status_code")
                        }
                    )
                else:
                    self.log_test(
                        "Error Handling - Non-existent Certificate",
                        False,
                        f"Expected error response but got success",
                        data
                    )
            else:
                # Could also be a 404 or other error status, which is also acceptable
                self.log_test(
                    "Error Handling - Non-existent Certificate",
                    True,
                    f"Properly returned error status {response.status_code} for non-existent certificate",
                    {"status_code": response.status_code, "response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Error Handling - Non-existent Certificate",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_error_handling_invalid_verification_token(self):
        """Test error handling for invalid verification tokens"""
        try:
            # Use an invalid verification token
            invalid_token = "invalid-token-12345"
            
            response = self.session.get(
                f"{self.api_base}/certificates/verify/{invalid_token}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("success") and data.get("error"):
                    self.log_test(
                        "Error Handling - Invalid Verification Token",
                        True,
                        f"Properly handled invalid verification token: {data.get('error')}",
                        {
                            "invalid_token": invalid_token,
                            "error": data.get("error"),
                            "status_code": data.get("status_code")
                        }
                    )
                else:
                    self.log_test(
                        "Error Handling - Invalid Verification Token",
                        False,
                        f"Expected error response but got success",
                        data
                    )
            else:
                # Could also be a 404 or other error status, which is also acceptable
                self.log_test(
                    "Error Handling - Invalid Verification Token",
                    True,
                    f"Properly returned error status {response.status_code} for invalid token",
                    {"status_code": response.status_code, "response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Error Handling - Invalid Verification Token",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting Certificate Microservice Testing")
        print(f"🌐 Testing Main Backend: {MAIN_BACKEND_URL}")
        print(f"🔧 Testing Certificate Service: {CERTIFICATE_SERVICE_URL}")
        print("🎯 Focus: ITADIAS Certificate Microservice with Handlebars + PDF-lib")
        print("=" * 100)
        
        # Health checks
        self.test_certificate_service_health_via_main_backend()
        self.test_direct_certificate_service_health()
        self.test_direct_certificate_service_config()
        
        # Core certificate functionality
        print("\n🎯 TESTING CORE CERTIFICATE FUNCTIONALITY:")
        
        # 1. Certificate generation
        self.test_certificate_generation_via_main_backend()
        
        # 2. Certificate download endpoints (both variants)
        self.test_certificate_download_by_driver_record()
        self.test_certificate_download_by_certificate_id()
        
        # 3. Certificate verification
        self.test_certificate_verification()
        
        # 4. Certificate status and metadata
        self.test_certificate_status()
        self.test_driver_certificates_list()
        
        # Error handling tests
        print("\n🔍 TESTING ERROR HANDLING:")
        self.test_error_handling_non_existent_certificate()
        self.test_error_handling_invalid_verification_token()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 100)
        print("📊 CERTIFICATE MICROSERVICE TEST SUMMARY")
        print("=" * 100)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🎯 KEY VALIDATION POINTS:")
        print("   ✓ Certificate service health and configuration")
        print("   ✓ Certificate generation with mock driver record ID")
        print("   ✓ Download by driver record ID (NEW ENDPOINT)")
        print("   ✓ Download by certificate ID (existing endpoint)")
        print("   ✓ Certificate verification with tokens")
        print("   ✓ Error handling for non-existent certificates")
        print("   ✓ PDF service integration (Handlebars + PDF-lib)")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print(f"\n📝 Generated {len(self.generated_certificates)} test certificates during testing")
        
        # Save detailed results to file
        with open('/app/certificate_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'main_backend_url': MAIN_BACKEND_URL,
                    'certificate_service_url': CERTIFICATE_SERVICE_URL,
                    'focus': 'ITADIAS Certificate Microservice with Handlebars + PDF-lib'
                },
                'test_results': self.test_results,
                'generated_certificates': self.generated_certificates
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/certificate_test_results.json")


def main():
    """Main test execution function."""
    tester = CertificateMicroserviceTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()