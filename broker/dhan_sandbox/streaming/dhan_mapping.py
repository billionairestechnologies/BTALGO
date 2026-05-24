"""
Mapping utilities for Dhan broker integration.
Provides exchange code mappings between BTAlgo and Dhan formats.
"""

from typing import Dict

# Exchange code mappings
# BTAlgo exchange code -> Dhan exchange code
BTALGO_TO_DHAN_EXCHANGE = {
    "NSE": "NSE_EQ",
    "BSE": "BSE_EQ",
    "NFO": "NSE_FNO",
    "BFO": "BSE_FNO",
    "CDS": "NSE_CURRENCY",
    "BCD": "BSE_CURRENCY",
    "MCX": "MCX_COMM",
    "NSE_INDEX": "IDX_I",
    "BSE_INDEX": "IDX_I",
}

# Dhan exchange code -> BTAlgo exchange code
DHAN_TO_BTALGO_EXCHANGE = {v: k for k, v in BTALGO_TO_DHAN_EXCHANGE.items()}


def get_dhan_exchange(btalgo_exchange: str) -> str:
    """
    Convert BTAlgo exchange code to Dhan exchange code.

    Args:
        btalgo_exchange (str): Exchange code in BTAlgo format

    Returns:
        str: Exchange code in Dhan format
    """
    return BTALGO_TO_DHAN_EXCHANGE.get(btalgo_exchange, btalgo_exchange)


def get_btalgo_exchange(dhan_exchange: str) -> str:
    """
    Convert Dhan exchange code to BTAlgo exchange code.

    Args:
        dhan_exchange (str): Exchange code in Dhan format

    Returns:
        str: Exchange code in BTAlgo format
    """
    return DHAN_TO_BTALGO_EXCHANGE.get(dhan_exchange, dhan_exchange)
