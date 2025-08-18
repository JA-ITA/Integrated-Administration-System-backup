#!/usr/bin/env python3
"""
Debug JWT token generation for audit service
"""
import jwt
import uuid
from datetime import datetime, timedelta

# Same configuration as audit service
JWT_SECRET = "your-secret-key-here"
JWT_ALGORITHM = "HS256"

def generate_rd_jwt_token(user_id: str = None, role: str = "rd", expires_in_hours: int = 1) -> str:
    """Generate a mock RD JWT token for testing"""
    if not user_id:
        user_id = str(uuid.uuid4())
        
    payload = {
        "user_id": user_id,
        "role": role,
        "iat": datetime.utcnow().timestamp(),
        "exp": (datetime.utcnow() + timedelta(hours=expires_in_hours)).timestamp()
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    print(f"Generated token: {token}")
    
    # Decode to verify
    decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    print(f"Decoded payload: {decoded}")
    
    return token

if __name__ == "__main__":
    token = generate_rd_jwt_token()
    
    # Test with httpx
    import asyncio
    import httpx
    
    async def test_token():
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            override_data = {
                "resource_type": "RECEIPT",
                "resource_id": str(uuid.uuid4()),
                "new_status": "APPROVED",
                "reason": "Testing JWT token generation and validation"
            }
            
            response = await client.post(
                "http://localhost:8008/api/v1/overrides/",
                json=override_data,
                headers=headers
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
    
    asyncio.run(test_token())