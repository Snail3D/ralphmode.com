#!/usr/bin/env python3
"""
SEC-006: Broken Access Control Prevention - Test Suite

Tests for RBAC implementation, covering:
1. Role-Based Access Control (RBAC)
2. Resource ownership verification
3. Permission checking
4. Subscription tier enforcement
5. Vertical privilege escalation prevention
6. Horizontal access control (users can only access their own resources)
7. Admin function protection
"""

import sys
import traceback
from rbac import (
    RBACManager,
    Role,
    Permission,
    require_permission,
    require_role,
    require_ownership,
    require_subscription,
)


def test_role_assignment():
    """Test 1: Role assignment and retrieval"""
    print("\n[Test 1] Role assignment and retrieval...")

    # Assign roles
    RBACManager.assign_role("user1", Role.USER)
    RBACManager.assign_role("user2", Role.BUILDER_PLUS)
    RBACManager.assign_role("admin1", Role.ADMIN)
    RBACManager.assign_role("superadmin1", Role.SUPERADMIN)

    # Verify roles
    assert RBACManager.get_role("user1") == Role.USER, "User1 should be USER"
    assert RBACManager.get_role("user2") == Role.BUILDER_PLUS, "User2 should be BUILDER_PLUS"
    assert RBACManager.get_role("admin1") == Role.ADMIN, "Admin1 should be ADMIN"
    assert RBACManager.get_role("superadmin1") == Role.SUPERADMIN, "Superadmin1 should be SUPERADMIN"

    # Guest (default)
    assert RBACManager.get_role("unknown_user") == Role.GUEST, "Unknown user should be GUEST"

    print("  ✅ PASS: Role assignment works correctly")


def test_permission_checking():
    """Test 2: Permission checking"""
    print("\n[Test 2] Permission checking...")

    # User permissions
    assert RBACManager.has_permission("user1", Permission.FEEDBACK_CREATE), \
        "USER should have FEEDBACK_CREATE"
    assert not RBACManager.has_permission("user1", Permission.ADMIN_ACCESS), \
        "USER should NOT have ADMIN_ACCESS"

    # Admin permissions
    assert RBACManager.has_permission("admin1", Permission.ADMIN_ACCESS), \
        "ADMIN should have ADMIN_ACCESS"
    assert RBACManager.has_permission("admin1", Permission.FEEDBACK_DELETE_ANY), \
        "ADMIN should have FEEDBACK_DELETE_ANY"

    # Superadmin has all permissions
    assert RBACManager.has_permission("superadmin1", Permission.SYSTEM_MANAGE), \
        "SUPERADMIN should have SYSTEM_MANAGE"
    assert RBACManager.has_permission("superadmin1", Permission.USER_DELETE), \
        "SUPERADMIN should have USER_DELETE"

    print("  ✅ PASS: Permission checking works correctly")


def test_resource_ownership():
    """Test 3: Resource ownership"""
    print("\n[Test 3] Resource ownership...")

    # Set resource owners
    RBACManager.set_resource_owner("feedback", "fb1", "user1")
    RBACManager.set_resource_owner("feedback", "fb2", "user2")
    RBACManager.set_resource_owner("session", "sess1", "user1")

    # Check ownership
    assert RBACManager.is_resource_owner("user1", "feedback", "fb1"), \
        "User1 should own fb1"
    assert not RBACManager.is_resource_owner("user2", "feedback", "fb1"), \
        "User2 should NOT own fb1"
    assert RBACManager.is_resource_owner("user2", "feedback", "fb2"), \
        "User2 should own fb2"
    assert RBACManager.is_resource_owner("user1", "session", "sess1"), \
        "User1 should own sess1"

    # Get owner
    assert RBACManager.get_resource_owner("feedback", "fb1") == "user1", \
        "Owner of fb1 should be user1"
    assert RBACManager.get_resource_owner("feedback", "fb2") == "user2", \
        "Owner of fb2 should be user2"

    print("  ✅ PASS: Resource ownership tracking works correctly")


def test_horizontal_access_control():
    """Test 4: Horizontal access control (users can only access their own resources)"""
    print("\n[Test 4] Horizontal access control...")

    # User1 can edit their own feedback
    assert RBACManager.can_access_resource("user1", "feedback", "fb1", "edit"), \
        "User1 should be able to edit their own feedback"

    # User2 cannot edit user1's feedback
    assert not RBACManager.can_access_resource("user2", "feedback", "fb1", "edit"), \
        "User2 should NOT be able to edit user1's feedback"

    # User2 can edit their own feedback
    assert RBACManager.can_access_resource("user2", "feedback", "fb2", "edit"), \
        "User2 should be able to edit their own feedback"

    # User1 cannot delete user2's feedback
    assert not RBACManager.can_access_resource("user1", "feedback", "fb2", "delete"), \
        "User1 should NOT be able to delete user2's feedback"

    print("  ✅ PASS: Horizontal access control prevents unauthorized access")


