# Core — OpenAlgo Engine

This directory is a conceptual boundary marker.

The OpenAlgo engine lives at the **repository root** — packages `blueprints/`, `broker/`,
`services/`, `utils/`, `database/`, `restx_api/`, `websocket_proxy/`, etc. — because
Python import paths are resolved relative to the project root and must remain unchanged
for the application to function.

## Rules

- **NEVER** edit files in the root OpenAlgo packages directly.
- Add new features inside `/btalgo/` using wrapper imports.
- Override UI templates in `/overrides/`.
- Keep branding assets in `/branding/` and config in `/config/branding.json`.

## Upstream updates

```bash
git fetch upstream
git merge upstream/main
# Resolve conflicts only in btalgo/, overrides/, branding/, config/, docs/
```
