import json
import os
from datetime import datetime, timedelta

from broker.sharekhan.api.baseurl import get_url
from broker.sharekhan.database.master_contract_db import (
    SymToken,
    get_db_path,
    master_contract_exists,
)
from database.token_db import get_br_symbol, get_token
from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)

# Exchanges to download for master contract
MASTER_EXCHANGES = ["NSE", "BSE", "NFO", "BFO", "CDS", "MCX"]


def _get_headers(auth_token):
    api_key = os.getenv("BROKER_API_KEY", "")
    return {
        "api-key": api_key,
        "access-token": auth_token,
        "Authorization": auth_token,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ── Quotes ─────────────────────────────────────────────────────────────────────

def get_quotes(auth_token, symbol, exchange):
    """Fetch real-time quote for a symbol."""
    try:
        token = get_token(symbol, exchange)
        if not token:
            logger.error(f"Sharekhan: token not found for {symbol}/{exchange}")
            return {}

        br_symbol = get_br_symbol(symbol, exchange) or symbol
        client = get_httpx_client()
        headers = _get_headers(auth_token)

        # Sharekhan doesn't have a dedicated quotes endpoint in the documented API.
        # We use the script master approach combined with real-time data via WebSocket.
        # As a fallback, return empty dict — the UI will handle gracefully.
        logger.warning("Sharekhan REST quotes not available; use WebSocket for real-time data")
        return {}

    except Exception as e:
        logger.exception(f"Sharekhan get_quotes error: {e}")
        return {}


# ── Historical Data ─────────────────────────────────────────────────────────────

def get_historical_data(auth_token, symbol, exchange, interval, start_date=None, end_date=None):
    """
    Fetch OHLCV historical data.
    interval: '1' (1 min), '5', '15', '30', '60', 'D' (daily)
    """
    try:
        token = get_token(symbol, exchange)
        if not token:
            return []

        # Map OpenAlgo interval to Sharekhan interval string
        interval_map = {
            "1m": "1", "5m": "5", "15m": "15", "30m": "30",
            "1h": "60", "60m": "60", "1d": "D", "D": "D",
        }
        sk_interval = interval_map.get(str(interval), interval)

        client = get_httpx_client()
        headers = _get_headers(auth_token)

        # Sharekhan exchange codes for historical data
        exch_map = {"NSE": "NSE", "BSE": "BSE", "NFO": "NSE", "BFO": "BSE", "MCX": "MCX", "CDS": "NSE"}
        sk_exchange = exch_map.get(exchange.upper(), exchange)

        url = get_url(f"/skapi/services/historical/{sk_exchange}/{token}/{sk_interval}")

        params = {}
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date

        response = client.get(url, headers=headers, params=params)
        data = response.json()
        logger.debug(f"Sharekhan historical data ({symbol}): {len(data) if isinstance(data, list) else data}")

        if isinstance(data, list):
            result = []
            for candle in data:
                result.append({
                    "datetime": candle.get("datetime") or candle.get("date") or candle.get("time"),
                    "open": float(candle.get("open", 0)),
                    "high": float(candle.get("high", 0)),
                    "low": float(candle.get("low", 0)),
                    "close": float(candle.get("close", 0)),
                    "volume": int(candle.get("volume", 0)),
                })
            return result
        return []

    except Exception as e:
        logger.exception(f"Sharekhan get_historical_data error: {e}")
        return []


# ── Master Contract Download ────────────────────────────────────────────────────

def get_master_contract(exchange, auth_token):
    """Download and return raw instrument list for an exchange."""
    try:
        client = get_httpx_client()
        headers = _get_headers(auth_token)
        url = get_url(f"/skapi/services/master/{exchange}")
        response = client.get(url, headers=headers, timeout=30.0)

        if response.status_code != 200:
            logger.error(f"Sharekhan master contract {exchange}: HTTP {response.status_code}")
            return None

        # Response may be JSON list or CSV text
        content_type = response.headers.get("content-type", "")
        if "json" in content_type:
            return response.json()
        else:
            # Parse CSV
            return _parse_csv_master(response.text, exchange)

    except Exception as e:
        logger.exception(f"Sharekhan get_master_contract error ({exchange}): {e}")
        return None


def _parse_csv_master(text, exchange):
    """Parse Sharekhan CSV master contract into list of dicts."""
    lines = text.strip().split("\n")
    if not lines:
        return []

    headers_row = [h.strip().strip('"') for h in lines[0].split(",")]
    instruments = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = [p.strip().strip('"') for p in line.split(",")]
        record = dict(zip(headers_row, parts))
        record["_exchange"] = exchange
        instruments.append(record)
    return instruments


def master_download(auth_token):
    """Download master contract for all exchanges and populate SymToken DB."""
    from broker.sharekhan.database.master_contract_db import (
        init_db, delete_symtoken_table, bulk_insert_symtokens,
    )

    init_db()
    delete_symtoken_table()

    total = 0
    for exchange in MASTER_EXCHANGES:
        try:
            instruments = get_master_contract(exchange, auth_token)
            if not instruments:
                logger.warning(f"Sharekhan: no instruments for {exchange}")
                continue

            tokens = _map_instruments(instruments, exchange)
            bulk_insert_symtokens(tokens)
            total += len(tokens)
            logger.info(f"Sharekhan master contract: {len(tokens)} symbols for {exchange}")
        except Exception as e:
            logger.exception(f"Sharekhan master_download error ({exchange}): {e}")

    logger.info(f"Sharekhan master contract download complete: {total} total symbols")
    return True


def _map_instruments(instruments, exchange):
    """Map raw Sharekhan instrument records to SymToken format."""
    result = []
    for inst in instruments:
        if not isinstance(inst, dict):
            continue
        try:
            # Sharekhan field names may vary — we try common variants
            symbol = (
                inst.get("Symbol") or inst.get("symbol") or
                inst.get("TradingSymbol") or inst.get("tradingSymbol") or ""
            )
            token = str(
                inst.get("ScripCode") or inst.get("scripCode") or
                inst.get("Token") or inst.get("token") or ""
            )
            name = inst.get("Name") or inst.get("name") or symbol
            expiry = inst.get("Expiry") or inst.get("expiry") or ""
            strike = inst.get("Strike") or inst.get("strike") or 0
            lot_size = inst.get("LotSize") or inst.get("lotSize") or inst.get("lot_size") or 1
            tick_size = inst.get("TickSize") or inst.get("tickSize") or inst.get("tick_size") or 0.05
            inst_type = inst.get("InstrumentType") or inst.get("instrumentType") or "EQ"

            if not symbol or not token:
                continue

            # Map Sharekhan exchange to OpenAlgo standard
            oa_exchange = _map_exchange_to_oa(
                inst.get("Exchange") or inst.get("exchange") or exchange, inst_type
            )

            result.append({
                "symbol": symbol,
                "brsymbol": symbol,
                "name": name,
                "exchange": oa_exchange,
                "brexchange": exchange,
                "token": token,
                "expiry": expiry,
                "strike": float(strike) if strike else 0.0,
                "lotsize": int(lot_size) if lot_size else 1,
                "instrumenttype": inst_type,
                "tick_size": float(tick_size) if tick_size else 0.05,
            })
        except Exception:
            continue
    return result


def _map_exchange_to_oa(br_exchange, inst_type="EQ"):
    """Map Sharekhan exchange + instrument type to OpenAlgo standard exchange codes."""
    br = (br_exchange or "").upper()
    itype = (inst_type or "").upper()

    if br in ("NSE",):
        if itype in ("FUT", "OPT", "FUTIDX", "OPTIDX", "FUTSTK", "OPTSTK"):
            return "NFO"
        if itype in ("CUR", "FUTCUR", "OPTCUR"):
            return "CDS"
        if "INDEX" in itype or itype == "INDEX":
            return "NSE_INDEX"
        return "NSE"

    if br in ("BSE",):
        if itype in ("FUT", "OPT", "FUTIDX", "OPTIDX", "FUTSTK", "OPTSTK"):
            return "BFO"
        if "INDEX" in itype or itype == "INDEX":
            return "BSE_INDEX"
        return "BSE"

    if br in ("MCX",):
        return "MCX"
    if br in ("CDS",):
        return "CDS"

    return br
