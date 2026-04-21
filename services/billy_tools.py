"""
Billy AI Agent - Platform tool wrappers.
Exposes BTAlgo trading capabilities as AI-callable tools.
"""

import json
from datetime import datetime, timedelta

from utils.logging import get_logger

logger = get_logger(__name__)


def _get_api_key() -> str:
    """Get the user's BTAlgo API key for service calls."""
    try:
        from database.auth_db import get_api_key_for_tradingplatform
        return get_api_key_for_tradingplatform() or ""
    except Exception:
        return ""


def _call_service(service_fn, *args, **kwargs):
    """Call a BTAlgo service function safely."""
    try:
        result = service_fn(*args, **kwargs)
        return result if result is not None else {}
    except Exception as e:
        logger.exception(f"Billy tool error: {e}")
        return {"error": str(e)}


# ── Tool definitions (OpenAI/Anthropic tool schema format) ─────────────────────

BILLY_TOOLS = [
    {
        "name": "get_market_quote",
        "description": "Get real-time price quote for a stock, futures, or options symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol e.g. NIFTY, RELIANCE, INFY"},
                "exchange": {"type": "string", "description": "Exchange: NSE, BSE, NFO, MCX, CDS", "default": "NSE"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_option_chain",
        "description": "Get full option chain with LTP, IV, OI for an underlying symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Underlying symbol e.g. NIFTY, BANKNIFTY"},
                "expiry": {"type": "string", "description": "Expiry date in DDMMMYY format e.g. 25APR25. Leave blank for nearest expiry."},
                "strike_count": {"type": "integer", "description": "Number of strikes around ATM (default 10)", "default": 10},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_option_greeks",
        "description": "Calculate delta, gamma, theta, vega, rho and implied volatility for an option.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Option symbol e.g. NIFTY25APR2524000CE"},
                "exchange": {"type": "string", "description": "Exchange, usually NFO", "default": "NFO"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_historical_data",
        "description": "Get OHLCV (candlestick) historical data for a symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Symbol e.g. NIFTY, RELIANCE"},
                "exchange": {"type": "string", "description": "Exchange", "default": "NSE"},
                "interval": {"type": "string", "description": "Candle interval: 1m, 5m, 15m, 1h, D, W", "default": "D"},
                "from_date": {"type": "string", "description": "Start date YYYY-MM-DD"},
                "to_date": {"type": "string", "description": "End date YYYY-MM-DD"},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_trade_journal",
        "description": "Get the user's executed trade history (tradebook).",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_positions",
        "description": "Get all current open positions with unrealized P&L.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_account_summary",
        "description": "Get account funds, available cash, margin used, and total balance.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_orderbook",
        "description": "Get all pending and completed orders.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "search_symbol",
        "description": "Search for a trading instrument by name or symbol.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term e.g. 'Reliance' or 'BANKNIFTY'"},
                "exchange": {"type": "string", "description": "Optional exchange filter: NSE, BSE, NFO"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "place_order",
        "description": "Place a buy or sell order. Only use when user explicitly confirms they want to trade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "exchange": {"type": "string"},
                "action": {"type": "string", "enum": ["BUY", "SELL"]},
                "quantity": {"type": "integer"},
                "price_type": {"type": "string", "enum": ["MARKET", "LIMIT", "SL", "SL-M"], "default": "MARKET"},
                "price": {"type": "number", "description": "Required for LIMIT orders"},
                "product": {"type": "string", "enum": ["MIS", "NRML", "CNC"], "default": "MIS"},
                "strategy": {"type": "string", "description": "Strategy name tag", "default": "Billy"},
            },
            "required": ["symbol", "exchange", "action", "quantity"],
        },
    },
    {
        "name": "cancel_order",
        "description": "Cancel a specific pending order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID to cancel"},
                "strategy": {"type": "string", "default": "Billy"},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "create_flow_strategy",
        "description": "Create a new visual workflow strategy in the Flow Editor.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Strategy name"},
                "description": {"type": "string", "description": "What the strategy does"},
                "nodes": {"type": "array", "description": "Flow nodes array"},
                "edges": {"type": "array", "description": "Flow edges array"},
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "get_pnl_summary",
        "description": "Calculate profit and loss summary over a date range from trade history.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of past days to analyze (default 30)", "default": 30},
            },
        },
    },
    {
        "name": "toggle_analyzer_mode",
        "description": "Switch between live trading mode and sandbox/analyzer (paper trading) mode.",
        "input_schema": {
            "type": "object",
            "properties": {
                "enable": {"type": "boolean", "description": "true = enable sandbox, false = live mode"},
            },
            "required": ["enable"],
        },
    },
]


