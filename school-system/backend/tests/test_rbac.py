"""Integration tests for RBAC enforcement.

Validates that every role has correct access across the permission matrix.
"""

import pytest
from app.core.rbac import has_permission, ROLES, get_permissions
from app.core.rbac_enforcer import RBAC_ROUTE_MAP, generate_permission_matrix


class TestRBACPermissions:
    """Test the complete permission matrix."""

    def test_all_roles_defined(self):
        """Every role in the system has permissions defined."""
        for role_name, role_def in ROLES.items():
            assert "permissions" in role_def
            assert len(role_def["permissions"]) > 0, f"{role_name} has no permissions"

    def test_platform_admin_has_all(self):
        """Platform admin can do everything."""
        assert has_permission("platform_admin", "students:create")
        assert has_permission("platform_admin", "schools:manage")
        assert has_permission("platform_admin", "any:thing")

    def test_school_admin_permissions(self):
        """School admin has broad but not unlimited access."""
        assert has_permission("school_admin", "students:create")
        assert has_permission("school_admin", "teachers:create")
        assert has_permission("school_admin", "reports:export")
        assert has_permission("school_admin", "settings:manage")
        assert not has_permission("school_admin", "any:unknown")

    def test_teacher_cannot_manage_schools(self):
        """Regular teacher cannot manage schools or settings."""
        assert not has_permission("teacher", "schools:create")
        assert not has_permission("teacher", "settings:manage")
        assert not has_permission("teacher", "students:promote")

    def test_teacher_can_write_attendance(self):
        """Teacher CAN record attendance and marks."""
        assert has_permission("teacher", "attendance:write")
        assert has_permission("teacher", "marks:write")
        assert has_permission("teacher", "lessons:write")
        assert has_permission("teacher", "timetable:view")

    def test_head_teacher_permissions(self):
        """Head teacher has elevated academic permissions."""
        assert has_permission("head_teacher", "students:promote")
        assert has_permission("head_teacher", "exams:manage")
        assert has_permission("head_teacher", "analytics:view")
        assert has_permission("head_teacher", "timetable:manage")
        assert not has_permission("head_teacher", "settings:manage")

    def test_class_teacher_vs_subject_teacher(self):
        """Class teacher has attendance rights; subject teacher may not."""
        assert has_permission("class_teacher", "attendance:write")
        # Subject teacher doesn't have attendance:write in default config
        # This depends on how we configure it

    def test_deputy_principal_permissions(self):
        """Deputy principal is between head and school admin."""
        assert has_permission("deputy_principal", "reports:export")
        assert has_permission("deputy_principal", "analytics:view")
        assert has_permission("deputy_principal", "students:promote")
        assert not has_permission("deputy_principal", "settings:manage")
        assert not has_permission("deputy_principal", "students:create")


class TestRouteMap:
    """Test the RBAC route map covers all known endpoints."""

    def test_all_routes_have_permissions(self):
        """Every route in the map has a permission string."""
        for route, meta in RBAC_ROUTE_MAP.items():
            assert "perm" in meta, f"Route {route} missing 'perm'"
            assert isinstance(meta["perm"], str)

    def test_public_routes_identified(self):
        """Login/refresh routes marked as public."""
        assert RBAC_ROUTE_MAP["POST /api/v1/auth/login"]["public"] is True
        assert RBAC_ROUTE_MAP["POST /api/v1/auth/refresh"]["public"] is True

    def test_matrix_generation(self):
        """Permission matrix generates without errors."""
        matrix = generate_permission_matrix()
        assert len(matrix) == len(ROLES)
        # Platform admin has access to everything
        for route, allowed in matrix["platform_admin"].items():
            assert allowed is True, f"Platform admin denied: {route}"

    def test_student_endpoints(self):
        """Student endpoints covered."""
        assert "GET  /api/v1/students" in RBAC_ROUTE_MAP
        assert "POST /api/v1/students" in RBAC_ROUTE_MAP
        assert "POST /api/v1/students/{student_id}/promote" in RBAC_ROUTE_MAP


class TestPermissionWildcards:
    """Wildcard and resource-level permission checks."""

    def test_resource_wildcard(self):
        """'students:*' grants all student permissions."""
        perms = get_permissions("school_admin")
        assert "students:*" in perms or (
            "students:create" in perms and "students:read" in perms
        )

    def test_global_wildcard(self):
        """'*:*' grants everything."""
        perms = get_permissions("platform_admin")
        assert "*:*" in perms
        assert has_permission("platform_admin", "nonexistent:action")
