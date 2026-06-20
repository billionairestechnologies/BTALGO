"""Regression tests for SaaS broker credential resolution."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database.saas_db as saas_db  # noqa: E402
from utils.broker_context import resolve_broker_credentials  # noqa: E402


class _FakeQuery:
    def __init__(self, account):
        self.account = account

    def filter_by(self, **kwargs):
        if self.account is None:
            return self
        for key, value in kwargs.items():
            if getattr(self.account, key) != value:
                self.account = None
                break
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.account


class _FakeAccount:
    def __init__(self):
        self.id = 7
        self.user_profile_id = 11
        self.broker = "zerodha"
        self.is_active = True
        self.is_default = True
        self.redirect_url = "https://tenant.example.com/zerodha/callback"
        self.ip_route_key = "route-mumbai-1"
        self._secrets = {
            "api_key_encrypted": "tenant-key",
            "api_secret_encrypted": "tenant-secret",
            "market_api_key_encrypted": "tenant-market-key",
            "market_api_secret_encrypted": "tenant-market-secret",
        }

    def reveal_secret(self, field_name):
        return self._secrets.get(field_name)


def test_resolve_broker_credentials_prefers_user_saas_account(monkeypatch):
    monkeypatch.setenv("REDIRECT_URL", "https://legacy.example.com/zerodha/callback")
    monkeypatch.setenv("BROKER_API_KEY", "legacy-key")
    monkeypatch.setenv("BROKER_API_SECRET", "legacy-secret")
    monkeypatch.setenv("BROKER_API_KEY_MARKET", "legacy-market-key")
    monkeypatch.setenv("BROKER_API_SECRET_MARKET", "legacy-market-secret")

    fake_account = _FakeAccount()
    fake_broker_account = SimpleNamespace(
        is_default=SimpleNamespace(desc=lambda: None),
        query=_FakeQuery(fake_account),
    )

    monkeypatch.setattr(saas_db, "get_profile_by_username", lambda username: SimpleNamespace(id=11))
    monkeypatch.setattr(saas_db, "BrokerAccount", fake_broker_account)

    context = resolve_broker_credentials(username="trader1", broker="zerodha")

    assert context.source == "saas"
    assert context.broker == "zerodha"
    assert context.api_key == "tenant-key"
    assert context.api_secret == "tenant-secret"
    assert context.market_api_key == "tenant-market-key"
    assert context.market_api_secret == "tenant-market-secret"
    assert context.redirect_url == "https://tenant.example.com/zerodha/callback"
    assert context.ip_route_key == "route-mumbai-1"


def test_resolve_broker_credentials_falls_back_to_env_for_unknown_user(monkeypatch):
    monkeypatch.setenv("REDIRECT_URL", "https://legacy.example.com/upstox/callback")
    monkeypatch.setenv("BROKER_API_KEY", "legacy-key")
    monkeypatch.setenv("BROKER_API_SECRET", "legacy-secret")
    monkeypatch.setenv("BROKER_API_KEY_MARKET", "legacy-market-key")
    monkeypatch.setenv("BROKER_API_SECRET_MARKET", "legacy-market-secret")

    monkeypatch.setattr(saas_db, "get_profile_by_username", lambda username: None)

    context = resolve_broker_credentials(username="missing-user", broker="upstox")

    assert context.source == "env"
    assert context.broker == "upstox"
    assert context.api_key == "legacy-key"
    assert context.api_secret == "legacy-secret"
    assert context.market_api_key == "legacy-market-key"
    assert context.market_api_secret == "legacy-market-secret"
    assert context.redirect_url == "https://legacy.example.com/upstox/callback"
