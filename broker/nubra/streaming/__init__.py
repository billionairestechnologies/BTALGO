"""
Nubra WebSocket streaming module for BTAlgo.

This module provides WebSocket integration with Nubra's market data streaming API,
following the BTAlgo WebSocket proxy architecture.
"""

from .nubra_adapter import NubraWebSocketAdapter

__all__ = ["NubraWebSocketAdapter"]
