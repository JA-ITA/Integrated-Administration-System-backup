"""
Authentication service for JWT validation with Identity microservice
"""
import jwt
import httpx
import logging
from datetime import datetime
from typing import Optional
from fastapi import HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import config
from models import RDAuthUser, JWTPayload, ActorRole

logger = logging.getLogger(__name__)

security = HTTPBearer()

class AuthService:
    """Authentication service for RD JWT validation"""
    
    def __init__(self):
        self.identity_service_url = config.identity.service_url
        self.jwt_secret = config.identity.jwt_secret
        self.jwt_algorithm = config.identity.jwt_algorithm
    
    async def validate_jwt_token(self, token: str) -> Optional[RDAuthUser]:
        """Validate JWT token and return user info"""
        try:
            # Decode JWT token
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm]
            )
            
            # Validate token structure
            jwt_payload = JWTPayload(**payload)
            
            # Check if token is expired
            current_timestamp = datetime.utcnow().timestamp()
            if jwt_payload.exp < current_timestamp:
                logger.warning("JWT token expired")
                return None
            
            # Verify role is Regional Director
            if jwt_payload.role != ActorRole.RD.value:
                logger.warning(f"Invalid role for audit operations: {jwt_payload.role}")
                return None
            
            return RDAuthUser(
                user_id=jwt_payload.user_id,
                role=jwt_payload.role
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return None
    
    async def verify_with_identity_service(self, token: str) -> Optional[dict]:
        """Verify token with identity microservice (fallback)"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.identity_service_url}/api/v1/auth/verify",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"require_role": "rd"}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Identity service verification failed: {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.warning("Identity service timeout during token verification")
            return None
        except Exception as e:
            logger.error(f"Error verifying token with identity service: {e}")
            return None

# Global auth service instance
auth_service = AuthService()

async def get_current_rd_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> RDAuthUser:
    """Dependency to get current authenticated RD user"""
    try:
        token = credentials.credentials
        
        # Try local JWT validation first
        user = await auth_service.validate_jwt_token(token)
        
        if not user:
            # Fallback to identity service verification
            identity_response = await auth_service.verify_with_identity_service(token)
            if identity_response and identity_response.get("valid") and identity_response.get("role") == "rd":
                user = RDAuthUser(
                    user_id=identity_response["user_id"],
                    role=identity_response["role"]
                )
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired RD authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=401,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )