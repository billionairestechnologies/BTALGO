"""
Billy AI Agent - Multi-provider AI service with streaming and tool-use support.
Supports: Anthropic, OpenAI, Ollama, OpenRouter, Grok, Gemini, Nexos AI.
"""

import json
from enum import Enum

from utils.logging import get_logger

logger = get_logger(__name__)


class AIProvider(str, Enum):
    ANTHROPIC  = "anthropic"
    OPENAI     = "openai"
    OLLAMA     = "ollama"
    OPENROUTER = "openrouter"
    GROK       = "grok"
    GEMINI     = "gemini"
    NEXOS      = "nexos"


# Default models per provider
DEFAULT_MODELS = {
    AIProvider.ANTHROPIC:  "claude-sonnet-4-6",
    AIProvider.OPENAI:     "gpt-4o",
    AIProvider.OLLAMA:     "llama3.2",
    AIProvider.OPENROUTER: "anthropic/claude-sonnet-4-6",
    AIProvider.GROK:       "grok-3",
    AIProvider.GEMINI:     "gemini-2.0-flash",
    AIProvider.NEXOS:      "nexos-pro",
}

# Providers that use OpenAI-compatible API
OPENAI_COMPAT_BASE_URLS = {
    AIProvider.OPENROUTER: "https://openrouter.ai/api/v1",
    AIProvider.GROK:       "https://api.x.ai/v1",
    AIProvider.NEXOS:      "https://api.nexosai.com/v1",
    AIProvider.GEMINI:     "https://generativelanguage.googleapis.com/v1beta/openai/",
}

BILLY_SYSTEM_PROMPT = """You are Billy, an intelligent AI trading assistant built into the BTAlgo platform by Billionaires Technologies.

You have access to the full BTAlgo trading platform including:
- Real-time market quotes, option chains, and Greeks
- Historical OHLCV data
- User's live positions, trade journal, orderbook, and account funds
- Ability to create Flow Editor strategies and Python strategies
- Ability to place/cancel orders (only when user explicitly confirms)
- Symbol search across all exchanges

Your personality:
- Friendly, sharp, and confident — like a knowledgeable trading desk partner
- Proactively fetch real data before giving analysis (don't guess prices)
- Always confirm before placing real orders
- When creating strategies, explain what you're building and why
- Keep responses concise but complete

When asked about markets: fetch live data first, then analyze.
When asked about portfolio: fetch positions and tradebook, then give insights.
When asked to create a strategy: build it in Flow Editor unless user asks for Python.
When asked to place an order: confirm details first, then execute only after explicit confirmation.
"""


def get_billy_system_prompt(context: dict = None) -> str:
    """Build system prompt, optionally injecting current context."""
    prompt = BILLY_SYSTEM_PROMPT
    if context:
        if context.get("page"):
            prompt += f"\n\nUser is currently on the '{context['page']}' page."
        if context.get("workflow_id"):
            prompt += f"\n\nUser has Flow Workflow #{context['workflow_id']} open."
    return prompt


# ── Streaming chat ─────────────────────────────────────────────────────────────

def stream_chat(messages: list, settings: dict, context: dict = None):
    """
    Generator that yields SSE-formatted chunks.
    Handles tool calls internally and streams final text response.
    """
    provider = AIProvider(settings.get("provider", "anthropic"))
    model = settings.get("model") or DEFAULT_MODELS.get(provider, "")
    api_key = settings.get("api_key", "")
    base_url = settings.get("base_url", "")
    allow_orders = settings.get("allow_orders", False)

    from services.billy_tools import BILLY_TOOLS, execute_tool

    system = get_billy_system_prompt(context)

    try:
        if provider == AIProvider.ANTHROPIC:
            yield from _stream_anthropic(messages, system, model, api_key, BILLY_TOOLS, allow_orders)
        elif provider == AIProvider.GEMINI:
            yield from _stream_openai_compat(
                messages, system, model, api_key,
                OPENAI_COMPAT_BASE_URLS[AIProvider.GEMINI],
                BILLY_TOOLS, allow_orders
            )
        elif provider == AIProvider.OLLAMA:
            yield from _stream_openai_compat(
                messages, system, model, api_key or "ollama",
                base_url or "http://localhost:11434/v1",
                BILLY_TOOLS, allow_orders
            )
        elif provider in (AIProvider.OPENROUTER, AIProvider.GROK, AIProvider.NEXOS):
            url = base_url or OPENAI_COMPAT_BASE_URLS.get(provider, "")
            yield from _stream_openai_compat(messages, system, model, api_key, url, BILLY_TOOLS, allow_orders)
        else:  # OpenAI default
            yield from _stream_openai_compat(
                messages, system, model, api_key,
                base_url or "https://api.openai.com/v1",
                BILLY_TOOLS, allow_orders
            )
    except Exception as e:
        logger.exception(f"Billy stream error ({provider}): {e}")
        yield _sse("error", {"message": str(e)})


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Anthropic streaming ────────────────────────────────────────────────────────

