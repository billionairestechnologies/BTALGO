"""Regression tests for SaaS MPIN hashing helpers."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.saas_db import UserProfile  # noqa: E402


def test_profile_mpin_roundtrip():
    profile = UserProfile()
    profile.set_mpin("1234")
    assert profile.mpin_enabled is True
    assert profile.mpin_hash
    assert profile.verify_mpin("1234") is True
    assert profile.verify_mpin("9999") is False


def test_profile_clear_mpin():
    profile = UserProfile()
    profile.set_mpin("123456")
    profile.clear_mpin()
    assert profile.mpin_enabled is False
    assert profile.mpin_hash is None


def test_profile_mpin_rejects_invalid_length():
    profile = UserProfile()
    try:
        profile.set_mpin("12")
    except ValueError as exc:
        assert "4 or 6 digits" in str(exc)
    else:
        raise AssertionError("Expected invalid MPIN length to raise ValueError")