def test_vertical_privilege_escalation_prevention():
    """Test 5: Vertical privilege escalation prevention"""
    print("\n[Test 5] Vertical privilege escalation prevention...")

    # Regular users cannot access admin resources
    assert not RBACManager.has_permission("user1", Permission.ADMIN_MANAGE_USERS), \
        "Regular user should NOT have admin permissions"
    assert not RBACManager.has_permission("user1", Permission.USER_DELETE), \
        "Regular user should NOT be able to delete users"

    # Builder users cannot access admin functions
    assert not RBACManager.has_permission("user2", Permission.ADMIN_ACCESS), \
        "Builder user should NOT have admin access"

    # Admin can access admin functions
    assert RBACManager.has_permission("admin1", Permission.ADMIN_ACCESS), \
        "Admin should have admin access"
    assert RBACManager.has_permission("admin1", Permission.USER_DELETE), \
        "Admin should be able to delete users"

    # But admin cannot manage system (only superadmin can)
    assert not RBACManager.has_permission("admin1", Permission.SYSTEM_MANAGE), \
        "Admin should NOT have SYSTEM_MANAGE (only superadmin)"

    # Only superadmin can manage system
    assert RBACManager.has_permission("superadmin1", Permission.SYSTEM_MANAGE), \
        "Superadmin should have SYSTEM_MANAGE"

    print("  ✅ PASS: Vertical privilege escalation is prevented")


def test_admin_bypass():
    """Test 6: Admins can access all resources"""
    print("\n[Test 6] Admin bypass for resource access...")

    # Admin can access any user's resources
    assert RBACManager.can_access_resource("admin1", "feedback", "fb1", "edit"), \
        "Admin should be able to edit any feedback"
    assert RBACManager.can_access_resource("admin1", "feedback", "fb2", "delete"), \
        "Admin should be able to delete any feedback"

    # Superadmin can also access everything
    assert RBACManager.can_access_resource("superadmin1", "feedback", "fb1", "edit"), \
        "Superadmin should be able to edit any feedback"

    print("  ✅ PASS: Admins can bypass ownership checks")


def test_subscription_tier_enforcement():
    """Test 7: Subscription tier enforcement"""
    print("\n[Test 7] Subscription tier enforcement...")

    # USER doesn't meet builder requirement
    assert not RBACManager.enforce_subscription_tier("user1", "builder"), \
        "USER should not meet builder tier requirement"

    # BUILDER_PLUS meets builder requirement
    assert RBACManager.enforce_subscription_tier("user2", "builder"), \
        "BUILDER_PLUS should meet builder tier requirement"

    # BUILDER_PLUS meets builder_plus requirement
    assert RBACManager.enforce_subscription_tier("user2", "builder_plus"), \
        "BUILDER_PLUS should meet builder_plus tier requirement"

    # USER doesn't meet priority requirement
    assert not RBACManager.enforce_subscription_tier("user1", "priority"), \
        "USER should not meet priority tier requirement"

    # Admin meets all subscription requirements
    assert RBACManager.enforce_subscription_tier("admin1", "priority"), \
        "Admin should meet all subscription tier requirements"

    print("  ✅ PASS: Subscription tier enforcement works correctly")


def test_role_hierarchy():
    """Test 8: Role hierarchy"""
    print("\n[Test 8] Role hierarchy...")

    # User has USER role or higher
    assert RBACManager.has_role("user1", Role.USER), \
        "User1 should have USER role"
    assert not RBACManager.has_role("user1", Role.ADMIN), \
        "User1 should NOT have ADMIN role"

    # Builder+ has USER and BUILDER roles
    assert RBACManager.has_role("user2", Role.USER), \
        "BUILDER_PLUS should have USER role (hierarchy)"
    assert RBACManager.has_role("user2", Role.BUILDER), \
        "BUILDER_PLUS should have BUILDER role (hierarchy)"

    # Admin has all roles below it
    assert RBACManager.has_role("admin1", Role.USER), \
        "ADMIN should have USER role (hierarchy)"
    assert RBACManager.has_role("admin1", Role.ADMIN), \
        "ADMIN should have ADMIN role"
    assert not RBACManager.has_role("admin1", Role.SUPERADMIN), \
        "ADMIN should NOT have SUPERADMIN role"

    # Superadmin has all roles
    assert RBACManager.has_role("superadmin1", Role.USER), \
        "SUPERADMIN should have USER role (hierarchy)"
    assert RBACManager.has_role("superadmin1", Role.ADMIN), \
        "SUPERADMIN should have ADMIN role (hierarchy)"
    assert RBACManager.has_role("superadmin1", Role.SUPERADMIN), \
        "SUPERADMIN should have SUPERADMIN role"

    print("  ✅ PASS: Role hierarchy works correctly")


