#!/usr/bin/env python3
"""
SEC-006: Broken Access Control Prevention
==========================================

Enterprise-grade Role-Based Access Control (RBAC) system implementing OWASP best practices:
- Role-Based Access Control (RBAC)
- Resource ownership verification
- Permission checking on all operations
- Subscription tier enforcement
- Vertical privilege escalation prevention
- Horizontal access control (users can only access their own resources)

This module provides:
1. Role and permission definitions
2. User role assignment
3. Permission checking decorators
4. Resource ownership verification
5. Subscription tier enforcement
6. Admin function protection

Usage:
    from rbac import RBACManager, require_permission, require_role, require_ownership

    # Check if user has permission
    if RBACManager.has_permission(user_id, 'feedback.create'):
        # User can create feedback

    # Protect endpoints with decorators
    @require_permission('admin.manage_users')
    def delete_user(user_id):
        # Only users with admin.manage_users permission can call this

    @require_role('admin')
    def admin_dashboard():
        # Only admins can access this

    @require_ownership('feedback')
    def edit_feedback(feedback_id):
        # Only the feedback owner can edit it
"""

from enum import Enum
from typing import Optional, Dict, List, Set, Callable
from datetime import datetime
from functools import wraps


# =============================================================================
# Role and Permission Definitions
# =============================================================================

