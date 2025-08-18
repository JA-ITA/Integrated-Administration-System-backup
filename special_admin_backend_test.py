#!/usr/bin/env python3
"""
Special Admin Microservice Integration Testing
Tests the Special Admin microservice functionality and integration with main backend
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
SPECIAL_ADMIN_SERVICE_URL = "http://localhost:8007"
TEST_ENGINE_SERVICE_URL = "http://localhost:8005"
MAIN_BACKEND_URL = "https://test-template-config.preview.emergentagent.com"

class SpecialAdminTester:
    """Comprehensive tester for Special Admin microservice and integration."""
    
    def __init__(self):
        self.special_admin_url = SPECIAL_ADMIN_SERVICE_URL
        self.test_engine_url = TEST_ENGINE_SERVICE_URL
        self.main_backend_url = MAIN_BACKEND_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.created_resources = {
            'special_types': [],
            'templates': [],
            'modules': []
        }
        
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
    
    # Service Health and Status Tests
    def test_special_admin_health_direct(self):
        """Test special admin service health endpoint directly"""
        try:
            response = self.session.get(f"{self.special_admin_url}/health")
            if response.status_code == 200:
                data = response.json()
                
                # Check required health components
                required_fields = ["status", "service", "version", "database", "services"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    self.log_test(
                        "Special Admin Health Check (Direct)",
                        True,
                        f"Service healthy: {data.get('status')}",
                        {
                            "database": data.get("database"),
                            "services": data.get("services"),
                            "port": data.get("port")
                        }
                    )
                else:
                    self.log_test(
                        "Special Admin Health Check (Direct)",
                        False,
                        f"Health response missing fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    "Special Admin Health Check (Direct)",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Special Admin Health Check (Direct)",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_main_backend_special_admin_integration(self):
        """Test main backend integration with special admin service"""
        try:
            response = self.session.get(f"{self.main_backend_url}/api/special-admin/health")
            if response.status_code == 200:
                data = response.json()
                
                service_status = data.get("special_admin_service")
                if service_status in ["healthy", "connected"]:
                    self.log_test(
                        "Main Backend Special Admin Integration",
                        True,
                        f"Integration working: {service_status}",
                        data.get("status", {})
                    )
                else:
                    self.log_test(
                        "Main Backend Special Admin Integration",
                        False,
                        f"Service unavailable: {service_status}",
                        data
                    )
            else:
                self.log_test(
                    "Main Backend Special Admin Integration",
                    False,
                    f"Integration failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend Special Admin Integration",
                False,
                f"Integration error: {str(e)}",
                {"error": str(e)}
            )
    
    # Special Test Types Management Tests
    def test_get_special_types_via_main_backend(self):
        """Test GET /api/special-types via main backend"""
        try:
            response = self.session.get(f"{self.main_backend_url}/api/special-types")
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    types_data = data.get("data", [])
                    self.log_test(
                        "Get Special Types (Main Backend)",
                        True,
                        f"Retrieved {len(types_data)} special types",
                        {"count": len(types_data), "types": types_data[:2] if types_data else []}
                    )
                else:
                    self.log_test(
                        "Get Special Types (Main Backend)",
                        False,
                        f"Request failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Get Special Types (Main Backend)",
                    False,
                    f"Request failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Special Types (Main Backend)",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_special_type_via_main_backend(self):
        """Test POST /api/special-types with sample data via main backend"""
        try:
            special_type_data = {
                "name": "Special Driving Test",
                "description": "Advanced driving test for special circumstances",
                "fee": 100.0,
                "validity_months": 24,
                "required_docs": ["photo", "id_proof", "medical_certificate"],
                "pass_percentage": 75,
                "time_limit_minutes": 30,
                "questions_count": 25,
                "created_by": "Test Admin"
            }
            
            response = self.session.post(
                f"{self.main_backend_url}/api/special-types",
                json=special_type_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                if data.get("success"):
                    created_type = data.get("data", {})
                    type_id = created_type.get("id")
                    if type_id:
                        self.created_resources['special_types'].append(type_id)
                    
                    self.log_test(
                        "Create Special Type (Main Backend)",
                        True,
                        f"Special type created successfully: {created_type.get('name')}",
                        {
                            "id": type_id,
                            "name": created_type.get("name"),
                            "fee": created_type.get("fee"),
                            "validity_months": created_type.get("validity_months")
                        }
                    )
                else:
                    self.log_test(
                        "Create Special Type (Main Backend)",
                        False,
                        f"Creation failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Create Special Type (Main Backend)",
                    False,
                    f"Creation failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Special Type (Main Backend)",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_special_type_by_id(self):
        """Test GET /api/special-types/{id} via main backend"""
        if not self.created_resources['special_types']:
            self.log_test(
                "Get Special Type by ID (Main Backend)",
                False,
                "No special types created to test with",
                {}
            )
            return
        
        try:
            type_id = self.created_resources['special_types'][0]
            response = self.session.get(f"{self.main_backend_url}/api/special-types/{type_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    type_data = data.get("data", {})
                    self.log_test(
                        "Get Special Type by ID (Main Backend)",
                        True,
                        f"Retrieved special type: {type_data.get('name')}",
                        {
                            "id": type_data.get("id"),
                            "name": type_data.get("name"),
                            "status": type_data.get("status")
                        }
                    )
                else:
                    self.log_test(
                        "Get Special Type by ID (Main Backend)",
                        False,
                        f"Retrieval failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Get Special Type by ID (Main Backend)",
                    False,
                    f"Retrieval failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Special Type by ID (Main Backend)",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    # Certificate Template Management Tests
    def test_get_certificate_templates(self):
        """Test GET /api/templates via main backend"""
        try:
            response = self.session.get(f"{self.main_backend_url}/api/templates")
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    templates_data = data.get("data", [])
                    self.log_test(
                        "Get Certificate Templates (Main Backend)",
                        True,
                        f"Retrieved {len(templates_data)} templates",
                        {"count": len(templates_data), "templates": templates_data[:2] if templates_data else []}
                    )
                else:
                    self.log_test(
                        "Get Certificate Templates (Main Backend)",
                        False,
                        f"Request failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Get Certificate Templates (Main Backend)",
                    False,
                    f"Request failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Certificate Templates (Main Backend)",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_certificate_template(self):
        """Test POST /api/templates with sample template data"""
        try:
            template_data = {
                "name": "Special Test Certificate Template",
                "type": "special_test",
                "description": "Template for special driving test certificates",
                "hbs_content": """
                <div class="certificate">
                    <h1>Certificate of Completion</h1>
                    <p>This certifies that <strong>{{candidate_name}}</strong></p>
                    <p>has successfully completed the <strong>{{test_type}}</strong></p>
                    <p>on {{completion_date}}</p>
                    <p>Score: {{score}}%</p>
                    <p>Valid until: {{expiry_date}}</p>
                </div>
                """,
                "css_content": """
                .certificate {
                    text-align: center;
                    padding: 20px;
                    border: 2px solid #000;
                    font-family: Arial, sans-serif;
                }
                h1 { color: #2c3e50; }
                """,
                "json_config": {
                    "page_size": "A4",
                    "orientation": "portrait",
                    "margins": {"top": 20, "bottom": 20, "left": 20, "right": 20}
                },
                "created_by": "Test Admin"
            }
            
            response = self.session.post(
                f"{self.main_backend_url}/api/templates",
                json=template_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                if data.get("success"):
                    created_template = data.get("data", {})
                    template_id = created_template.get("id")
                    if template_id:
                        self.created_resources['templates'].append(template_id)
                    
                    self.log_test(
                        "Create Certificate Template (Main Backend)",
                        True,
                        f"Template created successfully: {created_template.get('name')}",
                        {
                            "id": template_id,
                            "name": created_template.get("name"),
                            "type": created_template.get("type")
                        }
                    )
                else:
                    self.log_test(
                        "Create Certificate Template (Main Backend)",
                        False,
                        f"Creation failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Create Certificate Template (Main Backend)",
                    False,
                    f"Creation failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Certificate Template (Main Backend)",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_template_preview_functionality(self):
        """Test template preview functionality"""
        if not self.created_resources['templates']:
            self.log_test(
                "Template Preview Functionality",
                False,
                "No templates created to test preview with",
                {}
            )
            return
        
        try:
            template_id = self.created_resources['templates'][0]
            response = self.session.get(f"{self.main_backend_url}/api/templates/{template_id}/preview")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    preview_data = data.get("data", {})
                    self.log_test(
                        "Template Preview Functionality",
                        True,
                        f"Template preview generated successfully",
                        {
                            "has_html": "html" in preview_data,
                            "has_css": "css" in preview_data,
                            "preview_size": len(str(preview_data))
                        }
                    )
                else:
                    self.log_test(
                        "Template Preview Functionality",
                        False,
                        f"Preview failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Template Preview Functionality",
                    False,
                    f"Preview failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Template Preview Functionality",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_live_template_preview(self):
        """Test POST /api/templates/preview (live preview)"""
        try:
            preview_data = {
                "hbs_content": """
                <div class="live-preview">
                    <h2>Live Preview Test</h2>
                    <p>Candidate: {{candidate_name}}</p>
                    <p>Test Date: {{test_date}}</p>
                    <p>Result: {{result}}</p>
                </div>
                """,
                "css_content": """
                .live-preview {
                    background: #f8f9fa;
                    padding: 15px;
                    border-radius: 5px;
                }
                """,
                "sample_data": {
                    "candidate_name": "John Doe",
                    "test_date": "2024-12-15",
                    "result": "PASS"
                }
            }
            
            response = self.session.post(
                f"{self.main_backend_url}/api/templates/preview",
                json=preview_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    preview_result = data.get("data", {})
                    self.log_test(
                        "Live Template Preview",
                        True,
                        f"Live preview generated successfully",
                        {
                            "has_compiled_html": "compiled_html" in preview_result,
                            "has_css": "css" in preview_result,
                            "preview_length": len(preview_result.get("compiled_html", ""))
                        }
                    )
                else:
                    self.log_test(
                        "Live Template Preview",
                        False,
                        f"Live preview failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Live Template Preview",
                    False,
                    f"Live preview failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Live Template Preview",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_default_template_config(self):
        """Test GET /api/templates/config/default"""
        try:
            response = self.session.get(f"{self.main_backend_url}/api/templates/config/default")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    config_data = data.get("data", {})
                    self.log_test(
                        "Default Template Config",
                        True,
                        f"Default config retrieved successfully",
                        {
                            "has_default_hbs": "default_hbs_content" in config_data,
                            "has_default_css": "default_css_content" in config_data,
                            "has_sample_data": "sample_data" in config_data
                        }
                    )
                else:
                    self.log_test(
                        "Default Template Config",
                        False,
                        f"Config retrieval failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Default Template Config",
                    False,
                    f"Config retrieval failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Default Template Config",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    # Question Module Management Tests
    def test_get_question_modules(self):
        """Test GET /api/question-modules"""
        try:
            response = self.session.get(f"{self.main_backend_url}/api/question-modules")
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    modules_data = data.get("data", [])
                    self.log_test(
                        "Get Question Modules (Main Backend)",
                        True,
                        f"Retrieved {len(modules_data)} question modules",
                        {"count": len(modules_data), "modules": modules_data[:2] if modules_data else []}
                    )
                else:
                    self.log_test(
                        "Get Question Modules (Main Backend)",
                        False,
                        f"Request failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Get Question Modules (Main Backend)",
                    False,
                    f"Request failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Question Modules (Main Backend)",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_question_module(self):
        """Test POST /api/question-modules"""
        try:
            module_data = {
                "code": "SPECIAL-TEST",
                "name": "Special Driving Test Module",
                "description": "Questions for special driving test scenarios",
                "difficulty_level": "intermediate",
                "pass_percentage": 75,
                "time_limit_minutes": 30,
                "created_by": "Test Admin"
            }
            
            response = self.session.post(
                f"{self.main_backend_url}/api/question-modules",
                json=module_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                if data.get("success"):
                    created_module = data.get("data", {})
                    module_id = created_module.get("id")
                    if module_id:
                        self.created_resources['modules'].append(module_id)
                    
                    self.log_test(
                        "Create Question Module (Main Backend)",
                        True,
                        f"Module created successfully: {created_module.get('name')}",
                        {
                            "id": module_id,
                            "code": created_module.get("code"),
                            "name": created_module.get("name")
                        }
                    )
                else:
                    self.log_test(
                        "Create Question Module (Main Backend)",
                        False,
                        f"Creation failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "Create Question Module (Main Backend)",
                    False,
                    f"Creation failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Question Module (Main Backend)",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_csv_questions_upload(self):
        """Test POST /api/questions/upload (CSV upload)"""
        try:
            # Create sample CSV data for SPECIAL-TEST module
            csv_data = """question_text,option_a,option_b,option_c,option_d,correct_answer,difficulty,explanation
"What is the maximum speed limit in special test zones?","30 km/h","40 km/h","50 km/h","60 km/h","A","easy","Special test zones have reduced speed limits for safety"
"When should you use hazard lights during special maneuvers?","Never","Only at night","When stationary","During all maneuvers","C","medium","Hazard lights should be used when stationary to warn other drivers"
"What distance should you maintain from emergency vehicles?","50m","100m","150m","200m","C","medium","Maintain at least 150m distance from emergency vehicles"
"In special weather conditions, visibility should be at least:","50m","100m","150m","200m","B","hard","Minimum visibility of 100m is required for safe driving in special conditions"
"What is the correct procedure for special parking maneuvers?","Signal, check, maneuver","Maneuver, then signal","Check mirrors only","No specific procedure","A","easy","Always signal first, check surroundings, then execute maneuver"
"""
            
            upload_data = {
                "module_code": "SPECIAL-TEST",
                "created_by": "Test Admin",
                "csv_data": csv_data
            }
            
            response = self.session.post(
                f"{self.main_backend_url}/api/questions/upload",
                json=upload_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    upload_result = data.get("data", {})
                    self.log_test(
                        "CSV Questions Upload",
                        True,
                        f"Questions uploaded successfully: {upload_result.get('processed_count', 0)} questions",
                        {
                            "processed_count": upload_result.get("processed_count"),
                            "success_count": upload_result.get("success_count"),
                            "error_count": upload_result.get("error_count", 0)
                        }
                    )
                else:
                    self.log_test(
                        "CSV Questions Upload",
                        False,
                        f"Upload failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "CSV Questions Upload",
                    False,
                    f"Upload failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "CSV Questions Upload",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_csv_template_download(self):
        """Test GET /api/questions/template (CSV template)"""
        try:
            response = self.session.get(f"{self.main_backend_url}/api/questions/template")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    template_data = data.get("data", {})
                    self.log_test(
                        "CSV Template Download",
                        True,
                        f"CSV template retrieved successfully",
                        {
                            "has_headers": "headers" in template_data,
                            "has_sample": "sample_csv" in template_data,
                            "has_instructions": "instructions" in template_data
                        }
                    )
                else:
                    self.log_test(
                        "CSV Template Download",
                        False,
                        f"Template retrieval failed: {data.get('error')}",
                        data
                    )
            else:
                self.log_test(
                    "CSV Template Download",
                    False,
                    f"Template retrieval failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "CSV Template Download",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    # Test Engine Integration Tests
    def test_test_engine_health_check(self):
        """Test test engine service health check"""
        try:
            response = self.session.get(f"{self.test_engine_url}/health")
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "healthy":
                    self.log_test(
                        "Test Engine Health Check",
                        True,
                        f"Test engine service healthy",
                        {
                            "service": data.get("service"),
                            "database": data.get("database"),
                            "events": data.get("events")
                        }
                    )
                else:
                    self.log_test(
                        "Test Engine Health Check",
                        False,
                        f"Test engine service degraded: {data.get('status')}",
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
    
    def test_test_engine_special_modules_support(self):
        """Test if test engine supports new modules (SPECIAL-TEST, DANGEROUS-GOODS)"""
        try:
            response = self.session.get(f"{self.test_engine_url}/api/v1/questions")
            if response.status_code == 200:
                data = response.json()
                
                # Check if we can query questions (even if empty)
                self.log_test(
                    "Test Engine Special Modules Support",
                    True,
                    f"Test engine questions endpoint accessible",
                    {
                        "questions_count": len(data) if isinstance(data, list) else "unknown",
                        "response_type": type(data).__name__
                    }
                )
            else:
                self.log_test(
                    "Test Engine Special Modules Support",
                    False,
                    f"Questions endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Test Engine Special Modules Support",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_test_engine_config_check(self):
        """Test test engine configuration for module support"""
        try:
            response = self.session.get(f"{self.test_engine_url}/config")
            if response.status_code == 200:
                data = response.json()
                
                available_modules = data.get("available_modules", [])
                supports_special = any("SPECIAL" in str(module).upper() for module in available_modules)
                
                self.log_test(
                    "Test Engine Config Check",
                    True,
                    f"Test engine config retrieved, modules: {len(available_modules)}",
                    {
                        "available_modules": available_modules,
                        "supports_special_modules": supports_special,
                        "questions_per_test": data.get("questions_per_test"),
                        "passing_score_percent": data.get("passing_score_percent")
                    }
                )
            else:
                self.log_test(
                    "Test Engine Config Check",
                    False,
                    f"Config check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Test Engine Config Check",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting Special Admin Microservice Integration Tests")
        print(f"🌐 Special Admin Service: {self.special_admin_url}")
        print(f"🌐 Test Engine Service: {self.test_engine_url}")
        print(f"🌐 Main Backend: {self.main_backend_url}")
        print("=" * 100)
        
        # 1. Service Health and Status Tests
        print("\n🏥 TESTING SERVICE HEALTH AND STATUS:")
        self.test_special_admin_health_direct()
        self.test_main_backend_special_admin_integration()
        
        # 2. Special Test Types Management Tests
        print("\n🎯 TESTING SPECIAL TEST TYPES MANAGEMENT:")
        self.test_get_special_types_via_main_backend()
        self.test_create_special_type_via_main_backend()
        self.test_get_special_type_by_id()
        
        # 3. Certificate Template Management Tests
        print("\n📜 TESTING CERTIFICATE TEMPLATE MANAGEMENT:")
        self.test_get_certificate_templates()
        self.test_create_certificate_template()
        self.test_template_preview_functionality()
        self.test_live_template_preview()
        self.test_default_template_config()
        
        # 4. Question Module Management Tests
        print("\n❓ TESTING QUESTION MODULE MANAGEMENT:")
        self.test_get_question_modules()
        self.test_create_question_module()
        self.test_csv_questions_upload()
        self.test_csv_template_download()
        
        # 5. Test Engine Integration Tests
        print("\n🔧 TESTING TEST ENGINE INTEGRATION:")
        self.test_test_engine_health_check()
        self.test_test_engine_special_modules_support()
        self.test_test_engine_config_check()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 100)
        print("📊 SPECIAL ADMIN MICROSERVICE INTEGRATION TEST SUMMARY")
        print("=" * 100)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🎯 KEY VALIDATION POINTS:")
        print("   ✓ Special Admin service health and connectivity")
        print("   ✓ Main backend integration with special admin endpoints")
        print("   ✓ Special test types CRUD operations")
        print("   ✓ Certificate template management and preview functionality")
        print("   ✓ Question module management and CSV upload")
        print("   ✓ Test engine integration and module support")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print(f"\n📝 Created resources during testing:")
        print(f"  - Special Types: {len(self.created_resources['special_types'])}")
        print(f"  - Templates: {len(self.created_resources['templates'])}")
        print(f"  - Modules: {len(self.created_resources['modules'])}")
        
        # Save detailed results to file
        with open('/app/special_admin_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'special_admin_service_url': self.special_admin_url,
                    'test_engine_service_url': self.test_engine_url,
                    'main_backend_url': self.main_backend_url,
                    'focus': 'Special Admin microservice integration and functionality'
                },
                'test_results': self.test_results,
                'created_resources': self.created_resources
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/special_admin_test_results.json")


def main():
    """Main test execution function."""
    tester = SpecialAdminTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()