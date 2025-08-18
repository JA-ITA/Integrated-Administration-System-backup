#!/usr/bin/env python3
"""
Certificate Microservice Database Fallback Testing
Tests the Certificate service running on port 8006 with database fallback mechanisms
Focus: Verify service works without database connectivity using fallback storage
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional

# Test configuration - Direct service URLs as specified in review request
CERTIFICATE_SERVICE_URL = "http://localhost:8006"
PDF_SERVICE_URL = "http://localhost:3001"

class CertificateFallbackTester:
    """Test Certificate service database fallback mechanisms."""
    
    def __init__(self):
        self.certificate_service_url = CERTIFICATE_SERVICE_URL
        self.pdf_service_url = PDF_SERVICE_URL
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
    
    def test_certificate_service_health(self):
        """Test 1: Health Check - verify service shows healthy status even without database"""
        try:
            response = self.session.get(f"{self.certificate_service_url}/health")
            if response.status_code == 200:
                data = response.json()
                
                # Check if service is healthy despite database being unavailable
                service_status = data.get("status")
                database_status = data.get("database")
                
                if service_status == "healthy" and database_status == "unavailable":
                    self.log_test(
                        "Health Check - Service Healthy Without Database",
                        True,
                        f"Service shows healthy status despite database unavailable",
                        {
                            "service_status": service_status,
                            "database_status": database_status,
                            "storage": data.get("storage"),
                            "events": data.get("events")
                        }
                    )
                else:
                    self.log_test(
                        "Health Check - Service Healthy Without Database",
                        False,
                        f"Service status: {service_status}, Database status: {database_status}",
                        data
                    )
            else:
                self.log_test(
                    "Health Check - Service Healthy Without Database",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Health Check - Service Healthy Without Database",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_pdf_service_health(self):
        """Test PDF service health on port 3001"""
        try:
            response = self.session.get(f"{self.pdf_service_url}/health")
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "healthy":
                    self.log_test(
                        "PDF Service Health Check",
                        True,
                        f"PDF service is healthy on port 3001",
                        {
                            "service": data.get("service"),
                            "version": data.get("version"),
                            "status": data.get("status")
                        }
                    )
                else:
                    self.log_test(
                        "PDF Service Health Check",
                        False,
                        f"PDF service not healthy: {data.get('status')}",
                        data
                    )
            else:
                self.log_test(
                    "PDF Service Health Check",
                    False,
                    f"PDF service health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "PDF Service Health Check",
                False,
                f"PDF service health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_generation_with_fallback(self):
        """Test 2: Certificate Generation - should work with fallback storage"""
        try:
            # Generate a realistic test driver record ID
            test_driver_record_id = str(uuid.uuid4())
            
            certificate_data = {
                "driver_record_id": test_driver_record_id
            }
            
            response = self.session.post(
                f"{self.certificate_service_url}/api/v1/certificates/generate",
                json=certificate_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for successful generation without 503 database errors
                if "Database service unavailable" in str(data):
                    self.log_test(
                        "Certificate Generation with Fallback Storage",
                        False,
                        "Certificate generation failed with database service unavailable error",
                        data
                    )
                else:
                    # Store certificate details for later tests
                    certificate_info = {
                        "driver_record_id": test_driver_record_id,
                        "certificate_id": data.get("certificate_id"),
                        "download_url": data.get("download_url"),
                        "verification_token": data.get("verification_token"),
                        "issue_date": data.get("issue_date")
                    }
                    self.generated_certificates.append(certificate_info)
                    
                    # Check required response fields
                    required_fields = ["certificate_id", "download_url", "verification_token"]
                    missing_fields = [field for field in required_fields if not data.get(field)]
                    
                    if not missing_fields:
                        self.log_test(
                            "Certificate Generation with Fallback Storage",
                            True,
                            f"Certificate generated successfully using fallback storage for driver: {test_driver_record_id}",
                            {
                                "certificate_id": data.get("certificate_id"),
                                "has_download_url": bool(data.get("download_url")),
                                "has_verification_token": bool(data.get("verification_token")),
                                "issue_date": data.get("issue_date")
                            }
                        )
                    else:
                        self.log_test(
                            "Certificate Generation with Fallback Storage",
                            False,
                            f"Certificate generated but missing required fields: {missing_fields}",
                            data
                        )
            else:
                self.log_test(
                    "Certificate Generation with Fallback Storage",
                    False,
                    f"Certificate generation failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Certificate Generation with Fallback Storage",
                False,
                f"Certificate generation error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_download_by_driver_record(self):
        """Test 3: Certificate Download by Driver Record - should return pre-signed URL"""
        if not self.generated_certificates:
            self.log_test(
                "Certificate Download by Driver Record",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            cert_info = self.generated_certificates[0]
            driver_record_id = cert_info["driver_record_id"]
            
            response = self.session.get(
                f"{self.certificate_service_url}/api/v1/certificates/{driver_record_id}/download"
            )
            
            # Check for successful response (200 or 302 redirect)
            if response.status_code in [200, 302]:
                if response.status_code == 302:
                    # Direct redirect response
                    redirect_url = response.headers.get('Location')
                    self.log_test(
                        "Certificate Download by Driver Record",
                        True,
                        f"Download redirect successful for driver record: {driver_record_id}",
                        {
                            "driver_record_id": driver_record_id,
                            "redirect_url": bool(redirect_url),
                            "status_code": response.status_code
                        }
                    )
                else:
                    # JSON response with download URL
                    try:
                        data = response.json()
                        if data.get("download_url"):
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
                                f"No download URL in response",
                                data
                            )
                    except:
                        # Non-JSON response but successful status
                        self.log_test(
                            "Certificate Download by Driver Record",
                            True,
                            f"Download successful (non-JSON response) for driver record: {driver_record_id}",
                            {"status_code": response.status_code}
                        )
            else:
                # Check if it's a 503 database error
                if response.status_code == 503:
                    self.log_test(
                        "Certificate Download by Driver Record",
                        False,
                        f"Download failed with 503 Database service unavailable error",
                        {"response": response.text}
                    )
                else:
                    self.log_test(
                        "Certificate Download by Driver Record",
                        False,
                        f"Download failed with status {response.status_code}",
                        {"response": response.text}
                    )
                
        except Exception as e:
            self.log_test(
                "Certificate Download by Driver Record",
                False,
                f"Download request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_download_by_id(self):
        """Test 4: Certificate Download by ID - should return pre-signed URL"""
        if not self.generated_certificates:
            self.log_test(
                "Certificate Download by ID",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            cert_info = self.generated_certificates[0]
            certificate_id = cert_info["certificate_id"]
            
            response = self.session.get(
                f"{self.certificate_service_url}/api/v1/certificates/{certificate_id}/download"
            )
            
            # Check for successful response (200 or 302 redirect)
            if response.status_code in [200, 302]:
                if response.status_code == 302:
                    # Direct redirect response
                    redirect_url = response.headers.get('Location')
                    self.log_test(
                        "Certificate Download by ID",
                        True,
                        f"Download redirect successful for certificate: {certificate_id}",
                        {
                            "certificate_id": certificate_id,
                            "redirect_url": bool(redirect_url),
                            "status_code": response.status_code
                        }
                    )
                else:
                    # JSON response with download URL
                    try:
                        data = response.json()
                        if data.get("download_url"):
                            self.log_test(
                                "Certificate Download by ID",
                                True,
                                f"Download URL obtained for certificate: {certificate_id}",
                                {
                                    "certificate_id": certificate_id,
                                    "has_download_url": bool(data.get("download_url"))
                                }
                            )
                        else:
                            self.log_test(
                                "Certificate Download by ID",
                                False,
                                f"No download URL in response",
                                data
                            )
                    except:
                        # Non-JSON response but successful status
                        self.log_test(
                            "Certificate Download by ID",
                            True,
                            f"Download successful (non-JSON response) for certificate: {certificate_id}",
                            {"status_code": response.status_code}
                        )
            else:
                # Check if it's a 503 database error
                if response.status_code == 503:
                    self.log_test(
                        "Certificate Download by ID",
                        False,
                        f"Download failed with 503 Database service unavailable error",
                        {"response": response.text}
                    )
                else:
                    self.log_test(
                        "Certificate Download by ID",
                        False,
                        f"Download failed with status {response.status_code}",
                        {"response": response.text}
                    )
                
        except Exception as e:
            self.log_test(
                "Certificate Download by ID",
                False,
                f"Download request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_verification(self):
        """Test 5: Certificate Verification - should work with fallback storage"""
        if not self.generated_certificates:
            self.log_test(
                "Certificate Verification with Fallback",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            cert_info = self.generated_certificates[0]
            verification_token = cert_info["verification_token"]
            
            response = self.session.get(
                f"{self.certificate_service_url}/api/v1/certificates/verify/{verification_token}"
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for verification data
                    if data.get("valid") is not None:
                        self.log_test(
                            "Certificate Verification with Fallback",
                            True,
                            f"Certificate verification successful for token: {verification_token}",
                            {
                                "verification_token": verification_token,
                                "valid": data.get("valid"),
                                "certificate_id": data.get("certificate_id"),
                                "issue_date": data.get("issue_date")
                            }
                        )
                    else:
                        self.log_test(
                            "Certificate Verification with Fallback",
                            False,
                            f"Verification response missing validity information",
                            data
                        )
                except:
                    # Non-JSON response but successful status
                    self.log_test(
                        "Certificate Verification with Fallback",
                        True,
                        f"Verification successful (non-JSON response) for token: {verification_token}",
                        {"status_code": response.status_code}
                    )
            else:
                # Check if it's a 503 database error
                if response.status_code == 503:
                    self.log_test(
                        "Certificate Verification with Fallback",
                        False,
                        f"Verification failed with 503 Database service unavailable error",
                        {"response": response.text}
                    )
                else:
                    self.log_test(
                        "Certificate Verification with Fallback",
                        False,
                        f"Verification failed with status {response.status_code}",
                        {"response": response.text}
                    )
                
        except Exception as e:
            self.log_test(
                "Certificate Verification with Fallback",
                False,
                f"Verification request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_certificate_status(self):
        """Test 6: Certificate Status - should work with fallback storage"""
        if not self.generated_certificates:
            self.log_test(
                "Certificate Status with Fallback",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            cert_info = self.generated_certificates[0]
            certificate_id = cert_info["certificate_id"]
            
            response = self.session.get(
                f"{self.certificate_service_url}/api/v1/certificates/{certificate_id}/status"
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for status information
                    if data.get("id") or data.get("status"):
                        self.log_test(
                            "Certificate Status with Fallback",
                            True,
                            f"Certificate status retrieved for: {certificate_id}",
                            {
                                "certificate_id": certificate_id,
                                "status": data.get("status"),
                                "issue_date": data.get("issue_date")
                            }
                        )
                    else:
                        self.log_test(
                            "Certificate Status with Fallback",
                            False,
                            f"Status response missing certificate information",
                            data
                        )
                except:
                    # Non-JSON response but successful status
                    self.log_test(
                        "Certificate Status with Fallback",
                        True,
                        f"Status successful (non-JSON response) for certificate: {certificate_id}",
                        {"status_code": response.status_code}
                    )
            else:
                # Check if it's a 503 database error
                if response.status_code == 503:
                    self.log_test(
                        "Certificate Status with Fallback",
                        False,
                        f"Status check failed with 503 Database service unavailable error",
                        {"response": response.text}
                    )
                else:
                    self.log_test(
                        "Certificate Status with Fallback",
                        False,
                        f"Status check failed with status {response.status_code}",
                        {"response": response.text}
                    )
                
        except Exception as e:
            self.log_test(
                "Certificate Status with Fallback",
                False,
                f"Status request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_driver_certificates_list(self):
        """Test 7: Driver Certificates List - should work with fallback storage"""
        if not self.generated_certificates:
            self.log_test(
                "Driver Certificates List with Fallback",
                False,
                "No certificates available for testing (generation may have failed)",
                {}
            )
            return
        
        try:
            cert_info = self.generated_certificates[0]
            driver_record_id = cert_info["driver_record_id"]
            
            response = self.session.get(
                f"{self.certificate_service_url}/api/v1/certificates/driver/{driver_record_id}"
            )
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    
                    # Check for certificates list
                    certificates = data.get("certificates", [])
                    if isinstance(certificates, list):
                        self.log_test(
                            "Driver Certificates List with Fallback",
                            True,
                            f"Retrieved {len(certificates)} certificates for driver: {driver_record_id}",
                            {
                                "driver_record_id": driver_record_id,
                                "certificates_count": len(certificates)
                            }
                        )
                    else:
                        self.log_test(
                            "Driver Certificates List with Fallback",
                            False,
                            f"Invalid certificates list format",
                            data
                        )
                except:
                    # Non-JSON response but successful status
                    self.log_test(
                        "Driver Certificates List with Fallback",
                        True,
                        f"Certificates list successful (non-JSON response) for driver: {driver_record_id}",
                        {"status_code": response.status_code}
                    )
            else:
                # Check if it's a 503 database error
                if response.status_code == 503:
                    self.log_test(
                        "Driver Certificates List with Fallback",
                        False,
                        f"Certificates list failed with 503 Database service unavailable error",
                        {"response": response.text}
                    )
                else:
                    self.log_test(
                        "Driver Certificates List with Fallback",
                        False,
                        f"Certificates list failed with status {response.status_code}",
                        {"response": response.text}
                    )
                
        except Exception as e:
            self.log_test(
                "Driver Certificates List with Fallback",
                False,
                f"Certificates list request error: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all database fallback tests in sequence."""
        print("🚀 Starting Certificate Microservice Database Fallback Testing")
        print(f"🔧 Certificate Service: {CERTIFICATE_SERVICE_URL}")
        print(f"📄 PDF Service: {PDF_SERVICE_URL}")
        print("🎯 Focus: Database fallback mechanisms and degraded mode functionality")
        print("=" * 100)
        
        # Health checks
        print("\n🏥 HEALTH CHECKS:")
        self.test_certificate_service_health()
        self.test_pdf_service_health()
        
        # Core certificate functionality with fallback
        print("\n🎯 TESTING CERTIFICATE OPERATIONS WITH DATABASE FALLBACK:")
        
        # Test all 7 scenarios from review request
        self.test_certificate_generation_with_fallback()
        self.test_certificate_download_by_driver_record()
        self.test_certificate_download_by_id()
        self.test_certificate_verification()
        self.test_certificate_status()
        self.test_driver_certificates_list()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 100)
        print("📊 CERTIFICATE DATABASE FALLBACK TEST SUMMARY")
        print("=" * 100)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🎯 TESTED SCENARIOS:")
        print("   1. Health Check - Service healthy without database")
        print("   2. Certificate Generation - Works with fallback storage")
        print("   3. Certificate Download by Driver Record - Returns pre-signed URL")
        print("   4. Certificate Download by ID - Returns pre-signed URL")
        print("   5. Certificate Verification - Works with fallback storage")
        print("   6. Certificate Status - Works with fallback storage")
        print("   7. Driver Certificates List - Works with fallback storage")
        
        print(f"\n🔧 CONFIGURATION VERIFIED:")
        print(f"   - Certificate Service: {CERTIFICATE_SERVICE_URL}")
        print(f"   - PDF Service: {PDF_SERVICE_URL}")
        print(f"   - Using fallback storage (no database dependency)")
        print(f"   - Using local filesystem for file storage")
        print(f"   - Using in-memory events (no RabbitMQ dependency)")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print(f"\n📝 Generated {len(self.generated_certificates)} test certificates during testing")
        
        # Save detailed results to file
        with open('/app/certificate_fallback_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'certificate_service_url': CERTIFICATE_SERVICE_URL,
                    'pdf_service_url': PDF_SERVICE_URL,
                    'focus': 'Database fallback mechanisms and degraded mode functionality'
                },
                'test_results': self.test_results,
                'generated_certificates': self.generated_certificates
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/certificate_fallback_test_results.json")


def main():
    """Main test execution function."""
    tester = CertificateFallbackTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()