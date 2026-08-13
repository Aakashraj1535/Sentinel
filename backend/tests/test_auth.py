"""
Tests for app/auth.py — the role-enforcement layer behind require_role().
No FastAPI test client needed; the dependency function is a plain
callable once you unwrap the factory.
"""
import pytest
from fastapi import HTTPException

from app.auth import get_current_role, require_role, ROLE_LEVELS


def test_role_order_is_as_expected():
    assert ROLE_LEVELS["Viewer"] < ROLE_LEVELS["Procurement Manager"] < ROLE_LEVELS["Admin"]


def test_unknown_role_header_falls_back_to_viewer():
    assert get_current_role("SuperHacker") == "Viewer"


def test_missing_role_header_defaults_to_viewer():
    assert get_current_role() == "Viewer"


def test_known_roles_pass_through():
    for role in ROLE_LEVELS:
        assert get_current_role(role) == role


def test_require_role_allows_exact_match():
    dependency = require_role("Procurement Manager")
    assert dependency(role="Procurement Manager") == "Procurement Manager"


def test_require_role_allows_higher_role():
    dependency = require_role("Procurement Manager")
    assert dependency(role="Admin") == "Admin"


def test_require_role_blocks_lower_role():
    dependency = require_role("Admin")
    with pytest.raises(HTTPException) as exc_info:
        dependency(role="Viewer")
    assert exc_info.value.status_code == 403


def test_require_role_blocks_viewer_from_manager_actions():
    dependency = require_role("Procurement Manager")
    with pytest.raises(HTTPException) as exc_info:
        dependency(role="Viewer")
    assert exc_info.value.status_code == 403
