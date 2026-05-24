# BTAlgo — Algorithmic Trading Platform

**BTAlgo** is a production-ready, self-hosted algorithmic trading platform built on Python Flask + React 19. It gives traders a complete environment to design, host, and execute strategies across 30+ Indian brokers through a single unified API.

---

## Four Products in One

| Surface | Route | Purpose |
|---|---|---|
| **Unified Broker API** | `/api/v1/` | Connect TradingView, Amibroker, ChartInk, Excel, Python, and more |
| **Python Strategy Host** | `/python` | In-browser editor — write, schedule, and run Python strategies with live logs |
| **Flow — No-Code Builder** | `/flow` | Drag-and-drop strategy builder with webhook triggers and JSON export |
| **Options Trading Suite** | `/tools` | 12 analytical tools — Option Chain, IV Smile, Max Pain, GEX, OI Tracker, and more |

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/billionairestechnologies/BTALGO.git
cd BTALGO

# 2. Copy and configure environment
cp .sample.env .env
# Edit .env with your broker credentials, APP_KEY, and API_KEY_PEPPER

# 3. Run (uv handles the virtual environment automatically)
uv run app.py
```

Access the platform at **http://127.0.0.1:5000**

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

---

## Supported Brokers

AliceBlue · Angel · CompositEdge · Definedge · Delta Exchange · Dhan · Firstock · Fivepaisa · Flattrade · Fyers · Groww · IBulls · IIFL · IIFLCapital · IndMoney · JainamXTS · Kotak · Motilal · MStock · Nubra · Paytm · Pocketful · RMoney · Samco · Shoonya · Tradejini · Upstox · Wisdom · Zebu · Zerodha

---

## Key Features

- **Single API** for 30+ brokers — one integration, all brokers
- **Sandbox mode** — ₹1 Crore virtual capital, exchange-aligned auto square-off
- **Real-time WebSocket** — unified market data feed across all connected brokers
- **MCP server** — AI assistant integration via Claude Desktop, Cursor, and Windsurf
- **Telegram & WhatsApp alerts** — trade notifications and bot commands
- **GTT orders** — Good-Till-Triggered order support (Zerodha, Dhan)
- **Options suite** — Strategy Builder, payoff diagrams, live Greeks, Vol Surface, GEX dashboard

---

## Documentation

[https://docs.billionairestechnologies.com](https://docs.billionairestechnologies.com)

---

## Powered by Billionaires Technologies

[www.billionairestechnologies.com](https://www.billionairestechnologies.com)
