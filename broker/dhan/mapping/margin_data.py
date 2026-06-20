# Mapping BTAlgo API Request https://billionairestechnologies.com/docs
# Mapping Dhan Margin API https://dhanhq.co/docs/v2/funds/

from broker.dhan.mapping.transform_data import map_exchange_type
from database.token_db import get_token
from utils.logging import get_logger

logger = get_logger(__name__)


def transform_margin_position(position, client_id):
    """
    Transform a single BTAlgo margin position to Dhan margin format.

    Args:
        position: Position in BTAlgo format
        client_id: Dhan client ID

    Returns:
        Dict in Dhan margin format or None if transformation fails
    """
    try:
        token = get_token(position["symbol"], position["exchange"])

        if not token:
            logger.warning(
                f"Token not found for symbol: {position['symbol']} on exchange: {position['exchange']}"
            )
            return None

        exchange_segment = map_exchange_type(position["exchange"])
        if not exchange_segment:
            logger.warning(f"Invalid exchange: {position['exchange']}")
            return None

        transformed = {
            "dhanClientId": client_id,
            "exchangeSegment": exchange_segment,
            "transactionType": position["action"].upper(),
            "quantity": int(position["quantity"]),
            "productType": map_product_type_for_margin(position["product"]),
            "securityId": str(token),
            "price": float(position.get("price", 0)),
        }

        trigger_price = position.get("trigger_price", 0)
        if trigger_price and float(trigger_price) > 0:
            transformed["triggerPrice"] = float(trigger_price)

        return transformed

    except Exception as e:
        logger.error(f"Error transforming position: {position}, Error: {e}")
        return None


def map_product_type_for_margin(product):
    """
    Maps BTAlgo product type to Dhan product type for margin calculation.

    BTAlgo: CNC, NRML, MIS
    Dhan: CNC, MARGIN, INTRADAY, MTF, CO, BO
    """
    product_type_mapping = {
        "CNC": "CNC",
        "NRML": "MARGIN",
        "MIS": "INTRADAY",
    }
    return product_type_mapping.get(product, "INTRADAY")


def parse_margin_response(response_data):
    """
    Parse Dhan margin response to BTAlgo standard format.

    According to Dhan API docs, response includes:
    - totalMargin: Total margin required for placing the order
    - spanMargin: SPAN margin required
    - exposureMargin: Exposure margin required
    - availableBalance: Available amount in trading account
    - variableMargin: VAR or variable margin required
    - insufficientBalance: Insufficient amount in account
    - brokerage: Brokerage charges
    - leverage: Margin leverage based on product type

    Args:
        response_data: Raw response from Dhan API

    Returns:
        Standardized margin response matching BTAlgo format
    """
    try:
        if not response_data or not isinstance(response_data, dict):
            return {"status": "error", "message": "Invalid response from broker"}

        status = str(response_data.get("status", "")).lower()
        if response_data.get("errorType") or status in {"error", "failed", "failure"}:
            error_message = (
                response_data.get("errorMessage")
                or response_data.get("message")
                or response_data.get("errors")
                or "Failed to calculate margin"
            )
            return {"status": "error", "message": str(error_message)}

        total_margin = float(response_data.get("totalMargin", 0))
        span_margin = float(response_data.get("spanMargin", 0))
        exposure_margin = float(response_data.get("exposureMargin", 0))

        return {
            "status": "success",
            "data": {
                "total_margin_required": total_margin,
                "span_margin": span_margin,
                "exposure_margin": exposure_margin,
            },
        }

    except Exception as e:
        logger.error(f"Error parsing margin response: {e}")
        return {"status": "error", "message": f"Failed to parse margin response: {str(e)}"}


def parse_batch_margin_response(responses):
    """
    Parse multiple Dhan margin responses and aggregate them by simple summation.

    IMPORTANT - Limitation:
    Since Dhan API only supports single-leg margin calculation, we calculate
    each leg individually and SUM the results. This approach:

    ✓ Works correctly for independent positions
    ✗ Does NOT account for spread/hedge benefits in combo strategies
    ✗ Does NOT provide portfolio-level margin optimization

    Example:
    - Short Straddle (CE + PE): Sum of individual margins (no hedge benefit)
    - Iron Condor: Sum of 4 individual leg margins (no spread benefit)

    This is a limitation of the Dhan API, not BTAlgo.

    Args:
        responses: List of individual margin responses (one per leg)

    Returns:
        Aggregated margin response matching BTAlgo format
    """
    try:
        total_margin = 0
        total_span = 0
        total_exposure = 0
        successful_legs = 0

        logger.debug("AGGREGATING INDIVIDUAL LEG MARGINS")
        logger.debug("-" * 80)

        for idx, response in enumerate(responses, 1):
            if response.get("status") == "success":
                data = response.get("data", {})
                leg_margin = data.get("total_margin_required", 0)
                leg_span = data.get("span_margin", 0)
                leg_exposure = data.get("exposure_margin", 0)

                total_margin += leg_margin
                total_span += leg_span
                total_exposure += leg_exposure
                successful_legs += 1

                logger.debug(
                    f"Leg {idx}: Total={leg_margin:,.2f}, SPAN={leg_span:,.2f}, Exposure={leg_exposure:,.2f}"
                )

        logger.debug(f"Successfully aggregated {successful_legs} legs")
        logger.debug(f"Total Margin (Sum):      Rs. {total_margin:,.2f}")
        logger.debug(f"Total SPAN (Sum):        Rs. {total_span:,.2f}")
        logger.debug(f"Total Exposure (Sum):    Rs. {total_exposure:,.2f}")
        logger.debug("-" * 80)

        return {
            "status": "success",
            "data": {
                "total_margin_required": total_margin,
                "span_margin": total_span,
                "exposure_margin": total_exposure,
            },
        }

    except Exception as e:
        logger.error(f"Error parsing batch margin response: {e}")
        return {"status": "error", "message": f"Failed to parse batch margin response: {str(e)}"}