def _stream_anthropic(messages, system, model, api_key, tools, allow_orders):
    import anthropic as ac

    client = ac.Anthropic(api_key=api_key)

    # Convert tools to Anthropic format
    anthropic_tools = [
        {
            "name": t["name"],
            "description": t["description"],
            "input_schema": t["input_schema"],
        }
        for t in tools
    ]

    # Agentic loop — keep going until no more tool calls
    current_messages = list(messages)
    while True:
        with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system,
            messages=current_messages,
            tools=anthropic_tools,
        ) as stream:
            tool_calls = []
            full_text = ""

            for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_start":
                        if hasattr(event.content_block, "type"):
                            if event.content_block.type == "tool_use":
                                tool_calls.append({
                                    "id": event.content_block.id,
                                    "name": event.content_block.name,
                                    "input": {},
                                })
                                yield _sse("tool_start", {"name": event.content_block.name})

                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "type"):
                            if delta.type == "text_delta":
                                full_text += delta.text
                                yield _sse("text", {"chunk": delta.text})
                            elif delta.type == "input_json_delta":
                                if tool_calls:
                                    tool_calls[-1]["input"] = tool_calls[-1].get("_raw", "") + delta.partial_json
                                    tool_calls[-1]["_raw"] = tool_calls[-1]["input"]

                    elif event.type == "message_stop":
                        pass

            final_msg = stream.get_final_message()

            # If no tool calls, we're done
            if not any(b.type == "tool_use" for b in final_msg.content):
                yield _sse("done", {"message": full_text})
                break

            # Execute tool calls and continue loop
            tool_results = []
            for block in final_msg.content:
                if block.type == "tool_use":
                    yield _sse("tool_start", {"name": block.name})
                    result = execute_tool(block.name, block.input, allow_orders)
                    yield _sse("tool_done", {"name": block.name, "result_preview": result[:200]})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            current_messages = current_messages + [
                {"role": "assistant", "content": final_msg.content},
                {"role": "user", "content": tool_results},
            ]


# ── OpenAI-compatible streaming (OpenAI, Ollama, OpenRouter, Grok, Nexos) ──────

def _stream_openai_compat(messages, system, model, api_key, base_url, tools, allow_orders):
    from openai import OpenAI

    client = OpenAI(api_key=api_key or "none", base_url=base_url)

    openai_tools = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]

    oai_messages = [{"role": "system", "content": system}] + list(messages)
    full_text = ""

    while True:
        stream = client.chat.completions.create(
            model=model,
            messages=oai_messages,
            tools=openai_tools,
            tool_choice="auto",
            stream=True,
        )

        tool_call_map = {}
        finish_reason = None

        for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue

            finish_reason = choice.finish_reason or finish_reason
            delta = choice.delta

            if delta.content:
                full_text += delta.content
                yield _sse("text", {"chunk": delta.content})

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_call_map:
                        tool_call_map[idx] = {"id": tc.id or "", "name": "", "args": ""}
                    if tc.id:
                        tool_call_map[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_call_map[idx]["name"] = tc.function.name
                            yield _sse("tool_start", {"name": tc.function.name})
                        if tc.function.arguments:
                            tool_call_map[idx]["args"] += tc.function.arguments

        if finish_reason != "tool_calls" or not tool_call_map:
            yield _sse("done", {"message": full_text})
            break

        # Execute tools
        assistant_tool_calls = []
        tool_results = []
        for idx, tc in tool_call_map.items():
            try:
                tool_input = json.loads(tc["args"] or "{}")
            except Exception:
                tool_input = {}
            result = execute_tool(tc["name"], tool_input, allow_orders)
            yield _sse("tool_done", {"name": tc["name"], "result_preview": result[:200]})
            assistant_tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["args"]},
            })
            tool_results.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

        oai_messages = oai_messages + [
            {"role": "assistant", "content": None, "tool_calls": assistant_tool_calls},
            *tool_results,
        ]


# ── Provider status check ──────────────────────────────────────────────────────

def check_provider_status(settings: dict) -> dict:
    """Quick connectivity check for the configured provider."""
    provider = settings.get("provider", "anthropic")
    api_key = settings.get("api_key", "")
    base_url = settings.get("base_url", "")

    if not api_key and provider not in ("ollama",):
        return {"status": "no_key", "message": "No API key configured"}

    try:
        if provider == "anthropic":
            import anthropic as ac
            client = ac.Anthropic(api_key=api_key)
            client.models.list()
            return {"status": "ok", "provider": provider}
        elif provider in ("openai", "openrouter", "grok", "nexos"):
            from openai import OpenAI
            url = base_url or OPENAI_COMPAT_BASE_URLS.get(provider, "https://api.openai.com/v1")
            client = OpenAI(api_key=api_key, base_url=url)
            client.models.list()
            return {"status": "ok", "provider": provider}
        elif provider == "ollama":
            import urllib.request
            url = (base_url or "http://localhost:11434").rstrip("/") + "/api/tags"
            urllib.request.urlopen(url, timeout=3)
            return {"status": "ok", "provider": "ollama"}
        elif provider == "gemini":
            from openai import OpenAI
            client = OpenAI(api_key=api_key,
                            base_url=OPENAI_COMPAT_BASE_URLS[AIProvider.GEMINI])
            client.models.list()
            return {"status": "ok", "provider": "gemini"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    return {"status": "unknown"}
