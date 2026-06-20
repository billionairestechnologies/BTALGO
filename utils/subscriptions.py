"""Plan catalog and entitlement helpers for BillionairsHQ SaaS billing."""

import os


PLAN_DEFINITIONS = [
    {
        "code": "starter",
        "name": "Starter",
        "price_label": "Rs 2,499 / month",
        "env_key": "RAZORPAY_PLAN_STARTER_ID",
        "entitlements": {
            "live_trading": True,
            "mcp_write": False,
            "static_ip": False,
            "copy_trading": False,
            "strategy_builder": True,
            "python_sdk": True,
            "telegram": True,
            "whatsapp": True,
            "broker_accounts_limit": 2,
        },
    },
    {
        "code": "pro",
        "name": "Pro",
        "price_label": "Rs 6,999 / month",
        "env_key": "RAZORPAY_PLAN_PRO_ID",
        "entitlements": {
            "live_trading": True,
            "mcp_write": True,
            "static_ip": False,
            "copy_trading": True,
            "strategy_builder": True,
            "python_sdk": True,
            "telegram": True,
            "whatsapp": True,
            "broker_accounts_limit": 5,
        },
    },
    {
        "code": "elite",
        "name": "Elite",
        "price_label": "Rs 14,999 / month",
        "env_key": "RAZORPAY_PLAN_ELITE_ID",
        "entitlements": {
            "live_trading": True,
            "mcp_write": True,
            "static_ip": True,
            "copy_trading": True,
            "strategy_builder": True,
            "python_sdk": True,
            "telegram": True,
            "whatsapp": True,
            "broker_accounts_limit": 20,
        },
    },
]

ACTIVE_SUBSCRIPTION_STATUSES = {
    "active",
    "authenticated",
    "created",
    "resumed",
    "trialing",
}


def get_plan_catalog() -> list[dict]:
    plans = []
    for definition in PLAN_DEFINITIONS:
        plan_id = (os.getenv(definition["env_key"]) or "").strip()
        plans.append(
            {
                "code": definition["code"],
                "name": definition["name"],
                "price_label": definition["price_label"],
                "configured": bool(plan_id),
                "plan_id": plan_id or None,
                "entitlements": definition["entitlements"],
            }
        )
    return plans


def get_plan_definition(plan_code: str) -> dict | None:
    normalized = (plan_code or "").strip().lower()
    for plan in get_plan_catalog():
        if plan["code"] == normalized:
            return plan
    return None


def resolve_plan_id(plan_code: str) -> str | None:
    plan = get_plan_definition(plan_code)
    if not plan:
        return None
    return plan["plan_id"]


def is_subscription_active(status: str | None) -> bool:
    return (status or "").strip().lower() in ACTIVE_SUBSCRIPTION_STATUSES


def resolve_entitlements(subscription) -> dict:
    plan = get_plan_definition(getattr(subscription, "plan_code", "free") or "free")
    entitlements = dict(plan["entitlements"]) if plan else {
        "live_trading": False,
        "mcp_write": False,
        "static_ip": False,
        "copy_trading": False,
        "strategy_builder": True,
        "python_sdk": True,
        "telegram": True,
        "whatsapp": True,
        "broker_accounts_limit": 1,
    }
    entitlements["billing_active"] = is_subscription_active(getattr(subscription, "status", None))
    entitlements["plan_code"] = getattr(subscription, "plan_code", "free") or "free"
    entitlements["status"] = getattr(subscription, "status", "trialing") or "trialing"
    return entitlements