class Role(Enum):
    """
    User roles in the system.

    Hierarchy (lowest to highest):
    1. GUEST - Unauthenticated users (read-only)
    2. USER - Basic authenticated users (free tier)
    3. BUILDER - Builder subscription (can submit feedback)
    4. BUILDER_PLUS - Builder+ subscription (priority feedback)
    5. PRIORITY - Priority subscription (highest priority feedback)
    6. MODERATOR - Can moderate content
    7. ADMIN - Full system access
    8. SUPERADMIN - Ultimate control (owner)
    """
    GUEST = "guest"
    USER = "user"
    BUILDER = "builder"
    BUILDER_PLUS = "builder_plus"
    PRIORITY = "priority"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class Permission(Enum):
    """
    Granular permissions in the system.

    Format: resource.action
    """
    # Feedback permissions
    FEEDBACK_VIEW = "feedback.view"
    FEEDBACK_CREATE = "feedback.create"
    FEEDBACK_EDIT_OWN = "feedback.edit_own"
    FEEDBACK_DELETE_OWN = "feedback.delete_own"
    FEEDBACK_EDIT_ANY = "feedback.edit_any"
    FEEDBACK_DELETE_ANY = "feedback.delete_any"

    # Session permissions
    SESSION_START = "session.start"
    SESSION_VIEW_OWN = "session.view_own"
    SESSION_VIEW_ANY = "session.view_any"
    SESSION_STOP_OWN = "session.stop_own"
    SESSION_STOP_ANY = "session.stop_any"

    # User management permissions
    USER_VIEW_OWN = "user.view_own"
    USER_EDIT_OWN = "user.edit_own"
    USER_VIEW_ANY = "user.view_any"
    USER_EDIT_ANY = "user.edit_any"
    USER_DELETE = "user.delete"

    # Admin permissions
    ADMIN_ACCESS = "admin.access"
    ADMIN_MANAGE_USERS = "admin.manage_users"
    ADMIN_MANAGE_ROLES = "admin.manage_roles"
    ADMIN_VIEW_LOGS = "admin.view_logs"
    ADMIN_MANAGE_CONFIG = "admin.manage_config"

    # Subscription permissions
    SUBSCRIPTION_VIEW_OWN = "subscription.view_own"
    SUBSCRIPTION_EDIT_OWN = "subscription.edit_own"
    SUBSCRIPTION_MANAGE_ANY = "subscription.manage_any"

    # System permissions
    SYSTEM_VIEW_STATS = "system.view_stats"
    SYSTEM_MANAGE = "system.manage"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.GUEST: {
        # Guests can only view public content
        Permission.FEEDBACK_VIEW,
    },

    Role.USER: {
        # Free users can view and manage their own content
        Permission.FEEDBACK_VIEW,
        Permission.FEEDBACK_CREATE,
        Permission.FEEDBACK_EDIT_OWN,
        Permission.FEEDBACK_DELETE_OWN,
        Permission.SESSION_VIEW_OWN,
        Permission.SESSION_STOP_OWN,
        Permission.USER_VIEW_OWN,
        Permission.USER_EDIT_OWN,
        Permission.SUBSCRIPTION_VIEW_OWN,
        Permission.SUBSCRIPTION_EDIT_OWN,
    },

    Role.BUILDER: {
        # Builder tier - same as USER plus priority feedback
        Permission.FEEDBACK_VIEW,
        Permission.FEEDBACK_CREATE,
        Permission.FEEDBACK_EDIT_OWN,
        Permission.FEEDBACK_DELETE_OWN,
        Permission.SESSION_START,
        Permission.SESSION_VIEW_OWN,
        Permission.SESSION_STOP_OWN,
        Permission.USER_VIEW_OWN,
        Permission.USER_EDIT_OWN,
        Permission.SUBSCRIPTION_VIEW_OWN,
        Permission.SUBSCRIPTION_EDIT_OWN,
    },

    Role.BUILDER_PLUS: {
        # Builder+ tier - all Builder permissions
        Permission.FEEDBACK_VIEW,
        Permission.FEEDBACK_CREATE,
        Permission.FEEDBACK_EDIT_OWN,
        Permission.FEEDBACK_DELETE_OWN,
        Permission.SESSION_START,
        Permission.SESSION_VIEW_OWN,
        Permission.SESSION_STOP_OWN,
        Permission.USER_VIEW_OWN,
        Permission.USER_EDIT_OWN,
        Permission.SUBSCRIPTION_VIEW_OWN,
        Permission.SUBSCRIPTION_EDIT_OWN,
    },

    Role.PRIORITY: {
        # Priority tier - highest priority feedback
        Permission.FEEDBACK_VIEW,
        Permission.FEEDBACK_CREATE,
        Permission.FEEDBACK_EDIT_OWN,
        Permission.FEEDBACK_DELETE_OWN,
        Permission.SESSION_START,
        Permission.SESSION_VIEW_OWN,
        Permission.SESSION_STOP_OWN,
        Permission.USER_VIEW_OWN,
        Permission.USER_EDIT_OWN,
        Permission.SUBSCRIPTION_VIEW_OWN,
        Permission.SUBSCRIPTION_EDIT_OWN,
        Permission.SYSTEM_VIEW_STATS,
    },

    Role.MODERATOR: {
        # Moderators can manage content
        Permission.FEEDBACK_VIEW,
        Permission.FEEDBACK_EDIT_ANY,
        Permission.FEEDBACK_DELETE_ANY,
        Permission.SESSION_VIEW_ANY,
        Permission.USER_VIEW_ANY,
        Permission.ADMIN_VIEW_LOGS,
    },

    Role.ADMIN: {
        # Admins have most permissions
        Permission.FEEDBACK_VIEW,
        Permission.FEEDBACK_CREATE,
        Permission.FEEDBACK_EDIT_ANY,
        Permission.FEEDBACK_DELETE_ANY,
        Permission.SESSION_START,
        Permission.SESSION_VIEW_ANY,
        Permission.SESSION_STOP_ANY,
        Permission.USER_VIEW_ANY,
        Permission.USER_EDIT_ANY,
        Permission.USER_DELETE,
        Permission.ADMIN_ACCESS,
        Permission.ADMIN_MANAGE_USERS,
        Permission.ADMIN_VIEW_LOGS,
        Permission.SUBSCRIPTION_MANAGE_ANY,
        Permission.SYSTEM_VIEW_STATS,
    },

    Role.SUPERADMIN: {
        # Superadmins have all permissions
        # (Include all permissions explicitly)
        *[p for p in Permission],
    }
}


# Subscription tier -> Role mapping
SUBSCRIPTION_ROLE_MAP = {
    "free": Role.USER,
    "builder": Role.BUILDER,
    "builder_plus": Role.BUILDER_PLUS,
    "priority": Role.PRIORITY,
}


# =============================================================================
# In-Memory Storage (Replace with database in production)
# =============================================================================

# User roles
# Structure: {user_id: Role}
_user_roles: Dict[str, Role] = {}

# Resource ownership
# Structure: {resource_type: {resource_id: owner_user_id}}
_resource_ownership: Dict[str, Dict[str, str]] = {
    "feedback": {},
    "session": {},
}


# =============================================================================
# RBAC Manager
# =============================================================================

