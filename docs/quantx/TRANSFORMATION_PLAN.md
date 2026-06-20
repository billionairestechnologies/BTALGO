# QuantX Transformation Plan

QuantX is the SaaS evolution of the current BTAlgo/OpenAlgo-derived stack. The goal is to stop running one VPS per client and move to one managed platform with many users, per-user broker accounts, subscriptions, IP routing, copy trading, MCP, and strategy execution.

## Product Scope

QuantX must retain the current trading product surface:

- Broker login and trading across all supported broker plugins.
- Order placement, smart orders, basket orders, split orders, GTT where broker support exists, orderbook, tradebook, positions, holdings, funds, margin, and close/cancel flows.
- Strategy Builder, Chartink webhooks, TradingView JSON/webhook support, GoCharting support, Flow workflows, Python Strategy hosting, and Python SDK support.
- TradingView-style charting and bright chart views for symbol analysis and strategy work.
- WebSocket market data streaming with LTP, quote, and depth modes.
- Analyzer/sandbox mode, Action Center, semi-auto approval, logs, latency, health, and security dashboards.
- WhatsApp and Telegram notifications, alerts, and user-facing configuration.
- Remote MCP with per-user OAuth, scopes, and optional write-order approval gates.
- Copy trading under the same QuantX domain and admin model.

## SaaS Architecture Direction

QuantX should become a multi-tenant platform, not a collection of per-client installs.

Core direction:

- PostgreSQL as the primary transactional database.
- Redis for sessions, short-lived OTP state, rate-limit state, queues, and distributed locks.
- Object/file storage for strategy artifacts, generated reports, and large historical exports.
- DuckDB or columnar storage for historical market data where appropriate.
- Per-user encrypted broker accounts instead of shared `.env` broker credentials.
- Static-IP egress routing by broker account for brokers that need IP whitelisting.
- Background workers for strategy execution, scheduled jobs, broker keepalive, notifications, and copy-trade fanout.

## First Data Model Slice

The first implementation slice should add these platform tables:

- `organizations`: billing and workspace owner boundary.
- `organization_members`: role membership.
- `user_profiles`: user metadata beyond the existing login record.
- `broker_accounts`: one user can connect many brokers.
- `broker_account_credentials`: encrypted broker keys, client IDs, TOTP/MPIN metadata, and market-data keys.
- `subscriptions`: plan state and entitlement source.
- `payments`: Razorpay orders, payments, refunds, and webhook events.
- `ip_egress_nodes`: static-IP gateway inventory.
- `broker_account_routes`: mapping from broker account to egress node.
- `audit_events`: immutable security and trading admin audit trail.

## Migration Priorities

1. Baseline safety
   - Keep `.env` ignored and never push live secrets.
   - Remove generated frontend build churn from ordinary product commits.
   - Add migration tooling before changing core tables.

2. Multi-user broker accounts
   - Replace server-wide broker credentials editing with per-user broker account CRUD.
   - Resolve broker credentials from the authenticated user or API key.
   - Keep existing broker plugins, but route their config through a resolver.

3. Billing and entitlements
   - Add Razorpay checkout and webhook verification.
   - Gate live trading, copy trading, strategy runner, MCP write scope, and IP routing by entitlement.
   - Always allow risk-reduction actions such as cancel, squareoff, and close position even when billing fails.

4. IP routing
   - Add egress node registry.
   - Add per-broker-account route assignment.
   - Route broker HTTP and WebSocket traffic through the assigned static-IP node.

5. Strategy isolation
   - Move Python strategy config from shared local JSON into database-backed per-user records.
   - Run user strategies in isolated worker processes or containers.
   - Add strategy run logs, resource limits, and stop controls.

6. Copy trading
   - Bring copy trading under QuantX auth, billing, broker accounts, IP routing, and audit logs.
   - Support master, follower, risk multiplier, symbol mapping, and kill switch controls.

7. MCP
   - Make Remote MCP per-user, OAuth-scoped, and entitlement-aware.
   - Keep read-only defaults and require fresh TOTP for order-writing scopes.

## Immediate Commit Plan

The first code commits after this document should be:

1. Add QuantX SaaS database models and migrations.
2. Add broker account CRUD APIs without removing legacy `.env` credentials yet.
3. Add a broker credential resolver that prefers per-user accounts and falls back to legacy env config.
4. Convert one broker path end-to-end through the resolver.
5. Add tests for tenant isolation and secret masking.

## Non-Negotiables

- No live user secret should be written to Git.
- No tenant should ever see another tenant's broker account, strategy, logs, or API keys.
- Trading safety comes before billing enforcement.
- Legacy single-install mode can remain during migration, but QuantX SaaS paths must be explicit and testable.
