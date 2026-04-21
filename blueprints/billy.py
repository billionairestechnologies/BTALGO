"""
Billy AI Agent - Flask Blueprint.
Provides chat, history, and settings endpoints.
"""

import json

from flask import Blueprint, Response, request, session, stream_with_context

from database.billy_db import (
    clear_history,
    get_history,
    get_settings,
    save_message,
    save_settings,
)
from services.billy_service import check_provider_status, stream_chat
from utils.logging import get_logger

logger = get_logger(__name__)

billy_bp = Blueprint("billy", __name__)


def _require_login():
    if not session.get("user"):
        return {"status": "error", "message": "Not authenticated"}, 401
    return None


# ── Chat ───────────────────────────────────────────────────────────────────────

@billy_bp.route("/api/billy/chat", methods=["POST"])
def billy_chat():
    err = _require_login()
    if err:
        return err

    data = request.get_json(force=True)
    user_message = data.get("message", "").strip()
    context = data.get("context", {})

    if not user_message:
        return {"status": "error", "message": "Empty message"}, 400

    # Save user message to DB
    save_message("user", user_message)

    # Build message history for the AI
    history = get_history(limit=20)
    messages = [
        {"role": h["role"], "content": h["content"]}
        for h in history
        if h["role"] in ("user", "assistant")
    ]

    settings = get_settings()

    def generate():
        full_response = ""
        tool_info = []

        try:
            for chunk in stream_chat(messages, settings, context):
                yield chunk
                # Parse SSE to capture final response for saving
                if chunk.startswith("event: text"):
                    try:
                        data_line = [l for l in chunk.split("\n") if l.startswith("data:")]
                        if data_line:
                            payload = json.loads(data_line[0][5:])
                            full_response += payload.get("chunk", "")
                    except Exception:
                        pass
                elif chunk.startswith("event: tool_start"):
                    try:
                        data_line = [l for l in chunk.split("\n") if l.startswith("data:")]
                        if data_line:
                            payload = json.loads(data_line[0][5:])
                            tool_info.append(payload.get("name", ""))
                    except Exception:
                        pass
        finally:
            if full_response:
                save_message("assistant", full_response,
                             tool_calls=tool_info if tool_info else None)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── History ────────────────────────────────────────────────────────────────────

@billy_bp.route("/api/billy/history", methods=["GET"])
def billy_history():
    err = _require_login()
    if err:
        return err
    return {"status": "success", "data": get_history(limit=50)}


@billy_bp.route("/api/billy/history", methods=["DELETE"])
def billy_clear_history():
    err = _require_login()
    if err:
        return err
    clear_history()
    return {"status": "success", "message": "Conversation cleared"}


# ── Settings ───────────────────────────────────────────────────────────────────

@billy_bp.route("/api/billy/settings", methods=["GET"])
def billy_get_settings():
    err = _require_login()
    if err:
        return err
    s = get_settings()
    # Mask API key — only show last 4 chars
    if s.get("api_key") and len(s["api_key"]) > 4:
        s["api_key_masked"] = "••••" + s["api_key"][-4:]
    else:
        s["api_key_masked"] = ""
    return {"status": "success", "data": s}


@billy_bp.route("/api/billy/settings", methods=["POST"])
def billy_save_settings():
    err = _require_login()
    if err:
        return err

    data = request.get_json(force=True)
    save_settings(
        provider=data.get("provider", "anthropic"),
        model=data.get("model", ""),
        api_key=data.get("api_key", ""),
        base_url=data.get("base_url", ""),
        allow_orders=data.get("allow_orders", False),
        allow_strategies=data.get("allow_strategies", True),
    )
    return {"status": "success", "message": "Settings saved"}


@billy_bp.route("/api/billy/status", methods=["GET"])
def billy_status():
    err = _require_login()
    if err:
        return err
    settings = get_settings()
    result = check_provider_status(settings)
    return {"status": "success", "data": result}
