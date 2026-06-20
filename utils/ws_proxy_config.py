"""Helpers for proxy-routing outbound broker WebSocket traffic."""

from __future__ import annotations

from types import SimpleNamespace
from urllib.parse import urlparse


_SUPPORTED_PROXY_SCHEMES = {"http", "https", "socks4", "socks5", "socks5h"}


def _coerce_route_context(route_context):
    if route_context is None:
        return None
    if isinstance(route_context, dict):
        return SimpleNamespace(**route_context)
    return route_context


def select_websocket_proxy_url(route_context=None, proxy_url: str | None = None) -> str | None:
    """Choose a proxy URL usable by websocket-client."""
    context = _coerce_route_context(route_context)
    candidate = proxy_url

    if candidate is None and context is not None:
        ws_candidate = getattr(context, "websocket_proxy_url", None)
        if ws_candidate:
            parsed = urlparse(ws_candidate)
            if parsed.scheme in _SUPPORTED_PROXY_SCHEMES:
                candidate = ws_candidate
        if candidate is None:
            candidate = getattr(context, "proxy_url", None)

    if not candidate:
        return None

    parsed = urlparse(candidate)
    if parsed.scheme not in _SUPPORTED_PROXY_SCHEMES:
        return None
    if not parsed.hostname or not parsed.port:
        return None
    return candidate


def build_websocket_proxy_kwargs(route_context=None, proxy_url: str | None = None) -> dict:
    """Translate route context into websocket-client proxy kwargs."""
    selected = select_websocket_proxy_url(route_context=route_context, proxy_url=proxy_url)
    if not selected:
        return {}

    parsed = urlparse(selected)
    proxy_type = "socks5h" if parsed.scheme == "socks5h" else (
        "socks5" if parsed.scheme == "socks5" else (
            "socks4" if parsed.scheme == "socks4" else "http"
        )
    )
    kwargs = {
        "http_proxy_host": parsed.hostname,
        "http_proxy_port": parsed.port,
        "proxy_type": proxy_type,
    }
    if parsed.username or parsed.password:
        kwargs["http_proxy_auth"] = (parsed.username or "", parsed.password or "")
    return kwargs


def build_requests_proxy_kwargs(route_context=None, proxy_url: str | None = None) -> dict:
    """Translate route context into requests proxy kwargs for HTTP auth calls."""
    context = _coerce_route_context(route_context)
    selected = proxy_url
    if selected is None and context is not None:
        selected = getattr(context, "proxy_url", None)
    if not selected:
        return {}

    parsed = urlparse(selected)
    if parsed.scheme not in _SUPPORTED_PROXY_SCHEMES:
        return {}
    return {"proxies": {"http": selected, "https": selected}}
