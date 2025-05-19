"""
Role-based access control (RBAC) for WiseFlow.

This module provides functions for managing and checking permissions.
"""

from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session

from core.auth.models import User, Role, Permission
from core.utils.error_handling import AuthorizationError


def get_user_roles(user: User) -> List[str]:
    """
    Get the roles assigned to a user.
    
    Args:
        user: The user
        
    Returns:
        List[str]: List of role names
    """
    return [role.name for role in user.roles]


def get_role_permissions(role: Role) -> List[str]:
    """
    Get the permissions assigned to a role.
    
    Args:
        role: The role
        
    Returns:
        List[str]: List of permission names
    """
    return [permission.name for permission in role.permissions]


def get_user_permissions(user: User, db: Session) -> Set[str]:
    """
    Get all permissions for a user across all their roles.
    
    Args:
        user: The user
        db: Database session
        
    Returns:
        Set[str]: Set of permission names
    """
    permissions = set()
    
    for role in user.roles:
        role_permissions = get_role_permissions(role)
        permissions.update(role_permissions)
    
    return permissions


def has_permission(user: User, permission_name: str, db: Session) -> bool:
    """
    Check if a user has a specific permission.
    
    Args:
        user: The user
        permission_name: The permission name to check
        db: Database session
        
    Returns:
        bool: True if the user has the permission
    """
    user_permissions = get_user_permissions(user, db)
    return permission_name in user_permissions


def has_role(user: User, role_name: str) -> bool:
    """
    Check if a user has a specific role.
    
    Args:
        user: The user
        role_name: The role name to check
        
    Returns:
        bool: True if the user has the role
    """
    user_roles = get_user_roles(user)
    return role_name in user_roles


def assign_role_to_user(user: User, role: Role, db: Session) -> None:
    """
    Assign a role to a user.
    
    Args:
        user: The user
        role: The role to assign
        db: Database session
    """
    if role not in user.roles:
        user.roles.append(role)
        db.commit()


def remove_role_from_user(user: User, role: Role, db: Session) -> None:
    """
    Remove a role from a user.
    
    Args:
        user: The user
        role: The role to remove
        db: Database session
    """
    if role in user.roles:
        user.roles.remove(role)
        db.commit()


def create_role(name: str, description: str, db: Session) -> Role:
    """
    Create a new role.
    
    Args:
        name: Role name
        description: Role description
        db: Database session
        
    Returns:
        Role: The created role
    """
    role = Role(name=name, description=description)
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def create_permission(
    name: str, 
    description: str, 
    resource: str, 
    action: str, 
    db: Session
) -> Permission:
    """
    Create a new permission.
    
    Args:
        name: Permission name
        description: Permission description
        resource: Resource name (e.g., 'users', 'webhooks')
        action: Action name (e.g., 'read', 'write', 'delete')
        db: Database session
        
    Returns:
        Permission: The created permission
    """
    permission = Permission(
        name=name,
        description=description,
        resource=resource,
        action=action
    )
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


def assign_permission_to_role(role: Role, permission: Permission, db: Session) -> None:
    """
    Assign a permission to a role.
    
    Args:
        role: The role
        permission: The permission to assign
        db: Database session
    """
    if permission not in role.permissions:
        role.permissions.append(permission)
        db.commit()


def remove_permission_from_role(role: Role, permission: Permission, db: Session) -> None:
    """
    Remove a permission from a role.
    
    Args:
        role: The role
        permission: The permission to remove
        db: Database session
    """
    if permission in role.permissions:
        role.permissions.remove(permission)
        db.commit()


def check_permission(user: User, permission_name: str, db: Session) -> None:
    """
    Check if a user has a permission, raising an exception if not.
    
    Args:
        user: The user
        permission_name: The permission name to check
        db: Database session
        
    Raises:
        AuthorizationError: If the user doesn't have the permission
    """
    if not has_permission(user, permission_name, db):
        raise AuthorizationError(f"User does not have the required permission: {permission_name}")


def check_role(user: User, role_name: str) -> None:
    """
    Check if a user has a role, raising an exception if not.
    
    Args:
        user: The user
        role_name: The role name to check
        
    Raises:
        AuthorizationError: If the user doesn't have the role
    """
    if not has_role(user, role_name):
        raise AuthorizationError(f"User does not have the required role: {role_name}")


def get_resource_permissions(user: User, resource: str, db: Session) -> Dict[str, bool]:
    """
    Get all permissions a user has for a specific resource.
    
    Args:
        user: The user
        resource: The resource name
        db: Database session
        
    Returns:
        Dict[str, bool]: Dictionary mapping actions to permission status
    """
    user_permissions = get_user_permissions(user, db)
    resource_permissions = {}
    
    # Query all permissions for the resource
    resource_perms = db.query(Permission).filter(Permission.resource == resource).all()
    
    for perm in resource_perms:
        resource_permissions[perm.action] = perm.name in user_permissions
    
    return resource_permissions

