"""Branding helpers for BillionairsHQ and future whitelabel deployments."""

import os


DEFAULT_PRODUCT_NAME = "BillionairsHQ"
DEFAULT_COMPANY_NAME = "Billionaires Technologies"
DEFAULT_DOCS_URL = "https://docs.billionairestechnologies.com"
DEFAULT_WEBSITE_URL = "https://www.billionairestechnologies.com"
DEFAULT_REPO_URL = "https://github.com/billionairestechnologies/QuantX"


def get_branding() -> dict[str, str]:
    """Return display branding, falling back to BillionairsHQ defaults."""
    return {
        "product_name": os.getenv("PRODUCT_NAME", DEFAULT_PRODUCT_NAME),
        "company_name": os.getenv("COMPANY_NAME", DEFAULT_COMPANY_NAME),
        "docs_url": os.getenv("DOCS_URL", DEFAULT_DOCS_URL),
        "website_url": os.getenv("WEBSITE_URL", DEFAULT_WEBSITE_URL),
        "repo_url": os.getenv("REPO_URL", DEFAULT_REPO_URL),
    }
