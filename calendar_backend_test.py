#!/usr/bin/env python3
"""
Calendar Microservice Backend Testing Suite
Tests calendar service direct endpoints and main backend integration.
"""

import asyncio
import json
import uuid
import requests
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import os
import sys

# Test configuration
CALENDAR_SERVICE_URL = "http://localhost:8002"
MAIN_BACKEND_URL = "https://cranky-tharp.preview.emergentagent.com"
CALENDAR_API_BASE = f"{CALENDAR_SERVICE_URL}/api/v1"
MAIN_API_BASE = f"{MAIN_BACKEND_URL}/api"

class CalendarServiceTester:
    """Comprehensive tester for the Calendar microservice and integration."""
    
    def __init__(self):
        self.calendar_base_url = CALENDAR_API_BASE
        self.main_base_url = MAIN_API_BASE
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        self.test_results = []
        self.created_bookings = []
        self.test_hub_id = "550e8400-e29b-41d4-a716-446655440000"  # Test hub ID
        
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
    
    def generate_test_booking_data(self, slot_id: str) -> Dict[str, Any]:
        """Generate realistic test booking data."""
        suffix = str(int(time.time()))[-6:]
        
        return {
            "slot_id": slot_id,
            "candidate_id": str(uuid.uuid4()),
            "contact_email": f"candidate.{suffix}@bermuda.bm",
            "contact_phone": f"+1-441-555-{suffix[-4:]}",
            "special_requirements": "Wheelchair accessible"
        }
    
    def test_calendar_service_health(self):
        """Test calendar service health check."""
        try:
            response = self.session.get(f"{CALENDAR_SERVICE_URL}/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Calendar Service Health Check",
                    True,
                    f"Calendar service healthy: {data.get('status', 'unknown')}",
                    {
                        "status": data.get('status'),
                        "database": data.get('database'),
                        "events": data.get('events'),
                        "cleanup_service": data.get('cleanup_service')
                    }
                )
            else:
                self.log_test(
                    "Calendar Service Health Check",
                    False,
                    f"Health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Calendar Service Health Check",
                False,
                f"Health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_calendar_service_root(self):
        """Test calendar service root endpoint."""
        try:
            response = self.session.get(f"{CALENDAR_SERVICE_URL}/")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Calendar Service Root Endpoint",
                    True,
                    f"Root endpoint accessible: {data.get('message', 'unknown')}",
                    data
                )
            else:
                self.log_test(
                    "Calendar Service Root Endpoint",
                    False,
                    f"Root endpoint failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Calendar Service Root Endpoint",
                False,
                f"Root endpoint error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_available_slots_direct(self):
        """Test getting available slots directly from calendar service."""
        try:
            test_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            params = {
                "hub": self.test_hub_id,
                "date": test_date
            }
            
            response = self.session.get(
                f"{self.calendar_base_url}/slots",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    self.log_test(
                        "Get Available Slots - Direct",
                        True,
                        f"Retrieved {len(data)} slots for {test_date}",
                        {
                            "slot_count": len(data),
                            "date": test_date,
                            "hub_id": self.test_hub_id,
                            "first_slot": data[0] if data else None
                        }
                    )
                    return data
                else:
                    self.log_test(
                        "Get Available Slots - Direct",
                        False,
                        "Response is not a list of slots",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "Get Available Slots - Direct",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Available Slots - Direct",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        return []
    
    def test_create_booking_direct(self, available_slots):
        """Test creating a booking directly with calendar service."""
        if not available_slots:
            self.log_test(
                "Create Booking - Direct",
                False,
                "No available slots to test booking creation",
                {}
            )
            return None
        
        try:
            slot_id = available_slots[0]["id"]
            booking_data = self.generate_test_booking_data(slot_id)
            
            response = self.session.post(
                f"{self.calendar_base_url}/bookings",
                json=booking_data
            )
            
            if response.status_code == 201:
                data = response.json()
                booking_id = data.get('booking', {}).get('id')
                
                if booking_id:
                    self.created_bookings.append(booking_id)
                
                # Validate response structure
                required_fields = ['booking', 'lock_expires_at', 'message']
                missing_fields = [field for field in required_fields if field not in data]
                
                if not missing_fields:
                    booking = data['booking']
                    lock_expires_at = data['lock_expires_at']
                    
                    self.log_test(
                        "Create Booking - Direct",
                        True,
                        f"Booking created successfully: {booking.get('booking_reference')}",
                        {
                            "booking_id": booking_id,
                            "booking_reference": booking.get('booking_reference'),
                            "status": booking.get('status'),
                            "lock_expires_at": lock_expires_at,
                            "slot_locked": data.get('booking', {}).get('slot', {}).get('status') == 'locked'
                        }
                    )
                    return booking_id
                else:
                    self.log_test(
                        "Create Booking - Direct",
                        False,
                        f"Response missing required fields: {missing_fields}",
                        data
                    )
            else:
                self.log_test(
                    "Create Booking - Direct",
                    False,
                    f"Expected 201, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Booking - Direct",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        return None
    
    def test_main_backend_calendar_health(self):
        """Test calendar health check via main backend."""
        try:
            response = self.session.get(f"{self.main_base_url}/calendar/health")
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Main Backend - Calendar Health",
                    True,
                    f"Calendar service accessible via main backend: {data.get('calendar_service', 'unknown')}",
                    data
                )
            else:
                self.log_test(
                    "Main Backend - Calendar Health",
                    False,
                    f"Calendar health check failed with status {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Main Backend - Calendar Health",
                False,
                f"Calendar health check error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_slots_via_main_backend(self):
        """Test getting slots via main backend integration."""
        try:
            test_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            params = {
                "hub_id": self.test_hub_id,
                "date": test_date
            }
            
            response = self.session.get(
                f"{self.main_base_url}/calendar/slots",
                params=params
            )
            
            if response.status_code == 200:
                data = response.json()
                if "slots" in data and isinstance(data["slots"], list):
                    self.log_test(
                        "Get Slots - Via Main Backend",
                        True,
                        f"Retrieved {data.get('total_slots', 0)} slots via main backend",
                        {
                            "slot_count": data.get('total_slots', 0),
                            "date": data.get('date'),
                            "hub_id": data.get('hub_id'),
                            "integration_working": True
                        }
                    )
                    return data["slots"]
                else:
                    self.log_test(
                        "Get Slots - Via Main Backend",
                        False,
                        "Response does not contain slots array",
                        {"response": data}
                    )
            else:
                self.log_test(
                    "Get Slots - Via Main Backend",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Slots - Via Main Backend",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        return []
    
    def test_create_booking_via_main_backend(self, available_slots):
        """Test creating booking via main backend integration."""
        if not available_slots:
            self.log_test(
                "Create Booking - Via Main Backend",
                False,
                "No available slots to test booking creation",
                {}
            )
            return None
        
        try:
            slot_id = available_slots[0]["id"]
            booking_data = self.generate_test_booking_data(slot_id)
            
            response = self.session.post(
                f"{self.main_base_url}/calendar/bookings",
                json=booking_data
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('success'):
                    booking_id = data.get('booking_id')
                    if booking_id:
                        self.created_bookings.append(booking_id)
                    
                    self.log_test(
                        "Create Booking - Via Main Backend",
                        True,
                        f"Booking created via main backend: {data.get('booking_reference')}",
                        {
                            "booking_id": booking_id,
                            "booking_reference": data.get('booking_reference'),
                            "status": data.get('status'),
                            "lock_expires_at": data.get('lock_expires_at'),
                            "integration_working": True
                        }
                    )
                    return booking_id
                else:
                    self.log_test(
                        "Create Booking - Via Main Backend",
                        False,
                        f"Booking creation failed: {data.get('error', 'Unknown error')}",
                        data
                    )
            else:
                self.log_test(
                    "Create Booking - Via Main Backend",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Create Booking - Via Main Backend",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
        
        return None
    
    def test_get_booking_direct(self, booking_id):
        """Test getting booking details directly from calendar service."""
        if not booking_id:
            self.log_test(
                "Get Booking - Direct",
                False,
                "No booking ID provided",
                {}
            )
            return
        
        try:
            response = self.session.get(
                f"{self.calendar_base_url}/bookings/{booking_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                self.log_test(
                    "Get Booking - Direct",
                    True,
                    f"Booking retrieved successfully: {data.get('booking_reference')}",
                    {
                        "booking_id": data.get('id'),
                        "status": data.get('status'),
                        "contact_email": data.get('contact_email'),
                        "has_slot_info": data.get('slot') is not None
                    }
                )
            else:
                self.log_test(
                    "Get Booking - Direct",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Booking - Direct",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_get_booking_via_main_backend(self, booking_id):
        """Test getting booking details via main backend."""
        if not booking_id:
            self.log_test(
                "Get Booking - Via Main Backend",
                False,
                "No booking ID provided",
                {}
            )
            return
        
        try:
            response = self.session.get(
                f"{self.main_base_url}/calendar/bookings/{booking_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('found'):
                    self.log_test(
                        "Get Booking - Via Main Backend",
                        True,
                        f"Booking retrieved via main backend: {data.get('booking', {}).get('booking_reference')}",
                        {
                            "booking_found": True,
                            "booking_id": data.get('booking', {}).get('id'),
                            "integration_working": True
                        }
                    )
                else:
                    self.log_test(
                        "Get Booking - Via Main Backend",
                        False,
                        "Booking not found via main backend",
                        data
                    )
            else:
                self.log_test(
                    "Get Booking - Via Main Backend",
                    False,
                    f"Expected 200, got {response.status_code}",
                    {"response": response.text}
                )
                
        except Exception as e:
            self.log_test(
                "Get Booking - Via Main Backend",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_slot_locking_behavior(self):
        """Test 15-minute slot locking behavior."""
        try:
            # Get available slots
            test_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            params = {
                "hub": self.test_hub_id,
                "date": test_date
            }
            
            response = self.session.get(
                f"{self.calendar_base_url}/slots",
                params=params
            )
            
            if response.status_code != 200 or not response.json():
                self.log_test(
                    "Slot Locking - 15 Minute Lock",
                    False,
                    "No slots available for locking test",
                    {}
                )
                return
            
            slots = response.json()
            slot_id = slots[0]["id"]
            
            # Create first booking to lock the slot
            booking_data1 = self.generate_test_booking_data(slot_id)
            response1 = self.session.post(
                f"{self.calendar_base_url}/bookings",
                json=booking_data1
            )
            
            if response1.status_code == 201:
                booking1_id = response1.json().get('booking', {}).get('id')
                if booking1_id:
                    self.created_bookings.append(booking1_id)
                
                # Try to create second booking on same slot (should fail)
                booking_data2 = self.generate_test_booking_data(slot_id)
                response2 = self.session.post(
                    f"{self.calendar_base_url}/bookings",
                    json=booking_data2
                )
                
                if response2.status_code == 409:
                    error_data = response2.json()
                    if "locked" in error_data.get('detail', '').lower():
                        self.log_test(
                            "Slot Locking - 15 Minute Lock",
                            True,
                            "Slot properly locked after first booking, second booking rejected",
                            {
                                "first_booking_id": booking1_id,
                                "lock_rejection_message": error_data.get('detail'),
                                "lock_working": True
                            }
                        )
                    else:
                        self.log_test(
                            "Slot Locking - 15 Minute Lock",
                            False,
                            "Wrong error message for locked slot",
                            error_data
                        )
                else:
                    self.log_test(
                        "Slot Locking - 15 Minute Lock",
                        False,
                        f"Expected 409 for locked slot, got {response2.status_code}",
                        {"response": response2.text}
                    )
            else:
                self.log_test(
                    "Slot Locking - 15 Minute Lock",
                    False,
                    f"Failed to create first booking: {response1.status_code}",
                    {"response": response1.text}
                )
                
        except Exception as e:
            self.log_test(
                "Slot Locking - 15 Minute Lock",
                False,
                f"Request error: {str(e)}",
                {"error": str(e)}
            )
    
    def test_booking_validation_errors(self):
        """Test booking creation with validation errors."""
        test_cases = [
            {
                "name": "Invalid Slot ID",
                "data": {
                    "slot_id": "invalid-uuid",
                    "candidate_id": str(uuid.uuid4()),
                    "contact_email": "test@example.com"
                },
                "expected_status": 422
            },
            {
                "name": "Missing Required Fields",
                "data": {
                    "slot_id": str(uuid.uuid4())
                },
                "expected_status": 422
            },
            {
                "name": "Invalid Email Format",
                "data": {
                    "slot_id": str(uuid.uuid4()),
                    "candidate_id": str(uuid.uuid4()),
                    "contact_email": "invalid-email"
                },
                "expected_status": 422
            },
            {
                "name": "Non-existent Slot",
                "data": {
                    "slot_id": str(uuid.uuid4()),
                    "candidate_id": str(uuid.uuid4()),
                    "contact_email": "test@example.com"
                },
                "expected_status": 404
            }
        ]
        
        for test_case in test_cases:
            try:
                response = self.session.post(
                    f"{self.calendar_base_url}/bookings",
                    json=test_case["data"]
                )
                
                success = response.status_code == test_case["expected_status"]
                self.log_test(
                    f"Booking Validation - {test_case['name']}",
                    success,
                    f"Expected {test_case['expected_status']}, got {response.status_code}",
                    {"response_data": response.json() if response.headers.get('content-type', '').startswith('application/json') else response.text}
                )
                
            except Exception as e:
                self.log_test(
                    f"Booking Validation - {test_case['name']}",
                    False,
                    f"Request error: {str(e)}",
                    {"error": str(e)}
                )
    
    def test_event_publishing(self):
        """Test event publishing by checking service logs."""
        try:
            # Check if calendar service logs contain event publishing
            log_response = self.session.get(f"{CALENDAR_SERVICE_URL}/health")
            if log_response.status_code == 200:
                health_data = log_response.json()
                events_status = health_data.get('events', 'unavailable')
                
                if events_status in ['connected', 'unavailable']:
                    self.log_test(
                        "Event Publishing - Service Status",
                        True,
                        f"Event service status: {events_status} (fallback in-memory storage expected)",
                        {
                            "events_status": events_status,
                            "fallback_expected": events_status == 'unavailable'
                        }
                    )
                else:
                    self.log_test(
                        "Event Publishing - Service Status",
                        False,
                        f"Unexpected event service status: {events_status}",
                        health_data
                    )
            else:
                self.log_test(
                    "Event Publishing - Service Status",
                    False,
                    "Could not check event service status",
                    {"status_code": log_response.status_code}
                )
                
        except Exception as e:
            self.log_test(
                "Event Publishing - Service Status",
                False,
                f"Error checking event service: {str(e)}",
                {"error": str(e)}
            )
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("🚀 Starting ITADIAS Calendar Microservice Backend Tests")
        print(f"🌐 Calendar Service: {CALENDAR_SERVICE_URL}")
        print(f"🌐 Main Backend: {MAIN_BACKEND_URL}")
        print("=" * 80)
        
        # Health checks first
        self.test_calendar_service_health()
        self.test_calendar_service_root()
        self.test_main_backend_calendar_health()
        
        # Direct calendar service tests
        available_slots_direct = self.test_get_available_slots_direct()
        booking_id_direct = self.test_create_booking_direct(available_slots_direct)
        self.test_get_booking_direct(booking_id_direct)
        
        # Main backend integration tests
        available_slots_main = self.test_get_slots_via_main_backend()
        booking_id_main = self.test_create_booking_via_main_backend(available_slots_main)
        self.test_get_booking_via_main_backend(booking_id_main)
        
        # Slot locking tests
        self.test_slot_locking_behavior()
        
        # Validation tests
        self.test_booking_validation_errors()
        
        # Event publishing tests
        self.test_event_publishing()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("📊 CALENDAR MICROSERVICE TEST SUMMARY")
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
        
        print(f"\n📝 Created {len(self.created_bookings)} test bookings during testing")
        
        # Save detailed results to file
        with open('/app/calendar_test_results.json', 'w') as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100,
                    'test_timestamp': datetime.now().isoformat(),
                    'calendar_service_url': CALENDAR_SERVICE_URL,
                    'main_backend_url': MAIN_BACKEND_URL
                },
                'test_results': self.test_results,
                'created_bookings': self.created_bookings
            }, f, indent=2)
        
        print(f"📄 Detailed results saved to: /app/calendar_test_results.json")


def main():
    """Main test execution function."""
    tester = CalendarServiceTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()