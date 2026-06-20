"""Minimal Razorpay helpers for BillionairsHQ billing flows."""

import base64
import hashlib
import hmac
import json
import os
from typing import Any

import requests

from utils.logging import get_logger

logger = get_logger(__name__)

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"


def _auth_header() -> dict[str, str]:
    key_id = (os.getenv("RAZORPAY_KEY_ID") or "").strip()
    key_secret = (os.getenv("RAZORPAY_KEY_SECRET") or "").strip()
    token = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _require_api_keys() -> tuple[str, str]:
    key_id = (os.getenv("RAZORPAY_KEY_ID") or "").strip()
    key_secret = (os.getenv("RAZORPAY_KEY_SECRET") or "").strip()
    if not key_id or not key_secret:
        raise ValueError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be configured.")
    return key_id, key_secret


def create_customer(*, name: str, email: str, contact: str | None = None, notes: dict | None = None) -> dict[str, Any]:
    _require_api_keys()
    payload: dict[str, Any] = {
        "name": name[:80] or email,
        "email": email,
        "fail_existing": 0,
    }
    if contact:
        payload["contact"] = contact
    if notes:
        payload["notes"] = notes

    response = requests.post(
        f"{RAZORPAY_API_BASE}/customers",
        headers=_auth_header(),
        data=json.dumps(payload),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def create_subscription(
    *,
    plan_id: str,
    total_count: int = 12,
    quantity: int = 1,
    customer_notify: int = 1,
    notes: dict | None = None,
) -> dict[str, Any]:
    _require_api_keys()
    payload: dict[str, Any] = {
        "plan_id": plan_id,
        "total_count": total_count,
        "quantity": quantity,
        "customer_notify": customer_notify,
    }
    if notes:
        payload["notes"] = notes

    response = requests.post(
        f"{RAZORPAY_API_BASE}/subscriptions",
        headers=_auth_header(),
        data=json.dumps(payload),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def fetch_subscription(subscription_id: str) -> dict[str, Any]:
    _require_api_keys()
    response = requests.get(
        f"{RAZORPAY_API_BASE}/subscriptions/{subscription_id}",
        headers=_auth_header(),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def verify_webhook_signature(raw_body: bytes, signature: str | None, secret: str | None = None) -> bool:
    secret = (secret or os.getenv("RAZORPAY_WEBHOOK_SECRET") or "").strip()
    if not signature or not secret:
        return False

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
