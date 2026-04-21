# services/billy_ai_service.py

import json
import os

import httpx

from utils.logging import get_logger

logger = get_logger(__name__)

# ── Provider Configuration ──────────────────────────────────────────────────

PROVIDERS = {
    "nexos": {
        "name": "Nexos AI",
        "base_url": "https://api.nexos.ai/v1",
        "env_key": "NEXOS_API_KEY",
        "models": [
            {"id": "Claude Sonnet 4.6", "name": "Claude Sonnet 4.6"},
            {"id": "Claude Haiku 4.5", "name": "Claude Haiku 4.5"},
            {"id": "GPT 5.4", "name": "GPT 5.4"},
            {"id": "GPT 5.4 mini", "name": "GPT 5.4 Mini"},
            {"id": "Gemini 2.5 Pro", "name": "Gemini 2.5 Pro"},
            {"id": "gemini-3-flash-preview", "name": "Gemini 3 Flash"},
            {"id": "gpt-4.1", "name": "GPT 4.1"},
            {"id": "Grok 4.20 Reasoning", "name": "Grok 4.20 Reasoning"},
            {"id": "Mistral Large 3", "name": "Mistral Large 3"},
            {"id": "Devstral 2", "name": "Devstral 2"},
            {"id": "claude-opus-4-20250514", "name": "Claude Opus 4"},
        ],
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "env_key": "OPENAI_API_KEY",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini"},
        ],
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "env_key": "ANTHROPIC_API_KEY",
        "models": [
            {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
        ],
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "models": [
            {"id": "llama-3.3-70b-versatile", "name": "Llama 3.3 70B"},
            {"id": "mixtral-8x7b-32768", "name": "Mixtral 8x7B"},
        ],
    },
    "gemini": {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "env_key": "GEMINI_API_KEY",
        "models": [
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
            {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro"},
        ],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "models": [
            {"id": "openai/gpt-4o", "name": "GPT-4o (via OpenRouter)"},
            {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4 (via OpenRouter)"},
            {"id": "google/gemini-2.0-flash-exp", "name": "Gemini 2.0 Flash (via OpenRouter)"},
        ],
    },
}


# ── System Prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Billy AI, the intelligent trading assistant built into BT Algo — a professional algorithmic trading platform for Indian financial markets.

IDENTITY:
- Your name is Billy AI.
- The platform is BT Algo (short for Billionaires Technologies Algo). Never call it "OpenAlgo" or "Billionaires Terminal".
- You represent BT Algo's AI layer: knowledgeable, precise, and trader-focused.

YOUR ROLE:
You assist traders at every level — from beginners learning the basics to professional algo traders managing complex strategies. You have access to the user's LIVE account data (positions, holdings, orders, funds) which is injected below. Use it whenever relevant without being asked.

CORE CAPABILITIES:
- Portfolio analysis: review live positions, holdings, P&L, drawdowns, and exposure
- Order management guidance: explain order types, statuses, and execution strategies
- Strategy building: design entry/exit logic, help with Pine Script, Python, and webhook payloads
- Options expertise: straddles, strangles, iron condors, butterflies, calendar spreads, delta/gamma/theta analysis
- Risk management: position sizing, stop-loss placement, portfolio heat, margin utilization
- Platform integration: BT Algo API endpoints, TradingView webhooks, Amibroker AFL, Python SDK
- Market education: explain instruments, exchanges, derivatives, and trading concepts clearly

RESPONSE STYLE:
- Be professional, direct, and actionable — traders value clarity over verbosity.
- Lead with the answer, then provide context or explanation.
- Use markdown formatting: headers for structure, code blocks for code/JSON, tables for comparisons, bullet points for lists.
- Never use emojis.
- When the user's live data is available, reference it specifically (e.g., "Your RELIANCE position is currently at a loss of ₹2,340").
- If positions/holdings are empty, state it clearly and pivot to what the user can do next.
- Always include a brief risk note when suggesting trades or strategies.
- For code examples, use Python with the BT Algo SDK or Pine Script as appropriate.

LIVE DATA USAGE:
- The user's live account snapshot is appended below this prompt.
- Always check it before answering questions about portfolio, P&L, margins, or exposure.
- If the data shows no activity, acknowledge it and offer relevant next steps.

INDIAN MARKET CONTEXT:
- Exchanges: NSE, BSE (equity), NFO, BFO (F&O), MCX (commodity), CDS (currency), NSE_INDEX, BSE_INDEX
- Equity symbol format: SYMBOL-EQ (e.g., SBIN-EQ, RELIANCE-EQ) on NSE/BSE
- Index format: NIFTY or BANKNIFTY on NSE_INDEX exchange
- F&O format: NIFTY28MAR2422000CE, BANKNIFTY24APR24FUT
- Order types: MARKET, LIMIT, SL, SL-M | Products: CNC (delivery), NRML (F&O carry), MIS (intraday)
- Market hours: 9:15 AM – 3:30 PM IST (equity/F&O), 9:00 AM – 11:30 PM IST (MCX)
"""


def get_available_providers():
    """Return list of providers that have API keys configured"""
    available = []
    for key, config in PROVIDERS.items():
        api_key = os.getenv(config["env_key"], "")
        available.append({
            "id": key,
            "name": config["name"],
            "available": bool(api_key),
            "models": config["models"],
        })
    return available


def generate_title(message):
    """Generate a short title from the first message (basic version)"""
    words = message.split()[:5]
    return " ".join(words) + ("..." if len(message.split()) > 5 else "")


def get_trading_context(api_key=None):
    """Get live trading context (positions, orders, holdings, funds) from broker"""
    if not api_key:
        return {"positions": [], "orders": [], "holdings": [], "funds": {}}

    context = {"positions": [], "orders": [], "holdings": [], "funds": {}}

    try:
        from services.positionbook_service import get_positionbook
        success, data, _ = get_positionbook(api_key=api_key)
        if success:
            context["positions"] = data.get("data", [])
    except Exception as e:
        logger.exception(f"Billy AI: failed to fetch positions: {e}")

    try:
        from services.holdings_service import get_holdings
        success, data, _ = get_holdings(api_key=api_key)
        if success:
            raw = data.get("data", {})
            context["holdings"] = raw.get("holdings", []) if isinstance(raw, dict) else raw
    except Exception as e:
        logger.exception(f"Billy AI: failed to fetch holdings: {e}")

    try:
        from services.orderbook_service import get_orderbook
        success, data, _ = get_orderbook(api_key=api_key)
        if success:
            raw = data.get("data", {})
            context["orders"] = raw.get("orders", []) if isinstance(raw, dict) else raw
    except Exception as e:
        logger.exception(f"Billy AI: failed to fetch orders: {e}")

    try:
        from services.funds_service import get_funds
        success, data, _ = get_funds(api_key=api_key)
        if success:
            context["funds"] = data.get("data", {})
    except Exception as e:
        logger.exception(f"Billy AI: failed to fetch funds: {e}")

    return context


def _format_trading_context(context):
    """Format trading context dict into a concise text block for the system prompt"""
    lines = ["--- LIVE ACCOUNT DATA (fetched right now) ---"]

    funds = context.get("funds", {})
    if funds:
        cash = funds.get("availablecash", funds.get("availablemargin", "N/A"))
        margin = funds.get("usedmargin", "N/A")
        lines.append(f"Funds: Available cash={cash}, Used margin={margin}")
    else:
        lines.append("Funds: Not available")

    positions = context.get("positions", [])
    if positions:
        lines.append(f"Open Positions ({len(positions)}):")
        for p in positions[:30]:
            sym = p.get("symbol", "?")
            qty = p.get("netqty", p.get("quantity", 0))
            pnl = p.get("pnl", 0)
            price = p.get("price", 0)
            lines.append(f"  {sym}: qty={qty}, avg={price}, pnl={pnl}")
    else:
        lines.append("Open Positions: None")

    holdings = context.get("holdings", [])
    if holdings:
        lines.append(f"Holdings ({len(holdings)} stocks):")
        for h in holdings[:30]:
            sym = h.get("symbol", "?")
            qty = h.get("quantity", 0)
            pnl = h.get("pnl", 0)
            pnlpct = h.get("pnlpercent", 0)
            lines.append(f"  {sym}: qty={qty}, pnl={pnl} ({pnlpct}%)")
    else:
        lines.append("Holdings: None")

    orders = context.get("orders", [])
    if orders:
        lines.append(f"Today's Orders ({len(orders)} total):")
        for o in orders[:20]:
            sym = o.get("symbol", "?")
            status = o.get("status", "?")
            qty = o.get("quantity", 0)
            ptype = o.get("pricetype", "?")
            lines.append(f"  {sym}: {status}, qty={qty}, type={ptype}")
    else:
        lines.append("Today's Orders: None")

    lines.append("--- END LIVE DATA ---")
    return "\n".join(lines)


def stream_chat(messages, provider_id="nexos", model_id="Claude Sonnet 4.6", trading_context=None, user_api_key=None):
    """Stream a chat completion response"""
    
    if provider_id not in PROVIDERS:
        yield json.dumps({"error": f"Provider {provider_id} not found"})
        return
    
    config = PROVIDERS[provider_id]
    api_key = os.getenv(config["env_key"], "")
    
    if not api_key:
        yield json.dumps({"error": f"API key not configured for {config['name']}"})
        return
    
    # Prepare request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    system_content = SYSTEM_PROMPT
    if trading_context:
        system_content += "\n\n" + _format_trading_context(trading_context)

    payload = {
        "model": model_id or config["models"][0]["id"],
        "messages": [{"role": "system", "content": system_content}] + messages,
        "stream": True,
        "temperature": 0.7,
    }
    
    try:
        with httpx.Client(timeout=httpx.Timeout(60.0)) as client:
            with client.stream(
                "POST",
                f"{config['base_url']}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue

                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]":
                            yield json.dumps({"content": ""})
                            break

                        try:
                            parsed = json.loads(data)
                            if "choices" in parsed and len(parsed["choices"]) > 0:
                                choice = parsed["choices"][0]
                                if "delta" in choice and "content" in choice["delta"]:
                                    content = choice["delta"]["content"]
                                    if content:
                                        yield json.dumps({"content": content})
                        except json.JSONDecodeError:
                            pass

    except httpx.HTTPStatusError as e:
        yield json.dumps({"error": f"API error {e.response.status_code}: {e.response.text[:200]}"})
    except httpx.RequestError as e:
        yield json.dumps({"error": f"API request failed: {str(e)}"})
