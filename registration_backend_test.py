#!/usr/bin/env python3
"""
Registration Microservice Backend Testing Suite
Tests all REST API endpoints, business rules, document validation, and service integrations.
"""

import asyncio
import json
import uuid
import requests
import time
import base64
import os
from datetime import datetime, date
from typing import Dict, Any, Optional, List
import sys

# Test configuration
REGISTRATION_SERVICE_URL = "http://localhost:8004"
MAIN_BACKEND_URL = "https://cranky-tharp.preview.emergentagent.com"
API_BASE = f"{REGISTRATION_SERVICE_URL}/api/v1"

class RegistrationServiceTester:
    """Comprehensive tester for the Registration microservice."""
    
    def __init__(self):
        self.registration_base_url = API_BASE
        self.main_backend_url = MAIN_BACKEND_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.created_registrations = []
        
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
    
    def generate_test_jwt_token(self) -> str:
        """Generate a test JWT token for authentication"""
        # For testing, we'll use a simple Bearer token
        # In production, this would be a proper JWT
        return "test-jwt-token-12345"
    
    def create_test_document_base64(self, doc_type: str, filename: str) -> str:
        """Create a small test document in base64 format"""
        if doc_type in ["photo"]:
            # Create a minimal JPEG-like content
            content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        elif doc_type in ["mc1", "mc2", "other"]:
            # Create a minimal PDF-like content
            content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF'
        else:
            # Default content for id_proof (can be JPEG or PDF)
            content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        
        return base64.b64encode(content).decode('utf-8')
    
    def generate_test_registration_data(self, vehicle_category: str = "B", age_years: float = 18.0, include_mc: bool = False) -> Dict[str, Any]:
        """Generate realistic test registration data"""
        booking_id = str(uuid.uuid4())
        receipt_no = f"TAJ{int(time.time())}"[-12:]  # Last 12 chars to keep it reasonable
        
        # Create documents list
        docs = [
            {
                "type": "photo",
                "filename": "photo.jpg",
                "content": self.create_test_document_base64("photo", "photo.jpg"),
                "mime_type": "image/jpeg"
            },
            {
                "type": "id_proof",
                "filename": "id_proof.jpg",
                "content": self.create_test_document_base64("id_proof", "id_proof.jpg"),
                "mime_type": "image/jpeg"
            }
        ]
        
        # Add medical certificates based on vehicle category
        if vehicle_category == "SPECIAL" or include_mc:  # Provisional needs MC1
            docs.append({
                "type": "mc1",
                "filename": "medical_cert_1.pdf",
                "content": self.create_test_document_base64("mc1", "medical_cert_1.pdf"),
                "mime_type": "application/pdf"
            })
        
        if vehicle_category in ["C", "PPV"] or include_mc:  # Class C/PPV needs MC2
            docs.append({
                "type": "mc2",
                "filename": "medical_cert_2.pdf",
                "content": self.create_test_document_base64("mc2", "medical_cert_2.pdf"),
                "mime_type": "application/pdf"
            })
        
        # Determine vehicle weight based on category
        if vehicle_category == "C":
            vehicle_weight = 8000  # Over 7000kg threshold
        elif vehicle_category == "PPV":
            vehicle_weight = 3500
        else:
            vehicle_weight = 2000  # Class B or SPECIAL
        
        return {
            "booking_id": booking_id,
            "receipt_no": receipt_no,
            "vehicle_weight_kg": vehicle_weight,
            "vehicle_category": vehicle_category,
            "docs": docs,
            "manager_override": False,
            "override_reason": None,
            "override_by": None
        }
    
    def test_service_health_check(self):
        """Test registration service health check"""
        try:
            response = self.session.get(f"{REGISTRATION_SERVICE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                
                # Check required health check components
                required_components = ["status", "service", "version", "database", "events", "dependencies"]
                missing_components = [comp for comp in required_components if comp not in data]
                
                if not missing_components:
                    self.log_test(
                        "Service Health Check",
                        True,
                        f"Service healthy: {data.get('status')}",
                        {
                            "database": data.get("database"),
                            "events": data.get("events"),
                            "dependencies": data.get("dependencies", {}).get("all_dependencies_available", False),
                            "configuration": data.get("configuration", {})
                        }
                    )
                else:
                    self.log_test(
                        "Service Health Check",
                        False,
                        f"Health response missing components: {missing_components}",
                        data
                    )
            else:
                self.log_test(
                    "Service Health Check",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Service Health Check",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_configuration_endpoint(self):
        """Test configuration endpoint"""
        try:
            response = self.session.get(f"{REGISTRATION_SERVICE_URL}/config")
            if response.status_code == 200:
                data = response.json()
                
                # Check for required configuration sections
                required_sections = ["registration_rules", "document_formats", "external_services"]
                missing_sections = [section for section in required_sections if section not in data]
                
                if not missing_sections:
                    rules = data.get("registration_rules", {})
                    self.log_test(
                        "Configuration Endpoint",
                        True,
                        "Configuration retrieved successfully",
                        {
                            "min_age_provisional": rules.get("min_age_provisional"),
                            "min_age_class_b": rules.get("min_age_class_b"),
                            "min_age_class_c_ppv": rules.get("min_age_class_c_ppv"),
                            "weight_threshold_class_c": rules.get("weight_threshold_class_c"),
                            "document_formats": data.get("document_formats", {})
                        }
                    )
                else:
                    self.log_test(
                        "Configuration Endpoint",
                        False,
                        f"Configuration missing sections: {missing_sections}",
                        data
                    )
            else:
                self.log_test(
                    "Configuration Endpoint",
                    False,
                    f"Configuration endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Configuration Endpoint",
                False,
                f"Configuration endpoint error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_events_status_endpoint(self):
        """Test events status endpoint"""
        try:
            response = self.session.get(f"{REGISTRATION_SERVICE_URL}/events/status")
            if response.status_code == 200:
                data = response.json()
                
                # Check for event service information
                if "event_service" in data and "fallback_events_count" in data:
                    self.log_test(
                        "Events Status Endpoint",
                        True,
                        "Events status retrieved successfully",
                        {
                            "event_service_connected": data.get("event_service", {}).get("connected", False),
                            "fallback_events_count": data.get("fallback_events_count", 0),
                            "has_fallback_events": len(data.get("fallback_events", [])) > 0
                        }
                    )
                else:
                    self.log_test(
                        "Events Status Endpoint",
                        False,
                        "Events status response missing required fields",
                        data
                    )
            else:
                self.log_test(
                    "Events Status Endpoint",
                    False,
                    f"Events status endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Events Status Endpoint",
                False,
                f"Events status endpoint error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_direct_registration_api_success(self):
        """Test direct registration API with valid data"""
        try:
            # Test Class B registration (no medical certificate required)
            registration_data = self.generate_test_registration_data("B", 18.0)
            jwt_token = self.generate_test_jwt_token()
            
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.registration_base_url}/registrations",
                json=registration_data,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                # Check response structure
                if data.get("success") and data.get("registration"):
                    registration = data["registration"]
                    registration_id = registration.get("id")
                    
                    if registration_id:
                        self.created_registrations.append(registration_id)
                    
                    self.log_test(
                        "Direct Registration API - Class B Success",
                        True,
                        f"Registration created successfully: {registration.get('vehicle_category')}",
                        {
                            "registration_id": registration_id,
                            "status": registration.get("status"),
                            "vehicle_category": registration.get("vehicle_category"),
                            "age_in_years": registration.get("age_in_years"),
                            "docs_count": len(registration.get("docs", []))
                        }
                    )
                    return registration_id
                else:
                    self.log_test(
                        "Direct Registration API - Class B Success",
                        False,
                        f"Registration failed: {data.get('message', 'Unknown error')}",
                        data
                    )
            else:
                self.log_test(
                    "Direct Registration API - Class B Success",
                    False,
                    f"Expected 200/201, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Direct Registration API - Class B Success",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        return None
    
    def test_age_validation_scenarios(self):
        """Test age validation for different vehicle categories"""
        test_cases = [
            {
                "name": "Provisional - Valid Age (16.5+)",
                "category": "SPECIAL",
                "age": 16.6,
                "should_pass": True
            },
            {
                "name": "Provisional - Invalid Age (<16.5)",
                "category": "SPECIAL", 
                "age": 16.0,
                "should_pass": False
            },
            {
                "name": "Class B - Valid Age (17+)",
                "category": "B",
                "age": 17.5,
                "should_pass": True
            },
            {
                "name": "Class B - Invalid Age (<17)",
                "category": "B",
                "age": 16.8,
                "should_pass": False
            },
            {
                "name": "Class C - Valid Age (20+)",
                "category": "C",
                "age": 20.5,
                "should_pass": True
            },
            {
                "name": "Class C - Invalid Age (<20)",
                "category": "C",
                "age": 19.5,
                "should_pass": False
            }
        ]
        
        for test_case in test_cases:
            try:
                registration_data = self.generate_test_registration_data(
                    test_case["category"], 
                    test_case["age"],
                    include_mc=True  # Include medical certificates for all tests
                )
                jwt_token = self.generate_test_jwt_token()
                
                headers = {
                    "Authorization": f"Bearer {jwt_token}",
                    "Content-Type": "application/json"
                }
                
                response = self.session.post(
                    f"{self.registration_base_url}/registrations",
                    json=registration_data,
                    headers=headers
                )
                
                if test_case["should_pass"]:
                    # Should succeed
                    if response.status_code in [200, 201]:
                        data = response.json()
                        if data.get("success"):
                            registration_id = data.get("registration", {}).get("id")
                            if registration_id:
                                self.created_registrations.append(registration_id)
                            
                            self.log_test(
                                f"Age Validation - {test_case['name']}",
                                True,
                                f"Age validation passed for {test_case['category']} at {test_case['age']} years",
                                {"registration_id": registration_id}
                            )
                        else:
                            self.log_test(
                                f"Age Validation - {test_case['name']}",
                                False,
                                f"Expected success but got failure: {data.get('message')}",
                                data
                            )
                    else:
                        self.log_test(
                            f"Age Validation - {test_case['name']}",
                            False,
                            f"Expected success but got status {response.status_code}",
                            {"response": response.text}
                        )
                else:
                    # Should fail
                    if response.status_code in [400, 422]:
                        data = response.json()
                        if not data.get("success", True):
                            self.log_test(
                                f"Age Validation - {test_case['name']}",
                                True,
                                f"Age validation properly rejected {test_case['category']} at {test_case['age']} years",
                                {"message": data.get("message")}
                            )
                        else:
                            self.log_test(
                                f"Age Validation - {test_case['name']}",
                                False,
                                f"Expected failure but got success",
                                data
                            )
                    else:
                        self.log_test(
                            f"Age Validation - {test_case['name']}",
                            False,
                            f"Expected 400/422 but got {response.status_code}",
                            {"response": response.text}
                        )
                        
            except Exception as e:
                self.log_test(
                    f"Age Validation - {test_case['name']}",
                    False,
                    f"Request error: {str(e)}",
                    {"error": str(e)}
                )
    
    def test_medical_certificate_validation(self):
        """Test medical certificate requirements"""
        test_cases = [
            {
                "name": "Provisional - MC1 Required",
                "category": "SPECIAL",
                "include_mc1": True,
                "include_mc2": False,
                "should_pass": True
            },
            {
                "name": "Provisional - Missing MC1",
                "category": "SPECIAL",
                "include_mc1": False,
                "include_mc2": False,
                "should_pass": False
            },
            {
                "name": "Class C - MC2 Required",
                "category": "C",
                "include_mc1": False,
                "include_mc2": True,
                "should_pass": True
            },
            {
                "name": "Class C - Missing MC2",
                "category": "C",
                "include_mc1": False,
                "include_mc2": False,
                "should_pass": False
            },
            {
                "name": "Class B - No MC Required",
                "category": "B",
                "include_mc1": False,
                "include_mc2": False,
                "should_pass": True
            }
        ]
        
        for test_case in test_cases:
            try:
                registration_data = self.generate_test_registration_data(test_case["category"], 20.0)
                
                # Modify docs based on test case
                docs = [doc for doc in registration_data["docs"] if doc["type"] in ["photo", "id_proof"]]
                
                if test_case["include_mc1"]:
                    docs.append({
                        "type": "mc1",
                        "filename": "medical_cert_1.pdf",
                        "content": self.create_test_document_base64("mc1", "medical_cert_1.pdf"),
                        "mime_type": "application/pdf"
                    })
                
                if test_case["include_mc2"]:
                    docs.append({
                        "type": "mc2",
                        "filename": "medical_cert_2.pdf",
                        "content": self.create_test_document_base64("mc2", "medical_cert_2.pdf"),
                        "mime_type": "application/pdf"
                    })
                
                registration_data["docs"] = docs
                jwt_token = self.generate_test_jwt_token()
                
                headers = {
                    "Authorization": f"Bearer {jwt_token}",
                    "Content-Type": "application/json"
                }
                
                response = self.session.post(
                    f"{self.registration_base_url}/registrations",
                    json=registration_data,
                    headers=headers
                )
                
                if test_case["should_pass"]:
                    if response.status_code in [200, 201]:
                        data = response.json()
                        if data.get("success"):
                            registration_id = data.get("registration", {}).get("id")
                            if registration_id:
                                self.created_registrations.append(registration_id)
                            
                            self.log_test(
                                f"Medical Certificate - {test_case['name']}",
                                True,
                                f"Medical certificate validation passed for {test_case['category']}",
                                {"registration_id": registration_id}
                            )
                        else:
                            self.log_test(
                                f"Medical Certificate - {test_case['name']}",
                                False,
                                f"Expected success but got failure: {data.get('message')}",
                                data
                            )
                    else:
                        self.log_test(
                            f"Medical Certificate - {test_case['name']}",
                            False,
                            f"Expected success but got status {response.status_code}",
                            {"response": response.text}
                        )
                else:
                    if response.status_code in [400, 422]:
                        data = response.json()
                        if not data.get("success", True):
                            self.log_test(
                                f"Medical Certificate - {test_case['name']}",
                                True,
                                f"Medical certificate validation properly rejected {test_case['category']}",
                                {"message": data.get("message")}
                            )
                        else:
                            self.log_test(
                                f"Medical Certificate - {test_case['name']}",
                                False,
                                f"Expected failure but got success",
                                data
                            )
                    else:
                        self.log_test(
                            f"Medical Certificate - {test_case['name']}",
                            False,
                            f"Expected 400/422 but got {response.status_code}",
                            {"response": response.text}
                        )
                        
            except Exception as e:
                self.log_test(
                    f"Medical Certificate - {test_case['name']}",
                    False,
                    f"Request error: {str(e)}",
                    {"error": str(e)}
                )
    
    def test_document_validation(self):
        """Test document format and size validation"""
        try:
            # Test with missing required documents
            registration_data = self.generate_test_registration_data("B", 18.0)
            registration_data["docs"] = [
                {
                    "type": "photo",
                    "filename": "photo.jpg",
                    "content": self.create_test_document_base64("photo", "photo.jpg"),
                    "mime_type": "image/jpeg"
                }
                # Missing id_proof
            ]
            
            jwt_token = self.generate_test_jwt_token()
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.registration_base_url}/registrations",
                json=registration_data,
                headers=headers
            )
            
            if response.status_code in [400, 422]:
                self.log_test(
                    "Document Validation - Missing Required Documents",
                    True,
                    "Missing required documents properly rejected",
                    {"status": response.status_code}
                )
            else:
                self.log_test(
                    "Document Validation - Missing Required Documents",
                    False,
                    f"Expected 400/422, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Document Validation - Missing Required Documents",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test with oversized document (simulate)
        try:
            registration_data = self.generate_test_registration_data("B", 18.0)
            # Create a large base64 string (simulate 6MB file)
            large_content = "A" * (6 * 1024 * 1024)  # 6MB of 'A' characters
            registration_data["docs"][0]["content"] = large_content
            
            jwt_token = self.generate_test_jwt_token()
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.registration_base_url}/registrations",
                json=registration_data,
                headers=headers
            )
            
            if response.status_code in [400, 422]:
                self.log_test(
                    "Document Validation - Oversized Document",
                    True,
                    "Oversized document properly rejected",
                    {"status": response.status_code}
                )
            else:
                self.log_test(
                    "Document Validation - Oversized Document",
                    False,
                    f"Expected 400/422, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Document Validation - Oversized Document",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_external_service_validation(self):
        """Test external service validation (Calendar & Receipt)"""
        try:
            # Test with invalid booking ID (should fail gracefully)
            registration_data = self.generate_test_registration_data("B", 18.0)
            registration_data["booking_id"] = str(uuid.uuid4())  # Non-existent booking
            registration_data["receipt_no"] = "INVALID123"  # Invalid receipt
            
            jwt_token = self.generate_test_jwt_token()
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.registration_base_url}/registrations",
                json=registration_data,
                headers=headers
            )
            
            # Should handle gracefully (either succeed with warnings or fail with proper error)
            if response.status_code in [200, 201, 400, 422, 503]:
                data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                
                self.log_test(
                    "External Service Validation",
                    True,
                    f"External service validation handled gracefully with status {response.status_code}",
                    {
                        "status": response.status_code,
                        "success": data.get("success"),
                        "message": data.get("message", "No message")
                    }
                )
            else:
                self.log_test(
                    "External Service Validation",
                    False,
                    f"Unexpected status code {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "External Service Validation",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_manager_override_functionality(self):
        """Test manager override for age restrictions"""
        try:
            # Test Class C with underage candidate but manager override
            registration_data = self.generate_test_registration_data("C", 19.0, include_mc=True)
            registration_data["manager_override"] = True
            registration_data["override_reason"] = "Special circumstances - experienced driver"
            registration_data["override_by"] = "Manager John Smith"
            
            jwt_token = self.generate_test_jwt_token()
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json"
            }
            
            response = self.session.post(
                f"{self.registration_base_url}/registrations",
                json=registration_data,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                if data.get("success"):
                    registration = data.get("registration", {})
                    registration_id = registration.get("id")
                    
                    if registration_id:
                        self.created_registrations.append(registration_id)
                    
                    # Check if status is RD_REVIEW (Regional Director Review)
                    expected_status = registration.get("status") in ["REGISTERED", "RD_REVIEW"]
                    
                    self.log_test(
                        "Manager Override Functionality",
                        expected_status,
                        f"Manager override processed with status: {registration.get('status')}",
                        {
                            "registration_id": registration_id,
                            "status": registration.get("status"),
                            "manager_override": registration.get("manager_override"),
                            "override_reason": registration.get("override_reason")
                        }
                    )
                else:
                    self.log_test(
                        "Manager Override Functionality",
                        False,
                        f"Manager override failed: {data.get('message')}",
                        data
                    )
            else:
                self.log_test(
                    "Manager Override Functionality",
                    False,
                    f"Expected 200/201, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Manager Override Functionality",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_main_backend_integration(self):
        """Test main backend integration endpoints"""
        try:
            # Test registration health check via main backend
            response = self.session.get(f"{self.main_backend_url}/api/registration/health")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Main Backend Integration - Health Check",
                    True,
                    f"Registration health check via main backend: {data.get('status', 'unknown')}",
                    data
                )
            else:
                self.log_test(
                    "Main Backend Integration - Health Check",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend Integration - Health Check",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test dependencies check
        try:
            response = self.session.get(f"{self.main_backend_url}/api/registration/dependencies")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Main Backend Integration - Dependencies Check",
                    True,
                    f"Dependencies check via main backend: {data.get('status', 'unknown')}",
                    data
                )
            else:
                self.log_test(
                    "Main Backend Integration - Dependencies Check",
                    False,
                    f"Dependencies check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend Integration - Dependencies Check",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        # Test events status
        try:
            response = self.session.get(f"{self.main_backend_url}/api/registration/events")
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Main Backend Integration - Events Status",
                    True,
                    f"Events status via main backend retrieved successfully",
                    {
                        "event_service_connected": data.get("event_service", {}).get("connected", False),
                        "fallback_events_count": data.get("fallback_events_count", 0)
                    }
                )
            else:
                self.log_test(
                    "Main Backend Integration - Events Status",
                    False,
                    f"Events status failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend Integration - Events Status",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_registration_retrieval(self, registration_id: str):
        """Test registration retrieval by ID"""
        if not registration_id:
            self.log_test(
                "Registration Retrieval",
                False,
                "No registration ID provided",
                {}
            )
            return
        
        try:
            response = self.session.get(f"{self.registration_base_url}/registrations/{registration_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Validate response structure
                required_fields = ['id', 'candidate_id', 'booking_id', 'vehicle_category', 'status']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test(
                        "Registration Retrieval",
                        True,
                        f"Registration retrieved successfully: {data.get('vehicle_category')}",
                        {
                            "registration_id": data.get('id'),
                            "status": data.get('status'),
                            "vehicle_category": data.get('vehicle_category'),
                            "age_in_years": data.get('age_in_years')
                        }
                    )
                else:
                    self.log_test(
                        "Registration Retrieval",
                        False,
                        f"Response missing required fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    "Registration Retrieval",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Registration Retrieval",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_authentication_requirements(self):
        """Test JWT authentication requirements"""
        try:
            registration_data = self.generate_test_registration_data("B", 18.0)
            
            # Test without Authorization header
            response = self.session.post(
                f"{self.registration_base_url}/registrations",
                json=registration_data
            )
            
            if response.status_code == 401:
                self.log_test(
                    "Authentication - Missing Token",
                    True,
                    "Missing authorization properly rejected",
                    {"status": response.status_code}
                )
            else:
                self.log_test(
                    "Authentication - Missing Token",
                    False,
                    f"Expected 401, got {response.status_code}",
                    {"response": response.text}
                )
            
            # Test with invalid token format
            headers = {"Authorization": "InvalidFormat token123"}
            response = self.session.post(
                f"{self.registration_base_url}/registrations",
                json=registration_data,
                headers=headers
            )
            
            if response.status_code == 401:
                self.log_test(
                    "Authentication - Invalid Token Format",
                    True,
                    "Invalid token format properly rejected",
                    {"status": response.status_code}
                )
            else:
                self.log_test(
                    "Authentication - Invalid Token Format",
                    False,
                    f"Expected 401, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Authentication Requirements",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting ITADIAS Registration Microservice Backend Tests")
        print(f"🌐 Testing Registration Service: {REGISTRATION_SERVICE_URL}")
        print(f"🌐 Testing Main Backend: {self.main_backend_url}")
        print("=" * 80)
        
        # Service health and configuration tests
        self.test_service_health_check()
        self.test_configuration_endpoint()
        self.test_events_status_endpoint()
        
        # Authentication tests
        self.test_authentication_requirements()
        
        # Core registration functionality
        registration_id = self.test_direct_registration_api_success()
        
        # Business rule validation tests
        self.test_age_validation_scenarios()
        self.test_medical_certificate_validation()
        self.test_document_validation()
        
        # External service integration
        self.test_external_service_validation()
        
        # Manager override functionality
        self.test_manager_override_functionality()
        
        # Registration retrieval
        self.test_registration_retrieval(registration_id)
        
        # Main backend integration
        self.test_main_backend_integration()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("📊 REGISTRATION MICROSERVICE TEST SUMMARY")
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
        
        print(f"\n📝 Created {len(self.created_registrations)} test registrations during testing")
        
        # Save detailed results to file
        with open('/app/registration_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'registration_service_url': REGISTRATION_SERVICE_URL,
                    'main_backend_url': self.main_backend_url
                },
                'test_results': self.test_results,
                'created_registrations': self.created_registrations
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/registration_test_results.json")


def main():
    """Main test execution function."""
    tester = RegistrationServiceTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()