# ── Tool execution ─────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict, allow_orders: bool = False) -> str:
    """Execute a Billy tool and return result as JSON string."""
    try:
        if tool_name == "get_market_quote":
            return _get_market_quote(**tool_input)
        elif tool_name == "get_option_chain":
            return _get_option_chain(**tool_input)
        elif tool_name == "get_option_greeks":
            return _get_option_greeks(**tool_input)
        elif tool_name == "get_historical_data":
            return _get_historical_data(**tool_input)
        elif tool_name == "get_trade_journal":
            return _get_trade_journal()
        elif tool_name == "get_positions":
            return _get_positions()
        elif tool_name == "get_account_summary":
            return _get_account_summary()
        elif tool_name == "get_orderbook":
            return _get_orderbook()
        elif tool_name == "search_symbol":
            return _search_symbol(**tool_input)
        elif tool_name == "place_order":
            if not allow_orders:
                return json.dumps({"error": "Order placement is disabled. Enable it in Billy Settings."})
            return _place_order(**tool_input)
        elif tool_name == "cancel_order":
            if not allow_orders:
                return json.dumps({"error": "Order operations are disabled. Enable in Billy Settings."})
            return _cancel_order(**tool_input)
        elif tool_name == "create_flow_strategy":
            return _create_flow_strategy(**tool_input)
        elif tool_name == "get_pnl_summary":
            return _get_pnl_summary(**tool_input)
        elif tool_name == "toggle_analyzer_mode":
            return _toggle_analyzer_mode(**tool_input)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    except Exception as e:
        logger.exception(f"Tool {tool_name} failed: {e}")
        return json.dumps({"error": str(e)})


def _get_market_quote(symbol: str, exchange: str = "NSE") -> str:
    from services.quotes_service import get_quotes
    result = _call_service(get_quotes, symbol.upper(), exchange.upper())
    return json.dumps(result)


def _get_option_chain(symbol: str, expiry: str = None, strike_count: int = 10) -> str:
    from services.option_chain_service import get_option_chain
    result = _call_service(get_option_chain, symbol.upper(), "NFO", expiry, strike_count)
    return json.dumps(result)


def _get_option_greeks(symbol: str, exchange: str = "NFO") -> str:
    from services.option_greeks_service import get_option_greeks
    result = _call_service(get_option_greeks, symbol.upper(), exchange.upper())
    return json.dumps(result)


def _get_historical_data(symbol: str, exchange: str = "NSE", interval: str = "D",
                         from_date: str = None, to_date: str = None) -> str:
    from services.history_service import get_history
    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")
    if not from_date:
        from_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    result = _call_service(get_history, symbol.upper(), exchange.upper(), interval, from_date, to_date)
    return json.dumps(result)


def _get_trade_journal() -> str:
    from services.tradebook_service import get_tradebook
    result = _call_service(get_tradebook)
    return json.dumps(result)


def _get_positions() -> str:
    from services.positionbook_service import get_positionbook
    result = _call_service(get_positionbook)
    return json.dumps(result)


def _get_account_summary() -> str:
    from services.funds_service import get_funds
    result = _call_service(get_funds)
    return json.dumps(result)


def _get_orderbook() -> str:
    from services.orderbook_service import get_orderbook
    result = _call_service(get_orderbook)
    return json.dumps(result)


def _search_symbol(query: str, exchange: str = None) -> str:
    from services.search_service import search_symbols
    result = _call_service(search_symbols, query, exchange)
    return json.dumps(result)


def _place_order(symbol: str, exchange: str, action: str, quantity: int,
                 price_type: str = "MARKET", price: float = 0,
                 product: str = "MIS", strategy: str = "Billy") -> str:
    from services.place_order_service import place_order_service
    order_data = {
        "symbol": symbol.upper(),
        "exchange": exchange.upper(),
        "action": action.upper(),
        "quantity": str(quantity),
        "pricetype": price_type.upper(),
        "price": str(price),
        "product": product.upper(),
        "strategy": strategy,
        "disclosed_quantity": "0",
        "trigger_price": "0",
    }
    result = _call_service(place_order_service, order_data)
    return json.dumps(result)


def _cancel_order(order_id: str, strategy: str = "Billy") -> str:
    from services.cancel_order_service import cancel_order_service
    result = _call_service(cancel_order_service, order_id, strategy)
    return json.dumps(result)


def _create_flow_strategy(name: str, description: str, nodes: list = None, edges: list = None) -> str:
    from database.flow_db import create_workflow
    wf = _call_service(create_workflow, name=name, description=description,
                       nodes=nodes or [], edges=edges or [])
    if wf and hasattr(wf, "id"):
        return json.dumps({
            "status": "success",
            "workflow_id": wf.id,
            "name": wf.name,
            "url": f"/flow/editor/{wf.id}",
            "message": f"Strategy '{name}' created. Open it in the Flow Editor to review and activate."
        })
    return json.dumps({"status": "success", "message": f"Strategy '{name}' created."})


def _get_pnl_summary(days: int = 30) -> str:
    from services.tradebook_service import get_tradebook
    trades = _call_service(get_tradebook)
    if isinstance(trades, dict) and "data" in trades:
        trade_list = trades["data"]
    elif isinstance(trades, list):
        trade_list = trades
    else:
        return json.dumps({"error": "Could not fetch trade data"})

    total_pnl = 0
    wins = 0
    losses = 0
    for t in trade_list:
        pnl = float(t.get("pnl", 0) or 0)
        total_pnl += pnl
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1

    total = wins + losses
    win_rate = round((wins / total * 100), 1) if total > 0 else 0
    return json.dumps({
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": win_rate,
        "total_pnl": round(total_pnl, 2),
        "period_days": days,
    })


def _toggle_analyzer_mode(enable: bool) -> str:
    from services.analyzer_service import toggle_analyzer_mode
    result = _call_service(toggle_analyzer_mode, enable)
    return json.dumps(result)
