"""QuantX SaaS account APIs."""

from flask import Blueprint, jsonify, request, session

from database.saas_db import (
    BrokerAccount,
    db_session,
    get_profile_by_username,
    list_ip_egress_nodes,
    serialize_broker_account,
    serialize_ip_egress_node,
    serialize_profile,
    serialize_subscription,
    serialize_tenant,
    upsert_ip_egress_node,
    upsert_broker_account,
)
from database.user_db import find_user_by_exact_username
from utils.access_control import get_entitlement_context
from utils.ip_routing import resolve_ip_route, serialize_ip_route_context
from utils.logging import get_logger
from utils.session import check_session_validity

logger = get_logger(__name__)

saas_bp = Blueprint("saas_bp", __name__, url_prefix="/api/saas")


def _current_profile():
    return get_profile_by_username(session.get("user"))


def _current_user():
    username = session.get("user")
    return find_user_by_exact_username(username) if username else None


@saas_bp.route("/me", methods=["GET"])
@check_session_validity
def get_saas_me():
    """Return the signed-in user's SaaS workspace context."""
    profile = _current_profile()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    subscription = profile.tenant.subscriptions[0] if profile.tenant.subscriptions else None
    entitlements = get_entitlement_context(username=session.get("user"))
    return jsonify(
        {
            "status": "success",
            "tenant": serialize_tenant(profile.tenant),
            "profile": serialize_profile(profile),
            "subscription": serialize_subscription(subscription),
            "entitlements": entitlements["entitlements"] if entitlements else None,
        }
    )


@saas_bp.route("/broker-accounts", methods=["GET"])
@check_session_validity
def list_broker_accounts():
    profile = _current_profile()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    accounts = (
        BrokerAccount.query.filter_by(user_profile_id=profile.id)
        .order_by(BrokerAccount.is_default.desc(), BrokerAccount.broker.asc())
        .all()
    )
    return jsonify(
        {
            "status": "success",
            "data": [serialize_broker_account(a, include_lengths=True) for a in accounts],
        }
    )


@saas_bp.route("/broker-accounts/<int:account_id>/route", methods=["GET"])
@check_session_validity
def get_broker_account_route(account_id: int):
    profile = _current_profile()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    account = BrokerAccount.query.filter_by(id=account_id, user_profile_id=profile.id).first()
    if account is None:
        return jsonify({"status": "error", "message": "Broker account not found"}), 404

    route_context = resolve_ip_route(
        username=session.get("user"),
        broker=account.broker,
        account_id=account.id,
    )
    return jsonify(
        {
            "status": "success",
            "route": serialize_ip_route_context(route_context),
        }
    )


@saas_bp.route("/broker-accounts", methods=["POST"])
@check_session_validity
def save_broker_account():
    profile = _current_profile()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    data = request.get_json(silent=True) or {}
    try:
        account = upsert_broker_account(profile, data)
        return jsonify(
            {
                "status": "success",
                "message": "Broker account saved",
                "data": serialize_broker_account(account, include_lengths=True),
            }
        )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        db_session.rollback()
        logger.exception(f"Failed to save SaaS broker account: {e}")
        return jsonify({"status": "error", "message": "Failed to save broker account"}), 500


@saas_bp.route("/broker-accounts/<int:account_id>/default", methods=["POST"])
@check_session_validity
def set_default_broker_account(account_id: int):
    profile = _current_profile()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    account = BrokerAccount.query.filter_by(id=account_id, user_profile_id=profile.id).first()
    if account is None:
        return jsonify({"status": "error", "message": "Broker account not found"}), 404

    BrokerAccount.query.filter_by(user_profile_id=profile.id).update({"is_default": False})
    account.is_default = True
    db_session.commit()
    return jsonify({"status": "success", "data": serialize_broker_account(account)})


@saas_bp.route("/broker-accounts/<int:account_id>", methods=["DELETE"])
@check_session_validity
def delete_broker_account(account_id: int):
    profile = _current_profile()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    account = BrokerAccount.query.filter_by(id=account_id, user_profile_id=profile.id).first()
    if account is None:
        return jsonify({"status": "error", "message": "Broker account not found"}), 404

    db_session.delete(account)
    db_session.commit()
    return jsonify({"status": "success", "message": "Broker account deleted"})


@saas_bp.route("/ip-routes", methods=["GET"])
@check_session_validity
def list_ip_routes():
    profile = _current_profile()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    entitlement_context = get_entitlement_context(username=session.get("user"))
    entitlements = entitlement_context["entitlements"] if entitlement_context else {}
    user = _current_user()
    include_all = bool(user and user.is_admin)

    if include_all:
        routes = list_ip_egress_nodes(active_only=False, healthy_only=False)
    elif entitlements.get("static_ip"):
        routes = list_ip_egress_nodes(active_only=True, healthy_only=True)
    else:
        routes = []

    return jsonify(
        {
            "status": "success",
            "entitlements": entitlements,
            "routes": [serialize_ip_egress_node(route) for route in routes],
        }
    )


@saas_bp.route("/ip-routes", methods=["POST"])
@check_session_validity
def save_ip_route():
    user = _current_user()
    if user is None or not user.is_admin:
        return jsonify({"status": "error", "message": "Admin access required"}), 403

    data = request.get_json(silent=True) or {}
    try:
        route = upsert_ip_egress_node(data)
        return jsonify(
            {
                "status": "success",
                "message": "IP route saved",
                "data": serialize_ip_egress_node(route),
            }
        )
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        db_session.rollback()
        logger.exception(f"Failed to save IP route: {e}")
        return jsonify({"status": "error", "message": "Failed to save IP route"}), 500
