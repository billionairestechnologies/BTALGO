"""Resend-backed transactional email helpers for public auth flows."""

import os
from html import escape

import requests

from utils.logging import get_logger

logger = get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _get_sender() -> tuple[str | None, str]:
    from_email = (os.getenv("RESEND_FROM_EMAIL") or "").strip()
    from_name = (os.getenv("RESEND_FROM_NAME") or os.getenv("PRODUCT_NAME") or "BillionairsHQ").strip()
    return (from_email or None), from_name


def send_registration_otp_email(recipient_email: str, otp_code: str, expiry_minutes: int = 10) -> dict:
    """Send a one-time signup verification code via Resend."""
    api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    from_email, from_name = _get_sender()
    product_name = (os.getenv("PRODUCT_NAME") or "BillionairsHQ").strip()

    if not api_key:
        return {"success": False, "message": "RESEND_API_KEY is not configured."}
    if not from_email:
        return {"success": False, "message": "RESEND_FROM_EMAIL is not configured."}

    subject = f"Verify your {product_name} account"
    safe_product_name = escape(product_name)
    safe_code = escape(otp_code)

    html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:Segoe UI,Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="min-height:100vh;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="100%" style="max-width:480px;background:#141414;border:1px solid #262626;border-radius:16px;overflow:hidden;">
          <tr>
            <td style="padding:36px 32px 20px 32px;text-align:center;">
              <h1 style="margin:0;font-size:24px;color:#fafafa;font-weight:600;">Verify your email</h1>
              <p style="margin:12px 0 0 0;font-size:15px;line-height:1.6;color:#a1a1aa;">
                Use this code to finish creating your {safe_product_name} account.
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 16px 32px;text-align:center;">
              <div style="display:inline-block;padding:16px 24px;border-radius:12px;background:#1c1c1c;border:1px solid #262626;font-size:32px;letter-spacing:8px;color:#fafafa;font-weight:700;">
                {safe_code}
              </div>
            </td>
          </tr>
          <tr>
            <td style="padding:0 32px 32px 32px;text-align:center;">
              <p style="margin:0;font-size:13px;color:#71717a;">
                This code expires in {expiry_minutes} minutes.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
    """.strip()

    text = (
        f"Verify your {product_name} account\n\n"
        f"Your verification code is: {otp_code}\n"
        f"This code expires in {expiry_minutes} minutes.\n"
    )

    payload = {
        "from": f"{from_name} <{from_email}>",
        "to": [recipient_email],
        "subject": subject,
        "html": html,
        "text": text,
    }

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=20,
        )
        if response.ok:
            return {"success": True, "message": "Verification code sent.", "provider": "resend"}

        logger.error("Resend OTP send failed: %s %s", response.status_code, response.text[:500])
        return {
            "success": False,
            "message": "Failed to send verification code. Please try again in a moment.",
        }
    except requests.RequestException as exc:
        logger.error("Resend OTP send exception: %s", exc)
        return {
            "success": False,
            "message": "Could not reach the email service. Please try again in a moment.",
        }
