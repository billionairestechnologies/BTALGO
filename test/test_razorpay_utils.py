"""Regression tests for Razorpay helpers."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.razorpay import verify_webhook_signature  # noqa: E402


def test_verify_webhook_signature_accepts_valid_signature():
    body = b'{"event":"subscription.activated"}'
    secret = "secret123"
    import hmac
    import hashlib

    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, signature, secret=secret) is True


def test_verify_webhook_signature_rejects_invalid_signature():
    body = b'{"event":"subscription.activated"}'
    assert verify_webhook_signature(body, "bad-signature", secret="secret123") is False
