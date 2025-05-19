"""
JWT token handling for authentication.

This module provides functions for generating, validating, and refreshing JWT tokens.
"""

import os
import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union

from core.utils.error_handling import AuthenticationError, AuthorizationError
from core.config import config

# JWT settings
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", config.get("JWT_SECRET_KEY", "dev-jwt-secret"))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", config.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30)))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", config.get("REFRESH_TOKEN_EXPIRE_DAYS", 7)))


def create_access_token(
    subject: Union[str, int],
    scopes: List[str] = None,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Dict[str, Any] = None
) -> str:
    """
    Create a new JWT access token.
    
    Args:
        subject: The subject of the token (usually user ID)
        scopes: List of permission scopes
        expires_delta: Optional custom expiration time
        additional_claims: Additional claims to include in the token
        
    Returns:
        str: Encoded JWT token
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    expire = datetime.utcnow() + expires_delta
    
    # Base claims
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    # Add scopes if provided
    if scopes:
        to_encode["scopes"] = scopes
        
    # Add any additional claims
    if additional_claims:
        to_encode.update(additional_claims)
        
    # Encode the JWT
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, int],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a new JWT refresh token.
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT refresh token
    """
    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
    expire = datetime.utcnow() + expires_delta
    
    # Base claims for refresh token
    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
        
    # Encode the JWT
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: The JWT token to decode
        
    Returns:
        Dict[str, Any]: The decoded token claims
        
    Raises:
        AuthenticationError: If the token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify a token and check its type.
    
    Args:
        token: The JWT token to verify
        token_type: The expected token type ('access' or 'refresh')
        
    Returns:
        Dict[str, Any]: The decoded token claims
        
    Raises:
        AuthenticationError: If the token is invalid, expired, or of wrong type
    """
    payload = decode_token(token)
    
    # Check token type
    if payload.get("type") != token_type:
        raise AuthenticationError(f"Invalid token type. Expected {token_type} token.")
    
    return payload


def get_token_expiration(token: str) -> datetime:
    """
    Get the expiration time of a token.
    
    Args:
        token: The JWT token
        
    Returns:
        datetime: The expiration time
        
    Raises:
        AuthenticationError: If the token is invalid
    """
    payload = decode_token(token)
    exp = payload.get("exp")
    if not exp:
        raise AuthenticationError("Token has no expiration")
    
    return datetime.fromtimestamp(exp)


def has_scope(token: str, required_scope: str) -> bool:
    """
    Check if a token has a specific scope.
    
    Args:
        token: The JWT token
        required_scope: The scope to check for
        
    Returns:
        bool: True if the token has the required scope
        
    Raises:
        AuthenticationError: If the token is invalid
        AuthorizationError: If the token doesn't have the required scope
    """
    payload = decode_token(token)
    scopes = payload.get("scopes", [])
    
    if required_scope in scopes:
        return True
    
    raise AuthorizationError(f"Token does not have the required scope: {required_scope}")


def get_token_subject(token: str) -> str:
    """
    Get the subject from a token.
    
    Args:
        token: The JWT token
        
    Returns:
        str: The subject (usually user ID)
        
    Raises:
        AuthenticationError: If the token is invalid or has no subject
    """
    payload = decode_token(token)
    subject = payload.get("sub")
    
    if not subject:
        raise AuthenticationError("Token has no subject")
    
    return subject

