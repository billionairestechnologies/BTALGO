from utils.logging import get_logger

logger = get_logger(__name__)


def map_margin_data(data):
    """Map Sharekhan fund/limit response to OpenAlgo standard margin format."""
    try:
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
            "m2munrealized": _f(record.get("unrealizedMTM") or record.get("mtmUnrealized") or 0),
            "m2mrealized": _f(record.get("realizedMTM") or record.get("mtmRealized") or 0),
            "utiliseddebits": _f(
                record.get("utilisedAmount") or record.get("usedMargin") or record.get("debit") or 0
            ),
        }
    except Exception as e:
        logger.exception(f"Sharekhan map_margin_data error: {e}")
        return {
            "availablecash": "0.00",
            "collateral": "0.00",
            "m2munrealized": "0.00",
            "m2mrealized": "0.00",
            "utiliseddebits": "0.00",
        }
