#!/usr/bin/env python3
"""
Focused Registration Microservice Test
Test core registration functionality now that external services are available
"""

import requests
import json
import uuid
import base64
from datetime import datetime

# Test configuration
REGISTRATION_SERVICE_URL = "http://localhost:8004"
API_BASE = f"{REGISTRATION_SERVICE_URL}/api/v1"

def create_test_document_base64(doc_type: str) -> str:
    """Create a small test document in base64 format"""
    if doc_type in ["photo"]:
        # Create a minimal JPEG-like content
        content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    else:
        # Create a minimal PDF-like content for medical certificates
        content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF'
    
    return base64.b64encode(content).decode('utf-8')

def test_registration_with_valid_external_services():
    """Test registration with valid external service data"""
    
    # First, let's create a valid booking in the calendar service
    calendar_response = requests.get("http://localhost:8002/api/v1/slots?hub_id=signup-system-2&date=2024-12-20")
    print(f"Calendar slots response: {calendar_response.status_code}")
    
    if calendar_response.status_code == 200:
        slots_data = calendar_response.json()
        print(f"Available slots: {len(slots_data.get('slots', []))}")
        
        if slots_data.get('slots'):
            # Use the first available slot
            slot_id = slots_data['slots'][0]['id']
            
            # Create a booking
            booking_data = {
                "slot_id": slot_id,
                "candidate_id": str(uuid.uuid4()),
                "contact_email": "test@example.com",
                "contact_phone": "+1234567890"
            }
            
            booking_response = requests.post(
                "http://localhost:8002/api/v1/bookings",
                json=booking_data
            )
            print(f"Booking creation response: {booking_response.status_code}")
            
            if booking_response.status_code in [200, 201]:
                booking_result = booking_response.json()
                booking_id = booking_result.get('booking', {}).get('id')
                print(f"Created booking: {booking_id}")
                
                # Now create a valid receipt
                receipt_data = {
                    "receipt_no": f"TAJ{int(datetime.now().timestamp())}",
                    "issue_date": "2024-12-19",
                    "location": "Hamilton",
                    "amount": 150.00
                }
                
                receipt_response = requests.post(
                    "http://localhost:8003/api/v1/receipts/validate",
                    json=receipt_data
                )
                print(f"Receipt validation response: {receipt_response.status_code}")
                
                if receipt_response.status_code in [200, 201]:
                    receipt_result = receipt_response.json()
                    print(f"Receipt validation: {receipt_result.get('success')}")
                    
                    # Now test registration with valid external data
                    registration_data = {
                        "booking_id": booking_id,
                        "receipt_no": receipt_data["receipt_no"],
                        "vehicle_weight_kg": 2000,
                        "vehicle_category": "B",
                        "docs": [
                            {
                                "type": "photo",
                                "filename": "photo.jpg",
                                "content": create_test_document_base64("photo"),
                                "mime_type": "image/jpeg"
                            },
                            {
                                "type": "id_proof",
                                "filename": "id_proof.jpg",
                                "content": create_test_document_base64("id_proof"),
                                "mime_type": "image/jpeg"
                            }
                        ],
                        "manager_override": False
                    }
                    
                    headers = {
                        "Authorization": "Bearer test-jwt-token-12345",
                        "Content-Type": "application/json"
                    }
                    
                    registration_response = requests.post(
                        f"{API_BASE}/registrations",
                        json=registration_data,
                        headers=headers
                    )
                    
                    print(f"Registration response: {registration_response.status_code}")
                    print(f"Registration result: {registration_response.json()}")
                    
                    return registration_response.status_code in [200, 201]
    
    return False

def test_age_validation_with_external_services():
    """Test age validation scenarios with external services available"""
    
    # Test underage Class B candidate
    registration_data = {
        "booking_id": str(uuid.uuid4()),  # Will fail external validation but should hit age validation first
        "receipt_no": "TESTRECEIPT123",
        "vehicle_weight_kg": 2000,
        "vehicle_category": "B",
        "docs": [
            {
                "type": "photo",
                "filename": "photo.jpg",
                "content": create_test_document_base64("photo"),
                "mime_type": "image/jpeg"
            },
            {
                "type": "id_proof",
                "filename": "id_proof.jpg",
                "content": create_test_document_base64("id_proof"),
                "mime_type": "image/jpeg"
            }
        ],
        "manager_override": False
    }
    
    headers = {
        "Authorization": "Bearer test-jwt-token-12345",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE}/registrations",
        json=registration_data,
        headers=headers
    )
    
    print(f"Age validation test response: {response.status_code}")
    result = response.json()
    print(f"Age validation result: {result}")
    
    # Check if age validation is working
    if "age" in result.get("message", "").lower() or any("age" in error.lower() for error in result.get("validation_errors", [])):
        print("✅ Age validation is working")
        return True
    else:
        print("❌ Age validation may not be working as expected")
        return False

def test_medical_certificate_validation():
    """Test medical certificate validation"""
    
    # Test Class C without MC2
    registration_data = {
        "booking_id": str(uuid.uuid4()),
        "receipt_no": "TESTRECEIPT456",
        "vehicle_weight_kg": 8000,  # Over 7000kg threshold
        "vehicle_category": "C",
        "docs": [
            {
                "type": "photo",
                "filename": "photo.jpg",
                "content": create_test_document_base64("photo"),
                "mime_type": "image/jpeg"
            },
            {
                "type": "id_proof",
                "filename": "id_proof.jpg",
                "content": create_test_document_base64("id_proof"),
                "mime_type": "image/jpeg"
            }
            # Missing MC2
        ],
        "manager_override": False
    }
    
    headers = {
        "Authorization": "Bearer test-jwt-token-12345",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{API_BASE}/registrations",
        json=registration_data,
        headers=headers
    )
    
    print(f"Medical certificate validation response: {response.status_code}")
    result = response.json()
    print(f"Medical certificate result: {result}")
    
    # Check if medical certificate validation is working
    if "medical" in result.get("message", "").lower() or any("medical" in error.lower() or "mc2" in error.lower() for error in result.get("validation_errors", [])):
        print("✅ Medical certificate validation is working")
        return True
    else:
        print("❌ Medical certificate validation may not be working as expected")
        return False

def main():
    """Run focused tests"""
    print("🚀 Running Focused Registration Tests")
    print("=" * 50)
    
    # Test health first
    health_response = requests.get(f"{REGISTRATION_SERVICE_URL}/health")
    print(f"Health check: {health_response.status_code}")
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"Dependencies available: {health_data.get('dependencies', {}).get('all_dependencies_available', False)}")
    
    print("\n1. Testing registration with valid external services...")
    success1 = test_registration_with_valid_external_services()
    
    print("\n2. Testing age validation...")
    success2 = test_age_validation_with_external_services()
    
    print("\n3. Testing medical certificate validation...")
    success3 = test_medical_certificate_validation()
    
    print(f"\n📊 Results:")
    print(f"Valid registration: {'✅' if success1 else '❌'}")
    print(f"Age validation: {'✅' if success2 else '❌'}")
    print(f"Medical validation: {'✅' if success3 else '❌'}")

if __name__ == "__main__":
    main()