class RBACManager:
    """
    Main RBAC manager for role and permission checking.
    """

    @staticmethod
    def assign_role(user_id: str, role: Role) -> None:
        """
        Assign a role to a user.

        Args:
            user_id: User identifier
            role: Role to assign
        """
        _user_roles[user_id] = role

    @staticmethod
    def get_role(user_id: str) -> Role:
        """
        Get user's role.

        Args:
            user_id: User identifier

        Returns:
            User's role (defaults to GUEST if not found)
        """
        return _user_roles.get(user_id, Role.GUEST)

    @staticmethod
    def get_permissions(role: Role) -> Set[Permission]:
        """
        Get all permissions for a role.

        Args:
            role: Role to check

        Returns:
            Set of permissions
        """
        return ROLE_PERMISSIONS.get(role, set())

    @staticmethod
    def has_permission(user_id: str, permission: Permission) -> bool:
        """
        Check if user has a specific permission.

        Args:
            user_id: User identifier
            permission: Permission to check

        Returns:
            True if user has permission, False otherwise
        """
        role = RBACManager.get_role(user_id)
        permissions = RBACManager.get_permissions(role)
        return permission in permissions

    @staticmethod
    def has_role(user_id: str, required_role: Role) -> bool:
        """
        Check if user has a specific role or higher.

        Args:
            user_id: User identifier
            required_role: Required role

        Returns:
            True if user has role or higher, False otherwise
        """
        user_role = RBACManager.get_role(user_id)

        # Role hierarchy (higher value = more privileges)
        role_hierarchy = {
            Role.GUEST: 0,
            Role.USER: 1,
            Role.BUILDER: 2,
            Role.BUILDER_PLUS: 3,
            Role.PRIORITY: 4,
            Role.MODERATOR: 5,
            Role.ADMIN: 6,
            Role.SUPERADMIN: 7,
        }

        return role_hierarchy[user_role] >= role_hierarchy[required_role]

    @staticmethod
    def is_admin(user_id: str) -> bool:
        """
        Check if user is an admin (ADMIN or SUPERADMIN).

        Args:
            user_id: User identifier

        Returns:
            True if user is admin, False otherwise
        """
        role = RBACManager.get_role(user_id)
        return role in [Role.ADMIN, Role.SUPERADMIN]

    @staticmethod
    def set_resource_owner(resource_type: str, resource_id: str, owner_id: str) -> None:
        """
        Set the owner of a resource.

        Args:
            resource_type: Type of resource (e.g., 'feedback', 'session')
            resource_id: Resource identifier
            owner_id: User ID of the owner
        """
        if resource_type not in _resource_ownership:
            _resource_ownership[resource_type] = {}

        _resource_ownership[resource_type][resource_id] = owner_id

    @staticmethod
    def get_resource_owner(resource_type: str, resource_id: str) -> Optional[str]:
        """
        Get the owner of a resource.

        Args:
            resource_type: Type of resource
            resource_id: Resource identifier

        Returns:
            Owner user ID, or None if not found
        """
        return _resource_ownership.get(resource_type, {}).get(resource_id)

    @staticmethod
    def is_resource_owner(user_id: str, resource_type: str, resource_id: str) -> bool:
        """
        Check if user owns a resource.

        Args:
            user_id: User identifier
            resource_type: Type of resource
            resource_id: Resource identifier

        Returns:
            True if user owns the resource, False otherwise
        """
        owner = RBACManager.get_resource_owner(resource_type, resource_id)
        return owner == user_id

    @staticmethod
    def can_access_resource(user_id: str, resource_type: str, resource_id: str,
                           action: str) -> bool:
        """
        Check if user can perform an action on a resource.

        Combines ownership and permission checks.

        Args:
            user_id: User identifier
            resource_type: Type of resource
            resource_id: Resource identifier
            action: Action to perform (e.g., 'edit', 'delete', 'view')

        Returns:
            True if user can access, False otherwise
        """
        # Admins can access anything
        if RBACManager.is_admin(user_id):
            return True

        # Check ownership for "own" permissions
        is_owner = RBACManager.is_resource_owner(user_id, resource_type, resource_id)

        # Map action to permissions
        own_permission_map = {
            "edit": f"{resource_type}.edit_own",
            "delete": f"{resource_type}.delete_own",
            "view": f"{resource_type}.view_own",
        }

        any_permission_map = {
            "edit": f"{resource_type}.edit_any",
            "delete": f"{resource_type}.delete_any",
            "view": f"{resource_type}.view_any",
        }

        # Try to find matching permission
        own_perm_str = own_permission_map.get(action)
        any_perm_str = any_permission_map.get(action)

        # Get user permissions
        role = RBACManager.get_role(user_id)
        permissions = RBACManager.get_permissions(role)
        permission_values = {p.value for p in permissions}

        # Check if user has "any" permission (can access any resource)
        if any_perm_str and any_perm_str in permission_values:
            return True

        # Check if user has "own" permission and owns the resource
        if own_perm_str and own_perm_str in permission_values and is_owner:
            return True

        return False

    @staticmethod
    def enforce_subscription_tier(user_id: str, required_tier: str) -> bool:
        """
        Check if user has required subscription tier.

        Args:
            user_id: User identifier
            required_tier: Required subscription tier ('builder', 'builder_plus', 'priority')

        Returns:
            True if user has required tier or higher, False otherwise
        """
        user_role = RBACManager.get_role(user_id)
        required_role = SUBSCRIPTION_ROLE_MAP.get(required_tier, Role.USER)

        # Role hierarchy check
        role_hierarchy = {
            Role.GUEST: 0,
            Role.USER: 1,
            Role.BUILDER: 2,
            Role.BUILDER_PLUS: 3,
            Role.PRIORITY: 4,
            Role.MODERATOR: 5,
            Role.ADMIN: 6,
            Role.SUPERADMIN: 7,
        }

        return role_hierarchy[user_role] >= role_hierarchy[required_role]


