"""
OAuth 2.0 implementation for WiseFlow.

This module provides the core OAuth 2.0 functionality, including:
- Authorization code flow
- Client credentials flow
- Refresh token flow
- Token validation and revocation
"""

import os
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple, Union
from urllib.parse import urlencode, quote

from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, Request, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2AuthorizationCodeBearer

from core.auth.models import (
    User, OAuthClient, AuthorizationCode, RefreshToken,
    TokenRequest, TokenResponse, TokenType
)
from core.auth.jwt import (
    create_access_token, create_refresh_token, 
    verify_token, decode_token
)
from core.utils.error_handling import (
    AuthenticationError, AuthorizationError, ValidationError
)
from core.utils.password import verify_password, get_password_hash
from core.config import config

# OAuth settings
AUTHORIZATION_CODE_EXPIRE_MINUTES = int(os.environ.get(
    "AUTHORIZATION_CODE_EXPIRE_MINUTES", 
    config.get("AUTHORIZATION_CODE_EXPIRE_MINUTES", 10)
))

# OAuth2 security schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class OAuth2Provider:
    """OAuth 2.0 provider implementation."""
    
    def __init__(self, db: Session):
        """
        Initialize the OAuth2 provider.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_authorization_code(
        self, 
        client_id: str, 
        user_id: int, 
        redirect_uri: str, 
        scope: Optional[str] = None
    ) -> str:
        """
        Create a new authorization code.
        
        Args:
            client_id: OAuth client ID
            user_id: User ID
            redirect_uri: Redirect URI
            scope: Optional scope
            
        Returns:
            str: The authorization code
            
        Raises:
            ValidationError: If client or redirect URI is invalid
        """
        # Verify client exists
        client = self.db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
        if not client:
            raise ValidationError(f"Invalid client ID: {client_id}")
        
        # Verify redirect URI is allowed for this client
        allowed_uris = client.redirect_uris.split(',') if client.redirect_uris else []
        if redirect_uri not in allowed_uris:
            raise ValidationError(f"Invalid redirect URI: {redirect_uri}")
        
        # Generate a random code
        code = secrets.token_urlsafe(32)
        
        # Set expiration time
        expires_at = datetime.utcnow() + timedelta(minutes=AUTHORIZATION_CODE_EXPIRE_MINUTES)
        
        # Create and save the authorization code
        auth_code = AuthorizationCode(
            code=code,
            client_id=client.id,
            user_id=user_id,
            redirect_uri=redirect_uri,
            scope=scope,
            expires_at=expires_at
        )
        
        self.db.add(auth_code)
        self.db.commit()
        
        return code
    
    def exchange_authorization_code(
        self, 
        code: str, 
        client_id: str, 
        client_secret: Optional[str], 
        redirect_uri: str
    ) -> TokenResponse:
        """
        Exchange an authorization code for tokens.
        
        Args:
            code: Authorization code
            client_id: OAuth client ID
            client_secret: OAuth client secret (required for confidential clients)
            redirect_uri: Redirect URI
            
        Returns:
            TokenResponse: Access and refresh tokens
            
        Raises:
            AuthenticationError: If code or client credentials are invalid
            ValidationError: If redirect URI doesn't match
        """
        # Find the authorization code
        auth_code = self.db.query(AuthorizationCode).filter(
            AuthorizationCode.code == code,
            AuthorizationCode.expires_at > datetime.utcnow()
        ).first()
        
        if not auth_code:
            raise AuthenticationError("Invalid or expired authorization code")
        
        # Verify client
        client = self.db.query(OAuthClient).filter(
            OAuthClient.client_id == client_id,
            OAuthClient.id == auth_code.client_id
        ).first()
        
        if not client:
            raise AuthenticationError("Invalid client ID")
        
        # For confidential clients, verify client secret
        if client.is_confidential and client.client_secret != client_secret:
            raise AuthenticationError("Invalid client secret")
        
        # Verify redirect URI matches the one used for the authorization code
        if auth_code.redirect_uri != redirect_uri:
            raise ValidationError("Redirect URI does not match the one used for the authorization code")
        
        # Generate tokens
        access_token = create_access_token(
            subject=auth_code.user_id,
            scopes=auth_code.scope.split() if auth_code.scope else [],
            additional_claims={"client_id": client_id}
        )
        
        refresh_token_str = create_refresh_token(subject=auth_code.user_id)
        
        # Store refresh token
        refresh_token = RefreshToken(
            token=refresh_token_str,
            user_id=auth_code.user_id,
            client_id=client_id,
            scope=auth_code.scope,
            expires_at=datetime.utcnow() + timedelta(days=7)  # Use config value
        )
        
        self.db.add(refresh_token)
        
        # Delete the used authorization code
        self.db.delete(auth_code)
        self.db.commit()
        
        # Return tokens
        return TokenResponse(
            access_token=access_token,
            token_type=TokenType.BEARER,
            expires_in=1800,  # 30 minutes in seconds
            refresh_token=refresh_token_str,
            scope=auth_code.scope
        )
    
    def refresh_access_token(
        self, 
        refresh_token: str, 
        client_id: str, 
        client_secret: Optional[str] = None
    ) -> TokenResponse:
        """
        Refresh an access token using a refresh token.
        
        Args:
            refresh_token: Refresh token
            client_id: OAuth client ID
            client_secret: OAuth client secret (required for confidential clients)
            
        Returns:
            TokenResponse: New access token and optionally a new refresh token
            
        Raises:
            AuthenticationError: If refresh token or client credentials are invalid
        """
        # Verify the refresh token exists and is not revoked
        token_record = self.db.query(RefreshToken).filter(
            RefreshToken.token == refresh_token,
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.utcnow()
        ).first()
        
        if not token_record:
            raise AuthenticationError("Invalid or expired refresh token")
        
        # Verify client
        client = self.db.query(OAuthClient).filter(
            OAuthClient.client_id == client_id
        ).first()
        
        if not client:
            raise AuthenticationError("Invalid client ID")
        
        # For confidential clients, verify client secret
        if client.is_confidential and client.client_secret != client_secret:
            raise AuthenticationError("Invalid client secret")
        
        # Verify client ID matches the one used for the refresh token
        if token_record.client_id != client_id:
            raise AuthenticationError("Client ID does not match the one used for the refresh token")
        
        # Generate new access token
        access_token = create_access_token(
            subject=token_record.user_id,
            scopes=token_record.scope.split() if token_record.scope else [],
            additional_claims={"client_id": client_id}
        )
        
        # Optionally rotate the refresh token for better security
        # This is a security best practice but not required by OAuth 2.0
        new_refresh_token = None
        if config.get("ROTATE_REFRESH_TOKENS", True):
            # Revoke the old refresh token
            token_record.revoked = True
            
            # Create a new refresh token
            new_refresh_token_str = create_refresh_token(subject=token_record.user_id)
            
            # Store the new refresh token
            new_refresh_token = RefreshToken(
                token=new_refresh_token_str,
                user_id=token_record.user_id,
                client_id=client_id,
                scope=token_record.scope,
                expires_at=datetime.utcnow() + timedelta(days=7)  # Use config value
            )
            
            self.db.add(new_refresh_token)
            self.db.commit()
        else:
            new_refresh_token_str = refresh_token
        
        # Return tokens
        return TokenResponse(
            access_token=access_token,
            token_type=TokenType.BEARER,
            expires_in=1800,  # 30 minutes in seconds
            refresh_token=new_refresh_token_str if new_refresh_token else None,
            scope=token_record.scope
        )
    
    def revoke_token(self, token: str, token_type_hint: Optional[str] = None) -> bool:
        """
        Revoke a token.
        
        Args:
            token: The token to revoke
            token_type_hint: Optional hint about the token type
            
        Returns:
            bool: True if token was revoked, False otherwise
        """
        # If token_type_hint is "refresh_token" or we don't know the type,
        # try to find and revoke a refresh token
        if token_type_hint in (None, "refresh_token"):
            refresh_token = self.db.query(RefreshToken).filter(
                RefreshToken.token == token,
                RefreshToken.revoked == False
            ).first()
            
            if refresh_token:
                refresh_token.revoked = True
                self.db.commit()
                return True
        
        # If token_type_hint is "access_token" or we don't know the type and didn't find a refresh token,
        # try to decode it as an access token
        if token_type_hint in (None, "access_token"):
            try:
                # We can't actually revoke JWT access tokens without maintaining a blacklist
                # This would require additional implementation
                # For now, we'll just verify it's a valid token
                payload = decode_token(token)
                
                # TODO: Add the token to a blacklist or implement token revocation
                # This would require additional database tables and logic
                
                return True
            except Exception:
                pass
        
        return False
    
    def client_credentials_grant(
        self, 
        client_id: str, 
        client_secret: str, 
        scope: Optional[str] = None
    ) -> TokenResponse:
        """
        Implement the client credentials grant type.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            scope: Optional requested scope
            
        Returns:
            TokenResponse: Access token
            
        Raises:
            AuthenticationError: If client credentials are invalid
        """
        # Verify client
        client = self.db.query(OAuthClient).filter(
            OAuthClient.client_id == client_id,
            OAuthClient.client_secret == client_secret,
            OAuthClient.is_confidential == True  # Only confidential clients can use this grant
        ).first()
        
        if not client:
            raise AuthenticationError("Invalid client credentials")
        
        # Verify requested scope is allowed for this client
        allowed_scopes = client.allowed_scopes.split(',') if client.allowed_scopes else []
        requested_scopes = scope.split() if scope else []
        
        for req_scope in requested_scopes:
            if req_scope not in allowed_scopes:
                raise AuthorizationError(f"Requested scope not allowed: {req_scope}")
        
        # Generate access token
        # Note: For client credentials, the subject is the client ID, not a user ID
        access_token = create_access_token(
            subject=f"client:{client.id}",
            scopes=requested_scopes,
            additional_claims={"client_id": client_id}
        )
        
        # Return token response (no refresh token for client credentials)
        return TokenResponse(
            access_token=access_token,
            token_type=TokenType.BEARER,
            expires_in=1800,  # 30 minutes in seconds
            scope=scope
        )
    
    def password_grant(
        self, 
        username: str, 
        password: str, 
        client_id: str, 
        client_secret: Optional[str] = None,
        scope: Optional[str] = None
    ) -> TokenResponse:
        """
        Implement the password grant type (Resource Owner Password Credentials).
        
        Args:
            username: User's username
            password: User's password
            client_id: OAuth client ID
            client_secret: OAuth client secret (required for confidential clients)
            scope: Optional requested scope
            
        Returns:
            TokenResponse: Access and refresh tokens
            
        Raises:
            AuthenticationError: If user credentials or client credentials are invalid
        """
        # Verify client
        client = self.db.query(OAuthClient).filter(
            OAuthClient.client_id == client_id
        ).first()
        
        if not client:
            raise AuthenticationError("Invalid client ID")
        
        # For confidential clients, verify client secret
        if client.is_confidential and client.client_secret != client_secret:
            raise AuthenticationError("Invalid client secret")
        
        # Verify user credentials
        user = self.db.query(User).filter(
            User.username == username,
            User.is_active == True
        ).first()
        
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
        
        # Verify requested scope is allowed for this client
        allowed_scopes = client.allowed_scopes.split(',') if client.allowed_scopes else []
        requested_scopes = scope.split() if scope else []
        
        for req_scope in requested_scopes:
            if req_scope not in allowed_scopes:
                raise AuthorizationError(f"Requested scope not allowed: {req_scope}")
        
        # Generate tokens
        access_token = create_access_token(
            subject=user.id,
            scopes=requested_scopes,
            additional_claims={"client_id": client_id}
        )
        
        refresh_token_str = create_refresh_token(subject=user.id)
        
        # Store refresh token
        refresh_token = RefreshToken(
            token=refresh_token_str,
            user_id=user.id,
            client_id=client_id,
            scope=scope,
            expires_at=datetime.utcnow() + timedelta(days=7)  # Use config value
        )
        
        self.db.add(refresh_token)
        self.db.commit()
        
        # Update last login time
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        # Return tokens
        return TokenResponse(
            access_token=access_token,
            token_type=TokenType.BEARER,
            expires_in=1800,  # 30 minutes in seconds
            refresh_token=refresh_token_str,
            scope=scope
        )
    
    def process_token_request(self, request: TokenRequest) -> TokenResponse:
        """
        Process a token request based on the grant type.
        
        Args:
            request: Token request
            
        Returns:
            TokenResponse: Token response
            
        Raises:
            ValidationError: If grant type is invalid or required parameters are missing
            AuthenticationError: If credentials are invalid
        """
        grant_type = request.grant_type
        
        if grant_type == "authorization_code":
            if not all([request.code, request.redirect_uri, request.client_id]):
                raise ValidationError("Missing required parameters for authorization_code grant")
            
            return self.exchange_authorization_code(
                code=request.code,
                client_id=request.client_id,
                client_secret=request.client_secret,
                redirect_uri=request.redirect_uri
            )
        
        elif grant_type == "refresh_token":
            if not all([request.refresh_token, request.client_id]):
                raise ValidationError("Missing required parameters for refresh_token grant")
            
            return self.refresh_access_token(
                refresh_token=request.refresh_token,
                client_id=request.client_id,
                client_secret=request.client_secret
            )
        
        elif grant_type == "client_credentials":
            if not all([request.client_id, request.client_secret]):
                raise ValidationError("Missing required parameters for client_credentials grant")
            
            return self.client_credentials_grant(
                client_id=request.client_id,
                client_secret=request.client_secret,
                scope=request.scope
            )
        
        elif grant_type == "password":
            if not all([request.username, request.password, request.client_id]):
                raise ValidationError("Missing required parameters for password grant")
            
            return self.password_grant(
                username=request.username,
                password=request.password,
                client_id=request.client_id,
                client_secret=request.client_secret,
                scope=request.scope
            )
        
        else:
            raise ValidationError(f"Unsupported grant type: {grant_type}")
    
    def generate_authorization_url(
        self, 
        client_id: str, 
        redirect_uri: str, 
        response_type: str = "code", 
        scope: Optional[str] = None, 
        state: Optional[str] = None
    ) -> str:
        """
        Generate an authorization URL for the authorization code flow.
        
        Args:
            client_id: OAuth client ID
            redirect_uri: Redirect URI
            response_type: Response type (usually "code")
            scope: Optional requested scope
            state: Optional state parameter for CSRF protection
            
        Returns:
            str: Authorization URL
            
        Raises:
            ValidationError: If client or redirect URI is invalid
        """
        # Verify client exists
        client = self.db.query(OAuthClient).filter(OAuthClient.client_id == client_id).first()
        if not client:
            raise ValidationError(f"Invalid client ID: {client_id}")
        
        # Verify redirect URI is allowed for this client
        allowed_uris = client.redirect_uris.split(',') if client.redirect_uris else []
        if redirect_uri not in allowed_uris:
            raise ValidationError(f"Invalid redirect URI: {redirect_uri}")
        
        # Build query parameters
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": response_type
        }
        
        if scope:
            params["scope"] = scope
        
        if state:
            params["state"] = state
        
        # Generate the URL
        base_url = f"{config.get('AUTH_SERVER_URL', 'http://localhost:8000')}/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"

