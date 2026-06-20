"""Regression tests for websocket proxy config helpers."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ws_proxy_config import (  # noqa: E402
    build_requests_proxy_kwargs,
    build_websocket_proxy_kwargs,
)


def test_build_websocket_proxy_kwargs_uses_supported_websocket_proxy_url():
    route_context = {
        "websocket_proxy_url": "http://proxy.example.com:8080",
        "proxy_url": "http://fallback.example.com:9000",
    }

    kwargs = build_websocket_proxy_kwargs(route_context=route_context)

    assert kwargs["http_proxy_host"] == "proxy.example.com"
    assert kwargs["http_proxy_port"] == 8080
    assert kwargs["proxy_type"] == "http"


def test_build_websocket_proxy_kwargs_falls_back_from_ws_scheme_to_http_proxy():
    route_context = {
        "websocket_proxy_url": "ws://relay.internal:8765",
        "proxy_url": "http://fallback.example.com:9000",
    }

    kwargs = build_websocket_proxy_kwargs(route_context=route_context)

    assert kwargs["http_proxy_host"] == "fallback.example.com"
    assert kwargs["http_proxy_port"] == 9000
    assert kwargs["proxy_type"] == "http"


def test_build_requests_proxy_kwargs_uses_http_proxy_only():
    route_context = {
        "websocket_proxy_url": "http://ignored-for-requests.example.com:8080",
        "proxy_url": "http://request-proxy.example.com:9000",
    }

    kwargs = build_requests_proxy_kwargs(route_context=route_context)

    assert kwargs == {
        "proxies": {
            "http": "http://request-proxy.example.com:9000",
            "https": "http://request-proxy.example.com:9000",
        }
    }
