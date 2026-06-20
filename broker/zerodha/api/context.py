"""Shared tenant-aware request context helpers for Zerodha APIs."""

from __future__ import annotations

from database.auth_db import get_username_by_apikey
from utils.broker_context import resolve_broker_credentials
from utils.ip_routing import resolve_ip_route


def resolve_request_context(api_key: str | None):
    username = get_username_by_apikey(api_key) if api_key else None
    route_context = resolve_ip_route(username=username, broker="zerodha")
    broker_context = resolve_broker_credentials(username=username, broker="zerodha")
    return username, route_context, broker_context
