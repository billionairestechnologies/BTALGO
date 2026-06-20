"""SaaS tenancy, billing, and per-user broker account storage.

This module is intentionally additive. Existing single-install flows keep
using the current users/auth/api_keys tables, while QuantX SaaS features can
start resolving account context from these tables.
"""

import os
from datetime import datetime

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


def init_db():
    from database.db_init_helper import init_db_with_logging

    init_db_with_logging(Base, engine, "SaaS DB", logger)


def _slugify(value: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "tenant"


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
    account.ip_route_key = (data.get("ip_route_key") or account.ip_route_key or "").strip() or None
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
