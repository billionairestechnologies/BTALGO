"""Static-IP route resolution helpers for BillionairsHQ."""

from __future__ import annotations

import os
from dataclasses import dataclass

from database.saas_db import get_ip_egress_node_by_key
from utils.access_control import get_entitlement_context
from utils.broker_context import resolve_broker_credentials


@dataclass(frozen=True)
class IpRouteContext:
    source: str
    route_key: str | None
    proxy_url: str | None
    websocket_proxy_url: str | None
    egress_ip: str | None
    node_name: str | None
    entitlement_enabled: bool
    is_active: bool = True
    is_healthy: bool = True

    def as_httpx_kwargs(self) -> dict:
        return {"proxy": self.proxy_url} if self.proxy_url else {}

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "route_key": self.route_key,
            "proxy_url": self.proxy_url,
            "websocket_proxy_url": self.websocket_proxy_url,
            "egress_ip": self.egress_ip,
            "node_name": self.node_name,
            "entitlement_enabled": self.entitlement_enabled,
            "is_active": self.is_active,
            "is_healthy": self.is_healthy,
        }


def _env_route_context() -> IpRouteContext | None:
    proxy_url = (os.getenv("BROKER_HTTP_PROXY_URL") or os.getenv("HTTP_PROXY_URL") or "").strip() or None
    websocket_proxy_url = (
        os.getenv("BROKER_WEBSOCKET_PROXY_URL") or os.getenv("WEBSOCKET_PROXY_URL") or ""
    ).strip() or None
    route_key = (os.getenv("DEFAULT_IP_ROUTE_KEY") or "").strip() or None
    egress_ip = (os.getenv("DEFAULT_EGRESS_IP") or "").strip() or None
    if not proxy_url and not websocket_proxy_url and not route_key and not egress_ip:
        return None
    return IpRouteContext(
        source="env",
        route_key=route_key,
        proxy_url=proxy_url,
        websocket_proxy_url=websocket_proxy_url,
        egress_ip=egress_ip,
        node_name="Environment default route",
        entitlement_enabled=True,
    )


def resolve_ip_route(
    *,
    username: str | None = None,
    broker: str | None = None,
    account_id: int | None = None,
    ip_route_key: str | None = None,
) -> IpRouteContext | None:
    context = get_entitlement_context(username=username)
    entitlement_enabled = bool(context and context["entitlements"].get("static_ip"))

    route_key = (ip_route_key or "").strip() or None
    if route_key is None:
        broker_context = resolve_broker_credentials(
            username=username,
            broker=broker,
            account_id=account_id,
        )
        route_key = broker_context.ip_route_key

    if route_key:
        node = get_ip_egress_node_by_key(route_key)
        if node is None:
            return IpRouteContext(
                source="missing",
                route_key=route_key,
                proxy_url=None,
                websocket_proxy_url=None,
                egress_ip=None,
                node_name=None,
                entitlement_enabled=entitlement_enabled,
                is_active=False,
                is_healthy=False,
            )
        return IpRouteContext(
            source="saas",
            route_key=node.route_key,
            proxy_url=node.proxy_url,
            websocket_proxy_url=node.websocket_proxy_url,
            egress_ip=node.egress_ip,
            node_name=node.name,
            entitlement_enabled=entitlement_enabled,
            is_active=bool(node.is_active),
            is_healthy=bool(node.is_healthy),
        )

    return _env_route_context()


def serialize_ip_route_context(context: IpRouteContext | None) -> dict | None:
    if context is None:
        return None
    return context.as_dict()