def test_decorator_require_permission():
    """Test 9: @require_permission decorator"""
    print("\n[Test 9] @require_permission decorator...")

    @require_permission(Permission.FEEDBACK_CREATE)
    def create_feedback(user_id, content):
        return f"Created: {content}"

    # User1 (USER role) has FEEDBACK_CREATE permission
    try:
        result = create_feedback("user1", "Test feedback")
        assert result == "Created: Test feedback", "Should succeed for authorized user"
    except PermissionError:
        raise AssertionError("User1 should have permission to create feedback")

    # Guest doesn't have FEEDBACK_CREATE permission
    try:
        result = create_feedback("unknown_guest", "Unauthorized feedback")
        raise AssertionError("Guest should not have permission to create feedback")
    except PermissionError:
        pass  # Expected

    print("  ✅ PASS: @require_permission decorator works correctly")


def test_decorator_require_role():
    """Test 10: @require_role decorator"""
    print("\n[Test 10] @require_role decorator...")

    @require_role(Role.ADMIN)
    def admin_function(user_id):
        return f"Admin action by {user_id}"

    # Admin can access
    try:
        result = admin_function("admin1")
        assert result == "Admin action by admin1", "Should succeed for admin"
    except PermissionError:
        raise AssertionError("Admin should be able to call admin functions")

    # User cannot access
    try:
        result = admin_function("user1")
        raise AssertionError("Regular user should not be able to call admin functions")
    except PermissionError:
        pass  # Expected

    print("  ✅ PASS: @require_role decorator works correctly")


def test_decorator_require_ownership():
    """Test 11: @require_ownership decorator"""
    print("\n[Test 11] @require_ownership decorator...")

    @require_ownership('feedback')
    def edit_feedback(user_id, feedback_id, new_content):
        return f"Edited {feedback_id}: {new_content}"

    # Owner can edit
    try:
        result = edit_feedback("user1", "fb1", "Updated content")
        assert result == "Edited fb1: Updated content", "Should succeed for owner"
    except PermissionError:
        raise AssertionError("Owner should be able to edit their feedback")

    # Non-owner cannot edit
    try:
        result = edit_feedback("user2", "fb1", "Hacked content")
        raise AssertionError("Non-owner should not be able to edit feedback")
    except PermissionError:
        pass  # Expected

    # Admin can edit (bypass ownership)
    try:
        result = edit_feedback("admin1", "fb1", "Admin override")
        assert result == "Edited fb1: Admin override", "Admin should be able to edit any feedback"
    except PermissionError:
        raise AssertionError("Admin should be able to edit any feedback")

    print("  ✅ PASS: @require_ownership decorator works correctly")


def test_decorator_require_subscription():
    """Test 12: @require_subscription decorator"""
    print("\n[Test 12] @require_subscription decorator...")

    @require_subscription('builder_plus')
    def priority_feature(user_id):
        return f"Priority feature for {user_id}"

    # USER doesn't have builder_plus
    try:
        result = priority_feature("user1")
        raise AssertionError("USER should not have access to builder_plus features")
    except PermissionError:
        pass  # Expected

    # BUILDER_PLUS has access
    try:
        result = priority_feature("user2")
        assert result == "Priority feature for user2", "Should succeed for builder_plus"
    except PermissionError:
        raise AssertionError("BUILDER_PLUS should have access to builder_plus features")

    # Admin has access (higher tier)
    try:
        result = priority_feature("admin1")
        assert result == "Priority feature for admin1", "Admin should have access"
    except PermissionError:
        raise AssertionError("Admin should have access to all subscription features")

    print("  ✅ PASS: @require_subscription decorator works correctly")


def run_all_tests():
    """Run all SEC-006 tests"""
    print("=" * 70)
    print("SEC-006: Broken Access Control Prevention - Test Suite")
    print("=" * 70)

    tests = [
        test_role_assignment,
        test_permission_checking,
        test_resource_ownership,
        test_horizontal_access_control,
        test_vertical_privilege_escalation_prevention,
        test_admin_bypass,
        test_subscription_tier_enforcement,
        test_role_hierarchy,
        test_decorator_require_permission,
        test_decorator_require_role,
        test_decorator_require_ownership,
        test_decorator_require_subscription,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ FAIL: {test.__name__}")
            print(f"     Error: {str(e)}")
            traceback.print_exc()

    print("\n" + "=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)

    if failed == 0:
        print("✅ ALL TESTS PASSED - SEC-006 implementation is secure!")
        return 0
    else:
        print(f"❌ {failed} TESTS FAILED - Please review implementation")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
