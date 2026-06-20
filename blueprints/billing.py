"""BillionairsHQ billing endpoints backed by Razorpay."""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from database.saas_db import (
    PaymentEvent,
    Subscription,
    Tenant,
    db_session,
    get_or_create_subscription_for_tenant,
    get_profile_by_username,
    record_payment_event,
    serialize_payment_event,
    serialize_subscription,
)
from utils.logging import get_logger
from utils.razorpay import (
    create_customer,
    create_subscription,
    fetch_subscription,
    verify_webhook_signature,
)
from utils.subscriptions import get_plan_catalog, resolve_entitlements, resolve_plan_id
from utils.session import check_session_validity

logger = get_logger(__name__)

billing_bp = Blueprint("billing_bp", __name__, url_prefix="/api/saas/billing")


def _current_profile():
    return get_profile_by_username(session.get("user"))


def _current_subscription():
    profile = _current_profile()
    if profile is None:
        return None, None
    return profile, get_or_create_subscription_for_tenant(profile.tenant_id)


def _sync_subscription_from_razorpay(subscription: Subscription, payload: dict) -> Subscription:
    status = payload.get("status") or subscription.status
    customer_id = payload.get("customer_id") or subscription.razorpay_customer_id
    subscription_id = payload.get("id") or subscription.razorpay_subscription_id
    current_start = payload.get("current_start")
    current_end = payload.get("current_end")

    subscription.status = status
    subscription.razorpay_customer_id = customer_id
    subscription.razorpay_subscription_id = subscription_id
    if current_start:
        subscription.current_period_start = datetime.fromtimestamp(current_start, tz=timezone.utc)
    if current_end:
        subscription.current_period_end = datetime.fromtimestamp(current_end, tz=timezone.utc)
    subscription.updated_at = datetime.utcnow()
    db_session.commit()
    return subscription


@billing_bp.route("/summary", methods=["GET"])
@check_session_validity
def get_billing_summary():
    profile, subscription = _current_subscription()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    return jsonify(
        {
            "status": "success",
            "tenant": {
                "id": profile.tenant.id,
                "name": profile.tenant.name,
                "slug": profile.tenant.slug,
            },
            "subscription": serialize_subscription(subscription),
            "entitlements": resolve_entitlements(subscription),
            "plans": get_plan_catalog(),
        }
    )


@billing_bp.route("/plans", methods=["GET"])
@check_session_validity
def get_billing_plans():
    profile, subscription = _current_subscription()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404
    return jsonify(
        {
            "status": "success",
            "plans": get_plan_catalog(),
            "subscription": serialize_subscription(subscription),
            "entitlements": resolve_entitlements(subscription),
        }
    )


@billing_bp.route("/customer", methods=["POST"])
@check_session_validity
def ensure_billing_customer():
    profile, subscription = _current_subscription()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    if subscription.razorpay_customer_id:
        return jsonify(
            {
                "status": "success",
                "message": "Customer already provisioned",
                "customer_id": subscription.razorpay_customer_id,
                "subscription": serialize_subscription(subscription),
            }
        )

    user = profile.user_id
    data = request.get_json(silent=True) or {}
    name = data.get("name") or profile.tenant.name
    email = data.get("email") or getattr(getattr(profile, "user", None), "email", None)

    # Profile does not relationship-bind to User; resolve directly.
    if not email:
        from database.user_db import User

        user_row = User.query.filter_by(id=user).first()
        email = user_row.email if user_row else None

    if not email:
        return jsonify({"status": "error", "message": "Email address is required for billing."}), 400

    try:
        customer = create_customer(
            name=name,
            email=email,
            contact=data.get("contact") or profile.phone,
            notes={"tenant_id": str(profile.tenant_id), "username": session.get("user", "")},
        )
    except Exception as exc:
        logger.exception("Failed to create Razorpay customer")
        return jsonify({"status": "error", "message": str(exc)}), 500

    subscription.razorpay_customer_id = customer.get("id")
    db_session.commit()
    return jsonify(
        {
            "status": "success",
            "customer_id": subscription.razorpay_customer_id,
            "customer": customer,
            "subscription": serialize_subscription(subscription),
        }
    )


