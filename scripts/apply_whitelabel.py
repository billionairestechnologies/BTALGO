"""Apply basic BillionairsHQ/whitelabel display branding.

Usage:
    python scripts/apply_whitelabel.py --product-name "ClientName"

This intentionally touches only display/config files. Runtime compatibility
identifiers such as BTALGO_MCP_HTTP_BOOT, placeholder secret names, database
paths, and SDK imports are left unchanged.
"""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def replace_between(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8", newline="\n")


def set_env_value(path: Path, key: str, value: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    prefix = f"{key} = "
    rendered = f"{key} = '{value}'"
    for i, line in enumerate(lines):
        if line.strip().startswith(prefix):
            lines[i] = rendered
            break
    else:
        lines.append(rendered)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--product-name", required=True)
    parser.add_argument("--company-name", default="Billionaires Technologies")
    parser.add_argument("--docs-url", default="https://docs.billionairestechnologies.com")
    parser.add_argument("--website-url", default="https://www.billionairestechnologies.com")
    parser.add_argument("--repo-url", default="https://github.com/billionairestechnologies/QuantX")
    args = parser.parse_args()

    env_path = ROOT / ".sample.env"
    for key, value in {
        "PRODUCT_NAME": args.product_name,
        "COMPANY_NAME": args.company_name,
        "DOCS_URL": args.docs_url,
        "WEBSITE_URL": args.website_url,
        "REPO_URL": args.repo_url,
        "VITE_PRODUCT_NAME": args.product_name,
        "VITE_COMPANY_NAME": args.company_name,
        "VITE_DOCS_URL": args.docs_url,
        "VITE_WEBSITE_URL": args.website_url,
        "VITE_REPO_URL": args.repo_url,
    }.items():
        set_env_value(env_path, key, value)

    replace_between(
        ROOT / "frontend" / "index.html",
        {
            "BTAlgo - Open Source Algorithmic Trading Platform": (
                f"{args.product_name} - Algorithmic Trading Platform"
            ),
            "BillionairsHQ - Algorithmic Trading Platform": (
                f"{args.product_name} - Algorithmic Trading Platform"
            ),
            "<title>BTAlgo</title>": f"<title>{args.product_name}</title>",
            "<title>BillionairsHQ</title>": f"<title>{args.product_name}</title>",
        },
    )

    print(f"Applied display branding for {args.product_name}")


if __name__ == "__main__":
    main()
