"""Regression tests for route-aware broker auth helper requests."""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import broker.definedge.api.auth_api as definedge_auth  # noqa: E402
import broker.dhan.api.auth_api as dhan_auth  # noqa: E402
import broker.dhan.api.order_api as dhan_order_api  # noqa: E402
import broker.iiflcapital.api.auth_api as iifl_auth  # noqa: E402
import broker.samco.api.auth_api as samco_auth  # noqa: E402
import broker.upstox.api.order_api as upstox_order_api  # noqa: E402
import broker.zerodha.api.funds as zerodha_funds  # noqa: E402
import broker.zerodha.api.margin_api as zerodha_margin  # noqa: E402
import broker.zerodha.api.order_api as zerodha_order_api  # noqa: E402


class _FakeResponse:
    def __init__(self, payload=None, status_code=200, text="ok", headers=None):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = text
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.text)


def test_dhan_generate_consent_passes_route_context(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["route_context"] = kwargs.get("route_context")
        return _FakeResponse({"status": "success", "consentAppId": "consent-1"})

    monkeypatch.setattr(dhan_auth, "post", fake_post)

    route_context = SimpleNamespace(proxy_url="http://proxy")
    consent_id, error = dhan_auth.generate_consent(
        "client123",
        broker_api_key="app123",
        broker_api_secret="secret123",
        route_context=route_context,
    )

    assert error is None
    assert consent_id == "consent-1"
    assert captured["route_context"] is route_context


def test_definedge_login_step1_passes_route_context(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["route_context"] = kwargs.get("route_context")
        return _FakeResponse({"otp_token": "otp-1", "message": "sent"})

    monkeypatch.setattr(definedge_auth, "get", fake_get)

    route_context = SimpleNamespace(proxy_url="http://proxy")
    payload = definedge_auth.login_step1("token123", "secret123", route_context=route_context)

    assert payload["otp_token"] == "otp-1"
    assert captured["route_context"] is route_context


def test_samco_generate_otp_passes_route_context(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["route_context"] = kwargs.get("route_context")
        return _FakeResponse({"status": "Success", "statusMessage": "OTP sent"})

    monkeypatch.setattr(samco_auth, "post", fake_post)

    route_context = SimpleNamespace(proxy_url="http://proxy")
    payload, error = samco_auth.generate_otp("SAMCO123", route_context=route_context)

    assert error is None
    assert payload["status"] == "Success"
    assert captured["route_context"] is route_context


def test_iifl_authenticate_broker_passes_route_context(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["route_context"] = kwargs.get("route_context")
        return _FakeResponse({"status": "ok", "userSession": "session-1"})

    monkeypatch.setattr(iifl_auth, "post", fake_post)

    route_context = SimpleNamespace(proxy_url="http://proxy")
    token, error = iifl_auth.authenticate_broker(
        "auth-code-1",
        "client-1",
        broker_api_secret="secret-1",
        route_context=route_context,
    )

    assert error is None
    assert token == "session-1"
    assert captured["route_context"] is route_context


def test_upstox_order_request_passes_route_context(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["route_context"] = kwargs.get("route_context")
        return _FakeResponse({"status": "success", "data": []})

    monkeypatch.setattr(upstox_order_api, "get", fake_get)

    route_context = SimpleNamespace(proxy_url="http://proxy")
    payload = upstox_order_api.get_api_response(
        "/v2/order/retrieve-all",
        "token-1",
        route_context=route_context,
    )

    assert payload["status"] == "success"
    assert captured["route_context"] is route_context


def test_dhan_order_request_passes_route_context(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["route_context"] = kwargs.get("route_context")
        return _FakeResponse([], text="[]")

    monkeypatch.setattr(dhan_order_api, "get", fake_get)

    route_context = SimpleNamespace(proxy_url="http://proxy")
    payload = dhan_order_api.get_api_response(
        "/v2/orders",
        "token-1",
        route_context=route_context,
    )

    assert payload == []
    assert captured["route_context"] is route_context


def test_zerodha_order_request_passes_route_context(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["route_context"] = kwargs.get("route_context")
        return _FakeResponse({"status": "success", "data": []})

    monkeypatch.setattr(zerodha_order_api, "get", fake_get)

    route_context = SimpleNamespace(proxy_url="http://proxy")
    payload = zerodha_order_api.get_api_response(
        "/orders",
        "token-1",
        route_context=route_context,
    )

    assert payload["status"] == "success"
    assert captured["route_context"] is route_context


def test_zerodha_funds_request_passes_route_context(monkeypatch):
    captured = {}

    def fake_resolve_request_context(api_key):
        return ("trader1", SimpleNamespace(proxy_url="http://proxy"), None)

    def fake_get(url, **kwargs):
        captured.setdefault("calls", []).append(kwargs.get("route_context"))
        if "user/margins" in url:
            return _FakeResponse(
                {
                    "status": "success",
                    "data": {
                        "commodity": {
                            "net": 100.0,
                            "utilised": {"debits": 10.0},
                            "available": {"collateral": 5.0},
                        },
                        "equity": {
                            "net": 200.0,
                            "utilised": {"debits": 20.0},
                            "available": {"collateral": 15.0},
                        },
                    },
                }
            )
        if "portfolio/positions" in url:
            return _FakeResponse({"status": "success", "data": {"net": []}})
        return _FakeResponse({"status": "success", "data": {}})

    monkeypatch.setattr(zerodha_funds, "resolve_request_context", fake_resolve_request_context)
    monkeypatch.setattr(zerodha_funds, "get", fake_get)

    result = zerodha_funds.get_margin_data("token-1", api_key="api-key-1")

    assert result["availablecash"] == "300.00"
    assert all(call.proxy_url == "http://proxy" for call in captured["calls"])


def test_zerodha_margin_request_passes_route_context(monkeypatch):
    captured = {}

    def fake_resolve_request_context(api_key):
        return ("trader1", SimpleNamespace(proxy_url="http://proxy"), None)

    def fake_post(url, **kwargs):
        captured["route_context"] = kwargs.get("route_context")
        response = _FakeResponse({"status": "success", "data": {"orders": []}})
        response.status = 200
        return response

    monkeypatch.setattr(zerodha_margin, "resolve_request_context", fake_resolve_request_context)
    monkeypatch.setattr(zerodha_margin, "post", fake_post)
    monkeypatch.setattr(zerodha_margin, "parse_margin_response", lambda payload: payload)
    monkeypatch.setattr(
        zerodha_margin,
        "transform_margin_positions",
        lambda positions: [{"tradingsymbol": "SBIN", "quantity": 1}],
    )

    response, payload = zerodha_margin.calculate_margin_api(
        [{"symbol": "SBIN"}],
        "token-1",
        api_key="api-key-1",
    )

    assert response.status == 200
    assert payload["status"] == "success"
    assert captured["route_context"].proxy_url == "http://proxy"
