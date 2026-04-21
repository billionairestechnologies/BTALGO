import json
import os

from broker.sharekhan.api.baseurl import get_url
from broker.sharekhan.mapping.transform_data import (
    map_exchange,
    map_order_type,
    map_product_type,
    reverse_map_exchange,
    reverse_map_order_type,
    reverse_map_product_type,
    transform_data,
    transform_modify_order_data,
)
from database.auth_db import get_auth_token, get_user_id, verify_api_key
from database.token_db import get_br_symbol, get_oa_symbol, get_symbol, get_token
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


def _api_call(endpoint, auth_token, method="GET", payload=None):
    client = get_httpx_client()
    headers = _get_headers(auth_token)
    url = get_url(endpoint)
    try:
        if method == "GET":
            response = client.get(url, headers=headers)
        elif method == "POST":
            response = client.post(url, headers=headers, content=json.dumps(payload or {}))
        elif method == "PUT":
            response = client.put(url, headers=headers, content=json.dumps(payload or {}))
        elif method == "DELETE":
            response = client.request("DELETE", url, headers=headers, content=json.dumps(payload or {}))
        else:
            response = client.request(method, url, headers=headers, content=json.dumps(payload or {}))
        return response.json()
    except Exception as e:
        logger.exception(f"Sharekhan API error {method} {url}: {e}")
        return {"error_type": "ConnectionError", "message": str(e)}


# ── Order Book ─────────────────────────────────────────────────────────────────

def get_order_book(auth_token):
    user_id = _get_customer_id(auth_token)
    data = _api_call(f"/skapi/services/reports/{user_id}", auth_token)
    logger.debug(f"Sharekhan OrderBook: {data}")
    return data


def get_trade_book(auth_token):
    user_id = _get_customer_id(auth_token)
    data = _api_call(f"/skapi/services/trades/{user_id}", auth_token)
    logger.debug(f"Sharekhan TradeBook: {data}")
    return data


def get_positions(auth_token):
    user_id = _get_customer_id(auth_token)
    data = _api_call(f"/skapi/services/trades/{user_id}", auth_token)
    logger.debug(f"Sharekhan Positions: {data}")
    return data


def get_holdings(auth_token):
    user_id = _get_customer_id(auth_token)
    data = _api_call(f"/skapi/services/holdings/{user_id}", auth_token)
    logger.debug(f"Sharekhan Holdings: {data}")
    return data


def _get_customer_id(auth_token):
    """Retrieve customerId stored as user_id in the auth DB."""
    try:
        from database.auth_db import get_user_id as _get_uid
        uid = _get_uid("sharekhan")
        return uid or ""
    except Exception:
        return ""


# ── Place / Modify / Cancel Order ──────────────────────────────────────────────

def place_order_api(data, auth_token):
    try:
        token = get_token(data["symbol"], data["exchange"])
        if not token:
            return None, f"Token not found for {data['symbol']} on {data['exchange']}"

        payload = transform_data(data, token)
        response = _api_call("/skapi/services/orders", auth_token, method="POST", payload=payload)
        logger.info(f"Sharekhan PlaceOrder response: {response}")

        if response.get("orderId") or response.get("order_id"):
            order_id = response.get("orderId") or response.get("order_id")
            return order_id, None
        else:
            err = response.get("message") or response.get("error_type") or str(response)
            return None, err

    except Exception as e:
        logger.exception(f"Sharekhan place_order_api error: {e}")
        return None, str(e)


def place_smartorder_api(data, auth_token):
    """Smart order: checks position before placing to avoid duplicate entries."""
    try:
        position_book = get_positions(auth_token)
        existing_qty = 0

        if isinstance(position_book, list):
            for pos in position_book:
                sym = pos.get("tradingSymbol", "") or pos.get("symbol", "")
                exch = pos.get("exchange", "")
                qty = int(pos.get("netQty", 0) or pos.get("quantity", 0))
                if sym == data.get("symbol") and exch == data.get("exchange"):
                    existing_qty = qty
                    break

        req_qty = int(data.get("quantity", 0))
        action = data.get("action", "BUY").upper()

        if action == "BUY" and existing_qty >= req_qty:
            return {"status": "success", "message": "Position already satisfied", "orderid": "smart_skip"}, None
        if action == "SELL" and existing_qty <= -req_qty:
            return {"status": "success", "message": "Position already satisfied", "orderid": "smart_skip"}, None

        order_id, err = place_order_api(data, auth_token)
        if order_id:
            return {"status": "success", "orderid": order_id}, None
        return None, err

    except Exception as e:
        logger.exception(f"Sharekhan place_smartorder_api error: {e}")
        return None, str(e)


