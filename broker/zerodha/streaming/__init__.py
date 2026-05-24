"""
Zerodha WebSocket streaming module for BTAlgo.

This module provides WebSocket integration with Zerodha's market data streaming API,
following the BTAlgo WebSocket proxy architecture.
"""

from .zerodha_adapter import ZerodhaWebSocketAdapter

__all__ = ["ZerodhaWebSocketAdapter"]
