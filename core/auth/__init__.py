"""
Authentication module for WiseFlow.

This module provides OAuth 2.0 authentication with JWT tokens and role-based access control.
"""

from core.auth.models import (
    User, Role, Permission, OAuthClient, 
    AuthorizationCode, RefreshToken,
    TokenResponse, TokenRequest
)
from core.auth.jwt import (
    create_access_token, create_refresh_token,
    decode_token, verify_token, has_scope
)
from core.auth.oauth import OAuth2Provider
from core.auth.middleware import (
    get_current_user, get_optional_user, verify_api_key,
    RBACMiddleware, require_permission, require_role, require_scope
)
from core.auth.rbac import (
    get_user_roles, get_role_permissions, get_user_permissions,
    has_permission, has_role, check_permission, check_role
)
from core.auth.password import (
    get_password_hash, verify_password, 
    generate_password_reset_token, generate_random_password
)

