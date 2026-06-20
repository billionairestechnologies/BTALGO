# BillionairsHQ TODO

Last updated: 2026-06-20

This is the execution queue, ordered by what should happen next.

## Current Priority

- [ ] Finish broker auth migration to resolver-based SaaS account context
- [x] Add Razorpay billing core
- [x] Add MPIN and stronger auth product flow
- [ ] Add static-IP routing
- [ ] Merge copy trading into BillionairsHQ auth, billing, routing, and broker account model

## 1. Broker Auth Migration

- [x] Add broker credential resolver
- [x] Add SaaS broker account CRUD
- [x] Migrate Fyers callback token exchange
- [x] Migrate Upstox callback token exchange
- [x] Migrate Zerodha callback token exchange
- [ ] Audit all broker plugins for direct `os.getenv("BROKER_*")` usage
- [ ] Move remaining broker callback flows to resolved broker account context
- [ ] Move deeper helper/API modules away from shared env assumptions
- [ ] Ensure API-key authenticated requests can resolve the correct broker account
- [ ] Add regression tests for tenant isolation and masked secret responses

## 2. Billing and Entitlements

- [x] Add Razorpay customer/order/subscription integration
- [x] Add webhook signature verification
- [x] Persist billing events and payment history
- [x] Add plan definitions and entitlement mapping
- [x] Gate live trading by subscription
- [x] Gate MCP write scope by subscription
- [ ] Gate static-IP routing by subscription
- [ ] Keep risk-reduction actions allowed even when billing is inactive

## 3. OTP / MPIN / Account Security

- [x] Add email OTP signup flow with Resend
- [x] Add MPIN set/reset flow
- [ ] Add optional mobile/phone OTP flow if product requires it
- [x] Add UI for auth preferences per user
- [ ] Add session/device management UI
- [ ] Add enforcement rules for sensitive actions:
  - [ ] broker connect
  - [ ] API key regenerate
  - [ ] MCP write approvals
  - [ ] billing/admin changes

## 4. Static-IP Routing

- [x] Add egress node table/model
- [x] Add route assignment per broker account
- [x] Add health status for route nodes
- [x] Add outbound broker HTTP routing foundation
- [ ] Add outbound broker WebSocket routing
- [x] Add admin API to manage route inventory
- [ ] Add admin UI to assign or rebalance routes
- [ ] Start using route context in broker API/helper modules that still call shared env-based clients
  - [x] Dhan auth flow
  - [x] IIFL Capital auth flow
  - [x] Samco auth/IP setup flow
  - [x] Definedge OTP auth flow
  - [x] Upstox auth exchange
  - [x] Zerodha auth exchange

## 5. Copy Trading Unification

- [ ] Move copy trading auth to BillionairsHQ users
- [ ] Move copy trading billing to BillionairsHQ subscriptions
- [ ] Reuse BillionairsHQ broker accounts for masters and followers
- [ ] Reuse routing model for copy trade execution
- [ ] Add audit trail and kill switch under same admin model

## 6. Strategy Platform

- [ ] Move strategy state to tenant-safe DB-backed models where still shared
- [ ] Isolate Python strategy execution per user
- [ ] Add worker/job model for schedules and logs
- [ ] Add quotas and safety limits
- [ ] Add platform API and Python SDK alignment for user-created strategies

## 7. Product Integration

- [ ] Same-domain nav and account model for:
  - [ ] strategy platform
  - [ ] copy trading
  - [ ] billing
  - [ ] MCP
  - [ ] Telegram
  - [ ] WhatsApp
- [ ] Tenant admin area
- [ ] Member invite flow
- [ ] Usage and audit dashboards

## Suggested Next Execution Order

1. Finish broker migration completely.
2. Finish broker migration completely.
3. Enforce billing entitlements in trading/MCP/routing paths.
4. Add static-IP routing.
5. Merge copy trading into the same SaaS model.
