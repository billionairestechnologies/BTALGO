"""Resolve broker app credentials for single-install and SaaS modes."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerCredentialContext:
    source: str
    broker: str | None
    api_key: str
    api_secret: str
    market_api_key: str
    market_api_secret: str
    redirect_url: str
    ip_route_key: str | None = None


def _broker_from_redirect_url(redirect_url: str) -> str | None:
    import re

    match = re.search(r"/([^/]+)/callback$", redirect_url or "")
    return match.group(1).lower() if match else None


def _env_context() -> BrokerCredentialContext:
    redirect_url = os.getenv("REDIRECT_URL", "")
    return BrokerCredentialContext(
        source="env",
        broker=_broker_from_redirect_url(redirect_url),
        api_key=os.getenv("BROKER_API_KEY", ""),
        api_secret=os.getenv("BROKER_API_SECRET", ""),
        market_api_key=os.getenv("BROKER_API_KEY_MARKET", ""),
        market_api_secret=os.getenv("BROKER_API_SECRET_MARKET", ""),
        redirect_url=redirect_url,
        ip_route_key=None,
    )


def resolve_broker_credentials(
    username: str | None = None,
    broker: str | None = None,
    account_id: int | None = None,
) -> BrokerCredentialContext:
    """Return broker credentials from SaaS storage or legacy `.env`.

    Existing broker plugins still read process env vars today. New
    SaaS-aware code can call this first and pass credentials explicitly,
    then fall back to the old env behavior when no per-user account exists.
    """
    if username:
        try:
            from database.saas_db import BrokerAccount, get_profile_by_username

            profile = get_profile_by_username(username)
            if profile:
                query = BrokerAccount.query.filter_by(user_profile_id=profile.id, is_active=True)
                if account_id is not None:
                    query = query.filter_by(id=account_id)
                if broker:
                    query = query.filter_by(broker=broker.lower())
                account = query.order_by(BrokerAccount.is_default.desc()).first()
                if account:
                    return BrokerCredentialContext(
                        source="saas",
                        broker=account.broker,
                        api_key=account.reveal_secret("api_key_encrypted") or "",
                        api_secret=account.reveal_secret("api_secret_encrypted") or "",
                        market_api_key=account.reveal_secret("market_api_key_encrypted") or "",
                        market_api_secret=account.reveal_secret("market_api_secret_encrypted") or "",
                        redirect_url=account.redirect_url or "",
                        ip_route_key=account.ip_route_key,
                    )
        except Exception:
            # Keep trading flows alive if the SaaS bridge has an issue.
            pass

    return _env_context()
