# BillionairsHQ Status

Last updated: 2026-06-21

This file is the fast handoff document for the BillionairsHQ SaaS transformation.
Read this first if you need to continue the work from a cold start.

## Product Goal

Turn the current BTAlgo/OpenAlgo-derived install-per-client model into one shared SaaS platform:

- one domain
- many users and tenants
- per-user broker accounts
- billing and entitlements
- static-IP routing
- strategy hosting
- MCP, Telegram, WhatsApp, and copy trading under the same account system

## What Is Done

### Branding and whitelabel

- Product renamed to `BillionairsHQ`.
- Shared branding helpers added for backend and frontend.
- One-click whitelabel scripts added so product text can be changed again later.

Relevant commits:

- `a9c96292` feat: add BillionairsHQ whitelabel branding

### SaaS data foundation

- Added SaaS tables for:
  - tenants
  - user profiles
  - broker accounts
  - subscriptions
- Existing user creation now auto-provisions the SaaS profile and tenant shell.

Relevant commits:

- `d6d1d9cb` feat: add SaaS tenant and broker account foundation

### Broker account management

- Added SaaS broker account APIs.
- Added credential resolver that prefers per-user broker accounts and falls back to legacy `.env`.
- Profile/broker settings now store user broker credentials into SaaS tables instead of forcing shared server config.

Relevant commits:

- `aa50dba0` feat: route broker settings through SaaS accounts

### Broker auth migration started

- Fyers, Upstox, and Zerodha OAuth callback flows now use SaaS-resolved broker credentials for token exchange.
- Zerodha token prefixing also uses resolved broker context.

Relevant commits:

- `9ff86904` feat: use SaaS broker credentials in OAuth callbacks

### Public registration with email OTP

- Added self-serve `/register` page.
- Added Resend-based email OTP sender.
- Added pending OTP storage and verification flow.
- Account creation after OTP verify now provisions the normal user + SaaS profile.
- Login page now links to registration.

Relevant commits:

- `9e4013f0` feat: add resend email otp signup flow
- `88a72a42` build: refresh frontend bundle for signup flow

### Billing foundation is now product-wired

- Added Razorpay billing blueprint for:
  - billing summary
  - plan catalog
  - customer creation
  - subscription creation
  - subscription refresh
  - webhook verification
  - payment event history
- Added tenant billing event persistence.
- Added plan definitions and entitlement mapping helpers.
- Added billing visibility to the Profile UI so a signed-in user can see plan state and trigger the subscription flow.
- Added first-round enforcement:
  - live order-entry flows now check subscription entitlements
  - MCP `write:orders` approval now checks subscription entitlements
  - risk-reduction paths still remain available
  - static-IP route assignment now checks subscription entitlements

### MPIN product flow now exists

- Added MPIN hashing and verification on SaaS user profiles.
- Added backend routes for:
  - MPIN status
  - configure/save
  - verify
  - disable
- Added Profile UI for MPIN setup, verification, and disable flow.

### Static-IP routing foundation is now in place

- Added SaaS route inventory table for egress nodes.
- Added route inventory APIs:
  - tenant-visible route listing
  - admin route create/update
- Broker accounts can now store validated `ip_route_key` assignments.
- Route assignment is entitlement-aware and blocks non-static-IP plans.
- Added shared route resolver and HTTP proxy-aware request foundation for future broker modules.
- Started pushing route context into real broker auth/helper calls:
  - Dhan auth
  - IIFL Capital auth
  - Samco auth and IP setup
  - Definedge OTP auth
  - Upstox auth exchange
  - Zerodha auth exchange
- Extended route-aware execution deeper into live traffic:
  - Upstox order HTTP requests now resolve tenant route context
  - Dhan order HTTP requests now resolve tenant route context
  - Zerodha order HTTP requests now resolve tenant route context
  - Zerodha funds HTTP requests now resolve tenant route context
  - Zerodha margin HTTP requests now resolve tenant route context
  - WebSocket proxy initialization now passes tenant broker/auth context into pooled adapters
  - pooled reconnect/new-connection flows now retain the same tenant auth context
  - Upstox websocket client can now dial through tenant-selected proxy routes
  - Dhan websocket client can now dial through tenant-selected proxy routes
  - Zerodha websocket client can now dial through tenant-selected proxy routes
  - funds/margin service layer now forwards API-key context where broker modules support it

## What Is Not Done Yet

### Broker migration is incomplete

Only some broker auth paths were moved to resolver-based context.

Still needed:

- remaining broker callback/login flows
- deeper broker helper functions that still assume global env credentials
- request execution paths that may still read `BROKER_API_KEY` or `BROKER_API_SECRET` directly

### Billing is partially live

Still needed:

- static-IP entitlement enforcement
- final checkout/hosted payment UX polish
- subscription state machine hardening
- broader entitlement enforcement across every remaining broker/mutation path

### Auth product flow is incomplete

Done:

- email OTP for registration
- MPIN setup, verify, disable flow

Still needed:

- phone/mobile OTP if required
- enforcement rules for sensitive actions
- session/device management

### Static-IP routing is not fully implemented

Still needed:

- move more broker HTTP helpers onto route-aware request paths
- extend WebSocket route selection to the rest of the broker adapters
- add admin/operator UI for route balancing and health controls

### Copy trading is not unified yet

Still needed:

- merge copy trading users into BillionairsHQ auth
- reuse broker accounts
- reuse billing and entitlements
- reuse routing and audit trail

## Repo Notes

- Main SaaS plan doc: [TRANSFORMATION_PLAN.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/TRANSFORMATION_PLAN.md)
- Whitelabel guide: [WHITELABEL.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/WHITELABEL.md)

## Important Caution

- `uv.lock` currently has a local modification and was intentionally left uncommitted.
- The pushed transformation work is on `quantx/main`.
- Do not assume frontend `dist/` is safe to ignore for deployment in this repo; the current flow committed rebuilt assets as a separate step.
