"""Entitlement checks for BillionairsHQ feature access."""

from __future__ import annotations

from typing import Any

from flask import has_request_context, session

from database.auth_db import verify_api_key
from database.saas_db import get_or_create_subscription_for_tenant, get_profile_by_username, serialize_subscription
from utils.subscriptions import resolve_entitlements


def _resolve_username(*, username: str | None = None, api_key: str | None = None) -> str | None:
    if username:
        return username
    if api_key:
        user_id = verify_api_key(api_key)
        if user_id:
            return str(user_id)
    if has_request_context():
        return session.get("user")
    return None


def get_entitlement_context(
    *,
    username: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any] | None:
    resolved_username = _resolve_username(username=username, api_key=api_key)
    if not resolved_username:
        return None

    profile = get_profile_by_username(resolved_username)
    if profile is None:
        return None

    subscription = get_or_create_subscription_for_tenant(profile.tenant_id)
    return {
        "username": resolved_username,
        "profile": profile,
        "subscription": subscription,
        "entitlements": resolve_entitlements(subscription),
    }


def _blocked_response(feature: str, message: str, subscription) -> tuple[bool, dict[str, Any], int]:
    return (
        False,
        {
            "status": "error",
            "code": "subscription_required",
            "feature": feature,
            "message": message,
            "subscription": serialize_subscription(subscription),
            "entitlements": resolve_entitlements(subscription),
        },
        403,
    )


def require_live_trading(
    *,
    username: str | None = None,
    api_key: str | None = None,
) -> tuple[bool, dict[str, Any] | None, int | None]:
    context = get_entitlement_context(username=username, api_key=api_key)
    if context is None:
        return True, None, None

    if context["entitlements"].get("live_trading"):
        return True, None, None

    return _blocked_response(
        "live_trading",
        "Live trading is not enabled for your current BillionairsHQ plan.",
        context["subscription"],
    )


def require_mcp_write(
    *,
    username: str | None = None,
) -> tuple[bool, dict[str, Any] | None, int | None]:
    context = get_entitlement_context(username=username)
    if context is None:
        return True, None, None

    if context["entitlements"].get("mcp_write"):
        return True, None, None

    return _blocked_response(
        "mcp_write",
        "MCP write access is not enabled for your current BillionairsHQ plan.",
        context["subscription"],
    )


def require_static_ip(
    *,
    username: str | None = None,
) -> tuple[bool, dict[str, Any] | None, int | None]:
    context = get_entitlement_context(username=username)
    if context is None:
        return True, None, None

    if context["entitlements"].get("static_ip"):
        return True, None, None

    return _blocked_response(
        "static_ip",
        "Static IP routing is not enabled for your current BillionairsHQ plan.",
        context["subscription"],
    )
