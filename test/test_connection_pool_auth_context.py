"""Regression tests for pooled websocket auth-context reuse."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from websocket_proxy.connection_manager import ConnectionPool  # noqa: E402


class _DummyAdapter:
    created = []

    def __init__(self):
        self.initialized_with = None
        self.connected = False
        _DummyAdapter.created.append(self)

    def initialize(self, broker_name, user_id, auth_data=None):
        self.initialized_with = {
            "broker_name": broker_name,
            "user_id": user_id,
            "auth_data": auth_data,
        }
        return {"status": "success"}

    def connect(self):
        self.connected = True
        return {"status": "success"}

    def disconnect(self):
        self.connected = False


def test_connection_pool_reuses_auth_data_for_new_adapters(monkeypatch):
    monkeypatch.setattr(
        "websocket_proxy.connection_manager.SharedZmqPublisher.bind",
        lambda self, port=None: 5555,
    )
    _DummyAdapter.created.clear()

    pool = ConnectionPool(
        adapter_class=_DummyAdapter,
        broker_name="upstox",
        user_id="trader1",
        max_symbols_per_connection=1,
        max_connections=2,
    )
    auth_data = {"api_key": "tenant-app", "route_context": {"proxy_url": "http://proxy"}}

    result = pool.initialize(auth_data=auth_data)

    assert result["success"] is True
    assert pool.auth_data == auth_data
    assert _DummyAdapter.created[0].initialized_with["auth_data"] == auth_data

    pool.adapter_symbol_counts[0] = 1
    _, adapter = pool._get_adapter_with_capacity()

    assert adapter.initialized_with["auth_data"] == auth_data
