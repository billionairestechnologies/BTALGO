# BillionairsHQ Memory

Last updated: 2026-06-21

This is the single-file relay note for the next model or developer.
Use this when you want the fastest possible restart.

## Current Stop Point

Work stopped right after pushing the Zerodha tenant-context slice.

Latest pushed commit:

- `3ff0e220` feat: route zerodha execution through tenant context

Recent pushed chain before that:

- `e37457ea` feat: add route-aware websocket proxy support
- `c0dd0c1c` feat: route websocket and order flows through tenant context
- `445bd19f` feat: route broker auth helpers through tenant ip context
- `6022869e` feat: add static ip routing foundation
- `798a201d` feat: enforce subscription access on trading and mcp

## What Is Definitely Done

- BillionairsHQ branding and whitelabel scripts exist.
- SaaS tenant/user/broker-account/subscription foundation exists.
- Resend email OTP registration exists.
- MPIN setup/verify/disable exists.
- Razorpay billing foundation exists.
- Entitlement checks already affect:
  - live trading
  - MCP order-writing scope
  - static-IP route assignment
- Static-IP route inventory and broker-account route assignment exist.
- Route-aware broker auth/helper flows exist for:
  - Dhan
  - IIFL Capital
  - Samco
  - Definedge
  - Upstox
  - Zerodha
- Route-aware live execution now exists for:
  - Upstox order HTTP path
  - Dhan order HTTP path
  - Zerodha order HTTP path
  - Zerodha funds HTTP path
  - Zerodha margin HTTP path
- WebSocket pooled adapters now retain tenant auth context across:
  - new pooled connections
  - reconnects
  - auth-refresh rebuilds
- Proxy-aware websocket client foundation exists for:
  - Upstox
  - Dhan
  - Zerodha

## Current Approximate Progress

- Overall transformation: about `74-76% done`
- Remaining: about `24-26%`

## Biggest Remaining Work

### 1. Finish broker tenant-isolation sweep

Still needed in practice:

- more broker helper/API/data/funds/margin/order modules still read shared `BROKER_*` env
- more broker websocket clients still need route-aware proxy support
- history/depth/data paths still need cleaner tenant-context threading in more brokers

### 2. Admin / operator UI

Still needed:

- tenant admin panel
- route inventory management UI
- broker account health/status UI
- billing/subscription operator visibility

### 3. Copy trading unification

Still needed:

- move copytrading to BillionairsHQ auth
- move copytrading to BillionairsHQ billing and entitlements
- reuse same broker-account model
- reuse same route model
- add unified audit / kill switch

### 4. Final product hardening

Still needed:

- more tenant-isolation tests
- session/device management UI
- stronger sensitive-action auth rules
- deployment/operator polish

## Best Next Task

Best next coding task:

`Continue the broker-isolation sweep on the next high-usage broker set, then switch into admin panel build.`

Suggested order:

1. next high-usage broker HTTP/data/helper modules
2. remaining broker websocket routing coverage
3. tenant-isolation regression pack
4. admin panel
5. copytrading merge

## Good Broker Candidates For The Next Slice

Pick one of these next:

- `fyers`
- `angel`
- `shoonya` / `flattrade`
- `fivepaisa`
- `mstock`

Selection rule:

- prefer the broker with the most active production use
- prefer modules with both order + funds + margin + websocket footprint

## Files To Read First On Resume

1. [STATUS.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/STATUS.md)
2. [TODO.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/TODO.md)
3. [HANDOFF.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/HANDOFF.md)
4. [TRANSFORMATION_PLAN.md](C:/Users/Parth Rathod/Desktop/BTALGO/docs/quantx/TRANSFORMATION_PLAN.md)

## Important Repo Notes

- `uv.lock` is locally modified and intentionally not committed.
- Do not revert unrelated repo changes.
- Some legacy BTAlgo naming is intentionally preserved for compatibility.
- `frontend/dist` is ignored by default; only add it if a deployment flow truly requires checked-in built assets.

## Resume Safety Checklist

Before starting new code:

1. check `git status`
2. leave `uv.lock` alone unless intentionally updating dependencies
3. read the last 3 pushed commits
4. continue from broker isolation first unless product priorities changed
