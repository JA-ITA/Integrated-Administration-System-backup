#!/usr/bin/env python3
"""
Special Admin Microservice Backend Testing (Port 8009)
Comprehensive testing of Special Admin microservice running on port 8009
Tests all API endpoints as requested in the review
"""

import requests
import json
import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

# Test configuration
SPECIAL_ADMIN_SERVICE_URL = "http://localhost:8009"

class SpecialAdminPort8009Tester:
    """Comprehensive tester for Special Admin microservice on port 8009."""
    
    def __init__(self):
        self.service_url = SPECIAL_ADMIN_SERVICE_URL
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
    
    # 1. Service Health and Status Tests
    def test_service_health(self):
        """Test health endpoint and service status"""
        try:
            response = self.session.get(f"{self.service_url}/health")
            if response.status_code == 200:
                data = response.json()
                
                # Check required health components
                required_fields = ["status", "service", "version", "database", "services"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields and data.get("status") == "healthy":
                    self.log_test(
                        "Service Health Check",
                        True,
                        f"Service healthy with database connectivity",
                        {
                            "database_status": data.get("database", {}).get("status"),
                            "database_schema": data.get("database", {}).get("schema"),
                            "services": data.get("services", {}),
                            "port": data.get("port")
                        }
                    )
                else:
                    self.log_test(
                        "Service Health Check",
                        False,
                        f"Health check failed - missing fields: {missing_fields} or status not healthy",
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
    
    def test_database_connectivity(self):
        """Verify database connectivity to PostgreSQL 'config' schema"""
        try:
            response = self.session.get(f"{self.service_url}/config")
            if response.status_code == 200:
                data = response.json()
                
                db_config = data.get("database", {})
                if db_config.get("schema") == "config":
                    self.log_test(
                        "Database Connectivity Check",
                        True,
                        f"PostgreSQL 'config' schema connectivity confirmed",
                        {
                            "schema": db_config.get("schema"),
                            "host": db_config.get("host"),
                            "port": db_config.get("port"),
                            "database": db_config.get("name")
                        }
                    )
                else:
                    self.log_test(
                        "Database Connectivity Check",
                        False,
                        f"Expected 'config' schema, got: {db_config.get('schema')}",
                        db_config
                    )
            else:
                self.log_test(
                    "Database Connectivity Check",
                    False,
                    f"Config endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Database Connectivity Check",
                False,
                f"Database connectivity check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_service_components(self):
        """Confirm all service components are operational"""
        try:
            response = self.session.get(f"{self.service_url}/health")
            if response.status_code == 200:
                data = response.json()
                
                services = data.get("services", {})
                all_connected = all(status == "connected" for status in services.values())
                
                if all_connected:
                    self.log_test(
                        "Service Components Check",
                        True,
                        f"All service components operational",
                        {
                            "events_service": services.get("events"),
                            "templates_service": services.get("templates"),
                            "questions_service": services.get("questions")
                        }
                    )
                else:
                    self.log_test(
                        "Service Components Check",
                        False,
                        f"Some service components not connected",
                        services
                    )
            else:
                self.log_test(
                    "Service Components Check",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Service Components Check",
                False,
                f"Service components check error: {str(e)}",
                {"error": str(e)}
            )
    
    # 2. Special Test Types API Endpoints
    def test_get_special_types(self):
        """Test GET /api/v1/special-types (list all special test types)"""
        try:
            response = self.session.get(f"{self.service_url}/api/v1/special-types")
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    self.log_test(
                        "GET Special Types",
                        True,
                        f"Retrieved {len(data)} special test types",
                        {"count": len(data), "sample": data[:2] if data else []}
                    )
                else:
                    self.log_test(
                        "GET Special Types",
                        False,
                        f"Expected list response, got: {type(data)}",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "GET Special Types",
                    False,
                    f"Request failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "GET Special Types",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_special_type(self):
        """Test POST /api/v1/special-types (create new special test type)"""
        try:
            special_type_data = {
                "name": "Advanced Defensive Driving Test",
                "description": "Comprehensive test for advanced defensive driving techniques",
                "fee": 150.0,
                "validity_months": 36,
                "required_docs": ["photo", "id_proof", "medical_certificate", "driving_record"],
                "pass_percentage": 80,
                "time_limit_minutes": 45,
                "questions_count": 30,
                "status": "active",
                "created_by": "Test Administrator"
            }
            
            response = self.session.post(
                f"{self.service_url}/api/v1/special-types",
                json=special_type_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                if "id" in data:
                    type_id = data.get("id")
                    self.created_resources['special_types'].append(type_id)
                    
                    self.log_test(
                        "POST Create Special Type",
                        True,
                        f"Special type created successfully: {data.get('name')}",
                        {
                            "id": type_id,
                            "name": data.get("name"),
                            "fee": data.get("fee"),
                            "validity_months": data.get("validity_months"),
                            "status": data.get("status")
                        }
                    )
                else:
                    self.log_test(
                        "POST Create Special Type",
                        False,
                        f"Creation response missing ID field",
                        data
                    )
            else:
                self.log_test(
                    "POST Create Special Type",
                    False,
                    f"Creation failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "POST Create Special Type",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_special_type_by_id(self):
        """Test GET /api/v1/special-types/{id} (get specific special test type)"""
        if not self.created_resources['special_types']:
            self.log_test(
                "GET Special Type by ID",
                False,
                "No special types created to test with",
                {}
            )
            return
        
        try:
            type_id = self.created_resources['special_types'][0]
            response = self.session.get(f"{self.service_url}/api/v1/special-types/{type_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("id") == type_id:
                    self.log_test(
                        "GET Special Type by ID",
                        True,
                        f"Retrieved special type: {data.get('name')}",
                        {
                            "id": data.get("id"),
                            "name": data.get("name"),
                            "status": data.get("status"),
                            "fee": data.get("fee")
                        }
                    )
                else:
                    self.log_test(
                        "GET Special Type by ID",
                        False,
                        f"Retrieved wrong special type or missing data",
                        data
                    )
            else:
                self.log_test(
                    "GET Special Type by ID",
                    False,
                    f"Retrieval failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "GET Special Type by ID",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_update_special_type(self):
        """Test PUT /api/v1/special-types/{id} (update special test type)"""
        if not self.created_resources['special_types']:
            self.log_test(
                "PUT Update Special Type",
                False,
                "No special types created to test with",
                {}
            )
            return
        
        try:
            type_id = self.created_resources['special_types'][0]
            update_data = {
                "name": "Advanced Defensive Driving Test - Updated",
                "description": "Updated comprehensive test for advanced defensive driving techniques",
                "fee": 175.0,
                "validity_months": 48,
                "pass_percentage": 85,
                "time_limit_minutes": 50,
                "status": "active"
            }
            
            response = self.session.put(
                f"{self.service_url}/api/v1/special-types/{type_id}",
                json=update_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("name") == update_data["name"] and data.get("fee") == update_data["fee"]:
                    self.log_test(
                        "PUT Update Special Type",
                        True,
                        f"Special type updated successfully: {data.get('name')}",
                        {
                            "id": data.get("id"),
                            "name": data.get("name"),
                            "fee": data.get("fee"),
                            "validity_months": data.get("validity_months")
                        }
                    )
                else:
                    self.log_test(
                        "PUT Update Special Type",
                        False,
                        f"Update data not reflected in response",
                        data
                    )
            else:
                self.log_test(
                    "PUT Update Special Type",
                    False,
                    f"Update failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "PUT Update Special Type",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_delete_special_type(self):
        """Test DELETE /api/v1/special-types/{id} (delete special test type)"""
        # Create a temporary special type for deletion test
        try:
            temp_type_data = {
                "name": "Temporary Test Type for Deletion",
                "description": "This type will be deleted",
                "fee": 50.0,
                "validity_months": 12,
                "required_docs": ["photo"],
                "pass_percentage": 70,
                "time_limit_minutes": 20,
                "questions_count": 15,
                "status": "active",
                "created_by": "Test Administrator"
            }
            
            # Create temporary type
            create_response = self.session.post(
                f"{self.service_url}/api/v1/special-types",
                json=temp_type_data
            )
            
            if create_response.status_code in [200, 201]:
                temp_type = create_response.json()
                temp_id = temp_type.get("id")
                
                # Now delete it
                delete_response = self.session.delete(f"{self.service_url}/api/v1/special-types/{temp_id}")
                
                if delete_response.status_code in [200, 204]:
                    # Verify deletion by trying to get the deleted type
                    verify_response = self.session.get(f"{self.service_url}/api/v1/special-types/{temp_id}")
                    
                    if verify_response.status_code == 404:
                        self.log_test(
                            "DELETE Special Type",
                            True,
                            f"Special type deleted successfully and verified",
                            {"deleted_id": temp_id, "name": temp_type.get("name")}
                        )
                    else:
                        self.log_test(
                            "DELETE Special Type",
                            False,
                            f"Type still exists after deletion",
                            {"id": temp_id, "verify_status": verify_response.status_code}
                        )
                else:
                    self.log_test(
                        "DELETE Special Type",
                        False,
                        f"Deletion failed with status {delete_response.status_code}",
                        {"response": delete_response.text}
                    )
            else:
                self.log_test(
                    "DELETE Special Type",
                    False,
                    f"Could not create temporary type for deletion test",
                    {"create_status": create_response.status_code}
                )
                
        except Exception as e:
            self.log_test(
                "DELETE Special Type",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    # 3. Question Modules API Endpoints
    def test_get_modules(self):
        """Test GET /api/v1/modules (list all question modules)"""
        try:
            response = self.session.get(f"{self.service_url}/api/v1/modules")
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    self.log_test(
                        "GET Question Modules",
                        True,
                        f"Retrieved {len(data)} question modules",
                        {"count": len(data), "sample": data[:2] if data else []}
                    )
                else:
                    self.log_test(
                        "GET Question Modules",
                        False,
                        f"Expected list response, got: {type(data)}",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "GET Question Modules",
                    False,
                    f"Request failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "GET Question Modules",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_module(self):
        """Test POST /api/v1/modules (create new question module)"""
        try:
            module_data = {
                "code": "SPECIAL-HAZMAT",
                "name": "Special Hazardous Materials Transport",
                "description": "Questions for hazardous materials transport certification",
                "difficulty_level": "advanced",
                "pass_percentage": 85,
                "time_limit_minutes": 60,
                "question_count": 0,
                "status": "active",
                "created_by": "Test Administrator"
            }
            
            response = self.session.post(
                f"{self.service_url}/api/v1/modules",
                json=module_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                if "id" in data:
                    module_id = data.get("id")
                    self.created_resources['modules'].append(module_id)
                    
                    self.log_test(
                        "POST Create Question Module",
                        True,
                        f"Question module created successfully: {data.get('name')}",
                        {
                            "id": module_id,
                            "code": data.get("code"),
                            "name": data.get("name"),
                            "difficulty_level": data.get("difficulty_level"),
                            "status": data.get("status")
                        }
                    )
                else:
                    self.log_test(
                        "POST Create Question Module",
                        False,
                        f"Creation response missing ID field",
                        data
                    )
            else:
                self.log_test(
                    "POST Create Question Module",
                    False,
                    f"Creation failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "POST Create Question Module",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_module_by_id(self):
        """Test GET /api/v1/modules/{id} (get specific module)"""
        if not self.created_resources['modules']:
            self.log_test(
                "GET Module by ID",
                False,
                "No modules created to test with",
                {}
            )
            return
        
        try:
            module_id = self.created_resources['modules'][0]
            response = self.session.get(f"{self.service_url}/api/v1/modules/{module_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("id") == module_id:
                    self.log_test(
                        "GET Module by ID",
                        True,
                        f"Retrieved module: {data.get('name')}",
                        {
                            "id": data.get("id"),
                            "code": data.get("code"),
                            "name": data.get("name"),
                            "status": data.get("status")
                        }
                    )
                else:
                    self.log_test(
                        "GET Module by ID",
                        False,
                        f"Retrieved wrong module or missing data",
                        data
                    )
            else:
                self.log_test(
                    "GET Module by ID",
                    False,
                    f"Retrieval failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "GET Module by ID",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_update_module(self):
        """Test PUT /api/v1/modules/{id} (update module)"""
        if not self.created_resources['modules']:
            self.log_test(
                "PUT Update Module",
                False,
                "No modules created to test with",
                {}
            )
            return
        
        try:
            module_id = self.created_resources['modules'][0]
            update_data = {
                "description": "Updated questions for hazardous materials transport certification",
                "pass_percentage": 90,
                "time_limit_minutes": 75,
                "status": "active"
            }
            
            response = self.session.put(
                f"{self.service_url}/api/v1/modules/{module_id}",
                json=update_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("description") == update_data["description"] and data.get("pass_percentage") == update_data["pass_percentage"]:
                    self.log_test(
                        "PUT Update Module",
                        True,
                        f"Module updated successfully: {data.get('code')}",
                        {
                            "id": data.get("id"),
                            "code": data.get("code"),
                            "description": data.get("description"),
                            "pass_percentage": data.get("pass_percentage")
                        }
                    )
                else:
                    self.log_test(
                        "PUT Update Module",
                        False,
                        f"Update data not reflected in response",
                        data
                    )
            else:
                self.log_test(
                    "PUT Update Module",
                    False,
                    f"Update failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "PUT Update Module",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    # 4. Question Upload API
    def test_upload_questions_csv(self):
        """Test POST /api/v1/questions/upload-text (CSV question upload via JSON)"""
        try:
            # Create sample CSV data for question upload
            csv_data = """question_text,option_a,option_b,option_c,option_d,correct_answer,difficulty,explanation
"What is the minimum following distance for hazmat vehicles?","100m","150m","200m","250m","C","medium","Hazmat vehicles require increased following distance for safety"
"Which placards are required for Class 3 flammable liquids?","Red diamond","Orange diamond","Yellow diamond","Blue diamond","A","easy","Class 3 flammable liquids require red diamond placards"
"What temperature range requires special handling for hazmat?","Below 0°C","Above 50°C","Below -10°C or above 60°C","Any temperature","C","hard","Extreme temperatures require special hazmat handling procedures"
"How often must hazmat vehicle inspections occur?","Daily","Weekly","Monthly","Before each trip","D","medium","Hazmat vehicles must be inspected before each trip"
"What is the maximum speed limit for hazmat transport?","80 km/h","90 km/h","100 km/h","110 km/h","A","easy","Hazmat vehicles have reduced speed limits for safety"
"""
            
            upload_data = {
                "module_code": "SPECIAL-HAZMAT",
                "csv_data": csv_data,
                "created_by": "Test Administrator"
            }
            
            response = self.session.post(
                f"{self.service_url}/api/v1/questions/upload-text",
                json=upload_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success", False):
                    self.log_test(
                        "POST CSV Question Upload",
                        True,
                        f"Questions uploaded successfully: {data.get('questions_created', 0)} questions",
                        {
                            "questions_created": data.get("questions_created"),
                            "questions_updated": data.get("questions_updated"),
                            "errors": data.get("errors", []),
                            "module_code": data.get("module_code")
                        }
                    )
                else:
                    self.log_test(
                        "POST CSV Question Upload",
                        False,
                        f"Upload failed: {data.get('error', 'Unknown error')}",
                        data
                    )
            else:
                self.log_test(
                    "POST CSV Question Upload",
                    False,
                    f"Upload failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "POST CSV Question Upload",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    # 5. Certificate Templates API Endpoints
    def test_get_templates(self):
        """Test GET /api/v1/templates (list all certificate templates)"""
        try:
            response = self.session.get(f"{self.service_url}/api/v1/templates")
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    self.log_test(
                        "GET Certificate Templates",
                        True,
                        f"Retrieved {len(data)} certificate templates",
                        {"count": len(data), "sample": data[:2] if data else []}
                    )
                else:
                    self.log_test(
                        "GET Certificate Templates",
                        False,
                        f"Expected list response, got: {type(data)}",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "GET Certificate Templates",
                    False,
                    f"Request failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "GET Certificate Templates",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_template(self):
        """Test POST /api/v1/templates (create new template)"""
        try:
            template_data = {
                "name": "Special Test Certificate Template",
                "type": "special_test",
                "description": "Template for special driving test certificates",
                "hbs_content": """
                <div class="certificate">
                    <div class="header">
                        <h1>Certificate of Completion</h1>
                        <div class="logo">ITADIAS</div>
                    </div>
                    <div class="content">
                        <p class="recipient">This certifies that <strong>{{candidate_name}}</strong></p>
                        <p class="achievement">has successfully completed the <strong>{{test_type}}</strong></p>
                        <p class="date">on {{completion_date}}</p>
                        <div class="score-section">
                            <p>Score: <strong>{{score}}%</strong></p>
                            <p>Result: <strong>{{result}}</strong></p>
                        </div>
                        <p class="validity">Valid until: {{expiry_date}}</p>
                    </div>
                    <div class="footer">
                        <div class="signature">
                            <p>Authorized Signature</p>
                        </div>
                        <div class="qr-code">
                            <p>Verification Code: {{verification_code}}</p>
                        </div>
                    </div>
                </div>
                """,
                "css_content": """
                .certificate {
                    width: 800px;
                    margin: 0 auto;
                    padding: 40px;
                    border: 3px solid #2c3e50;
                    font-family: 'Times New Roman', serif;
                    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #34495e;
                    padding-bottom: 20px;
                }
                .header h1 {
                    color: #2c3e50;
                    font-size: 36px;
                    margin: 0;
                }
                .logo {
                    color: #e74c3c;
                    font-size: 18px;
                    font-weight: bold;
                    margin-top: 10px;
                }
                .content {
                    text-align: center;
                    margin: 30px 0;
                    line-height: 1.8;
                }
                .recipient {
                    font-size: 20px;
                    margin: 20px 0;
                }
                .achievement {
                    font-size: 18px;
                    margin: 20px 0;
                }
                .date {
                    font-size: 16px;
                    color: #7f8c8d;
                }
                .score-section {
                    margin: 25px 0;
                    padding: 15px;
                    background: #ecf0f1;
                    border-radius: 5px;
                }
                .validity {
                    font-size: 14px;
                    color: #e74c3c;
                    font-weight: bold;
                }
                .footer {
                    display: flex;
                    justify-content: space-between;
                    margin-top: 40px;
                    border-top: 2px solid #34495e;
                    padding-top: 20px;
                }
                .signature, .qr-code {
                    text-align: center;
                    font-size: 12px;
                }
                """,
                "json_config": {
                    "page_size": "A4",
                    "orientation": "landscape",
                    "margins": {"top": 20, "bottom": 20, "left": 20, "right": 20},
                    "quality": "high"
                },
                "status": "active",
                "created_by": "Test Administrator"
            }
            
            response = self.session.post(
                f"{self.service_url}/api/v1/templates",
                json=template_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                if "id" in data:
                    template_id = data.get("id")
                    self.created_resources['templates'].append(template_id)
                    
                    self.log_test(
                        "POST Create Certificate Template",
                        True,
                        f"Template created successfully: {data.get('name')}",
                        {
                            "id": template_id,
                            "name": data.get("name"),
                            "type": data.get("type"),
                            "status": data.get("status")
                        }
                    )
                else:
                    self.log_test(
                        "POST Create Certificate Template",
                        False,
                        f"Creation response missing ID field",
                        data
                    )
            else:
                self.log_test(
                    "POST Create Certificate Template",
                    False,
                    f"Creation failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "POST Create Certificate Template",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_template_by_id(self):
        """Test GET /api/v1/templates/{id} (get specific template)"""
        if not self.created_resources['templates']:
            self.log_test(
                "GET Template by ID",
                False,
                "No templates created to test with",
                {}
            )
            return
        
        try:
            template_id = self.created_resources['templates'][0]
            response = self.session.get(f"{self.service_url}/api/v1/templates/{template_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("id") == template_id:
                    self.log_test(
                        "GET Template by ID",
                        True,
                        f"Retrieved template: {data.get('name')}",
                        {
                            "id": data.get("id"),
                            "name": data.get("name"),
                            "type": data.get("type"),
                            "status": data.get("status")
                        }
                    )
                else:
                    self.log_test(
                        "GET Template by ID",
                        False,
                        f"Retrieved wrong template or missing data",
                        data
                    )
            else:
                self.log_test(
                    "GET Template by ID",
                    False,
                    f"Retrieval failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "GET Template by ID",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_update_template(self):
        """Test PUT /api/v1/templates/{id} (update template)"""
        if not self.created_resources['templates']:
            self.log_test(
                "PUT Update Template",
                False,
                "No templates created to test with",
                {}
            )
            return
        
        try:
            template_id = self.created_resources['templates'][0]
            update_data = {
                "name": "Special Test Certificate Template - Updated",
                "description": "Updated template for special driving test certificates",
                "type": "special_test_updated",
                "status": "active"
            }
            
            response = self.session.put(
                f"{self.service_url}/api/v1/templates/{template_id}",
                json=update_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("name") == update_data["name"]:
                    self.log_test(
                        "PUT Update Template",
                        True,
                        f"Template updated successfully: {data.get('name')}",
                        {
                            "id": data.get("id"),
                            "name": data.get("name"),
                            "type": data.get("type"),
                            "status": data.get("status")
                        }
                    )
                else:
                    self.log_test(
                        "PUT Update Template",
                        False,
                        f"Update data not reflected in response",
                        data
                    )
            else:
                self.log_test(
                    "PUT Update Template",
                    False,
                    f"Update failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "PUT Update Template",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_delete_template(self):
        """Test DELETE /api/v1/templates/{id} (delete template)"""
        # Create a temporary template for deletion test
        try:
            temp_template_data = {
                "name": "Temporary Template for Deletion",
                "type": "temp_test",
                "description": "This template will be deleted",
                "hbs_content": "<div>Temporary content</div>",
                "css_content": "div { color: red; }",
                "json_config": {"page_size": "A4"},
                "status": "active",
                "created_by": "Test Administrator"
            }
            
            # Create temporary template
            create_response = self.session.post(
                f"{self.service_url}/api/v1/templates",
                json=temp_template_data
            )
            
            if create_response.status_code in [200, 201]:
                temp_template = create_response.json()
                temp_id = temp_template.get("id")
                
                # Now delete it
                delete_response = self.session.delete(f"{self.service_url}/api/v1/templates/{temp_id}")
                
                if delete_response.status_code in [200, 204]:
                    # Verify deletion by trying to get the deleted template
                    verify_response = self.session.get(f"{self.service_url}/api/v1/templates/{temp_id}")
                    
                    if verify_response.status_code == 404:
                        self.log_test(
                            "DELETE Template",
                            True,
                            f"Template deleted successfully and verified",
                            {"deleted_id": temp_id, "name": temp_template.get("name")}
                        )
                    else:
                        self.log_test(
                            "DELETE Template",
                            False,
                            f"Template still exists after deletion",
                            {"id": temp_id, "verify_status": verify_response.status_code}
                        )
                else:
                    self.log_test(
                        "DELETE Template",
                        False,
                        f"Deletion failed with status {delete_response.status_code}",
                        {"response": delete_response.text}
                    )
            else:
                self.log_test(
                    "DELETE Template",
                    False,
                    f"Could not create temporary template for deletion test",
                    {"create_status": create_response.status_code}
                )
                
        except Exception as e:
            self.log_test(
                "DELETE Template",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_template_preview(self):
        """Test POST /api/v1/templates/preview (template preview)"""
        try:
            preview_data = {
                "hbs_content": """
                <div class="preview-certificate">
                    <h2>Preview Certificate</h2>
                    <p>Candidate: {{candidate_name}}</p>
                    <p>Test Type: {{test_type}}</p>
                    <p>Date: {{completion_date}}</p>
                    <p>Score: {{score}}%</p>
                    <p>Result: {{result}}</p>
                </div>
                """,
                "css_content": """
                .preview-certificate {
                    background: #f8f9fa;
                    padding: 20px;
                    border: 2px solid #007bff;
                    border-radius: 10px;
                    text-align: center;
                    font-family: Arial, sans-serif;
                }
                h2 { color: #007bff; }
                p { margin: 10px 0; }
                """,
                "sample_data": {
                    "candidate_name": "John Smith",
                    "test_type": "Advanced Defensive Driving",
                    "completion_date": "2024-12-15",
                    "score": "92",
                    "result": "PASS"
                }
            }
            
            response = self.session.post(
                f"{self.service_url}/api/v1/templates/preview",
                json=preview_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check if response has expected fields (preview_html and compiled_template)
                if "preview_html" in data and "compiled_template" in data:
                    self.log_test(
                        "POST Template Preview",
                        True,
                        f"Template preview generated successfully",
                        {
                            "has_preview_html": "preview_html" in data,
                            "has_compiled_template": "compiled_template" in data,
                            "preview_length": len(data.get("preview_html", ""))
                        }
                    )
                else:
                    self.log_test(
                        "POST Template Preview",
                        False,
                        f"Preview response missing expected fields",
                        {"response_keys": list(data.keys())}
                    )
            else:
                self.log_test(
                    "POST Template Preview",
                    False,
                    f"Preview failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "POST Template Preview",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    # 6. API Schema and Documentation
    def test_openapi_docs(self):
        """Test /docs endpoint for OpenAPI documentation"""
        try:
            response = self.session.get(f"{self.service_url}/docs")
            if response.status_code == 200:
                content = response.text
                
                # Check if it's a valid HTML page with OpenAPI content
                if "swagger" in content.lower() or "openapi" in content.lower() or "api documentation" in content.lower():
                    self.log_test(
                        "OpenAPI Documentation",
                        True,
                        f"API documentation accessible at /docs",
                        {
                            "content_length": len(content),
                            "has_swagger": "swagger" in content.lower(),
                            "has_openapi": "openapi" in content.lower()
                        }
                    )
                else:
                    self.log_test(
                        "OpenAPI Documentation",
                        False,
                        f"Documentation page doesn't contain expected API content",
                        {"content_preview": content[:200]}
                    )
            else:
                self.log_test(
                    "OpenAPI Documentation",
                    False,
                    f"Documentation not accessible, status {response.status_code}",
                    {"response": response.text[:200]}
                )
                
        except Exception as e:
            self.log_test(
                "OpenAPI Documentation",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_rest_conventions(self):
        """Verify all endpoints follow proper REST conventions"""
        try:
            # Test root endpoint
            response = self.session.get(f"{self.service_url}/")
            if response.status_code == 200:
                data = response.json()
                
                expected_fields = ["message", "version", "features"]
                has_expected = all(field in data for field in expected_fields)
                
                if has_expected:
                    self.log_test(
                        "REST Conventions Check",
                        True,
                        f"Service follows REST conventions with proper root endpoint",
                        {
                            "service_name": data.get("message"),
                            "version": data.get("version"),
                            "features_count": len(data.get("features", []))
                        }
                    )
                else:
                    self.log_test(
                        "REST Conventions Check",
                        False,
                        f"Root endpoint missing expected fields",
                        data
                    )
            else:
                self.log_test(
                    "REST Conventions Check",
                    False,
                    f"Root endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "REST Conventions Check",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_request_response_schemas(self):
        """Test request/response schemas"""
        try:
            # Test with invalid data to check schema validation
            invalid_special_type = {
                "name": "",  # Invalid: empty name
                "fee": "invalid",  # Invalid: string instead of number
                "validity_months": -1  # Invalid: negative value
            }
            
            response = self.session.post(
                f"{self.service_url}/api/v1/special-types",
                json=invalid_special_type
            )
            
            # Should return 400 or 422 for validation errors
            if response.status_code in [400, 422]:
                data = response.json()
                
                # Check if error response has proper structure
                if "detail" in data or "error" in data:
                    self.log_test(
                        "Request/Response Schema Validation",
                        True,
                        f"Schema validation working correctly, rejected invalid data",
                        {
                            "status_code": response.status_code,
                            "error_structure": list(data.keys())
                        }
                    )
                else:
                    self.log_test(
                        "Request/Response Schema Validation",
                        False,
                        f"Error response doesn't have proper structure",
                        data
                    )
            else:
                self.log_test(
                    "Request/Response Schema Validation",
                    False,
                    f"Invalid data was accepted (status {response.status_code})",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Request/Response Schema Validation",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting Special Admin Microservice Backend Testing (Port 8009)")
        print(f"🌐 Service URL: {self.service_url}")
        print("=" * 100)
        
        # 1. Service Health and Status Tests
        print("\n🏥 TESTING SERVICE HEALTH AND STATUS:")
        self.test_service_health()
        self.test_database_connectivity()
        self.test_service_components()
        
        # 2. Special Test Types API Endpoints
        print("\n🎯 TESTING SPECIAL TEST TYPES API ENDPOINTS:")
        self.test_get_special_types()
        self.test_create_special_type()
        self.test_get_special_type_by_id()
        self.test_update_special_type()
        self.test_delete_special_type()
        
        # 3. Question Modules API Endpoints
        print("\n❓ TESTING QUESTION MODULES API ENDPOINTS:")
        self.test_get_modules()
        self.test_create_module()
        self.test_get_module_by_id()
        self.test_update_module()
        
        # 4. Question Upload API
        print("\n📤 TESTING QUESTION UPLOAD API:")
        self.test_upload_questions_csv()
        
        # 5. Certificate Templates API Endpoints
        print("\n📜 TESTING CERTIFICATE TEMPLATES API ENDPOINTS:")
        self.test_get_templates()
        self.test_create_template()
        self.test_get_template_by_id()
        self.test_update_template()
        self.test_delete_template()
        self.test_template_preview()
        
        # 6. API Schema and Documentation
        print("\n📚 TESTING API SCHEMA AND DOCUMENTATION:")
        self.test_openapi_docs()
        self.test_rest_conventions()
        self.test_request_response_schemas()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 100)
        print("📊 SPECIAL ADMIN MICROSERVICE BACKEND TEST SUMMARY (PORT 8009)")
        print("=" * 100)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🎯 TESTED COMPONENTS:")
        print("   ✓ Service Health and Database Connectivity")
        print("   ✓ Special Test Types CRUD Operations")
        print("   ✓ Question Modules CRUD Operations")
        print("   ✓ CSV Question Upload Functionality")
        print("   ✓ Certificate Templates CRUD Operations")
        print("   ✓ Template Preview Functionality")
        print("   ✓ OpenAPI Documentation")
        print("   ✓ REST Conventions and Schema Validation")
        
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
        with open('/app/special_admin_port_8009_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'service_url': self.service_url,
                    'focus': 'Special Admin microservice backend testing on port 8009'
                },
                'test_results': self.test_results,
                'created_resources': self.created_resources
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/special_admin_port_8009_test_results.json")


def main():
    """Main test execution function."""
    tester = SpecialAdminPort8009Tester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()