def modify_order_api(data, auth_token):
    try:
        token = get_token(data["symbol"], data["exchange"])
        payload = transform_modify_order_data(data, token)
        response = _api_call("/skapi/services/orders", auth_token, method="PUT", payload=payload)
        logger.info(f"Sharekhan ModifyOrder response: {response}")

        if response.get("orderId") or response.get("order_id"):
            return response.get("orderId") or response.get("order_id"), None
        else:
            err = response.get("message") or str(response)
            return None, err

    except Exception as e:
        logger.exception(f"Sharekhan modify_order_api error: {e}")
        return None, str(e)


def cancel_order_api(data, auth_token):
    try:
        user_id = _get_customer_id(auth_token)
        payload = {
            "orderId": data["orderid"],
            "customerId": user_id,
            "requestType": "CANCEL",
        }
        # scripCode needed — fetch from token_db
        token = get_token(data.get("symbol", ""), data.get("exchange", ""))
        if token:
            payload["scripCode"] = token

        response = _api_call("/skapi/services/orders", auth_token, method="DELETE", payload=payload)
        logger.info(f"Sharekhan CancelOrder response: {response}")

        if response.get("orderId") or response.get("order_id"):
            return response.get("orderId") or response.get("order_id"), None
        else:
            err = response.get("message") or str(response)
            return None, err

    except Exception as e:
        logger.exception(f"Sharekhan cancel_order_api error: {e}")
        return None, str(e)


def close_position(position_symbol, position_exchange, auth_token):
    """Square off a single open position."""
    try:
        positions = get_positions(auth_token)
        if not isinstance(positions, list):
            return {"status": "error", "message": "Could not fetch positions"}, None

        for pos in positions:
            sym = pos.get("tradingSymbol", "") or pos.get("symbol", "")
            exch = pos.get("exchange", "")
            qty = int(pos.get("netQty", 0) or pos.get("quantity", 0))

            if sym == position_symbol and exch == position_exchange and qty != 0:
                action = "SELL" if qty > 0 else "BUY"
                order_data = {
                    "symbol": position_symbol,
                    "exchange": position_exchange,
                    "action": action,
                    "quantity": abs(qty),
                    "price": "0",
                    "pricetype": "MARKET",
                    "product": pos.get("productType", "MIS"),
                }
                order_id, err = place_order_api(order_data, auth_token)
                if order_id:
                    return {"status": "success", "orderid": order_id}, None
                return {"status": "error", "message": err}, None

        return {"status": "error", "message": "No open position found"}, None

    except Exception as e:
        logger.exception(f"Sharekhan close_position error: {e}")
        return {"status": "error", "message": str(e)}, None


def cancel_all_orders_api(data, auth_token):
    """Cancel all pending orders for a given symbol+exchange."""
    try:
        order_book = get_order_book(auth_token)
        cancelled = []
        errors = []

        if isinstance(order_book, list):
            for order in order_book:
                status = (order.get("orderStatus") or order.get("status") or "").upper()
                if status not in ("PENDING", "OPEN", "TRIGGER_PENDING"):
                    continue
                sym = order.get("tradingSymbol", "") or order.get("symbol", "")
                exch = order.get("exchange", "")
                if data.get("symbol") and sym != data["symbol"]:
                    continue
                if data.get("exchange") and exch != data["exchange"]:
                    continue

                cancel_data = {
                    "orderid": order.get("orderId") or order.get("order_id"),
                    "symbol": sym,
                    "exchange": exch,
                }
                oid, err = cancel_order_api(cancel_data, auth_token)
                if oid:
                    cancelled.append(oid)
                else:
                    errors.append(err)

        return {
            "status": "success" if not errors else "partial",
            "cancelled": cancelled,
            "errors": errors,
        }, None

    except Exception as e:
        logger.exception(f"Sharekhan cancel_all_orders_api error: {e}")
        return None, str(e)
