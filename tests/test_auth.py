"""
Tests for the authentication system.
"""

import os
import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from core.auth.jwt import (
    create_access_token, create_refresh_token,
    decode_token, verify_token, has_scope
)
from core.auth.models import (
    User, Role, Permission, OAuthClient, 
    AuthorizationCode, RefreshToken
)
from core.auth.oauth import OAuth2Provider
from core.auth.middleware import (
    get_current_user, verify_api_key,
    require_permission, require_role
)
from core.auth.rbac import (
    has_permission, has_role, get_user_permissions
)
from core.auth.password import (
    get_password_hash, verify_password, 
    check_password_strength
)
from core.utils.error_handling import AuthenticationError, AuthorizationError


# JWT token tests
def test_create_access_token():
    """Test creating an access token."""
    token = create_access_token(subject="123", scopes=["read", "write"])
    assert token is not None
    
    # Decode the token and verify claims
    payload = jwt.decode(token, os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret"), algorithms=["HS256"])
    assert payload["sub"] == "123"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload
    assert payload["scopes"] == ["read", "write"]


def test_create_refresh_token():
    """Test creating a refresh token."""
    token = create_refresh_token(subject="123")
    assert token is not None
    
    # Decode the token and verify claims
    payload = jwt.decode(token, os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret"), algorithms=["HS256"])
    assert payload["sub"] == "123"
    assert payload["type"] == "refresh"
    assert "exp" in payload
    assert "iat" in payload


def test_verify_token():
    """Test verifying a token."""
    # Create a token
    token = create_access_token(subject="123")
    
    # Verify the token
    payload = verify_token(token, token_type="access")
    assert payload["sub"] == "123"
    
    # Test with wrong token type
    with pytest.raises(AuthenticationError):
        verify_token(token, token_type="refresh")


def test_has_scope():
    """Test checking token scopes."""
    # Create a token with scopes
    token = create_access_token(subject="123", scopes=["read", "write"])
    
    # Check for a scope that exists
    assert has_scope(token, "read") is True
    
    # Check for a scope that doesn't exist
    with pytest.raises(AuthorizationError):
        has_scope(token, "admin")


# Password tests
def test_password_hashing():
    """Test password hashing and verification."""
    password = "SecurePassword123!"
    hashed = get_password_hash(password)
    
    # Verify the password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_password_strength():
    """Test password strength checker."""
    # Strong password
    assert check_password_strength("SecurePassword123!") is True
    
    # Weak passwords
    assert check_password_strength("password") is False  # No uppercase, digits, or special chars
    assert check_password_strength("Password") is False  # No digits or special chars
    assert check_password_strength("Password123") is False  # No special chars
    assert check_password_strength("pass!") is False  # Too short


# RBAC tests
def test_has_permission():
    """Test permission checking."""
    # Create mock user, role, and permission
    permission = MagicMock(spec=Permission)
    permission.name = "users:read"
    
    role = MagicMock(spec=Role)
    role.permissions = [permission]
    
    user = MagicMock(spec=User)
    user.roles = [role]
    
    db = MagicMock()
    
    # Test permission check
    assert has_permission(user, "users:read", db) is True
    assert has_permission(user, "users:write", db) is False


def test_has_role():
    """Test role checking."""
    # Create mock user and role
    role = MagicMock(spec=Role)
    role.name = "admin"
    
    user = MagicMock(spec=User)
    user.roles = [role]
    
    # Test role check
    assert has_role(user, "admin") is True
    assert has_role(user, "user") is False


def test_get_user_permissions():
    """Test getting all user permissions."""
    # Create mock permissions
    perm1 = MagicMock(spec=Permission)
    perm1.name = "users:read"
    
    perm2 = MagicMock(spec=Permission)
    perm2.name = "users:write"
    
    # Create mock roles with permissions
    role1 = MagicMock(spec=Role)
    role1.permissions = [perm1]
    
    role2 = MagicMock(spec=Role)
    role2.permissions = [perm2]
    
    # Create mock user with roles
    user = MagicMock(spec=User)
    user.roles = [role1, role2]
    
    db = MagicMock()
    
    # Get user permissions
    permissions = get_user_permissions(user, db)
    
    # Verify permissions
    assert "users:read" in permissions
    assert "users:write" in permissions
    assert len(permissions) == 2


# OAuth tests
@patch('core.auth.oauth.create_access_token')
@patch('core.auth.oauth.create_refresh_token')
def test_oauth_provider_password_grant(mock_refresh_token, mock_access_token):
    """Test OAuth password grant."""
    # Mock tokens
    mock_access_token.return_value = "access-token"
    mock_refresh_token.return_value = "refresh-token"
    
    # Mock database session
    db = MagicMock()
    
    # Mock user
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.password_hash = get_password_hash("password")
    user.is_active = True
    
    # Mock client
    client = MagicMock(spec=OAuthClient)
    client.client_id = "test-client"
    client.client_secret = "test-secret"
    client.is_confidential = True
    client.allowed_scopes = "read,write"
    
    # Mock query results
    db.query.return_value.filter.return_value.first.side_effect = [client, user]
    
    # Create OAuth provider
    provider = OAuth2Provider(db)
    
    # Test password grant
    result = provider.password_grant(
        username="testuser",
        password="password",
        client_id="test-client",
        client_secret="test-secret",
        scope="read"
    )
    
    # Verify result
    assert result.access_token == "access-token"
    assert result.token_type == "bearer"
    assert result.refresh_token == "refresh-token"
    
    # Verify token creation calls
    mock_access_token.assert_called_once()
    mock_refresh_token.assert_called_once()
    
    # Verify database operations
    db.add.assert_called_once()
    db.commit.assert_called()


# Middleware tests
@patch('core.auth.middleware.verify_token')
def test_get_current_user(mock_verify_token):
    """Test getting the current user from a token."""
    # Mock token verification
    mock_verify_token.return_value = {"sub": "1", "type": "access"}
    
    # Mock database session
    db = MagicMock()
    
    # Mock user
    user = MagicMock(spec=User)
    user.id = 1
    user.is_active = True
    
    # Mock query result
    db.query.return_value.filter.return_value.first.return_value = user
    
    # Test getting current user
    result = get_current_user("token", db)
    
    # Verify result
    assert result == user
    
    # Verify token verification
    mock_verify_token.assert_called_once_with("token", token_type="access")


def test_verify_api_key():
    """Test API key verification."""
    # Test with valid API key
    with patch.dict(os.environ, {"WISEFLOW_API_KEY": "test-api-key"}):
        assert verify_api_key("test-api-key") is True
    
    # Test with invalid API key
    with patch.dict(os.environ, {"WISEFLOW_API_KEY": "test-api-key"}):
        with pytest.raises(AuthenticationError):
            verify_api_key("invalid-api-key")


# Integration tests
def test_full_authentication_flow():
    """Test the full authentication flow."""
    # This would be an integration test that tests the entire flow
    # from login to token generation to authenticated API access
    # For now, we'll just mark it as a placeholder
    pass

