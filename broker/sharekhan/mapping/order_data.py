from broker.sharekhan.mapping.transform_data import (
    reverse_map_exchange,
    reverse_map_order_type,
    reverse_map_product_type,
)
from database.token_db import get_oa_symbol
from utils.logging import get_logger

logger = get_logger(__name__)


def map_order_data(order):
    """Map a single Sharekhan order record to OpenAlgo standard format."""
    try:
        br_exchange = order.get("exchange") or order.get("Exchange") or ""
        exchange = reverse_map_exchange(br_exchange)

        br_symbol = order.get("tradingSymbol") or order.get("symbol") or ""
        token = str(order.get("scripCode") or order.get("token") or "")
        symbol = get_oa_symbol(token, exchange) or br_symbol

        return {
            "symbol": symbol,
            "exchange": exchange,
            "action": (order.get("transactionType") or order.get("buyOrSell") or "").upper(),
            "quantity": int(order.get("quantity") or order.get("qty") or 0),
            "price": float(order.get("price") or 0),
            "trigger_price": float(order.get("triggerPrice") or order.get("trigger_price") or 0),
            "pricetype": reverse_map_order_type(
                order.get("orderType") or order.get("order_type") or "MARKET"
            ),
            "product": reverse_map_product_type(
                order.get("productType") or order.get("product_type") or "MIS"
            ),
            "orderid": str(order.get("orderId") or order.get("order_id") or ""),
            "status": (order.get("orderStatus") or order.get("status") or "").upper(),
            "timestamp": order.get("orderTime") or order.get("time") or "",
            "remarks": order.get("remarks") or order.get("message") or "",
        }
    except Exception as e:
        logger.exception(f"Sharekhan map_order_data error: {e}")
        return {}


def map_order_data_for_tradebook(trade):
    """Map a Sharekhan trade record to OpenAlgo tradebook format."""
    try:
        br_exchange = trade.get("exchange") or ""
        exchange = reverse_map_exchange(br_exchange)
        token = str(trade.get("scripCode") or trade.get("token") or "")
        br_symbol = trade.get("tradingSymbol") or trade.get("symbol") or ""
        symbol = get_oa_symbol(token, exchange) or br_symbol

        return {
            "symbol": symbol,
            "exchange": exchange,
            "action": (trade.get("transactionType") or "").upper(),
            "quantity": int(trade.get("tradedQuantity") or trade.get("quantity") or 0),
            "price": float(trade.get("tradedPrice") or trade.get("price") or 0),
            "pricetype": reverse_map_order_type(trade.get("orderType") or "LIMIT"),
            "product": reverse_map_product_type(trade.get("productType") or "MIS"),
            "orderid": str(trade.get("orderId") or ""),
            "tradeid": str(trade.get("tradeId") or trade.get("trade_id") or ""),
            "timestamp": trade.get("tradeTime") or trade.get("time") or "",
        }
    except Exception as e:
        logger.exception(f"Sharekhan map_order_data_for_tradebook error: {e}")
        return {}


def map_position_data(position):
    """Map a Sharekhan position record to OpenAlgo position format."""
    try:
        br_exchange = position.get("exchange") or ""
        exchange = reverse_map_exchange(br_exchange)
        token = str(position.get("scripCode") or position.get("token") or "")
        br_symbol = position.get("tradingSymbol") or position.get("symbol") or ""
        symbol = get_oa_symbol(token, exchange) or br_symbol

        net_qty = int(position.get("netQty") or position.get("quantity") or 0)
        avg_price = float(position.get("netAvgPrice") or position.get("avgPrice") or 0)
        ltp = float(position.get("ltp") or position.get("lastTradedPrice") or 0)
        unrealized = float(position.get("unrealizedProfit") or position.get("mtm") or 0)
        realized = float(position.get("realizedProfit") or position.get("realizedPnL") or 0)

        return {
            "symbol": symbol,
            "exchange": exchange,
            "product": reverse_map_product_type(position.get("productType") or "MIS"),
            "quantity": net_qty,
            "average_price": avg_price,
            "last_price": ltp,
            "pnl": unrealized,
            "realized_pnl": realized,
            "unrealized_pnl": unrealized,
        }
    except Exception as e:
        logger.exception(f"Sharekhan map_position_data error: {e}")
        return {}
