"""Regression tests for BillionairsHQ billing plan helpers."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.subscriptions import get_plan_definition, is_subscription_active, resolve_entitlements  # noqa: E402


class DummySubscription:
    def __init__(self, plan_code: str, status: str):
        self.plan_code = plan_code
        self.status = status


def test_get_plan_definition_returns_catalog_entry():
    plan = get_plan_definition("pro")
    assert plan is not None
    assert plan["code"] == "pro"
    assert plan["entitlements"]["copy_trading"] is True


def test_is_subscription_active_accepts_trialing_and_active():
    assert is_subscription_active("trialing") is True
    assert is_subscription_active("active") is True
    assert is_subscription_active("cancelled") is False


def test_resolve_entitlements_uses_plan_and_status():
    entitlements = resolve_entitlements(DummySubscription("elite", "active"))
    assert entitlements["plan_code"] == "elite"
    assert entitlements["billing_active"] is True
    assert entitlements["static_ip"] is True


def test_resolve_entitlements_falls_back_for_unknown_plan():
    entitlements = resolve_entitlements(DummySubscription("unknown", "cancelled"))
    assert entitlements["billing_active"] is False
    assert entitlements["strategy_builder"] is True
    assert entitlements["live_trading"] is False
