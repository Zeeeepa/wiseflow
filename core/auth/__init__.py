"""
Authentication and authorization module for WiseFlow.

This module provides authentication and authorization utilities for the API server and dashboard.
"""

import os
import time
import logging
import hashlib
import hmac
import base64
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, status, Header, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader

logger = logging.getLogger(__name__)

# JWT configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-jwt-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 24 * 60 * 60  # 24 hours

# API key configuration
API_KEY = os.environ.get("WISEFLOW_API_KEY", "dev-api-key")
api_key_header = APIKeyHeader(name="X-API-Key")

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class User:
    """User model for authentication."""
    
    def __init__(
        self,
        user_id: str,
        username: str,
        email: Optional[str] = None,
        roles: Optional[List[str]] = None,
        is_active: bool = True
    ):
        """Initialize a user.
        
        Args:
            user_id: User ID
            username: Username
            email: Email address
            roles: User roles
            is_active: Whether the user is active
        """
        self.user_id = user_id
        self.username = username
        self.email = email
        self.roles = roles or []
        self.is_active = is_active
    
    def has_role(self, role: str) -> bool:
        """Check if the user has a specific role.
        
        Args:
            role: Role to check
            
        Returns:
            bool: True if the user has the role
        """
        return role in self.roles
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the user to a dictionary.
        
        Returns:
            Dict[str, Any]: User data
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "roles": self.roles,
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create a user from a dictionary.
        
        Args:
            data: User data
            
        Returns:
            User: User instance
        """
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            email=data.get("email"),
            roles=data.get("roles", []),
            is_active=data.get("is_active", True)
        )

def create_jwt_token(user: User) -> str:
    """Create a JWT token for a user.
    
    Args:
        user: User instance
        
    Returns:
        str: JWT token
    """
    payload = {
        "sub": user.user_id,
        "username": user.username,
        "roles": user.roles,
        "exp": datetime.utcnow() + timedelta(seconds=JWT_EXPIRATION)
    }
    
    if user.email:
        payload["email"] = user.email
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Dict[str, Any]:
    """Decode a JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        Dict[str, Any]: Token payload
        
    Raises:
        HTTPException: If the token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get the current user from a JWT token.
    
    Args:
        token: JWT token
        
    Returns:
        User: User instance
        
    Raises:
        HTTPException: If the token is invalid or the user is inactive
    """
    payload = decode_jwt_token(token)
    
    user = User(
        user_id=payload["sub"],
        username=payload["username"],
        email=payload.get("email"),
        roles=payload.get("roles", []),
        is_active=True
    )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

def verify_api_key(api_key: str = Depends(api_key_header)) -> bool:
    """Verify the API key.
    
    Args:
        api_key: API key
        
    Returns:
        bool: True if valid
        
    Raises:
        HTTPException: If the API key is invalid
    """
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return True

def has_role(required_role: str):
    """Dependency for role-based authorization.
    
    Args:
        required_role: Required role
        
    Returns:
        Callable: Dependency function
    """
    async def _has_role(user: User = Depends(get_current_user)) -> bool:
        if not user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {required_role} required"
            )
        return True
    
    return _has_role

def verify_webhook_signature(request: Request, webhook_secret: str) -> bool:
    """Verify a webhook signature.
    
    Args:
        request: Request object
        webhook_secret: Webhook secret
        
    Returns:
        bool: True if valid
    """
    signature_header = request.headers.get("X-Webhook-Signature")
    if not signature_header:
        return False
    
    # Get the request body
    body = await request.body()
    
    # Compute the expected signature
    expected_signature = hmac.new(
        webhook_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Compare signatures
    return hmac.compare_digest(signature_header, expected_signature)
"""