@billing_bp.route("/subscription", methods=["POST"])
@check_session_validity
def start_subscription_checkout():
    profile, subscription = _current_subscription()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    data = request.get_json(silent=True) or {}
    plan_code = (data.get("plan_code") or "starter").strip().lower()
    plan_id = (data.get("plan_id") or resolve_plan_id(plan_code) or "").strip()
    if not plan_id:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"No Razorpay plan configured for '{plan_code}'. Set its env mapping first.",
                }
            ),
            400,
        )

    try:
        created = create_subscription(
            plan_id=plan_id,
            total_count=int(data.get("total_count") or 12),
            quantity=int(data.get("quantity") or 1),
            customer_notify=1,
            notes={"tenant_id": str(profile.tenant_id), "plan_code": plan_code},
        )
    except Exception as exc:
        logger.exception("Failed to create Razorpay subscription")
        return jsonify({"status": "error", "message": str(exc)}), 500

    subscription.plan_code = plan_code
    subscription.razorpay_subscription_id = created.get("id")
    subscription.status = created.get("status") or "created"
    db_session.commit()

    return jsonify(
        {
            "status": "success",
            "subscription": serialize_subscription(subscription),
            "entitlements": resolve_entitlements(subscription),
            "razorpay": created,
        }
    )


@billing_bp.route("/subscription/refresh", methods=["POST"])
@check_session_validity
def refresh_subscription():
    profile, subscription = _current_subscription()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404
    if not subscription.razorpay_subscription_id:
        return jsonify({"status": "error", "message": "No Razorpay subscription linked yet."}), 400

    try:
        remote = fetch_subscription(subscription.razorpay_subscription_id)
        subscription = _sync_subscription_from_razorpay(subscription, remote)
    except Exception as exc:
        logger.exception("Failed to refresh Razorpay subscription")
        return jsonify({"status": "error", "message": str(exc)}), 500

    return jsonify(
        {
            "status": "success",
            "subscription": serialize_subscription(subscription),
            "entitlements": resolve_entitlements(subscription),
        }
    )


@billing_bp.route("/events", methods=["GET"])
@check_session_validity
def list_billing_events():
    profile, _subscription = _current_subscription()
    if profile is None:
        return jsonify({"status": "error", "message": "SaaS profile not found"}), 404

    events = (
        PaymentEvent.query.filter_by(tenant_id=profile.tenant_id)
        .order_by(PaymentEvent.created_at.desc())
        .limit(25)
        .all()
    )
    return jsonify({"status": "success", "events": [serialize_payment_event(event) for event in events]})


@billing_bp.route("/webhook", methods=["POST"])
def razorpay_webhook():
    raw_body = request.get_data(cache=False)
    signature = request.headers.get("X-Razorpay-Signature")
    if not verify_webhook_signature(raw_body, signature):
        logger.warning("Rejected Razorpay webhook due to invalid signature")
        return jsonify({"status": "error", "message": "Invalid signature"}), 401

    payload = request.get_json(silent=True) or {}
    event_type = payload.get("event", "unknown")
    subscription_entity = (
        payload.get("payload", {})
        .get("subscription", {})
        .get("entity", {})
    )
    payment_entity = (
        payload.get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )
    subscription_id = subscription_entity.get("id") or payment_entity.get("subscription_id")
    tenant = None
    subscription = None
    if subscription_id:
        subscription = Subscription.query.filter_by(razorpay_subscription_id=subscription_id).first()
        if subscription:
            tenant = Tenant.query.filter_by(id=subscription.tenant_id).first()

    record_payment_event(
        tenant_id=tenant.id if tenant else None,
        event_type=event_type,
        payload_json=raw_body.decode("utf-8", errors="replace"),
        signature=signature,
        provider_event_id=payment_entity.get("id") or subscription_entity.get("id"),
        provider_payment_id=payment_entity.get("id"),
        provider_subscription_id=subscription_id,
        status=subscription_entity.get("status") or payment_entity.get("status") or "received",
    )

    if subscription and subscription_entity:
        _sync_subscription_from_razorpay(subscription, subscription_entity)

    return jsonify({"status": "success"})
