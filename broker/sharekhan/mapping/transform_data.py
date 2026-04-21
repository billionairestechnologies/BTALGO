"""
OpenAlgo ↔ Sharekhan field mapping.

OpenAlgo standard:
  action:    BUY | SELL
  exchange:  NSE | BSE | NFO | BFO | CDS | MCX
  product:   CNC | MIS | NRML
  pricetype: MARKET | LIMIT | SL | SL-M
  symbol:    e.g. RELIANCE
  quantity:  int
  price:     float
  trigger_price: float (for SL orders)

Sharekhan order fields:
  transactionType: BUY | SELL
  exchange:        NSE | BSE | NFO | BFO | CDS | MCX
  productType:     CNC | MIS | NRML | BigTrade | EMF
  orderType:       MARKET | LIMIT | STOP_LOSS_LIMIT | STOP_LOSS_MARKET
  tradingSymbol:   e.g. RELIANCE
  scripCode:       broker instrument token
  quantity:        int
  price:           float
  triggerPrice:    float
  customerId:      broker user ID
  requestType:     NEW | MODIFY | CANCEL
"""


# ── Exchange mapping ──────────────────────────────────────────────────────────

def map_exchange(exchange):
    """OpenAlgo → Sharekhan exchange code."""
    mapping = {
        "NSE": "NSE",
        "BSE": "BSE",
        "NFO": "NFO",
        "BFO": "BFO",
        "CDS": "CDS",
        "MCX": "MCX",
        "NSE_INDEX": "NSE",
        "BSE_INDEX": "BSE",
    }
    return mapping.get(exchange.upper(), exchange)


def reverse_map_exchange(br_exchange):
    """Sharekhan → OpenAlgo exchange code."""
    mapping = {
        "NSE": "NSE",
        "BSE": "BSE",
        "NFO": "NFO",
        "BFO": "BFO",
        "CDS": "CDS",
        "MCX": "MCX",
    }
    return mapping.get(br_exchange.upper(), br_exchange)


# ── Product type mapping ──────────────────────────────────────────────────────

def map_product_type(product):
    """OpenAlgo → Sharekhan product type."""
    mapping = {
        "CNC": "CNC",
        "MIS": "MIS",
        "NRML": "NRML",
        "BO": "BO",
        "CO": "CO",
    }
    return mapping.get(product.upper(), product)


def reverse_map_product_type(br_product):
    """Sharekhan → OpenAlgo product type."""
    mapping = {
        "CNC": "CNC",
        "MIS": "MIS",
        "NRML": "NRML",
        "BIGTRADE": "NRML",
        "EMF": "CNC",
        "BO": "BO",
        "CO": "CO",
    }
    return mapping.get((br_product or "").upper(), br_product)


# ── Order type mapping ────────────────────────────────────────────────────────

def map_order_type(pricetype):
    """OpenAlgo → Sharekhan order type."""
    mapping = {
        "MARKET": "MARKET",
        "LIMIT": "LIMIT",
        "SL": "STOP_LOSS_LIMIT",
        "SL-M": "STOP_LOSS_MARKET",
    }
    return mapping.get(pricetype.upper(), "MARKET")


def reverse_map_order_type(br_order_type):
    """Sharekhan → OpenAlgo order type."""
    mapping = {
        "MARKET": "MARKET",
        "LIMIT": "LIMIT",
        "STOP_LOSS_LIMIT": "SL",
        "STOP_LOSS_MARKET": "SL-M",
    }
    return mapping.get((br_order_type or "").upper(), br_order_type)


# ── Transform order data ──────────────────────────────────────────────────────

def transform_data(data, token):
    """
    Convert OpenAlgo order request → Sharekhan place-order payload.
    `token` is the Sharekhan scripCode (instrument token).
    """
    customer_id = _get_customer_id()

    payload = {
        "transactionType": data["action"].upper(),
        "exchange": map_exchange(data["exchange"]),
        "productType": map_product_type(data["product"]),
        "orderType": map_order_type(data["pricetype"]),
        "tradingSymbol": data["symbol"],
        "scripCode": token,
        "quantity": int(data["quantity"]),
        "price": float(data.get("price", 0)),
        "requestType": "NEW",
    }

    if customer_id:
        payload["customerId"] = customer_id

    # Trigger price for stop-loss orders
    if data["pricetype"].upper() in ("SL", "SL-M"):
        trigger_price = float(data.get("trigger_price", 0))
        if trigger_price > 0:
            payload["triggerPrice"] = trigger_price
        else:
            raise ValueError("trigger_price required for SL/SL-M orders")

    # Validity
    validity = (data.get("validity") or "DAY").upper()
    payload["validity"] = "IOC" if validity == "IOC" else "DAY"

    # Disclosed quantity
    disclosed_qty = int(data.get("disclosed_quantity", 0))
    if disclosed_qty > 0:
        payload["disclosedQuantity"] = disclosed_qty

    return payload


def transform_modify_order_data(data, token=None):
    """Convert OpenAlgo modify-order request → Sharekhan modify payload."""
    customer_id = _get_customer_id()

    payload = {
        "orderId": data["orderid"],
        "transactionType": data.get("action", "BUY").upper(),
        "exchange": map_exchange(data["exchange"]),
        "productType": map_product_type(data["product"]),
        "orderType": map_order_type(data["pricetype"]),
        "tradingSymbol": data["symbol"],
        "quantity": int(data["quantity"]),
        "price": float(data.get("price", 0)),
        "requestType": "MODIFY",
    }

    if token:
        payload["scripCode"] = token
    if customer_id:
        payload["customerId"] = customer_id

    if data["pricetype"].upper() in ("SL", "SL-M"):
        payload["triggerPrice"] = float(data.get("trigger_price", 0))

    validity = (data.get("validity") or "DAY").upper()
    payload["validity"] = "IOC" if validity == "IOC" else "DAY"

    return payload


def _get_customer_id():
    try:
        from database.auth_db import get_user_id
        return get_user_id("sharekhan") or ""
    except Exception:
        return ""
