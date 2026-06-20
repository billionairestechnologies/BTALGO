"""Regression tests for BillionairsHQ static-IP route resolution."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import utils.ip_routing as ip_routing  # noqa: E402


def test_resolve_ip_route_uses_saas_node(monkeypatch):
    monkeypatch.setattr(
        ip_routing,
        "get_entitlement_context",
        lambda username=None: {"entitlements": {"static_ip": True}},
    )
    monkeypatch.setattr(
        ip_routing,
        "resolve_broker_credentials",
        lambda **kwargs: SimpleNamespace(ip_route_key="route-mumbai-1"),
    )
    monkeypatch.setattr(
        ip_routing,
        "get_ip_egress_node_by_key",
        lambda route_key: SimpleNamespace(
            route_key=route_key,
            proxy_url="http://proxy.internal:8080",
            websocket_proxy_url="ws://proxy.internal:8765",
            egress_ip="1.2.3.4",
            name="Mumbai 1",
            is_active=True,
            is_healthy=True,
        ),
    )

    context = ip_routing.resolve_ip_route(username="trader1", broker="zerodha")

    assert context is not None
    assert context.source == "saas"
    assert context.route_key == "route-mumbai-1"
    assert context.proxy_url == "http://proxy.internal:8080"
    assert context.entitlement_enabled is True


def test_resolve_ip_route_falls_back_to_env(monkeypatch):
    monkeypatch.setattr(ip_routing, "get_entitlement_context", lambda username=None: None)
    monkeypatch.setattr(
        ip_routing,
        "resolve_broker_credentials",
        lambda **kwargs: SimpleNamespace(ip_route_key=None),
    )
    monkeypatch.setenv("BROKER_HTTP_PROXY_URL", "http://fallback-proxy:9000")
    monkeypatch.setenv("BROKER_WEBSOCKET_PROXY_URL", "ws://fallback-proxy:8765")
    monkeypatch.setenv("DEFAULT_IP_ROUTE_KEY", "shared-route")
    monkeypatch.setenv("DEFAULT_EGRESS_IP", "5.6.7.8")

    context = ip_routing.resolve_ip_route(username="trader1", broker="upstox")

    assert context is not None
    assert context.source == "env"
    assert context.route_key == "shared-route"
    assert context.proxy_url == "http://fallback-proxy:9000"
    assert context.websocket_proxy_url == "ws://fallback-proxy:8765"


def test_resolve_ip_route_marks_missing_node(monkeypatch):
    monkeypatch.setattr(
        ip_routing,
        "get_entitlement_context",
        lambda username=None: {"entitlements": {"static_ip": False}},
    )
    monkeypatch.setattr(
        ip_routing,
        "resolve_broker_credentials",
        lambda **kwargs: SimpleNamespace(ip_route_key="missing-route"),
    )
    monkeypatch.setattr(ip_routing, "get_ip_egress_node_by_key", lambda route_key: None)

    context = ip_routing.resolve_ip_route(username="trader1", broker="fyers")

    assert context is not None
    assert context.source == "missing"
    assert context.route_key == "missing-route"
    assert context.is_active is False
    assert context.is_healthy is False