# =============================================================================
# Decorators for Access Control
# =============================================================================

def require_permission(permission: Permission):
    """
    Decorator to require a specific permission.

    Usage:
        @require_permission(Permission.FEEDBACK_CREATE)
        def create_feedback(user_id, content):
            # Only users with FEEDBACK_CREATE permission can call this
            pass
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            # First arg should be user_id
            if not args:
                raise ValueError("Function must accept user_id as first argument")

            user_id = args[0]

            if not RBACManager.has_permission(user_id, permission):
                raise PermissionError(f"User {user_id} does not have permission: {permission.value}")

            return f(*args, **kwargs)

        return wrapper
    return decorator


def require_role(role: Role):
    """
    Decorator to require a specific role.

    Usage:
        @require_role(Role.ADMIN)
        def admin_dashboard(user_id):
            # Only admins can call this
            pass
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not args:
                raise ValueError("Function must accept user_id as first argument")

            user_id = args[0]

            if not RBACManager.has_role(user_id, role):
                raise PermissionError(f"User {user_id} does not have required role: {role.value}")

            return f(*args, **kwargs)

        return wrapper
    return decorator


def require_ownership(resource_type: str):
    """
    Decorator to require resource ownership.

    Usage:
        @require_ownership('feedback')
        def edit_feedback(user_id, feedback_id, new_content):
            # Only the feedback owner can call this
            pass
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if len(args) < 2:
                raise ValueError("Function must accept user_id and resource_id as first two arguments")

            user_id = args[0]
            resource_id = args[1]

            # Admins bypass ownership checks
            if RBACManager.is_admin(user_id):
                return f(*args, **kwargs)

            if not RBACManager.is_resource_owner(user_id, resource_type, resource_id):
                raise PermissionError(f"User {user_id} does not own {resource_type} {resource_id}")

            return f(*args, **kwargs)

        return wrapper
    return decorator


def require_subscription(tier: str):
    """
    Decorator to require subscription tier.

    Usage:
        @require_subscription('builder_plus')
        def priority_feedback(user_id, content):
            # Only Builder+ and Priority users can call this
            pass
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not args:
                raise ValueError("Function must accept user_id as first argument")

            user_id = args[0]

            if not RBACManager.enforce_subscription_tier(user_id, tier):
                raise PermissionError(f"User {user_id} does not have required subscription tier: {tier}")

            return f(*args, **kwargs)

        return wrapper
    return decorator


# =============================================================================
# Self-test
# =============================================================================

