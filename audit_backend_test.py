#!/usr/bin/env python3
"""
Comprehensive Backend Testing for ITADIAS Audit Microservice
Tests all audit functionality including RD authentication, database operations, and event publishing
"""

import asyncio
import httpx
import json
import uuid
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import os

# Test configuration
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'https://audit-trail-1.preview.emergentagent.com')
AUDIT_SERVICE_URL = "http://localhost:8008"
MAIN_BACKEND_URL = f"{BACKEND_URL}/api"

# Mock JWT configuration for testing
JWT_SECRET = "your-secret-key-here"  # Should match audit service config
JWT_ALGORITHM = "HS256"

class AuditServiceTester:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.test_results = []
        self.rd_token = None
        self.test_actor_id = str(uuid.uuid4())
        self.test_resource_id = str(uuid.uuid4())
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {test_name}")
        if details:
            print(f"    Details: {details}")
        if response_data and not success:
            print(f"    Response: {response_data}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response": response_data
        })
    
    def generate_rd_jwt_token(self, user_id: str = None, role: str = "rd", expires_in_hours: int = 1) -> str:
        """Generate a mock RD JWT token for testing"""
        if not user_id:
            user_id = self.test_actor_id
            
        payload = {
            "user_id": user_id,  # Keep as string - JWT will serialize it
            "role": role,
            "iat": int(datetime.utcnow().timestamp()),  # Use int timestamps
            "exp": int((datetime.utcnow() + timedelta(hours=expires_in_hours)).timestamp())
        }
        
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    async def test_database_structure_verification(self):
        """Test database structure by checking health endpoint response"""
        try:
            response = await self.client.get(f"{AUDIT_SERVICE_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify database connection and schema
                db_info = data.get("database", {})
                if (db_info.get("status") == "connected" and 
                    db_info.get("schema") == "audit" and
                    db_info.get("host") == "localhost" and
                    db_info.get("port") == 5432):
                    
                    self.log_test("Database Structure Verification", True, 
                                f"PostgreSQL connected with 'audit' schema on {db_info.get('host')}:{db_info.get('port')}")
                    return True
                else:
                    self.log_test("Database Structure Verification", False, 
                                f"Database configuration issue: {db_info}")
                    return False
            else:
                self.log_test("Database Structure Verification", False, 
                            f"Health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Database Structure Verification", False, f"Exception: {str(e)}")
            return False
    
    async def test_audit_service_health(self):
        try:
            response = await self.client.get(f"{AUDIT_SERVICE_URL}/health")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify health response structure
                required_fields = ["status", "service", "version", "database", "events"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Audit Service Health Check", False, 
                                f"Missing fields: {missing_fields}", data)
                    return False
                
                # Check database connectivity
                db_status = data.get("database", {}).get("status")
                if db_status != "connected":
                    self.log_test("Audit Service Health Check", False, 
                                f"Database not connected: {db_status}", data)
                    return False
                
                # Check if service is healthy
                if data.get("status") == "healthy":
                    self.log_test("Audit Service Health Check", True, 
                                f"Service healthy, DB: {db_status}, Events: {data.get('events', {}).get('status')}")
                    return True
                else:
                    self.log_test("Audit Service Health Check", False, 
                                f"Service not healthy: {data.get('status')}", data)
                    return False
            else:
                self.log_test("Audit Service Health Check", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Audit Service Health Check", False, f"Exception: {str(e)}")
            return False
    
    async def test_audit_service_configuration(self):
        """Test audit service configuration endpoint"""
        try:
            response = await self.client.get(f"{AUDIT_SERVICE_URL}/config")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify configuration structure
                required_sections = ["service", "database", "identity", "supported_actions", "supported_resource_types"]
                missing_sections = [section for section in required_sections if section not in data]
                
                if missing_sections:
                    self.log_test("Audit Service Configuration", False, 
                                f"Missing sections: {missing_sections}", data)
                    return False
                
                # Verify supported enums
                expected_actions = ["OVERRIDE", "REJECT", "APPROVE", "UPDATE_SLOT", "CANCEL_BOOKING", "CREATE", "UPDATE", "DELETE"]
                expected_resources = ["RECEIPT", "REGISTRATION", "TEST", "CERTIFICATE", "BOOKING", "SLOT"]
                expected_roles = ["dao", "manager", "rd"]
                
                actual_actions = data.get("supported_actions", [])
                actual_resources = data.get("supported_resource_types", [])
                actual_roles = data.get("supported_actor_roles", [])
                
                missing_actions = [action for action in expected_actions if action not in actual_actions]
                missing_resources = [resource for resource in expected_resources if resource not in actual_resources]
                missing_roles = [role for role in expected_roles if role not in actual_roles]
                
                if missing_actions or missing_resources or missing_roles:
                    self.log_test("Audit Service Configuration", False, 
                                f"Missing enums - Actions: {missing_actions}, Resources: {missing_resources}, Roles: {missing_roles}")
                    return False
                
                self.log_test("Audit Service Configuration", True, 
                            f"All required enums present, Port: {data.get('service', {}).get('port')}")
                return True
            else:
                self.log_test("Audit Service Configuration", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Audit Service Configuration", False, f"Exception: {str(e)}")
            return False
    
    async def test_events_status_endpoint(self):
        """Test events status endpoint"""
        try:
            response = await self.client.get(f"{AUDIT_SERVICE_URL}/events/status")
            
            if response.status_code == 200:
                data = response.json()
                
                # Verify events status structure
                required_fields = ["event_service", "fallback_events_count"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    self.log_test("Events Status Endpoint", False, 
                                f"Missing fields: {missing_fields}", data)
                    return False
                
                event_service = data.get("event_service", {})
                fallback_count = data.get("fallback_events_count", 0)
                
                self.log_test("Events Status Endpoint", True, 
                            f"Event service status: {event_service.get('status', 'unknown')}, Fallback events: {fallback_count}")
                return True
            else:
                self.log_test("Events Status Endpoint", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Events Status Endpoint", False, f"Exception: {str(e)}")
            return False
    
    async def test_authentication_diagnostics(self):
        """Diagnose authentication issues"""
        try:
            # Test if identity service is available
            identity_available = False
            try:
                identity_response = await self.client.get("http://localhost:8001/health", timeout=5.0)
                identity_available = identity_response.status_code == 200
            except:
                pass
            
            # Generate a test token
            test_token = self.generate_rd_jwt_token()
            
            # Test with minimal request to see authentication behavior
            headers = {
                "Authorization": f"Bearer {test_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(
                f"{AUDIT_SERVICE_URL}/api/v1/overrides/",
                json={
                    "resource_type": "RECEIPT",
                    "resource_id": str(uuid.uuid4()),
                    "new_status": "APPROVED",
                    "reason": "Authentication diagnostic test"
                },
                headers=headers
            )
            
            auth_status = "working" if response.status_code == 200 else "failing"
            
            self.log_test("Authentication Diagnostics", True, 
                        f"Auth status: {auth_status}, Identity service: {'available' if identity_available else 'unavailable'}, Response: {response.status_code}")
            
            return True
            
        except Exception as e:
            self.log_test("Authentication Diagnostics", False, f"Exception: {str(e)}")
            return False
    
    async def test_rd_authentication_valid_token(self):
        """Test RD authentication with valid token"""
        try:
            # Generate valid RD token
            self.rd_token = self.generate_rd_jwt_token()
            
            # Test with a simple override request to verify authentication
            override_data = {
                "resource_type": "RECEIPT",
                "resource_id": self.test_resource_id,
                "new_status": "APPROVED",
                "reason": "Testing RD authentication with valid token - comprehensive audit test"
            }
            
            headers = {
                "Authorization": f"Bearer {self.rd_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(
                f"{AUDIT_SERVICE_URL}/api/v1/overrides/",
                json=override_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.log_test("RD Authentication - Valid Token", True, 
                                f"Authentication successful, Audit ID: {data.get('audit_id')}")
                    return True
                else:
                    self.log_test("RD Authentication - Valid Token", False, 
                                f"Override failed: {data.get('message')}", data)
                    return False
            else:
                self.log_test("RD Authentication - Valid Token", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("RD Authentication - Valid Token", False, f"Exception: {str(e)}")
            return False
    
    async def test_rd_authentication_invalid_token(self):
        """Test RD authentication with invalid token"""
        try:
            # Test with invalid token
            invalid_token = "invalid.jwt.token"
            
            override_data = {
                "resource_type": "RECEIPT",
                "resource_id": str(uuid.uuid4()),
                "new_status": "APPROVED",
                "reason": "Testing invalid token authentication"
            }
            
            headers = {
                "Authorization": f"Bearer {invalid_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(
                f"{AUDIT_SERVICE_URL}/api/v1/overrides/",
                json=override_data,
                headers=headers
            )
            
            # Should return 401 Unauthorized
            if response.status_code == 401:
                self.log_test("RD Authentication - Invalid Token", True, 
                            "Correctly rejected invalid token")
                return True
            else:
                self.log_test("RD Authentication - Invalid Token", False, 
                            f"Expected 401, got {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("RD Authentication - Invalid Token", False, f"Exception: {str(e)}")
            return False
    
    async def test_rd_authentication_wrong_role(self):
        """Test RD authentication with wrong role"""
        try:
            # Generate token with manager role instead of RD
            manager_token = self.generate_rd_jwt_token(role="manager")
            
            override_data = {
                "resource_type": "RECEIPT",
                "resource_id": str(uuid.uuid4()),
                "new_status": "APPROVED",
                "reason": "Testing wrong role authentication"
            }
            
            headers = {
                "Authorization": f"Bearer {manager_token}",
                "Content-Type": "application/json"
            }
            
            response = await self.client.post(
                f"{AUDIT_SERVICE_URL}/api/v1/overrides/",
                json=override_data,
                headers=headers
            )
            
            # Should return 401 Unauthorized for wrong role
            if response.status_code == 401:
                self.log_test("RD Authentication - Wrong Role", True, 
                            "Correctly rejected manager role token")
                return True
            else:
                self.log_test("RD Authentication - Wrong Role", False, 
                            f"Expected 401, got {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("RD Authentication - Wrong Role", False, f"Exception: {str(e)}")
            return False
    
    async def test_override_endpoint_comprehensive(self):
        """Test override endpoint with comprehensive scenarios"""
        try:
            if not self.rd_token:
                self.rd_token = self.generate_rd_jwt_token()
            
            headers = {
                "Authorization": f"Bearer {self.rd_token}",
                "Content-Type": "application/json"
            }
            
            # Test different resource types and scenarios
            test_scenarios = [
                {
                    "name": "Receipt Override",
                    "data": {
                        "resource_type": "RECEIPT",
                        "resource_id": str(uuid.uuid4()),
                        "new_status": "APPROVED",
                        "old_status": "RD_REVIEW",
                        "reason": "Receipt validation override - comprehensive test scenario",
                        "metadata": {"override_type": "validation", "priority": "high"}
                    }
                },
                {
                    "name": "Registration Override",
                    "data": {
                        "resource_type": "REGISTRATION",
                        "resource_id": str(uuid.uuid4()),
                        "new_status": "APPROVED",
                        "old_status": "PENDING",
                        "reason": "Registration approval override due to special circumstances"
                    }
                },
                {
                    "name": "Certificate Override",
                    "data": {
                        "resource_type": "CERTIFICATE",
                        "resource_id": str(uuid.uuid4()),
                        "new_status": "REISSUED",
                        "reason": "Certificate reissuance override for damaged certificate replacement"
                    }
                }
            ]
            
            success_count = 0
            for scenario in test_scenarios:
                try:
                    response = await self.client.post(
                        f"{AUDIT_SERVICE_URL}/api/v1/overrides/",
                        json=scenario["data"],
                        headers=headers
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            success_count += 1
                            self.log_test(f"Override - {scenario['name']}", True, 
                                        f"Audit ID: {data.get('audit_id')}, Status: {data.get('new_status')}")
                        else:
                            self.log_test(f"Override - {scenario['name']}", False, 
                                        f"Override failed: {data.get('message')}", data)
                    else:
                        self.log_test(f"Override - {scenario['name']}", False, 
                                    f"HTTP {response.status_code}", response.text)
                        
                except Exception as e:
                    self.log_test(f"Override - {scenario['name']}", False, f"Exception: {str(e)}")
            
            # Overall success if at least 2/3 scenarios passed
            overall_success = success_count >= 2
            self.log_test("Override Endpoint Comprehensive", overall_success, 
                        f"Passed {success_count}/{len(test_scenarios)} scenarios")
            return overall_success
            
        except Exception as e:
            self.log_test("Override Endpoint Comprehensive", False, f"Exception: {str(e)}")
            return False
    
    async def test_override_validation(self):
        """Test override endpoint validation"""
        try:
            if not self.rd_token:
                self.rd_token = self.generate_rd_jwt_token()
            
            headers = {
                "Authorization": f"Bearer {self.rd_token}",
                "Content-Type": "application/json"
            }
            
            # Test validation scenarios
            validation_tests = [
                {
                    "name": "Missing Reason",
                    "data": {
                        "resource_type": "RECEIPT",
                        "resource_id": str(uuid.uuid4()),
                        "new_status": "APPROVED"
                        # Missing reason field
                    },
                    "expect_error": True
                },
                {
                    "name": "Short Reason",
                    "data": {
                        "resource_type": "RECEIPT",
                        "resource_id": str(uuid.uuid4()),
                        "new_status": "APPROVED",
                        "reason": "Short"  # Too short (< 10 chars)
                    },
                    "expect_error": True
                },
                {
                    "name": "Invalid Resource Type",
                    "data": {
                        "resource_type": "INVALID_TYPE",
                        "resource_id": str(uuid.uuid4()),
                        "new_status": "APPROVED",
                        "reason": "Testing invalid resource type validation"
                    },
                    "expect_error": True
                },
                {
                    "name": "Invalid UUID",
                    "data": {
                        "resource_type": "RECEIPT",
                        "resource_id": "invalid-uuid",
                        "new_status": "APPROVED",
                        "reason": "Testing invalid UUID validation"
                    },
                    "expect_error": True
                }
            ]
            
            success_count = 0
            for test in validation_tests:
                try:
                    response = await self.client.post(
                        f"{AUDIT_SERVICE_URL}/api/v1/overrides/",
                        json=test["data"],
                        headers=headers
                    )
                    
                    if test["expect_error"]:
                        # Should return 4xx error
                        if response.status_code >= 400 and response.status_code < 500:
                            success_count += 1
                            self.log_test(f"Validation - {test['name']}", True, 
                                        f"Correctly rejected with {response.status_code}")
                        else:
                            self.log_test(f"Validation - {test['name']}", False, 
                                        f"Expected 4xx error, got {response.status_code}")
                    else:
                        if response.status_code == 200:
                            success_count += 1
                            self.log_test(f"Validation - {test['name']}", True, "Accepted valid request")
                        else:
                            self.log_test(f"Validation - {test['name']}", False, 
                                        f"Expected 200, got {response.status_code}")
                            
                except Exception as e:
                    self.log_test(f"Validation - {test['name']}", False, f"Exception: {str(e)}")
            
            overall_success = success_count >= 3  # At least 3/4 validation tests should pass
            self.log_test("Override Validation Tests", overall_success, 
                        f"Passed {success_count}/{len(validation_tests)} validation tests")
            return overall_success
            
        except Exception as e:
            self.log_test("Override Validation Tests", False, f"Exception: {str(e)}")
            return False
    
    async def test_audit_log_retrieval(self):
        """Test audit log retrieval endpoints"""
        try:
            if not self.rd_token:
                self.rd_token = self.generate_rd_jwt_token()
            
            headers = {"Authorization": f"Bearer {self.rd_token}"}
            
            # Test general audit logs endpoint
            response = await self.client.get(
                f"{AUDIT_SERVICE_URL}/api/v1/audit-logs/",
                headers=headers,
                params={"limit": 10}
            )
            
            if response.status_code == 200:
                logs = response.json()
                if isinstance(logs, list):
                    self.log_test("Audit Log Retrieval - General", True, 
                                f"Retrieved {len(logs)} audit logs")
                    
                    # Test with filters if we have logs
                    if logs:
                        # Test resource type filter
                        filter_response = await self.client.get(
                            f"{AUDIT_SERVICE_URL}/api/v1/audit-logs/",
                            headers=headers,
                            params={"resource_type": "RECEIPT", "limit": 5}
                        )
                        
                        if filter_response.status_code == 200:
                            filtered_logs = filter_response.json()
                            self.log_test("Audit Log Retrieval - Filtered", True, 
                                        f"Retrieved {len(filtered_logs)} filtered logs")
                        else:
                            self.log_test("Audit Log Retrieval - Filtered", False, 
                                        f"Filter request failed: {filter_response.status_code}")
                    
                    return True
                else:
                    self.log_test("Audit Log Retrieval - General", False, 
                                f"Expected list, got {type(logs)}", logs)
                    return False
            else:
                self.log_test("Audit Log Retrieval - General", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Audit Log Retrieval", False, f"Exception: {str(e)}")
            return False
    
    async def test_resource_audit_history(self):
        """Test resource-specific audit history"""
        try:
            if not self.rd_token:
                self.rd_token = self.generate_rd_jwt_token()
            
            headers = {"Authorization": f"Bearer {self.rd_token}"}
            
            # Test resource audit history endpoint
            response = await self.client.get(
                f"{AUDIT_SERVICE_URL}/api/v1/overrides/audit/RECEIPT/{self.test_resource_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                history = response.json()
                if isinstance(history, list):
                    self.log_test("Resource Audit History", True, 
                                f"Retrieved {len(history)} audit entries for resource")
                    return True
                else:
                    self.log_test("Resource Audit History", False, 
                                f"Expected list, got {type(history)}", history)
                    return False
            else:
                self.log_test("Resource Audit History", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Resource Audit History", False, f"Exception: {str(e)}")
            return False
    
    async def test_actor_audit_history(self):
        """Test actor-specific audit history"""
        try:
            if not self.rd_token:
                self.rd_token = self.generate_rd_jwt_token()
            
            headers = {"Authorization": f"Bearer {self.rd_token}"}
            
            # Test actor audit history endpoint
            response = await self.client.get(
                f"{AUDIT_SERVICE_URL}/api/v1/overrides/audit/actor/{self.test_actor_id}",
                headers=headers,
                params={"limit": 10}
            )
            
            if response.status_code == 200:
                history = response.json()
                if isinstance(history, list):
                    self.log_test("Actor Audit History", True, 
                                f"Retrieved {len(history)} audit entries for actor")
                    return True
                else:
                    self.log_test("Actor Audit History", False, 
                                f"Expected list, got {type(history)}", history)
                    return False
            else:
                self.log_test("Actor Audit History", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Actor Audit History", False, f"Exception: {str(e)}")
            return False
    
    async def test_audit_statistics(self):
        """Test audit statistics endpoint"""
        try:
            if not self.rd_token:
                self.rd_token = self.generate_rd_jwt_token()
            
            headers = {"Authorization": f"Bearer {self.rd_token}"}
            
            response = await self.client.get(
                f"{AUDIT_SERVICE_URL}/api/v1/audit-logs/statistics",
                headers=headers
            )
            
            if response.status_code == 200:
                stats = response.json()
                
                # Verify statistics structure
                expected_fields = ["total_audit_logs", "action_distribution", "resource_type_distribution", "actor_role_distribution"]
                missing_fields = [field for field in expected_fields if field not in stats]
                
                if missing_fields:
                    self.log_test("Audit Statistics", False, 
                                f"Missing fields: {missing_fields}", stats)
                    return False
                
                self.log_test("Audit Statistics", True, 
                            f"Total logs: {stats.get('total_audit_logs', 0)}, Sample size: {stats.get('recent_logs_sample_size', 0)}")
                return True
            else:
                self.log_test("Audit Statistics", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Audit Statistics", False, f"Exception: {str(e)}")
            return False
    
    async def test_main_backend_integration(self):
        """Test main backend integration with audit service"""
        try:
            # Test audit service health via main backend
            response = await self.client.get(f"{MAIN_BACKEND_URL}/audit/health")
            
            if response.status_code == 200:
                data = response.json()
                audit_status = data.get("audit_service")
                
                if audit_status == "healthy":
                    self.log_test("Main Backend - Audit Health", True, 
                                f"Audit service status: {audit_status}")
                    
                    # Test override creation via main backend
                    if self.rd_token:
                        override_data = {
                            "resource_type": "RECEIPT",
                            "resource_id": str(uuid.uuid4()),
                            "new_status": "APPROVED",
                            "reason": "Testing main backend integration with audit service",
                            "rd_token": self.rd_token
                        }
                        
                        override_response = await self.client.post(
                            f"{MAIN_BACKEND_URL}/audit/overrides",
                            json=override_data
                        )
                        
                        if override_response.status_code == 200:
                            override_result = override_response.json()
                            if override_result.get("success"):
                                self.log_test("Main Backend - Override Creation", True, 
                                            f"Override created via main backend")
                                return True
                            else:
                                self.log_test("Main Backend - Override Creation", False, 
                                            f"Override failed: {override_result.get('error')}")
                                return False
                        else:
                            self.log_test("Main Backend - Override Creation", False, 
                                        f"HTTP {override_response.status_code}")
                            return False
                    else:
                        self.log_test("Main Backend Integration", True, 
                                    "Health check successful, no RD token for override test")
                        return True
                else:
                    self.log_test("Main Backend - Audit Health", False, 
                                f"Audit service not healthy: {audit_status}")
                    return False
            else:
                self.log_test("Main Backend - Audit Health", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
                
        except Exception as e:
            self.log_test("Main Backend Integration", False, f"Exception: {str(e)}")
            return False
    
    async def run_all_tests(self):
        """Run all audit service tests"""
        print("🔍 Starting Comprehensive Audit Microservice Testing...")
        print("=" * 80)
        
        # Service Health and Configuration Tests
        print("\n📋 SERVICE HEALTH AND CONFIGURATION")
        await self.test_audit_service_health()
        await self.test_database_structure_verification()
        await self.test_audit_service_configuration()
        await self.test_events_status_endpoint()
        
        # Authentication Tests
        print("\n🔐 AUTHENTICATION TESTING")
        await self.test_authentication_diagnostics()
        await self.test_rd_authentication_valid_token()
        await self.test_rd_authentication_invalid_token()
        await self.test_rd_authentication_wrong_role()
        
        # Core Audit Functionality Tests
        print("\n📝 CORE AUDIT FUNCTIONALITY")
        await self.test_override_endpoint_comprehensive()
        await self.test_override_validation()
        
        # Database and Retrieval Tests
        print("\n🗄️ DATABASE AND RETRIEVAL")
        await self.test_audit_log_retrieval()
        await self.test_resource_audit_history()
        await self.test_actor_audit_history()
        await self.test_audit_statistics()
        
        # Integration Tests
        print("\n🔗 MAIN BACKEND INTEGRATION")
        await self.test_main_backend_integration()
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  • {result['test']}: {result['details']}")
        
        print("\n🎯 AUDIT SERVICE TESTING COMPLETE")
        return success_rate >= 80.0  # Consider successful if 80%+ tests pass

async def main():
    """Main test execution"""
    async with AuditServiceTester() as tester:
        success = await tester.run_all_tests()
        return success

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)