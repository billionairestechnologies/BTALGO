# BillionairsHQ Handoff

Last updated: 2026-06-20

This file is for the next agent or developer who needs to continue the SaaS transformation.

## Read Order

1. [STATUS.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/STATUS.md)
2. [TODO.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/TODO.md)
3. [TRANSFORMATION_PLAN.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/TRANSFORMATION_PLAN.md)

## Important Commits Already Pushed

- `950ef3b1` docs: add QuantX transformation plan
- `a9c96292` feat: add BillionairsHQ whitelabel branding
- `d6d1d9cb` feat: add SaaS tenant and broker account foundation
- `aa50dba0` feat: route broker settings through SaaS accounts
- `9ff86904` feat: use SaaS broker credentials in OAuth callbacks
- `9e4013f0` feat: add resend email otp signup flow
- `88a72a42` build: refresh frontend bundle for signup flow

## Current Truth

- SaaS signup with email OTP exists.
- Some broker auth flows are SaaS-aware.
- Billing foundation exists: plans, customer creation, subscription create/refresh, webhook validation, and payment-event persistence.
- MPIN setup/verify/disable flow exists in backend and Profile UI.
- Static-IP routing is not live.
- Copy trading is not unified into BillionairsHQ yet.

## Good Next Task

Best next engineering task:

`Finish broker auth migration, then enforce billing entitlements on live trading, MCP write scope, and future static-IP routing.`

Reason:

- It removes the biggest remaining architectural split in the codebase.
- It lets the new billing layer actually control product access.
- It is the cleanest path to routing and copy-trading unification.

## Watch Outs

- Do not commit live secrets.
- `uv.lock` is locally modified and was intentionally not pushed.
- `frontend/dist` is ignored by default, so if a deployment expects built assets in repo, add them with `git add -f frontend/dist`.
- Some legacy naming still intentionally preserves compatibility, including BTAlgo-prefixed env vars.

## Definition Of Done For The Next Slice

The next broker-migration and billing-enforcement slice should be considered done only when:

- all supported broker login/auth paths use the resolver
- helper modules do not silently read global broker env vars when a user account context exists
- at least one regression test covers tenant isolation for broker credentials
- UI behavior still works with legacy fallback for installs not yet migrated
- live trading and MCP write decisions read the tenant subscription entitlements instead of assuming access