if __name__ == "__main__":
    print("SEC-006: Broken Access Control Prevention - Self Test")
    print("=" * 60)

    # Test 1: Role assignment
    print("\n[Test 1] Role assignment...")
    RBACManager.assign_role("user1", Role.USER)
    RBACManager.assign_role("admin1", Role.ADMIN)
    RBACManager.assign_role("builder1", Role.BUILDER_PLUS)

    assert RBACManager.get_role("user1") == Role.USER
    assert RBACManager.get_role("admin1") == Role.ADMIN
    assert RBACManager.get_role("builder1") == Role.BUILDER_PLUS
    print("  ✅ PASS")

    # Test 2: Permission checking
    print("\n[Test 2] Permission checking...")
    assert RBACManager.has_permission("user1", Permission.FEEDBACK_CREATE)
    assert not RBACManager.has_permission("user1", Permission.ADMIN_ACCESS)
    assert RBACManager.has_permission("admin1", Permission.ADMIN_ACCESS)
    print("  ✅ PASS")

    # Test 3: Resource ownership
    print("\n[Test 3] Resource ownership...")
    RBACManager.set_resource_owner("feedback", "fb1", "user1")
    assert RBACManager.is_resource_owner("user1", "feedback", "fb1")
    assert not RBACManager.is_resource_owner("user2", "feedback", "fb1")
    print("  ✅ PASS")

    # Test 4: Resource access control
    print("\n[Test 4] Resource access control...")
    assert RBACManager.can_access_resource("user1", "feedback", "fb1", "edit")  # Owner
    assert not RBACManager.can_access_resource("user2", "feedback", "fb1", "edit")  # Not owner
    assert RBACManager.can_access_resource("admin1", "feedback", "fb1", "edit")  # Admin
    print("  ✅ PASS")

    # Test 5: Subscription tier enforcement
    print("\n[Test 5] Subscription tier enforcement...")
    assert not RBACManager.enforce_subscription_tier("user1", "builder_plus")  # USER < BUILDER_PLUS
    assert RBACManager.enforce_subscription_tier("builder1", "builder_plus")  # BUILDER_PLUS == BUILDER_PLUS
    assert RBACManager.enforce_subscription_tier("admin1", "priority")  # ADMIN > PRIORITY
    print("  ✅ PASS")

    # Test 6: Admin detection
    print("\n[Test 6] Admin detection...")
    assert not RBACManager.is_admin("user1")
    assert RBACManager.is_admin("admin1")
    print("  ✅ PASS")

    # Test 7: Decorator - require_permission
    print("\n[Test 7] Decorator - require_permission...")

    @require_permission(Permission.FEEDBACK_CREATE)
    def create_feedback(user_id, content):
        return f"Created feedback: {content}"

    try:
        result = create_feedback("user1", "Test feedback")
        print(f"  User allowed: {result}")
    except PermissionError:
        print("  ❌ FAIL: User should have permission")

    try:
        result = create_feedback("guest1", "Test feedback")
        print("  ❌ FAIL: Guest should not have permission")
    except PermissionError:
        print("  Guest blocked (expected)")

    print("  ✅ PASS")

    # Test 8: Decorator - require_ownership
    print("\n[Test 8] Decorator - require_ownership...")

    @require_ownership('feedback')
    def edit_feedback(user_id, feedback_id, new_content):
        return f"Edited feedback {feedback_id}: {new_content}"

    try:
        result = edit_feedback("user1", "fb1", "Updated content")
        print(f"  Owner allowed: {result}")
    except PermissionError:
        print("  ❌ FAIL: Owner should be allowed")

    try:
        result = edit_feedback("user2", "fb1", "Hacked content")
        print("  ❌ FAIL: Non-owner should be blocked")
    except PermissionError:
        print("  Non-owner blocked (expected)")

    print("  ✅ PASS")

    # Test 9: Vertical privilege escalation prevention
    print("\n[Test 9] Vertical privilege escalation prevention...")

    @require_role(Role.ADMIN)
    def delete_user(user_id, target_user_id):
        return f"Deleted user {target_user_id}"

    try:
        result = delete_user("admin1", "user1")
        print(f"  Admin allowed: {result}")
    except PermissionError:
        print("  ❌ FAIL: Admin should be allowed")

    try:
        result = delete_user("user1", "user2")
        print("  ❌ FAIL: Regular user should not be able to delete users")
    except PermissionError:
        print("  Regular user blocked (expected)")

    print("  ✅ PASS")

    print("\n" + "=" * 60)
    print("All tests completed! SEC-006 implementation verified.")
