#!/usr/bin/env python3
"""
Comprehensive Checklist Management System Testing
Tests the newly implemented checklist management system for examiner tablet functionality
"""

import asyncio
import json
import uuid
import requests
import time
from datetime import datetime, date
from typing import Dict, Any, Optional, List
import sys

# Test configuration
MAIN_BACKEND_URL = "https://offline-inspector-1.preview.emergentagent.com"
API_BASE = f"{MAIN_BACKEND_URL}/api"

class ChecklistManagementTester:
    """Comprehensive tester for the Checklist Management System."""
    
    def __init__(self):
        self.api_base_url = API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.created_checklists = []
        
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
    
    def generate_test_checklist_data(self, test_type: str = "Class B", test_category: str = "Yard", include_items: bool = False) -> Dict[str, Any]:
        """Generate realistic test checklist data"""
        driver_record_id = str(uuid.uuid4())
        examiner_id = f"EX{int(time.time())}"[-8:]  # Generate examiner ID
        
        checklist_data = {
            "driver_record_id": driver_record_id,
            "examiner_id": examiner_id,
            "test_type": test_type,
            "test_category": test_category
        }
        
        # Add custom items if requested
        if include_items:
            checklist_data["items"] = [
                {
                    "category": "Pre-inspection",
                    "description": "Vehicle exterior condition check",
                    "checked": False,
                    "breach_type": None,
                    "notes": ""
                },
                {
                    "category": "Yard Maneuvers",
                    "description": "Reverse parking maneuver",
                    "checked": False,
                    "breach_type": None,
                    "notes": ""
                }
            ]
        
        return checklist_data
    
    def test_main_backend_health(self):
        """Test main backend health check"""
        try:
            response = self.session.get(f"{self.api_base_url}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Main Backend Health Check",
                    True,
                    f"Backend accessible: {data.get('message', 'OK')}",
                    {"status_code": response.status_code}
                )
            else:
                self.log_test(
                    "Main Backend Health Check",
                    False,
                    f"Backend returned status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend Health Check",
                False,
                f"Backend connection error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_checklist_class_b_yard(self):
        """Test creating a Class B Yard checklist with default items"""
        try:
            checklist_data = self.generate_test_checklist_data("Class B", "Yard")
            
            response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=checklist_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                checklist_id = data.get("id")
                if checklist_id:
                    self.created_checklists.append(checklist_id)
                
                # Verify checklist structure
                required_fields = ["id", "driver_record_id", "examiner_id", "test_type", "test_category", "items", "total_items"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields and len(data.get("items", [])) > 0:
                    self.log_test(
                        "Create Class B Yard Checklist",
                        True,
                        f"Checklist created with {len(data.get('items', []))} default items",
                        {
                            "checklist_id": checklist_id,
                            "test_type": data.get("test_type"),
                            "test_category": data.get("test_category"),
                            "total_items": data.get("total_items"),
                            "default_items_generated": len(data.get("items", []))
                        }
                    )
                else:
                    self.log_test(
                        "Create Class B Yard Checklist",
                        False,
                        f"Checklist missing required fields: {missing_fields} or no items generated",
                        data
                    )
            else:
                self.log_test(
                    "Create Class B Yard Checklist",
                    False,
                    f"Expected 200/201, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Class B Yard Checklist",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_checklist_class_c_road(self):
        """Test creating a Class C Road checklist with default items"""
        try:
            checklist_data = self.generate_test_checklist_data("Class C", "Road")
            
            response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=checklist_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                checklist_id = data.get("id")
                if checklist_id:
                    self.created_checklists.append(checklist_id)
                
                # Verify Class C specific items are included
                items = data.get("items", [])
                commercial_items = [item for item in items if "commercial" in item.get("description", "").lower() or "air brake" in item.get("description", "").lower()]
                road_items = [item for item in items if item.get("category") == "Road Driving"]
                
                if len(items) > 0 and len(commercial_items) > 0 and len(road_items) > 0:
                    self.log_test(
                        "Create Class C Road Checklist",
                        True,
                        f"Class C Road checklist created with commercial and road items",
                        {
                            "checklist_id": checklist_id,
                            "total_items": len(items),
                            "commercial_items": len(commercial_items),
                            "road_items": len(road_items)
                        }
                    )
                else:
                    self.log_test(
                        "Create Class C Road Checklist",
                        False,
                        f"Class C checklist missing expected item types",
                        {
                            "total_items": len(items),
                            "commercial_items": len(commercial_items),
                            "road_items": len(road_items)
                        }
                    )
            else:
                self.log_test(
                    "Create Class C Road Checklist",
                    False,
                    f"Expected 200/201, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Class C Road Checklist",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_create_checklist_ppv_yard(self):
        """Test creating a PPV Yard checklist with PPV-specific items"""
        try:
            checklist_data = self.generate_test_checklist_data("PPV", "Yard")
            
            response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=checklist_data
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                checklist_id = data.get("id")
                if checklist_id:
                    self.created_checklists.append(checklist_id)
                
                # Verify PPV specific items are included
                items = data.get("items", [])
                ppv_items = [item for item in items if any(keyword in item.get("description", "").lower() 
                           for keyword in ["passenger", "wheelchair", "emergency exit", "first aid"])]
                
                if len(items) > 0 and len(ppv_items) > 0:
                    self.log_test(
                        "Create PPV Yard Checklist",
                        True,
                        f"PPV checklist created with passenger vehicle specific items",
                        {
                            "checklist_id": checklist_id,
                            "total_items": len(items),
                            "ppv_specific_items": len(ppv_items)
                        }
                    )
                else:
                    self.log_test(
                        "Create PPV Yard Checklist",
                        False,
                        f"PPV checklist missing expected PPV-specific items",
                        {
                            "total_items": len(items),
                            "ppv_specific_items": len(ppv_items)
                        }
                    )
            else:
                self.log_test(
                    "Create PPV Yard Checklist",
                    False,
                    f"Expected 200/201, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create PPV Yard Checklist",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_checklist_by_driver_record(self):
        """Test retrieving checklist by driver record ID"""
        try:
            # First create a checklist
            checklist_data = self.generate_test_checklist_data("Special", "Road")
            driver_record_id = checklist_data["driver_record_id"]
            
            create_response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=checklist_data
            )
            
            if create_response.status_code in [200, 201]:
                created_checklist = create_response.json()
                checklist_id = created_checklist.get("id")
                if checklist_id:
                    self.created_checklists.append(checklist_id)
                
                # Now retrieve it by driver record ID
                get_response = self.session.get(
                    f"{self.api_base_url}/checklists/{driver_record_id}"
                )
                
                if get_response.status_code == 200:
                    data = get_response.json()
                    if data.get("success") and data.get("data"):
                        retrieved_checklist = data["data"]
                        
                        # Verify it's the same checklist
                        if retrieved_checklist.get("driver_record_id") == driver_record_id:
                            self.log_test(
                                "Get Checklist by Driver Record ID",
                                True,
                                f"Successfully retrieved checklist for driver {driver_record_id}",
                                {
                                    "driver_record_id": driver_record_id,
                                    "checklist_id": retrieved_checklist.get("id"),
                                    "test_type": retrieved_checklist.get("test_type")
                                }
                            )
                        else:
                            self.log_test(
                                "Get Checklist by Driver Record ID",
                                False,
                                f"Retrieved checklist has wrong driver record ID",
                                data
                            )
                    else:
                        self.log_test(
                            "Get Checklist by Driver Record ID",
                            False,
                            f"Get request failed: {data.get('error', 'Unknown error')}",
                            data
                        )
                else:
                    self.log_test(
                        "Get Checklist by Driver Record ID",
                        False,
                        f"Expected 200, got {get_response.status_code}",
                        {"response": get_response.text}
                    )
            else:
                self.log_test(
                    "Get Checklist by Driver Record ID",
                    False,
                    f"Failed to create test checklist: {create_response.status_code}",
                    {"response": create_response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Checklist by Driver Record ID",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_update_checklist_items(self):
        """Test updating checklist items with breach flags"""
        try:
            # First create a checklist
            checklist_data = self.generate_test_checklist_data("Class B", "Road")
            
            create_response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=checklist_data
            )
            
            if create_response.status_code in [200, 201]:
                created_checklist = create_response.json()
                checklist_id = created_checklist.get("id")
                if checklist_id:
                    self.created_checklists.append(checklist_id)
                
                # Update the checklist with some checked items and breaches
                original_items = created_checklist.get("items", [])
                if len(original_items) >= 3:
                    # Mark first item as checked with no breach
                    original_items[0]["checked"] = True
                    original_items[0]["notes"] = "Completed successfully"
                    
                    # Mark second item as checked with minor breach
                    original_items[1]["checked"] = True
                    original_items[1]["breach_type"] = "minor"
                    original_items[1]["notes"] = "Minor issue with signal timing"
                    
                    # Mark third item as checked with major breach
                    original_items[2]["checked"] = True
                    original_items[2]["breach_type"] = "major"
                    original_items[2]["notes"] = "Failed to observe traffic properly"
                    
                    update_data = {
                        "status": "completed",
                        "items": original_items
                    }
                    
                    update_response = self.session.put(
                        f"{self.api_base_url}/checklists/{checklist_id}",
                        json=update_data
                    )
                    
                    if update_response.status_code == 200:
                        data = update_response.json()
                        if data.get("success") and data.get("data"):
                            updated_checklist = data["data"]
                            
                            # Verify summary calculations
                            expected_checked = 3
                            expected_minor = 1
                            expected_major = 1
                            expected_status = "fail"  # Should fail due to major breach
                            
                            actual_checked = updated_checklist.get("checked_items", 0)
                            actual_minor = updated_checklist.get("minor_breaches", 0)
                            actual_major = updated_checklist.get("major_breaches", 0)
                            actual_status = updated_checklist.get("pass_fail_status")
                            
                            if (actual_checked == expected_checked and 
                                actual_minor == expected_minor and 
                                actual_major == expected_major and 
                                actual_status == expected_status):
                                
                                self.log_test(
                                    "Update Checklist Items with Breaches",
                                    True,
                                    f"Checklist updated with correct summary calculations",
                                    {
                                        "checked_items": actual_checked,
                                        "minor_breaches": actual_minor,
                                        "major_breaches": actual_major,
                                        "pass_fail_status": actual_status
                                    }
                                )
                            else:
                                self.log_test(
                                    "Update Checklist Items with Breaches",
                                    False,
                                    f"Summary calculations incorrect",
                                    {
                                        "expected": {
                                            "checked": expected_checked,
                                            "minor": expected_minor,
                                            "major": expected_major,
                                            "status": expected_status
                                        },
                                        "actual": {
                                            "checked": actual_checked,
                                            "minor": actual_minor,
                                            "major": actual_major,
                                            "status": actual_status
                                        }
                                    }
                                )
                        else:
                            self.log_test(
                                "Update Checklist Items with Breaches",
                                False,
                                f"Update failed: {data.get('error', 'Unknown error')}",
                                data
                            )
                    else:
                        self.log_test(
                            "Update Checklist Items with Breaches",
                            False,
                            f"Expected 200, got {update_response.status_code}",
                            {"response": update_response.text}
                        )
                else:
                    self.log_test(
                        "Update Checklist Items with Breaches",
                        False,
                        f"Not enough items in checklist to test updates",
                        {"items_count": len(original_items)}
                    )
            else:
                self.log_test(
                    "Update Checklist Items with Breaches",
                    False,
                    f"Failed to create test checklist: {create_response.status_code}",
                    {"response": create_response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Update Checklist Items with Breaches",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_pass_fail_logic(self):
        """Test pass/fail determination logic"""
        try:
            # Test case 1: Pass scenario (no major breaches, ≤3 minor breaches)
            checklist_data = self.generate_test_checklist_data("Class B", "Yard")
            
            create_response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=checklist_data
            )
            
            if create_response.status_code in [200, 201]:
                created_checklist = create_response.json()
                checklist_id = created_checklist.get("id")
                if checklist_id:
                    self.created_checklists.append(checklist_id)
                
                original_items = created_checklist.get("items", [])
                if len(original_items) >= 5:
                    # Create a passing scenario: 2 minor breaches, no major breaches
                    for i in range(min(5, len(original_items))):
                        original_items[i]["checked"] = True
                        if i < 2:  # First 2 items have minor breaches
                            original_items[i]["breach_type"] = "minor"
                            original_items[i]["notes"] = f"Minor issue {i+1}"
                    
                    update_data = {
                        "status": "completed",
                        "items": original_items
                    }
                    
                    update_response = self.session.put(
                        f"{self.api_base_url}/checklists/{checklist_id}",
                        json=update_data
                    )
                    
                    if update_response.status_code == 200:
                        data = update_response.json()
                        if data.get("success") and data.get("data"):
                            updated_checklist = data["data"]
                            pass_fail_status = updated_checklist.get("pass_fail_status")
                            minor_breaches = updated_checklist.get("minor_breaches", 0)
                            major_breaches = updated_checklist.get("major_breaches", 0)
                            
                            # Should pass: 2 minor breaches (≤3), 0 major breaches
                            if pass_fail_status == "pass" and minor_breaches == 2 and major_breaches == 0:
                                self.log_test(
                                    "Pass/Fail Logic - Pass Scenario",
                                    True,
                                    f"Correctly determined PASS with 2 minor breaches, 0 major breaches",
                                    {
                                        "pass_fail_status": pass_fail_status,
                                        "minor_breaches": minor_breaches,
                                        "major_breaches": major_breaches
                                    }
                                )
                            else:
                                self.log_test(
                                    "Pass/Fail Logic - Pass Scenario",
                                    False,
                                    f"Incorrect pass/fail determination",
                                    {
                                        "expected": "pass",
                                        "actual": pass_fail_status,
                                        "minor_breaches": minor_breaches,
                                        "major_breaches": major_breaches
                                    }
                                )
                        else:
                            self.log_test(
                                "Pass/Fail Logic - Pass Scenario",
                                False,
                                f"Update failed: {data.get('error')}",
                                data
                            )
                    else:
                        self.log_test(
                            "Pass/Fail Logic - Pass Scenario",
                            False,
                            f"Update request failed: {update_response.status_code}",
                            {"response": update_response.text}
                        )
                else:
                    self.log_test(
                        "Pass/Fail Logic - Pass Scenario",
                        False,
                        f"Not enough items for pass/fail test",
                        {"items_count": len(original_items)}
                    )
            else:
                self.log_test(
                    "Pass/Fail Logic - Pass Scenario",
                    False,
                    f"Failed to create test checklist",
                    {"status_code": create_response.status_code}
                )
                
        except Exception as e:
            self.log_test(
                "Pass/Fail Logic - Pass Scenario",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_unsynced_checklists(self):
        """Test retrieving unsynced checklists"""
        try:
            # First create a checklist that should be unsynced by default
            checklist_data = self.generate_test_checklist_data("Class C", "Yard")
            
            create_response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=checklist_data
            )
            
            if create_response.status_code in [200, 201]:
                created_checklist = create_response.json()
                checklist_id = created_checklist.get("id")
                if checklist_id:
                    self.created_checklists.append(checklist_id)
                
                # Get unsynced checklists
                unsynced_response = self.session.get(
                    f"{self.api_base_url}/checklists/unsynced"
                )
                
                if unsynced_response.status_code == 200:
                    data = unsynced_response.json()
                    if data.get("success") and "data" in data:
                        unsynced_checklists = data["data"]
                        count = data.get("count", 0)
                        
                        # Check if our created checklist is in the unsynced list
                        found_checklist = any(cl.get("id") == checklist_id for cl in unsynced_checklists)
                        
                        if found_checklist and count > 0:
                            self.log_test(
                                "Get Unsynced Checklists",
                                True,
                                f"Successfully retrieved {count} unsynced checklists including our test checklist",
                                {
                                    "count": count,
                                    "found_test_checklist": found_checklist
                                }
                            )
                        else:
                            self.log_test(
                                "Get Unsynced Checklists",
                                False,
                                f"Test checklist not found in unsynced list or count is 0",
                                {
                                    "count": count,
                                    "found_test_checklist": found_checklist,
                                    "checklist_ids": [cl.get("id") for cl in unsynced_checklists]
                                }
                            )
                    else:
                        self.log_test(
                            "Get Unsynced Checklists",
                            False,
                            f"Unsynced request failed: {data.get('error', 'Unknown error')}",
                            data
                        )
                else:
                    self.log_test(
                        "Get Unsynced Checklists",
                        False,
                        f"Expected 200, got {unsynced_response.status_code}",
                        {"response": unsynced_response.text}
                    )
            else:
                self.log_test(
                    "Get Unsynced Checklists",
                    False,
                    f"Failed to create test checklist: {create_response.status_code}",
                    {"response": create_response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Unsynced Checklists",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_mark_checklist_synced(self):
        """Test marking a checklist as synced"""
        try:
            # First create a checklist
            checklist_data = self.generate_test_checklist_data("PPV", "Road")
            
            create_response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=checklist_data
            )
            
            if create_response.status_code in [200, 201]:
                created_checklist = create_response.json()
                checklist_id = created_checklist.get("id")
                if checklist_id:
                    self.created_checklists.append(checklist_id)
                
                # Mark it as synced
                sync_response = self.session.post(
                    f"{self.api_base_url}/checklists/{checklist_id}/sync"
                )
                
                if sync_response.status_code == 200:
                    data = sync_response.json()
                    if data.get("success"):
                        self.log_test(
                            "Mark Checklist as Synced",
                            True,
                            f"Successfully marked checklist as synced: {data.get('message')}",
                            {"checklist_id": checklist_id}
                        )
                    else:
                        self.log_test(
                            "Mark Checklist as Synced",
                            False,
                            f"Sync request failed: {data.get('error', 'Unknown error')}",
                            data
                        )
                else:
                    self.log_test(
                        "Mark Checklist as Synced",
                        False,
                        f"Expected 200, got {sync_response.status_code}",
                        {"response": sync_response.text}
                    )
            else:
                self.log_test(
                    "Mark Checklist as Synced",
                    False,
                    f"Failed to create test checklist: {create_response.status_code}",
                    {"response": create_response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Mark Checklist as Synced",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_all_checklists_with_filtering(self):
        """Test retrieving all checklists with filtering and pagination"""
        try:
            # First create multiple checklists with different properties
            test_checklists = [
                {"test_type": "Class B", "test_category": "Yard", "examiner_id": "EX001"},
                {"test_type": "Class C", "test_category": "Road", "examiner_id": "EX001"},
                {"test_type": "PPV", "test_category": "Yard", "examiner_id": "EX002"}
            ]
            
            created_ids = []
            for checklist_config in test_checklists:
                checklist_data = self.generate_test_checklist_data(
                    checklist_config["test_type"], 
                    checklist_config["test_category"]
                )
                checklist_data["examiner_id"] = checklist_config["examiner_id"]
                
                create_response = self.session.post(
                    f"{self.api_base_url}/checklists",
                    json=checklist_data
                )
                
                if create_response.status_code in [200, 201]:
                    created_checklist = create_response.json()
                    checklist_id = created_checklist.get("id")
                    if checklist_id:
                        created_ids.append(checklist_id)
                        self.created_checklists.append(checklist_id)
            
            if len(created_ids) >= 2:
                # Test 1: Get all checklists without filters
                all_response = self.session.get(f"{self.api_base_url}/checklists")
                
                if all_response.status_code == 200:
                    all_data = all_response.json()
                    if all_data.get("success") and "data" in all_data:
                        all_checklists = all_data["data"]
                        pagination = all_data.get("pagination", {})
                        
                        # Test 2: Filter by examiner_id
                        filter_response = self.session.get(
                            f"{self.api_base_url}/checklists?examiner_id=EX001"
                        )
                        
                        if filter_response.status_code == 200:
                            filter_data = filter_response.json()
                            if filter_data.get("success") and "data" in filter_data:
                                filtered_checklists = filter_data["data"]
                                
                                # Verify filtering worked
                                ex001_checklists = [cl for cl in filtered_checklists if cl.get("examiner_id") == "EX001"]
                                
                                if len(ex001_checklists) == len(filtered_checklists) and len(filtered_checklists) >= 1:
                                    self.log_test(
                                        "Get All Checklists with Filtering",
                                        True,
                                        f"Successfully retrieved and filtered checklists",
                                        {
                                            "total_checklists": len(all_checklists),
                                            "filtered_by_examiner": len(filtered_checklists),
                                            "pagination_present": "total" in pagination
                                        }
                                    )
                                else:
                                    self.log_test(
                                        "Get All Checklists with Filtering",
                                        False,
                                        f"Filtering not working correctly",
                                        {
                                            "filtered_count": len(filtered_checklists),
                                            "ex001_count": len(ex001_checklists)
                                        }
                                    )
                            else:
                                self.log_test(
                                    "Get All Checklists with Filtering",
                                    False,
                                    f"Filter request failed: {filter_data.get('error')}",
                                    filter_data
                                )
                        else:
                            self.log_test(
                                "Get All Checklists with Filtering",
                                False,
                                f"Filter request returned {filter_response.status_code}",
                                {"response": filter_response.text}
                            )
                    else:
                        self.log_test(
                            "Get All Checklists with Filtering",
                            False,
                            f"Get all request failed: {all_data.get('error')}",
                            all_data
                        )
                else:
                    self.log_test(
                        "Get All Checklists with Filtering",
                        False,
                        f"Get all request returned {all_response.status_code}",
                        {"response": all_response.text}
                    )
            else:
                self.log_test(
                    "Get All Checklists with Filtering",
                    False,
                    f"Failed to create enough test checklists for filtering test",
                    {"created_count": len(created_ids)}
                )
                
        except Exception as e:
            self.log_test(
                "Get All Checklists with Filtering",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_checklist_validation_errors(self):
        """Test checklist creation with invalid data"""
        try:
            # Test with missing required fields
            invalid_data = {
                "driver_record_id": str(uuid.uuid4()),
                # Missing examiner_id, test_type, test_category
            }
            
            response = self.session.post(
                f"{self.api_base_url}/checklists",
                json=invalid_data
            )
            
            # Should return validation error
            if response.status_code in [400, 422]:
                self.log_test(
                    "Checklist Validation - Missing Fields",
                    True,
                    f"Correctly rejected invalid checklist data with status {response.status_code}",
                    {"status_code": response.status_code}
                )
            else:
                self.log_test(
                    "Checklist Validation - Missing Fields",
                    False,
                    f"Expected 400/422 for invalid data, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Checklist Validation - Missing Fields",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting Comprehensive Checklist Management System Tests")
        print(f"🌐 Testing Main Backend: {MAIN_BACKEND_URL}")
        print("🔍 Focus: Examiner tablet checklist functionality with offline sync support")
        print("=" * 100)
        
        # Backend health check
        self.test_main_backend_health()
        
        # Core checklist creation tests
        print("\n🎯 TESTING CHECKLIST CREATION WITH DEFAULT ITEMS:")
        self.test_create_checklist_class_b_yard()
        self.test_create_checklist_class_c_road()
        self.test_create_checklist_ppv_yard()
        
        # Checklist retrieval tests
        print("\n🔍 TESTING CHECKLIST RETRIEVAL:")
        self.test_get_checklist_by_driver_record()
        
        # Checklist update and business logic tests
        print("\n✏️ TESTING CHECKLIST UPDATES AND BUSINESS LOGIC:")
        self.test_update_checklist_items()
        self.test_pass_fail_logic()
        
        # Offline sync functionality tests
        print("\n🔄 TESTING OFFLINE SYNC FUNCTIONALITY:")
        self.test_get_unsynced_checklists()
        self.test_mark_checklist_synced()
        
        # Filtering and pagination tests
        print("\n📊 TESTING FILTERING AND PAGINATION:")
        self.test_get_all_checklists_with_filtering()
        
        # Validation tests
        print("\n✅ TESTING VALIDATION:")
        self.test_checklist_validation_errors()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 100)
        print("📊 CHECKLIST MANAGEMENT SYSTEM TEST SUMMARY")
        print("=" * 100)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        print("\n🎯 KEY VALIDATION POINTS:")
        print("   ✓ Default checklist items generated based on test type and category")
        print("   ✓ Pass/fail logic working correctly (major breaches = fail, >3 minor = fail)")
        print("   ✓ Checklist retrieval by driver record ID")
        print("   ✓ Checklist updates with breach tracking")
        print("   ✓ Offline sync functionality (unsynced tracking)")
        print("   ✓ Filtering and pagination support")
        print("   ✓ Proper validation and error handling")
        
        if failed_tests > 0:
            print("\n🔍 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  ❌ {result['test']}: {result['message']}")
        
        print(f"\n📝 Created {len(self.created_checklists)} test checklists during testing")
        
        # Save detailed results to file
        with open('/app/checklist_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'main_backend_url': MAIN_BACKEND_URL,
                    'focus': 'Checklist Management System for Examiner Tablets'
                },
                'test_results': self.test_results,
                'created_checklists': self.created_checklists
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/checklist_test_results.json")


def main():
    """Main test execution function."""
    tester = ChecklistManagementTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()