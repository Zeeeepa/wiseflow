"""
Authentication middleware for WiseFlow.

This module provides middleware for authenticating requests using:
- JWT tokens (OAuth 2.0)
- API keys (legacy)
- Role-based access control
"""

import os
from typing import Optional, List, Callable, Dict, Any, Union
from functools import wraps

from fastapi import Request, HTTPException, Depends, Header, status
from fastapi.security import OAuth2PasswordBearer, OAuth2AuthorizationCodeBearer
from sqlalchemy.orm import Session

from core.auth.jwt import decode_token, verify_token, has_scope
from core.auth.models import User, Role, Permission
from core.auth.rbac import has_permission, get_user_permissions
from core.utils.error_handling import AuthenticationError, AuthorizationError
from core.config import config

# API key for backward compatibility
API_KEY = os.environ.get("WISEFLOW_API_KEY", config.get("WISEFLOW_API_KEY", "dev-api-key"))

# OAuth2 token URL
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/oauth/token")


async def get_db():
    """
    Get database session.
    
    This is a placeholder - implement actual database session management.
    """
    # TODO: Implement actual database session management
    db = None  # Replace with actual DB session
    try:
        yield db
    finally:
        if db:
            db.close()


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from a JWT token.
    
    Args:
        token: JWT token
        db: Database session
        
    Returns:
        User: The authenticated user
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    try:
        # Verify the token is valid
        payload = verify_token(token, token_type="access")
        user_id = payload.get("sub")
        
        if not user_id:
            raise AuthenticationError("Invalid token payload")
        
        # Get the user from the database
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        
        if not user:
            raise AuthenticationError("User not found or inactive")
        
        return user
    except Exception as e:
        raise AuthenticationError(f"Authentication failed: {str(e)}")


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.
    
    Args:
        token: Optional JWT token
        db: Database session
        
    Returns:
        Optional[User]: The authenticated user or None
    """
    if not token:
        return None
    
    try:
        return await get_current_user(token, db)
    except Exception:
        return None


async def verify_api_key(x_api_key: str = Header(None)) -> bool:
    """
    Verify the API key for backward compatibility.
    
    Args:
        x_api_key: API key from header
        
    Returns:
        bool: True if API key is valid
        
    Raises:
        AuthenticationError: If API key is invalid
    """
    if not x_api_key or x_api_key != API_KEY:
        raise AuthenticationError("Invalid API key")
    return True


class RBACMiddleware:
    """Middleware for role-based access control."""
    
    def __init__(self, required_permission: str = None, required_role: str = None):
        """
        Initialize the RBAC middleware.
        
        Args:
            required_permission: Required permission (e.g., "users:read")
            required_role: Required role (e.g., "admin")
        """
        self.required_permission = required_permission
        self.required_role = required_role
    
    async def __call__(
        self,
        request: Request,
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> bool:
        """
        Check if the user has the required permission or role.
        
        Args:
            request: FastAPI request
            user: Authenticated user
            db: Database session
            
        Returns:
            bool: True if user has the required permission or role
            
        Raises:
            AuthorizationError: If user doesn't have the required permission or role
        """
        if self.required_permission:
            if not has_permission(user, self.required_permission, db):
                raise AuthorizationError(f"User does not have the required permission: {self.required_permission}")
        
        if self.required_role:
            user_roles = [role.name for role in user.roles]
            if self.required_role not in user_roles:
                raise AuthorizationError(f"User does not have the required role: {self.required_role}")
        
        return True


def require_permission(permission: str):
    """
    Decorator to require a specific permission.
    
    Args:
        permission: Required permission (e.g., "users:read")
        
    Returns:
        Callable: Dependency that checks for the required permission
    """
    return RBACMiddleware(required_permission=permission)


def require_role(role: str):
    """
    Decorator to require a specific role.
    
    Args:
        role: Required role (e.g., "admin")
        
    Returns:
        Callable: Dependency that checks for the required role
    """
    return RBACMiddleware(required_role=role)


def require_scope(scope: str):
    """
    Decorator to require a specific OAuth scope.
    
    Args:
        scope: Required scope (e.g., "read:users")
        
    Returns:
        Callable: Function that checks for the required scope
    """
    def dependency(token: str = Depends(oauth2_scheme)):
        try:
            return has_scope(token, scope)
        except Exception as e:
            raise AuthorizationError(f"Scope check failed: {str(e)}")
    
    return dependency


class AuthBackend:
    """
    Authentication backend that supports both JWT and API key authentication.
    
    This allows for backward compatibility during the transition to OAuth.
    """
    
    async def authenticate(
        self,
        request: Request,
        db: Session = Depends(get_db)
    ) -> Optional[User]:
        """
        Authenticate a request using either JWT or API key.
        
        Args:
            request: FastAPI request
            db: Database session
            
        Returns:
            Optional[User]: Authenticated user or None
            
        Raises:
            AuthenticationError: If authentication fails
        """
        # Try JWT authentication first
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            try:
                payload = verify_token(token, token_type="access")
                user_id = payload.get("sub")
                
                if user_id:
                    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
                    if user:
                        return user
            except Exception:
                pass  # Fall through to API key authentication
        
        # Try API key authentication
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key == API_KEY:
            # For API key auth, we don't have a specific user
            # Could return a system user or None depending on requirements
            return None
        
        # No valid authentication found
        raise AuthenticationError("Authentication required")


# Convenience function to get the authentication backend
def get_auth_backend():
    """Get the authentication backend."""
    return AuthBackend()

