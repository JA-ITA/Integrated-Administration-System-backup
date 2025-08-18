#!/usr/bin/env python3
"""
Test JWT validation exactly as the audit service does it
"""
import jwt
import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel

# Same configuration as audit service
JWT_SECRET = "your-secret-key-here"
JWT_ALGORITHM = "HS256"

class JWTPayload(BaseModel):
    """JWT payload schema for validation"""
    user_id: uuid.UUID
    role: str
    exp: int
    iat: int

class RDAuthUser(BaseModel):
    """Authenticated RD user info"""
    user_id: uuid.UUID
    role: str

def test_jwt_validation():
    """Test JWT validation exactly as audit service does"""
    
    # Generate token
    user_id = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "role": "rd",
        "iat": int(datetime.utcnow().timestamp()),
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp())
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    print(f"Generated token: {token}")
    print(f"Payload: {payload}")
    
    try:
        # Decode JWT token (same as audit service)
        decoded_payload = jwt.decode(
            token, 
            JWT_SECRET, 
            algorithms=[JWT_ALGORITHM]
        )
        print(f"Decoded payload: {decoded_payload}")
        
        # Validate token structure (same as audit service)
        jwt_payload = JWTPayload(**decoded_payload)
        print(f"Validated JWT payload: {jwt_payload}")
        
        # Check if token is expired
        current_timestamp = datetime.utcnow().timestamp()
        if jwt_payload.exp < current_timestamp:
            print("JWT token expired")
            return None
        
        # Verify role is Regional Director
        if jwt_payload.role != "rd":
            print(f"Invalid role for audit operations: {jwt_payload.role}")
            return None
        
        user = RDAuthUser(
            user_id=jwt_payload.user_id,
            role=jwt_payload.role
        )
        print(f"Successfully validated user: {user}")
        return user
        
    except Exception as e:
        print(f"JWT validation error: {e}")
        return None

if __name__ == "__main__":
    test_jwt_validation()