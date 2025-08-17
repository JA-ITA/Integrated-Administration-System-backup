#!/usr/bin/env python3
"""
Registration Validation Test
Test the validation flow step by step
"""

import requests
import json
import uuid
import base64
from datetime import datetime

def create_test_document_base64(doc_type: str) -> str:
    """Create a small test document in base64 format"""
    if doc_type in ["photo"]:
        content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
    else:
        content = b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n174\n%%EOF'
    
    return base64.b64encode(content).decode('utf-8')

def test_step_by_step():
    """Test the registration process step by step"""
    
    print("Step 1: Get available slots from Calendar service")
    slots_response = requests.get("http://localhost:8002/api/v1/slots?hub=signup-system-2&date=2024-12-20")
    print(f"Slots response: {slots_response.status_code}")
    
    if slots_response.status_code == 200:
        slots = slots_response.json()
        print(f"Available slots: {len(slots)}")
        
        if slots:
            slot_id = slots[0]['id']
            print(f"Using slot: {slot_id}")
            
            print("\nStep 2: Create a booking")
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
            print(f"Booking response: {booking_response.status_code}")
            print(f"Booking result: {booking_response.json()}")
            
            if booking_response.status_code in [200, 201]:
                booking_result = booking_response.json()
                booking_id = booking_result.get('booking', {}).get('id')
                print(f"Created booking ID: {booking_id}")
                
                print("\nStep 3: Validate a receipt")
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
                print(f"Receipt response: {receipt_response.status_code}")
                print(f"Receipt result: {receipt_response.json()}")
                
                if receipt_response.status_code in [200, 201]:
                    print("\nStep 4: Test registration with valid external data")
                    
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
                        "http://localhost:8004/api/v1/registrations",
                        json=registration_data,
                        headers=headers
                    )
                    
                    print(f"Registration response: {registration_response.status_code}")
                    result = registration_response.json()
                    print(f"Registration result: {json.dumps(result, indent=2)}")
                    
                    if result.get('success'):
                        print("✅ Registration successful!")
                        return result.get('registration', {}).get('id')
                    else:
                        print("❌ Registration failed")
                        return None
                else:
                    print("❌ Receipt validation failed")
            else:
                print("❌ Booking creation failed")
    else:
        print("❌ Failed to get slots")
    
    return None

def test_age_validation_directly():
    """Test age validation by bypassing external services"""
    print("\nTesting age validation with invalid external data (should hit age validation first)")
    
    # Test with underage candidate for Class B (< 17 years)
    registration_data = {
        "booking_id": str(uuid.uuid4()),  # Invalid booking
        "receipt_no": "INVALID123",       # Invalid receipt
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
        "http://localhost:8004/api/v1/registrations",
        json=registration_data,
        headers=headers
    )
    
    print(f"Age validation test response: {response.status_code}")
    result = response.json()
    print(f"Result: {json.dumps(result, indent=2)}")

def main():
    print("🚀 Registration Validation Step-by-Step Test")
    print("=" * 50)
    
    # Check service health
    health_response = requests.get("http://localhost:8004/health")
    if health_response.status_code == 200:
        health_data = health_response.json()
        print(f"Registration service: {health_data.get('status')}")
        print(f"Dependencies available: {health_data.get('dependencies', {}).get('all_dependencies_available')}")
        print()
    
    # Test step by step
    registration_id = test_step_by_step()
    
    # Test age validation
    test_age_validation_directly()
    
    if registration_id:
        print(f"\n✅ Successfully created registration: {registration_id}")
    else:
        print("\n❌ No registration was created")

if __name__ == "__main__":
    main()