import json
import os

from broker.sharekhan.api.baseurl import get_url
from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)


def _get_headers(auth_token):
    api_key = os.getenv("BROKER_API_KEY", "")
    return {
        "api-key": api_key,
        "access-token": auth_token,
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _get_customer_id():
    try:
        from database.auth_db import get_user_id
        return get_user_id("sharekhan") or ""
    except Exception:
        return ""


def test_auth_token(auth_token):
    """Validate auth token by calling the funds endpoint."""
    try:
        user_id = _get_customer_id()
        client = get_httpx_client()
        headers = _get_headers(auth_token)
        # Use NSE as a quick check exchange
        url = get_url(f"/skapi/services/limitstmt/NSE/{user_id}")
        response = client.get(url, headers=headers)
        data = response.json()

        if response.status_code == 401 or data.get("error_type") in ("TokenException", "Invalid_Authentication"):
            return False, data.get("message", "Invalid authentication token")
        if response.status_code == 200:
            return True, None
        return False, f"HTTP {response.status_code}"
    except Exception as e:
        logger.error(f"Sharekhan test_auth_token error: {e}")
        return False, str(e)


def get_margin_data(auth_token):
    """Fetch available margin / funds from Sharekhan."""
    try:
        user_id = _get_customer_id()
        client = get_httpx_client()
        headers = _get_headers(auth_token)

        # Fetch funds for NSE (covers equity margin)
        url = get_url(f"/skapi/services/limitstmt/NSE/{user_id}")
        response = client.get(url, headers=headers)
        data = response.json()
        logger.info(f"Sharekhan Funds: {data}")

        if response.status_code != 200 or not data:
            return {
                "availablecash": "0.00",
                "collateral": "0.00",
                "m2munrealized": "0.00",
                "m2mrealized": "0.00",
                "utiliseddebits": "0.00",
            }

        # Sharekhan limitstmt may return a list or a dict
        if isinstance(data, list) and data:
            record = data[0]
        elif isinstance(data, dict):
            record = data
        else:
            record = {}

        def _f(val):
            try:
                return f"{float(val):.2f}"
            except Exception:
                return "0.00"

        return {
            "availablecash": _f(
                record.get("netAvailableBalance")
                or record.get("availableBalance")
                or record.get("availableCash")
                or 0
            ),
            "collateral": _f(record.get("collateral") or record.get("collateralValue") or 0),
            "m2munrealized": _f(
                record.get("unrealizedMTM") or record.get("mtmUnrealized") or 0
            ),
            "m2mrealized": _f(
                record.get("realizedMTM") or record.get("mtmRealized") or 0
            ),
            "utiliseddebits": _f(
                record.get("utilisedAmount")
                or record.get("usedMargin")
                or record.get("debit")
                or 0
            ),
        }

    except Exception as e:
        logger.exception(f"Sharekhan get_margin_data error: {e}")
        return {
            "availablecash": "0.00",
            "collateral": "0.00",
            "m2munrealized": "0.00",
            "m2mrealized": "0.00",
            "utiliseddebits": "0.00",
        }
