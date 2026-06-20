"""Regression tests for BillionairsHQ entitlement enforcement helpers."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.access_control as access_control  # noqa: E402


class _DummySubscription:
    def __init__(self, plan_code: str, status: str):
        self.plan_code = plan_code
        self.status = status
        self.razorpay_customer_id = None
        self.razorpay_subscription_id = None
        self.current_period_start = None
        self.current_period_end = None


def test_require_live_trading_allows_trial_workspace(monkeypatch):
    monkeypatch.setattr(access_control, "get_profile_by_username", lambda username: SimpleNamespace(tenant_id=1))
    monkeypatch.setattr(
        access_control,
        "get_or_create_subscription_for_tenant",
        lambda tenant_id: _DummySubscription("free", "trialing"),
    )

    allowed, payload, status = access_control.require_live_trading(username="trader1")

    assert allowed is True
    assert payload is None
    assert status is None


def test_require_mcp_write_blocks_without_entitlement(monkeypatch):
    monkeypatch.setattr(access_control, "get_profile_by_username", lambda username: SimpleNamespace(tenant_id=1))
    monkeypatch.setattr(
        access_control,
        "get_or_create_subscription_for_tenant",
        lambda tenant_id: _DummySubscription("starter", "active"),
    )

    allowed, payload, status = access_control.require_mcp_write(username="trader1")

    assert allowed is False
    assert status == 403
    assert payload["feature"] == "mcp_write"
    assert payload["code"] == "subscription_required"


def test_require_live_trading_blocks_cancelled_workspace(monkeypatch):
    monkeypatch.setattr(access_control, "get_profile_by_username", lambda username: SimpleNamespace(tenant_id=1))
    monkeypatch.setattr(
        access_control,
        "get_or_create_subscription_for_tenant",
        lambda tenant_id: _DummySubscription("free", "cancelled"),
    )

    allowed, payload, status = access_control.require_live_trading(username="trader1")

    assert allowed is False
    assert status == 403
    assert payload["feature"] == "live_trading"
