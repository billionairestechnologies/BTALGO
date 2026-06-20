# BillionairsHQ Status

Last updated: 2026-06-20

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

### MPIN product flow now exists

- Added MPIN hashing and verification on SaaS user profiles.
- Added backend routes for:
  - MPIN status
  - configure/save
  - verify
  - disable
- Added Profile UI for MPIN setup, verification, and disable flow.

## What Is Not Done Yet

### Broker migration is incomplete

Only some broker auth paths were moved to resolver-based context.

Still needed:

- remaining broker callback/login flows
- deeper broker helper functions that still assume global env credentials
- request execution paths that may still read `BROKER_API_KEY` or `BROKER_API_SECRET` directly

### Billing is partially live

Still needed:

- enforcement in trading/MCP/routing flows
- final checkout/hosted payment UX polish
- subscription state machine hardening
- entitlement enforcement

### Auth product flow is incomplete

Done:

- email OTP for registration
- MPIN setup, verify, disable flow

Still needed:

- phone/mobile OTP if required
- enforcement rules for sensitive actions
- session/device management

### Static-IP routing is not implemented

Still needed:

- route inventory
- broker account to route mapping
- outbound broker traffic via selected egress

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
