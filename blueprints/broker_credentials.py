# blueprints/broker_credentials.py
"""Broker credentials management API.

Broker app credentials now prefer the logged-in user's SaaS broker account,
while infrastructure settings still use the shared `.env` file.
"""

import os
import re

from flask import Blueprint, jsonify, request, session

from database.saas_db import get_profile_by_username, serialize_broker_account, upsert_broker_account
from utils.broker_context import resolve_broker_credentials
from utils.logging import get_logger
from utils.session import check_session_validity

logger = get_logger(__name__)

broker_credentials_bp = Blueprint("broker_credentials_bp", __name__, url_prefix="/api/broker")


def get_env_path():
    """Get the absolute path to the .env file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(base_dir, "..", ".env"))


def read_env_file():
    """Read and parse the .env file into a dictionary of lines."""
    env_path = get_env_path()
    if not os.path.exists(env_path):
        return None, "Environment file not found"

    try:
        # Use UTF-8 encoding for cross-platform compatibility
        with open(env_path, encoding="utf-8") as f:
            return f.read(), None
    except Exception as e:
        logger.exception(f"Error reading .env file: {e}")
        return None, str(e)


def update_env_value(content: str, key: str, value: str) -> str:
    """Update a specific key's value in the .env content.

    Uses single quotes for values. This is compatible with python-dotenv
    and most .env parsers across platforms.
    """
    # Pattern to match the key with various formats
    # Handles: KEY = 'value', KEY = "value", KEY = value, KEY='value', etc.
    pattern = rf"^({re.escape(key)}\s*=\s*).*$"

    # Always wrap in single quotes for consistency
    # Single quotes in .env files don't require escaping in most parsers
    # If value contains single quotes, use double quotes instead
    if "'" in value:
        # Use double quotes, escape any existing double quotes and backslashes
        escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
        new_value = f'"{escaped_value}"'
    else:
        # Use single quotes (no escaping needed)
        new_value = f"'{value}'"

    replacement = rf"\g<1>{new_value}"

    # Try to replace existing key
    new_content, count = re.subn(pattern, replacement, content, flags=re.MULTILINE)

    if count == 0:
        # Key doesn't exist, append it
        if not new_content.endswith("\n"):
            new_content += "\n"
        new_content += f"{key} = {new_value}\n"

    return new_content


def get_env_value(key: str) -> str:
    """Get a value from the .env file."""
    return os.getenv(key, "")


def mask_secret(value: str, show_chars: int = 4) -> str:
    """Mask a secret value, showing only the first few characters.

    Returns a FIXED-length output (``prefix + '*' * 8``) regardless of the
    original secret's length. This intentionally hides the secret's true
    length so an over-the-shoulder viewer (or a screenshot) cannot infer
    "this is a 64-char Zerodha API secret" vs "this is a 32-char Fyers
    secret" from the asterisk count.

    The fixed-length mask also keeps the rendered value bounded so a long
    secret (some brokers issue 80+ char tokens) cannot overflow the
    Profile UI's column layout — the bug originally reported in the
    Current Configuration card where the asterisks ran past the right
    edge of the card.

    For empty values, returns "" so the frontend can detect "not set" and
    show its placeholder copy.
    """
    if not value:
        return ""
    if len(value) <= show_chars:
        # Edge case: secret shorter than the prefix budget. Show only the
        # mask suffix to avoid revealing the entire short value.
        return "*" * 8
    return value[:show_chars] + "*" * 8


def get_broker_from_redirect_url(redirect_url: str) -> str:
    """Extract broker name from redirect URL."""
    try:
        match = re.search(r"/([^/]+)/callback$", redirect_url)
        if match:
            return match.group(1).lower()
    except Exception:
        pass
    return ""


def _server_settings_payload() -> dict:
    flask_host = get_env_value("FLASK_HOST_IP") or "127.0.0.1"
    flask_port = get_env_value("FLASK_PORT") or "5000"
    websocket_host = get_env_value("WEBSOCKET_HOST") or "127.0.0.1"
    websocket_port = get_env_value("WEBSOCKET_PORT") or "8765"
    zmq_host = get_env_value("ZMQ_HOST") or "127.0.0.1"
    zmq_port = get_env_value("ZMQ_PORT") or "5555"
    return {
        "ngrok_allow": get_env_value("NGROK_ALLOW").upper() == "TRUE",
        "host_server": get_env_value("HOST_SERVER"),
        "websocket_url": get_env_value("WEBSOCKET_URL"),
        "server_status": {
            "flask": {"host": flask_host, "port": flask_port},
            "websocket": {"host": websocket_host, "port": websocket_port},
            "zmq": {"host": zmq_host, "port": zmq_port},
        },
    }


@broker_credentials_bp.route("/credentials", methods=["GET"])
@check_session_validity
def get_credentials():
    """Get current broker credentials (masked)."""
    try:
        username = session.get("user")
        context = resolve_broker_credentials(username=username)
        redirect_url = context.redirect_url
        valid_brokers = get_env_value("VALID_BROKERS")

        # Parse valid brokers list
        brokers_list = [b.strip() for b in valid_brokers.split(",") if b.strip()]

        payload = {
            "broker_api_key": mask_secret(context.api_key, 6),
            "broker_api_key_raw_length": len(context.api_key),
            "broker_api_secret": mask_secret(context.api_secret, 4),
            "broker_api_secret_raw_length": len(context.api_secret),
            "broker_api_key_market": mask_secret(context.market_api_key, 6),
            "broker_api_key_market_raw_length": len(context.market_api_key),
            "broker_api_secret_market": mask_secret(context.market_api_secret, 4),
            "broker_api_secret_market_raw_length": len(context.market_api_secret),
            "redirect_url": redirect_url,
            "current_broker": context.broker or get_broker_from_redirect_url(redirect_url),
            "valid_brokers": brokers_list,
            "credential_source": context.source,
            "ip_route_key": context.ip_route_key,
        }
        payload.update(_server_settings_payload())

        return jsonify({"status": "success", "data": payload})
    except Exception as e:
        logger.exception(f"Error getting broker credentials: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@broker_credentials_bp.route("/credentials", methods=["POST"])
@check_session_validity
def update_credentials():
    """Update broker credentials.

    User broker app credentials go to the encrypted SaaS broker account store.
    Shared infra settings continue to live in `.env`.
    """
    try:
        # Support both JSON and form data
        if request.is_json:
            data = request.get_json() or {}
            broker_api_key = data.get("broker_api_key", "").strip()
            broker_api_secret = data.get("broker_api_secret", "").strip()
            broker_api_key_market = data.get("broker_api_key_market", "").strip()
            broker_api_secret_market = data.get("broker_api_secret_market", "").strip()
            redirect_url = data.get("redirect_url", "").strip()
            ip_route_key = data.get("ip_route_key", "").strip()
            ngrok_allow = data.get("ngrok_allow", "")
            host_server = data.get("host_server", "").strip()
            websocket_url = data.get("websocket_url", "").strip()
            has_ngrok_key = "ngrok_allow" in data
        else:
            # Form data
            broker_api_key = request.form.get("broker_api_key", "").strip()
            broker_api_secret = request.form.get("broker_api_secret", "").strip()
            broker_api_key_market = request.form.get("broker_api_key_market", "").strip()
            broker_api_secret_market = request.form.get("broker_api_secret_market", "").strip()
            redirect_url = request.form.get("redirect_url", "").strip()
            ip_route_key = request.form.get("ip_route_key", "").strip()
            ngrok_allow = request.form.get("ngrok_allow", "").strip()
            host_server = request.form.get("host_server", "").strip()
            websocket_url = request.form.get("websocket_url", "").strip()
            has_ngrok_key = "ngrok_allow" in request.form

        # Validate redirect URL format
        if redirect_url:
            if not re.match(r"^https?://.+/[^/]+/callback$", redirect_url):
                return jsonify(
                    {
                        "status": "error",
                        "message": "Invalid redirect URL format. Must end with /<broker>/callback",
                    }
                ), 400

            # Validate broker name
            broker_name = get_broker_from_redirect_url(redirect_url)
            valid_brokers_str = get_env_value("VALID_BROKERS")
            valid_brokers = set(
                b.strip().lower() for b in valid_brokers_str.split(",") if b.strip()
            )

            if broker_name and broker_name not in valid_brokers:
                return jsonify(
                    {
                        "status": "error",
                        "message": f"Invalid broker '{broker_name}'. Valid brokers: {', '.join(sorted(valid_brokers))}",
                    }
                ), 400

            # Validate broker-specific API key formats
            if broker_name == "fivepaisa" and broker_api_key:
                if ":::" not in broker_api_key or broker_api_key.count(":::") != 2:
                    return jsonify(
                        {
                            "status": "error",
                            "message": "5paisa API key must be in format: 'User_Key:::User_ID:::client_id'",
                        }
                    ), 400

            elif broker_name == "flattrade" and broker_api_key:
                if ":::" not in broker_api_key or broker_api_key.count(":::") != 1:
                    return jsonify(
                        {
                            "status": "error",
                            "message": "Flattrade API key must be in format: 'client_id:::api_key'",
                        }
                    ), 400

            elif broker_name == "dhan" and broker_api_key:
                if ":::" not in broker_api_key or broker_api_key.count(":::") != 1:
                    return jsonify(
                        {
                            "status": "error",
                            "message": "Dhan API key must be in format: 'client_id:::api_key'",
                        }
                    ), 400

        profile = get_profile_by_username(session.get("user"))
        updated_fields = []
        saved_account = None

        if profile and (
            broker_api_key
            or broker_api_secret
            or broker_api_key_market
            or broker_api_secret_market
            or redirect_url
            or ip_route_key
        ):
            broker_name = get_broker_from_redirect_url(redirect_url) if redirect_url else None
            if not broker_name:
                broker_name = resolve_broker_credentials(username=session.get("user")).broker
            if not broker_name:
                return jsonify(
                    {
                        "status": "error",
                        "message": "Select a broker before saving broker credentials.",
                    }
                ), 400

            saved_account = upsert_broker_account(
                profile,
                {
                    "broker": broker_name,
                    "label": "Primary",
                    "api_key": broker_api_key,
                    "api_secret": broker_api_secret,
                    "market_api_key": broker_api_key_market,
                    "market_api_secret": broker_api_secret_market,
                    "redirect_url": redirect_url,
                    "ip_route_key": ip_route_key,
                    "is_default": True,
                    "is_active": True,
                },
            )

            if broker_api_key:
                updated_fields.append("BROKER_API_KEY")
            if broker_api_secret:
                updated_fields.append("BROKER_API_SECRET")
            if broker_api_key_market:
                updated_fields.append("BROKER_API_KEY_MARKET")
            if broker_api_secret_market:
                updated_fields.append("BROKER_API_SECRET_MARKET")
            if redirect_url:
                updated_fields.append("REDIRECT_URL")
            if ip_route_key:
                updated_fields.append("IP_ROUTE_KEY")

        # Only touch .env for shared infrastructure settings.
        content = None
        if has_ngrok_key or host_server or websocket_url or (not profile and (
            broker_api_key
            or broker_api_secret
            or broker_api_key_market
            or broker_api_secret_market
            or redirect_url
        )):
            content, error = read_env_file()
            if error:
                return jsonify(
                    {"status": "error", "message": f"Failed to read .env file: {error}"}
                ), 500

        # Legacy fallback path: non-SaaS user credentials still write to .env.
        if content is not None and not profile and broker_api_key:
            content = update_env_value(content, "BROKER_API_KEY", broker_api_key)
            updated_fields.append("BROKER_API_KEY")

        if content is not None and not profile and broker_api_secret:
            content = update_env_value(content, "BROKER_API_SECRET", broker_api_secret)
            updated_fields.append("BROKER_API_SECRET")

        if content is not None and not profile and broker_api_key_market:
            content = update_env_value(content, "BROKER_API_KEY_MARKET", broker_api_key_market)
            updated_fields.append("BROKER_API_KEY_MARKET")

        if content is not None and not profile and broker_api_secret_market:
            content = update_env_value(
                content, "BROKER_API_SECRET_MARKET", broker_api_secret_market
            )
            updated_fields.append("BROKER_API_SECRET_MARKET")

        if content is not None and not profile and redirect_url:
            content = update_env_value(content, "REDIRECT_URL", redirect_url)
            updated_fields.append("REDIRECT_URL")

        # Check for ngrok_allow by key presence, not value truthiness
        # This allows setting it to FALSE (disabling ngrok)
        if content is not None and has_ngrok_key:
            ngrok_allow_str = str(ngrok_allow).strip().upper()
            ngrok_value = "TRUE" if ngrok_allow_str == "TRUE" else "FALSE"
            content = update_env_value(content, "NGROK_ALLOW", ngrok_value)
            updated_fields.append("NGROK_ALLOW")

        if content is not None and host_server:
            # Validate host_server URL format
            if not re.match(r"^https?://.+", host_server):
                return jsonify(
                    {
                        "status": "error",
                        "message": "Invalid HOST_SERVER format. Must start with http:// or https://",
                    }
                ), 400
            content = update_env_value(content, "HOST_SERVER", host_server)
            updated_fields.append("HOST_SERVER")

        if content is not None and websocket_url:
            # Validate websocket_url format
            if not re.match(r"^wss?://.+", websocket_url):
                return jsonify(
                    {
                        "status": "error",
                        "message": "Invalid WEBSOCKET_URL format. Must start with ws:// or wss://",
                    }
                ), 400
            content = update_env_value(content, "WEBSOCKET_URL", websocket_url)
            updated_fields.append("WEBSOCKET_URL")

        if not updated_fields:
            return jsonify({"status": "error", "message": "No credentials provided to update"}), 400

        restart_required = False
        if content is not None:
            env_path = get_env_path()
            try:
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write(content)
                restart_required = True
            except Exception as e:
                logger.exception(f"Error writing .env file: {e}")
                return jsonify(
                    {"status": "error", "message": f"Failed to write .env file: {e}"}
                ), 500

        logger.info(f"Updated broker credentials: {', '.join(updated_fields)}")

        return jsonify(
            {
                "status": "success",
                "message": f"Credentials updated successfully. Updated: {', '.join(updated_fields)}",
                "updated_fields": updated_fields,
                "restart_required": restart_required,
                "credential_source": "saas" if saved_account is not None else "env",
                "broker_account": serialize_broker_account(saved_account, include_lengths=True)
                if saved_account is not None
                else None,
            }
        )

    except Exception as e:
        logger.exception(f"Error updating broker credentials: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@broker_credentials_bp.route("/capabilities", methods=["GET"])
@check_session_validity
def get_capabilities():
    """Return broker capabilities (supported exchanges, type, features) from cached plugin.json."""
    from flask import session

    from utils.plugin_loader import get_broker_capabilities

    broker = session.get("broker")
    if not broker:
        return jsonify({"status": "error", "message": "No broker in session"}), 400

    capabilities = get_broker_capabilities(broker)
    if not capabilities:
        # Fallback for brokers without plugin.json capabilities
        return jsonify(
            {
                "status": "success",
                "data": {
                    "broker_name": broker,
                    "broker_type": "IN_stock",
                    "supported_exchanges": [],
                    "leverage_config": False,
                },
            }
        )

    return jsonify({"status": "success", "data": capabilities})
