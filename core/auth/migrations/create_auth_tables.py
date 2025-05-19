"""
Database migration script to create authentication tables.

This script creates the necessary tables for the OAuth 2.0 authentication system.
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, MetaData

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from core.auth.models import Base
from core.auth.password import get_password_hash
from core.auth.models import User, Role, Permission, OAuthClient
from core.config import config

# Database URL
DATABASE_URL = os.environ.get("DATABASE_URL", config.get("DATABASE_URL", "sqlite:///./wiseflow.db"))

# Create engine
engine = create_engine(DATABASE_URL)

def create_tables():
    """Create all tables defined in the models."""
    Base.metadata.create_all(engine)
    print("Created authentication tables")

def drop_tables():
    """Drop all tables defined in the models."""
    Base.metadata.drop_all(engine)
    print("Dropped authentication tables")

def create_initial_data():
    """Create initial data for testing and development."""
    from sqlalchemy.orm import sessionmaker
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Create admin role
        admin_role = Role(
            name="admin",
            description="Administrator role with full access"
        )
        session.add(admin_role)
        
        # Create user role
        user_role = Role(
            name="user",
            description="Standard user role with limited access"
        )
        session.add(user_role)
        
        # Create permissions
        permissions = [
            # User management permissions
            Permission(name="users:read", description="Read user data", resource="users", action="read"),
            Permission(name="users:write", description="Create and update users", resource="users", action="write"),
            Permission(name="users:delete", description="Delete users", resource="users", action="delete"),
            
            # Webhook permissions
            Permission(name="webhooks:read", description="Read webhooks", resource="webhooks", action="read"),
            Permission(name="webhooks:write", description="Create and update webhooks", resource="webhooks", action="write"),
            Permission(name="webhooks:delete", description="Delete webhooks", resource="webhooks", action="delete"),
            
            # API permissions
            Permission(name="api:read", description="Access API endpoints", resource="api", action="read"),
            Permission(name="api:write", description="Modify data via API", resource="api", action="write"),
            
            # Admin permissions
            Permission(name="admin:access", description="Access admin features", resource="admin", action="access"),
        ]
        
        for permission in permissions:
            session.add(permission)
        
        # Commit to get IDs
        session.commit()
        
        # Assign permissions to roles
        admin_permissions = session.query(Permission).all()
        for permission in admin_permissions:
            admin_role.permissions.append(permission)
        
        user_permissions = session.query(Permission).filter(
            Permission.name.in_([
                "users:read",
                "webhooks:read",
                "webhooks:write",
                "api:read"
            ])
        ).all()
        
        for permission in user_permissions:
            user_role.permissions.append(permission)
        
        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=get_password_hash("Admin123!"),
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_verified=True
        )
        session.add(admin_user)
        
        # Create test user
        test_user = User(
            username="testuser",
            email="test@example.com",
            password_hash=get_password_hash("Test123!"),
            first_name="Test",
            last_name="User",
            is_active=True,
            is_verified=True
        )
        session.add(test_user)
        
        # Commit to get IDs
        session.commit()
        
        # Assign roles to users
        admin_user.roles.append(admin_role)
        test_user.roles.append(user_role)
        
        # Create OAuth client for testing
        client = OAuthClient(
            client_id="test-client",
            client_secret="test-secret",
            client_name="Test Client",
            redirect_uris="http://localhost:8000/callback",
            allowed_grant_types="authorization_code,refresh_token,client_credentials,password",
            allowed_scopes="read write",
            is_confidential=True,
            user_id=admin_user.id
        )
        session.add(client)
        
        # Commit all changes
        session.commit()
        print("Created initial data")
        
    except Exception as e:
        session.rollback()
        print(f"Error creating initial data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Authentication database migration script")
    parser.add_argument("--action", choices=["create", "drop", "recreate"], default="create",
                        help="Action to perform (create, drop, or recreate tables)")
    parser.add_argument("--with-data", action="store_true", help="Create initial data")
    
    args = parser.parse_args()
    
    if args.action == "drop":
        drop_tables()
    elif args.action == "recreate":
        drop_tables()
        create_tables()
        if args.with_data:
            create_initial_data()
    else:  # create
        create_tables()
        if args.with_data:
            create_initial_data()

