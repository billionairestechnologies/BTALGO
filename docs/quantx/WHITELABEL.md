# BillionairsHQ Whitelabel Guide

BillionairsHQ branding is now centralized for the web app and backend metadata.

## One Command

Run this from the repository root:

```bash
python scripts/apply_whitelabel.py --product-name "ClientBrand"
```

On Windows, double-click `WHITELABEL.bat` from the repository root and fill in the prompts. Press Enter on any prompt to keep the default BillionairsHQ values.

Optional fields:

```bash
python scripts/apply_whitelabel.py \
  --product-name "ClientBrand" \
  --company-name "Client Company" \
  --docs-url "https://docs.example.com" \
  --website-url "https://example.com" \
  --repo-url "https://github.com/example/clientbrand"
```

## Runtime Overrides

Backend display metadata reads:

- `PRODUCT_NAME`
- `COMPANY_NAME`
- `DOCS_URL`
- `WEBSITE_URL`
- `REPO_URL`

Frontend display metadata reads:

- `VITE_PRODUCT_NAME`
- `VITE_COMPANY_NAME`
- `VITE_DOCS_URL`
- `VITE_WEBSITE_URL`
- `VITE_REPO_URL`
- `VITE_X_URL`
- `VITE_YOUTUBE_URL`
- `VITE_DISCORD_URL`
- `VITE_ROADMAP_URL`

## Compatibility Names

Some names intentionally remain unchanged for now because existing runtime code, migrations, strategy docs, or integrations rely on them:

- `APP_KEY`
- `API_KEY_PEPPER`
- `BTALGO_GIT_BRANCH`
- `BTALGO_GIT_COMMIT`
- `BTALGO_MCP_HTTP_BOOT`
- `BTALGO_API_KEY`
- `BTALGO_STRATEGY_EXCHANGE`
- `btalgo_username`

Those can be migrated later behind compatibility aliases.
