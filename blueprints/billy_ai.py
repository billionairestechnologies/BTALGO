# blueprints/billy_ai.py

from flask import Blueprint, Response, jsonify, request, session, stream_with_context

from database.auth_db import get_api_key_for_tradingview
from database.billy_ai_db import (
    add_message,
    create_conversation,
    delete_conversation,
    get_conversation_messages,
    get_conversations,
    update_conversation_title,
)
from services.billy_ai_service import (
    generate_title,
    get_available_providers,
    get_trading_context,
    stream_chat,
)
from utils.logging import get_logger
from utils.session import check_session_validity

billy_ai_bp = Blueprint("billy_ai", __name__, url_prefix="/billy-ai")
logger = get_logger(__name__)


@billy_ai_bp.route("/providers", methods=["GET"])
@check_session_validity
def providers():
    """Get available AI providers and models"""
    return jsonify({"status": "success", "data": get_available_providers()})


@billy_ai_bp.route("/conversations", methods=["GET"])
@check_session_validity
def list_conversations():
    """List all conversations"""
    convs = get_conversations()
    return jsonify({"status": "success", "data": convs})


@billy_ai_bp.route("/conversations", methods=["POST"])
@check_session_validity
def new_conversation():
    """Create a new conversation"""
    data = request.get_json() or {}
    provider = data.get("provider", "nexos")
    model = data.get("model", "")
    conv_id = create_conversation(title="New Chat", provider=provider, model=model)
    return jsonify({"status": "success", "data": {"id": conv_id}})


@billy_ai_bp.route("/conversations/<int:conv_id>", methods=["GET"])
@check_session_validity
def get_conversation(conv_id):
    """Get messages for a conversation"""
    messages = get_conversation_messages(conv_id)
    return jsonify({"status": "success", "data": messages})


@billy_ai_bp.route("/conversations/<int:conv_id>", methods=["DELETE"])
@check_session_validity
def remove_conversation(conv_id):
    """Delete a conversation"""
    delete_conversation(conv_id)
    return jsonify({"status": "success", "message": "Conversation deleted"})


@billy_ai_bp.route("/conversations/<int:conv_id>/title", methods=["PUT"])
@check_session_validity
def rename_conversation(conv_id):
    """Update conversation title"""
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    if not title:
        return jsonify({"status": "error", "message": "Title is required"}), 400
    update_conversation_title(conv_id, title[:500])
    return jsonify({"status": "success", "message": "Title updated"})


@billy_ai_bp.route("/chat", methods=["POST"])
@check_session_validity
def chat():
    """Stream a chat completion response via SSE"""
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Request body required"}), 400

    message = data.get("message", "").strip()
    conversation_id = data.get("conversation_id")
    provider = data.get("provider", "nexos")
    model = data.get("model", "")

    if not message:
        return jsonify({"status": "error", "message": "Message is required"}), 400

    # Create conversation if needed
    if not conversation_id:
        title = generate_title(message)
        conversation_id = create_conversation(title=title, provider=provider, model=model)

    # Save user message
    add_message(conversation_id, "user", message)

    # Get conversation history for context
    history = get_conversation_messages(conversation_id)
    messages = [{"role": m["role"], "content": m["content"]} for m in history]

    # Fetch live trading context from broker
    username = session.get("user")
    user_api_key = get_api_key_for_tradingview(username) if username else None
    trading_context = get_trading_context(user_api_key)

    # Collect full response for saving
    full_response = []

    def generate():
        for chunk in stream_chat(messages, provider_id=provider, model_id=model, trading_context=trading_context, user_api_key=user_api_key):
            yield f"data: {chunk}\n\n"
            # Extract content for saving
            import json
            try:
                parsed = json.loads(chunk)
                if parsed.get("content"):
                    full_response.append(parsed["content"])
            except:
                pass
        
        # Save assistant message
        if full_response:
            full_text = "".join(full_response)
            add_message(conversation_id, "assistant", full_text, provider=provider, model=model)

    response = Response(stream_with_context(generate()), mimetype="text/event-stream")
    response.headers["X-Conversation-Id"] = str(conversation_id)
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
