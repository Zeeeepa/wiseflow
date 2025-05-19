"""
User and authentication models for the OAuth 2.0 implementation.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, EmailStr, validator
import uuid
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, 
    ForeignKey, Table, Text, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# Association tables for many-to-many relationships
user_roles = Table(
    'user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('role_id', Integer, ForeignKey('roles.id'))
)

role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)


class User(Base):
    """User model for authentication and authorization."""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    roles = relationship("Role", secondary=user_roles, back_populates="users")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    oauth_clients = relationship("OAuthClient", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"


class Role(Base):
    """Role model for role-based access control."""
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

    def __repr__(self):
        return f"<Role {self.name}>"


class Permission(Base):
    """Permission model for fine-grained access control."""
    __tablename__ = 'permissions'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    resource = Column(String(50), nullable=False)  # e.g., 'users', 'webhooks'
    action = Column(String(50), nullable=False)    # e.g., 'read', 'write', 'delete'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

    def __repr__(self):
        return f"<Permission {self.name}>"


class OAuthClient(Base):
    """OAuth client model for client credentials."""
    __tablename__ = 'oauth_clients'

    id = Column(Integer, primary_key=True)
    client_id = Column(String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    client_secret = Column(String(100), nullable=False)
    client_name = Column(String(100), nullable=False)
    redirect_uris = Column(Text, nullable=True)  # Comma-separated list of URIs
    allowed_grant_types = Column(String(255), nullable=False)  # Comma-separated list
    allowed_scopes = Column(String(255), nullable=False)  # Comma-separated list
    is_confidential = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="oauth_clients")
    authorization_codes = relationship("AuthorizationCode", back_populates="client", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OAuthClient {self.client_name}>"


class AuthorizationCode(Base):
    """Authorization code model for OAuth authorization code flow."""
    __tablename__ = 'authorization_codes'

    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False)
    client_id = Column(Integer, ForeignKey('oauth_clients.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    redirect_uri = Column(String(255), nullable=False)
    scope = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    client = relationship("OAuthClient", back_populates="authorization_codes")
    user = relationship("User")

    def __repr__(self):
        return f"<AuthorizationCode {self.code}>"


class RefreshToken(Base):
    """Refresh token model for OAuth refresh token flow."""
    __tablename__ = 'refresh_tokens'

    id = Column(Integer, primary_key=True)
    token = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    client_id = Column(String(100), nullable=False)
    scope = Column(String(255), nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken {self.token[:8]}...>"


# Pydantic models for API requests/responses

class TokenType(str, Enum):
    """Token type enumeration."""
    BEARER = "bearer"


class UserCreate(BaseModel):
    """Model for user creation requests."""
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @validator('password')
    def password_strength(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v


class UserResponse(BaseModel):
    """Model for user response data."""
    id: int
    username: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    roles: List[str]
    created_at: datetime

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    """Model for token response data."""
    access_token: str
    token_type: TokenType = TokenType.BEARER
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class TokenRequest(BaseModel):
    """Model for token request data."""
    grant_type: str
    client_id: str
    client_secret: Optional[str] = None
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class ClientCreate(BaseModel):
    """Model for OAuth client creation."""
    client_name: str
    redirect_uris: str
    allowed_grant_types: str
    allowed_scopes: str
    is_confidential: bool = True


class ClientResponse(BaseModel):
    """Model for OAuth client response."""
    client_id: str
    client_secret: str
    client_name: str
    redirect_uris: str
    allowed_grant_types: str
    allowed_scopes: str
    is_confidential: bool
    created_at: datetime

    class Config:
        orm_mode = True

