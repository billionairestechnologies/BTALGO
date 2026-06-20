"""SaaS tenancy, billing, per-user broker accounts, and signup OTP state.

This module is intentionally additive. Existing single-install flows keep
using the current users/auth/api_keys tables, while QuantX SaaS features can
start resolving account context from these tables.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, scoped_session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import func

from database.auth_db import encrypt_token, safe_decrypt_token
from utils.logging import get_logger

logger = get_logger(__name__)
ph = PasswordHasher()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL, echo=False, poolclass=NullPool, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        DATABASE_URL, echo=False, pool_size=50, max_overflow=100, pool_timeout=10
    )

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class Tenant(Base):
    """A customer workspace / whitelabel install inside the shared platform."""

    __tablename__ = "saas_tenants"

    id = Column(Integer, primary_key=True)
    slug = Column(String(80), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    owner_user_id = Column(Integer, nullable=True)
    product_name = Column(String(120), nullable=False, default="BillionairsHQ")
    company_name = Column(String(120), nullable=False, default="Billionaires Technologies")
    custom_domain = Column(String(255), nullable=True)
    status = Column(String(30), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    members = relationship("UserProfile", back_populates="tenant")
    subscriptions = relationship("Subscription", back_populates="tenant")

    __table_args__ = (
        Index("idx_saas_tenants_status", "status"),
        Index("idx_saas_tenants_owner_user_id", "owner_user_id"),
    )


class UserProfile(Base):
    """SaaS profile linked to the existing users table by user id."""

    __tablename__ = "saas_user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, unique=True)
    tenant_id = Column(Integer, ForeignKey("saas_tenants.id"), nullable=False)
    role = Column(String(30), nullable=False, default="owner")
    status = Column(String(30), nullable=False, default="active")
    phone = Column(String(30), nullable=True)
    mpin_hash = Column(Text, nullable=True)
    otp_enabled = Column(Boolean, nullable=False, default=False)
    mpin_enabled = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="members")
    broker_accounts = relationship("BrokerAccount", back_populates="profile")

    __table_args__ = (
        Index("idx_saas_user_profiles_tenant_id", "tenant_id"),
        Index("idx_saas_user_profiles_status", "status"),
    )

    def set_mpin(self, mpin: str) -> None:
        normalized = "".join(ch for ch in (mpin or "") if ch.isdigit())
        if len(normalized) not in {4, 6}:
            raise ValueError("MPIN must be exactly 4 or 6 digits.")
        pepper = os.getenv("API_KEY_PEPPER", "")
        self.mpin_hash = ph.hash(normalized + pepper)
        self.mpin_enabled = True

    def verify_mpin(self, mpin: str) -> bool:
        if not self.mpin_hash:
            return False
        normalized = "".join(ch for ch in (mpin or "") if ch.isdigit())
        pepper = os.getenv("API_KEY_PEPPER", "")
        try:
            ph.verify(self.mpin_hash, normalized + pepper)
            if ph.check_needs_rehash(self.mpin_hash):
                self.set_mpin(normalized)
                db_session.commit()
            return True
        except VerifyMismatchError:
            return False

    def clear_mpin(self) -> None:
        self.mpin_hash = None
        self.mpin_enabled = False


class BrokerAccount(Base):
    """Encrypted per-user broker app credentials and routing metadata."""

    __tablename__ = "saas_broker_accounts"

    id = Column(Integer, primary_key=True)
    user_profile_id = Column(Integer, ForeignKey("saas_user_profiles.id"), nullable=False)
    broker = Column(String(40), nullable=False)
    label = Column(String(120), nullable=False, default="Primary")
    client_id = Column(String(255), nullable=True)
    api_key_encrypted = Column(Text, nullable=True)
    api_secret_encrypted = Column(Text, nullable=True)
    market_api_key_encrypted = Column(Text, nullable=True)
    market_api_secret_encrypted = Column(Text, nullable=True)
    redirect_url = Column(String(500), nullable=True)
    ip_route_key = Column(String(120), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    profile = relationship("UserProfile", back_populates="broker_accounts")

    __table_args__ = (
        UniqueConstraint("user_profile_id", "broker", "label", name="uq_saas_broker_account"),
        Index("idx_saas_broker_accounts_profile", "user_profile_id"),
        Index("idx_saas_broker_accounts_broker", "broker"),
        Index("idx_saas_broker_accounts_default", "user_profile_id", "is_default"),
    )

    def set_secret(self, field_name: str, value: str | None) -> None:
        setattr(self, field_name, encrypt_token(value) if value else None)

    def reveal_secret(self, field_name: str) -> str | None:
        return safe_decrypt_token(getattr(self, field_name))


class IpEgressNode(Base):
    """Static egress/proxy node inventory for tenant broker traffic."""

    __tablename__ = "saas_ip_egress_nodes"

    id = Column(Integer, primary_key=True)
    route_key = Column(String(120), unique=True, nullable=False)
    name = Column(String(120), nullable=False)
    region = Column(String(80), nullable=True)
    provider = Column(String(80), nullable=True)
    egress_ip = Column(String(80), nullable=True)
    proxy_url = Column(String(500), nullable=True)
    websocket_proxy_url = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_healthy = Column(Boolean, nullable=False, default=True)
    last_health_check_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_saas_ip_egress_nodes_active", "is_active"),
        Index("idx_saas_ip_egress_nodes_health", "is_healthy"),
    )


class Subscription(Base):
    """Billing state for a tenant. Razorpay IDs land here in the next slice."""

    __tablename__ = "saas_subscriptions"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("saas_tenants.id"), nullable=False)
    plan_code = Column(String(80), nullable=False, default="free")
    status = Column(String(30), nullable=False, default="trialing")
    razorpay_customer_id = Column(String(120), nullable=True)
    razorpay_subscription_id = Column(String(120), nullable=True)
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    tenant = relationship("Tenant", back_populates="subscriptions")

    __table_args__ = (
        Index("idx_saas_subscriptions_tenant", "tenant_id"),
        Index("idx_saas_subscriptions_status", "status"),
        Index("idx_saas_subscriptions_razorpay_customer", "razorpay_customer_id"),
    )


class PaymentEvent(Base):
    """Persist billing events and webhook payloads for reconciliation."""

    __tablename__ = "saas_payment_events"

    id = Column(Integer, primary_key=True)
    tenant_id = Column(Integer, ForeignKey("saas_tenants.id"), nullable=True)
    provider = Column(String(30), nullable=False, default="razorpay")
    event_type = Column(String(120), nullable=False)
    provider_event_id = Column(String(120), nullable=True)
    provider_payment_id = Column(String(120), nullable=True)
    provider_subscription_id = Column(String(120), nullable=True)
    status = Column(String(30), nullable=False, default="received")
    payload_json = Column(Text, nullable=False)
    signature = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_saas_payment_events_tenant", "tenant_id"),
        Index("idx_saas_payment_events_provider", "provider"),
        Index("idx_saas_payment_events_type", "event_type"),
        Index("idx_saas_payment_events_subscription", "provider_subscription_id"),
    )


class EmailOtpChallenge(Base):
    """Pending email OTP verification for registration and future auth flows."""

    __tablename__ = "saas_email_otp_challenges"

    id = Column(Integer, primary_key=True)
    purpose = Column(String(40), nullable=False, default="registration")
    email = Column(String(255), nullable=False)
    username = Column(String(80), nullable=False)
    password_encrypted = Column(Text, nullable=False)
    otp_hash = Column(String(64), nullable=False)
    attempts = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_sent_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_saas_email_otp_email", "email"),
        Index("idx_saas_email_otp_purpose", "purpose"),
        Index("idx_saas_email_otp_consumed", "consumed_at"),
    )


def init_db():
    from database.db_init_helper import init_db_with_logging

    init_db_with_logging(Base, engine, "SaaS DB", logger)


def _slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "tenant"


def _hash_otp(otp: str) -> str:
    pepper = os.getenv("API_KEY_PEPPER", "")
    return hashlib.sha256(f"{otp}:{pepper}".encode("utf-8")).hexdigest()


def _active_challenge(email: str, purpose: str = "registration") -> EmailOtpChallenge | None:
    return (
        EmailOtpChallenge.query.filter_by(email=email.lower().strip(), purpose=purpose, consumed_at=None)
        .order_by(EmailOtpChallenge.created_at.desc())
        .first()
    )


def create_or_refresh_email_otp(
    *,
    email: str,
    username: str,
    password: str,
    purpose: str = "registration",
    expiry_minutes: int = 10,
) -> tuple[EmailOtpChallenge, str]:
    """Create or refresh a pending OTP challenge and return the raw OTP once."""
    from database.auth_db import encrypt_token

    normalized_email = email.lower().strip()
    normalized_username = username.strip()

    challenge = _active_challenge(normalized_email, purpose=purpose)
    if challenge is None:
        challenge = EmailOtpChallenge(
            purpose=purpose,
            email=normalized_email,
            username=normalized_username,
            password_encrypted=encrypt_token(password),
            otp_hash="",
        )
        db_session.add(challenge)
    else:
        challenge.username = normalized_username
        challenge.password_encrypted = encrypt_token(password)
        challenge.attempts = 0
        challenge.consumed_at = None

    otp_code = f"{secrets.randbelow(1000000):06d}"
    challenge.otp_hash = _hash_otp(otp_code)
    challenge.last_sent_at = datetime.utcnow()
    challenge.expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)
    challenge.updated_at = datetime.utcnow()
    db_session.commit()
    return challenge, otp_code


def get_email_otp_status(email: str, purpose: str = "registration") -> dict | None:
    challenge = _active_challenge(email, purpose=purpose)
    if challenge is None:
        return None
    return {
        "email": challenge.email,
        "username": challenge.username,
        "expires_at": challenge.expires_at.isoformat() if challenge.expires_at else None,
        "last_sent_at": challenge.last_sent_at.isoformat() if challenge.last_sent_at else None,
        "attempts": challenge.attempts,
    }


def resend_email_otp(
    email: str,
    *,
    purpose: str = "registration",
    expiry_minutes: int = 10,
) -> tuple[EmailOtpChallenge, str]:
    challenge = _active_challenge(email, purpose=purpose)
    if challenge is None:
        raise ValueError("No pending verification found for this email.")

    plaintext_password = safe_decrypt_token(challenge.password_encrypted)
    if not plaintext_password:
        raise ValueError("Pending verification is invalid. Please start registration again.")

    return create_or_refresh_email_otp(
        email=challenge.email,
        username=challenge.username,
        password=plaintext_password,
        purpose=purpose,
        expiry_minutes=expiry_minutes,
    )


def verify_email_otp(
    email: str,
    otp_code: str,
    *,
    purpose: str = "registration",
    max_attempts: int = 5,
) -> dict:
    """Verify a pending OTP challenge and return the stored registration payload."""
    from database.auth_db import safe_decrypt_token

    challenge = _active_challenge(email, purpose=purpose)
    if challenge is None:
        raise ValueError("No pending verification found for this email.")

    now = datetime.utcnow()
    if challenge.expires_at and now > challenge.expires_at.replace(tzinfo=None):
        db_session.delete(challenge)
        db_session.commit()
        raise ValueError("Verification code expired. Please request a new code.")

    if challenge.attempts >= max_attempts:
        db_session.delete(challenge)
        db_session.commit()
        raise ValueError("Too many invalid attempts. Please request a new code.")

    if challenge.otp_hash != _hash_otp(otp_code.strip()):
        challenge.attempts += 1
        challenge.updated_at = now
        db_session.commit()
        remaining = max_attempts - challenge.attempts
        if remaining <= 0:
            db_session.delete(challenge)
            db_session.commit()
            raise ValueError("Too many invalid attempts. Please request a new code.")
        raise ValueError(f"Invalid verification code. {remaining} attempt(s) remaining.")

    challenge.consumed_at = now
    challenge.updated_at = now
    password = safe_decrypt_token(challenge.password_encrypted)
    if not password:
        db_session.commit()
        raise ValueError("Pending verification is invalid. Please start registration again.")
    payload = {
        "email": challenge.email,
        "username": challenge.username,
        "password": password,
    }
    db_session.commit()
    return payload


def ensure_profile_for_user(user) -> UserProfile:
    """Create a SaaS tenant/profile for an existing auth user if missing."""
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    if profile:
        return profile

    base_slug = _slugify(getattr(user, "username", "") or f"user-{user.id}")
    slug = base_slug
    suffix = 2
    while Tenant.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    tenant = Tenant(
        slug=slug,
        name=f"{user.username}'s Workspace",
        owner_user_id=user.id,
    )
    db_session.add(tenant)
    db_session.flush()

    profile = UserProfile(
        user_id=user.id,
        tenant_id=tenant.id,
        role="owner" if getattr(user, "is_admin", False) else "member",
        status="active",
    )
    db_session.add(profile)
    db_session.add(Subscription(tenant_id=tenant.id, plan_code="free", status="trialing"))
    db_session.commit()
    return profile


def get_profile_by_username(username: str) -> UserProfile | None:
    if not username:
        return None
    from database.user_db import find_user_by_exact_username

    user = find_user_by_exact_username(username)
    if not user:
        return None
    return ensure_profile_for_user(user)


def serialize_tenant(tenant: Tenant) -> dict:
    return {
        "id": tenant.id,
        "slug": tenant.slug,
        "name": tenant.name,
        "product_name": tenant.product_name,
        "company_name": tenant.company_name,
        "custom_domain": tenant.custom_domain,
        "status": tenant.status,
        "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
    }


def serialize_profile(profile: UserProfile) -> dict:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "tenant_id": profile.tenant_id,
        "role": profile.role,
        "status": profile.status,
        "phone": profile.phone,
        "otp_enabled": bool(profile.otp_enabled),
        "mpin_enabled": bool(profile.mpin_enabled),
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
    }


def serialize_subscription(subscription: Subscription | None) -> dict:
    return {
        "plan_code": subscription.plan_code if subscription else "free",
        "status": subscription.status if subscription else "trialing",
        "razorpay_customer_id": subscription.razorpay_customer_id if subscription else None,
        "razorpay_subscription_id": subscription.razorpay_subscription_id if subscription else None,
        "current_period_start": (
            subscription.current_period_start.isoformat()
            if subscription and subscription.current_period_start
            else None
        ),
        "current_period_end": (
            subscription.current_period_end.isoformat()
            if subscription and subscription.current_period_end
            else None
        ),
    }


def serialize_payment_event(event: PaymentEvent) -> dict:
    return {
        "id": event.id,
        "provider": event.provider,
        "event_type": event.event_type,
        "provider_event_id": event.provider_event_id,
        "provider_payment_id": event.provider_payment_id,
        "provider_subscription_id": event.provider_subscription_id,
        "status": event.status,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


def serialize_ip_egress_node(node: IpEgressNode) -> dict:
    return {
        "id": node.id,
        "route_key": node.route_key,
        "name": node.name,
        "region": node.region,
        "provider": node.provider,
        "egress_ip": node.egress_ip,
        "proxy_url": node.proxy_url,
        "websocket_proxy_url": node.websocket_proxy_url,
        "notes": node.notes,
        "is_active": bool(node.is_active),
        "is_healthy": bool(node.is_healthy),
        "last_health_check_at": (
            node.last_health_check_at.isoformat() if node.last_health_check_at else None
        ),
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "updated_at": node.updated_at.isoformat() if node.updated_at else None,
    }


def _mask(value: str | None, show_chars: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= show_chars:
        return "*" * 8
    return value[:show_chars] + "*" * 8


def serialize_broker_account(account: BrokerAccount, include_lengths: bool = False) -> dict:
    api_key = account.reveal_secret("api_key_encrypted")
    api_secret = account.reveal_secret("api_secret_encrypted")
    market_api_key = account.reveal_secret("market_api_key_encrypted")
    market_api_secret = account.reveal_secret("market_api_secret_encrypted")
    payload = {
        "id": account.id,
        "broker": account.broker,
        "label": account.label,
        "client_id": account.client_id,
        "api_key": _mask(api_key, 6),
        "api_secret": _mask(api_secret, 4),
        "market_api_key": _mask(market_api_key, 6),
        "market_api_secret": _mask(market_api_secret, 4),
        "redirect_url": account.redirect_url,
        "ip_route_key": account.ip_route_key,
        "is_default": bool(account.is_default),
        "is_active": bool(account.is_active),
        "created_at": account.created_at.isoformat() if account.created_at else None,
        "updated_at": account.updated_at.isoformat() if account.updated_at else None,
    }
    if include_lengths:
        payload.update(
            {
                "api_key_raw_length": len(api_key or ""),
                "api_secret_raw_length": len(api_secret or ""),
                "market_api_key_raw_length": len(market_api_key or ""),
                "market_api_secret_raw_length": len(market_api_secret or ""),
            }
        )
    return payload


def get_ip_egress_node_by_key(route_key: str | None) -> IpEgressNode | None:
    normalized = (route_key or "").strip()
    if not normalized:
        return None
    return IpEgressNode.query.filter_by(route_key=normalized).first()


def list_ip_egress_nodes(*, active_only: bool = False, healthy_only: bool = False) -> list[IpEgressNode]:
    query = IpEgressNode.query
    if active_only:
        query = query.filter_by(is_active=True)
    if healthy_only:
        query = query.filter_by(is_healthy=True)
    return query.order_by(IpEgressNode.name.asc(), IpEgressNode.route_key.asc()).all()


def upsert_ip_egress_node(data: dict) -> IpEgressNode:
    route_key = (data.get("route_key") or "").strip()
    name = (data.get("name") or "").strip()
    if not route_key:
        raise ValueError("route_key is required")
    if not name:
        raise ValueError("name is required")

    node = IpEgressNode.query.filter_by(route_key=route_key).first()
    if node is None:
        node = IpEgressNode(route_key=route_key, name=name)
        db_session.add(node)

    node.name = name
    node.region = (data.get("region") or "").strip() or None
    node.provider = (data.get("provider") or "").strip() or None
    node.egress_ip = (data.get("egress_ip") or "").strip() or None
    node.proxy_url = (data.get("proxy_url") or "").strip() or None
    node.websocket_proxy_url = (data.get("websocket_proxy_url") or "").strip() or None
    node.notes = (data.get("notes") or "").strip() or None
    node.is_active = bool(data.get("is_active", True))
    node.is_healthy = bool(data.get("is_healthy", True))
    if data.get("last_health_check_at"):
        node.last_health_check_at = data.get("last_health_check_at")
    node.updated_at = datetime.utcnow()
    db_session.commit()
    return node


def upsert_broker_account(profile: UserProfile, data: dict) -> BrokerAccount:
    broker = (data.get("broker") or "").strip().lower()
    label = (data.get("label") or "Primary").strip() or "Primary"
    if not broker:
        raise ValueError("broker is required")

    account = (
        BrokerAccount.query.filter_by(user_profile_id=profile.id, broker=broker, label=label)
        .first()
    )
    if account is None:
        account = BrokerAccount(user_profile_id=profile.id, broker=broker, label=label)
        db_session.add(account)

    account.client_id = (data.get("client_id") or account.client_id or "").strip() or None
    account.redirect_url = (data.get("redirect_url") or account.redirect_url or "").strip() or None
    route_key = (data.get("ip_route_key") or account.ip_route_key or "").strip() or None
    if route_key:
        subscription = get_or_create_subscription_for_tenant(profile.tenant_id)
        from utils.subscriptions import resolve_entitlements

        entitlements = resolve_entitlements(subscription)
        if not entitlements.get("static_ip"):
            raise ValueError(
                "Static IP routing requires a BillionairsHQ plan with static IP entitlement."
            )
        if get_ip_egress_node_by_key(route_key) is None:
            raise ValueError(f"Unknown IP route '{route_key}'.")
    account.ip_route_key = route_key
    account.is_active = bool(data.get("is_active", True))

    if data.get("api_key"):
        account.set_secret("api_key_encrypted", data["api_key"].strip())
    if data.get("api_secret"):
        account.set_secret("api_secret_encrypted", data["api_secret"].strip())
    if data.get("market_api_key"):
        account.set_secret("market_api_key_encrypted", data["market_api_key"].strip())
    if data.get("market_api_secret"):
        account.set_secret("market_api_secret_encrypted", data["market_api_secret"].strip())

    make_default = bool(data.get("is_default", False))
    if make_default:
        BrokerAccount.query.filter_by(user_profile_id=profile.id).update({"is_default": False})
        account.is_default = True
    elif BrokerAccount.query.filter_by(user_profile_id=profile.id, is_default=True).count() == 0:
        account.is_default = True

    account.updated_at = datetime.utcnow()
    db_session.commit()
    return account


def get_or_create_subscription_for_tenant(tenant_id: int) -> Subscription:
    subscription = Subscription.query.filter_by(tenant_id=tenant_id).first()
    if subscription:
        return subscription

    subscription = Subscription(tenant_id=tenant_id, plan_code="free", status="trialing")
    db_session.add(subscription)
    db_session.commit()
    return subscription


def record_payment_event(
    *,
    tenant_id: int | None,
    event_type: str,
    payload_json: str,
    signature: str | None = None,
    provider_event_id: str | None = None,
    provider_payment_id: str | None = None,
    provider_subscription_id: str | None = None,
    status: str = "received",
) -> PaymentEvent:
    event = PaymentEvent(
        tenant_id=tenant_id,
        event_type=event_type,
        payload_json=payload_json,
        signature=signature,
        provider_event_id=provider_event_id,
        provider_payment_id=provider_payment_id,
        provider_subscription_id=provider_subscription_id,
        status=status,
    )
    db_session.add(event)
    db_session.commit()
    return event
