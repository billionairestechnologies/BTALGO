import hashlib
import json
import os

from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)

AUTH_BASE_URL = "https://api.sharekhan.com"
LOGIN_URL = "https://api.sharekhan.com/skapi/auth"
TOKEN_URL = "https://api.sharekhan.com/skapi/services/access/token"


def get_login_url():
    """Build the Sharekhan OAuth redirect URL."""
    api_key = os.getenv("BROKER_API_KEY", "")
    # state is an arbitrary string; we use a fixed value for simplicity
    state = "btalgo"
    return f"{LOGIN_URL}?api_key={api_key}&state={state}&version_id=1.0"


def _decrypt_request_token(request_token):
    """
    Sharekhan returns a request_token that is SHA-256(api_key + request_token + api_secret).
    We do NOT decrypt it — we pass it directly and include the hash in the token exchange call.
    Returns (request_token, api_key, api_secret).
    """
    api_key = os.getenv("BROKER_API_KEY", "")
    api_secret = os.getenv("BROKER_API_SECRET", "")
    return request_token, api_key, api_secret


def authenticate_broker(request_token):
    """
    Exchange the OAuth request_token for an access_token.
    Returns (access_token, customer_id, error_message).
    """
    try:
        request_token, api_key, api_secret = _decrypt_request_token(request_token)

        if not api_key:
            return None, None, "BROKER_API_KEY not configured"
        if not api_secret:
            return None, None, "BROKER_API_SECRET not configured"
        if not request_token:
            return None, None, "No request token provided"

        # Build the checksum: SHA-256(api_key + request_token + api_secret)
        checksum = hashlib.sha256(
            f"{api_key}{request_token}{api_secret}".encode("utf-8")
        ).hexdigest()

        payload = {
            "api_key": api_key,
            "request_token": request_token,
            "checksum": checksum,
        }

        headers = {
            "api-key": api_key,
            "Content-Type": "application/json",
        }

        client = get_httpx_client()
        response = client.post(TOKEN_URL, headers=headers, content=json.dumps(payload))

        logger.info(f"Sharekhan token exchange status: {response.status_code}")
        logger.debug(f"Sharekhan token response: {response.text}")

        if response.status_code == 200:
            data = response.json()
            # Response keys: accessToken, customerId, publicToken, etc.
            access_token = data.get("accessToken") or data.get("access_token")
            customer_id = data.get("customerId") or data.get("customer_id") or data.get("userId")

            if access_token:
                logger.info(f"Sharekhan authentication successful for customer: {customer_id}")
                return access_token, customer_id, None
            else:
                err = data.get("message") or data.get("error_type") or "Access token not in response"
                logger.error(f"Sharekhan auth failed: {err}")
                return None, None, err
        else:
            try:
                err_data = response.json()
                err = err_data.get("message") or err_data.get("error_type") or response.text
            except Exception:
                err = f"HTTP {response.status_code}: {response.text}"
            logger.error(f"Sharekhan token exchange error: {err}")
            return None, None, err

    except Exception as e:
        logger.exception(f"Exception in Sharekhan authenticate_broker: {e}")
        return None, None, f"An exception occurred: {str(e)}"
