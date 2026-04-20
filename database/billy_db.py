"""
Billy AI Agent - Database models and CRUD operations.
Stores chat history and AI provider settings.
"""

import json
import os

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import func

from utils.logging import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10)

db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class BillyConversation(Base):
    __tablename__ = "billy_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(20), nullable=False)        # "user" | "assistant" | "tool"
    content = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True)         # JSON string of tool call info
    tool_name = Column(String(100), nullable=True)   # name of tool called
    created_at = Column(DateTime, server_default=func.now())


class BillySettings(Base):
    __tablename__ = "billy_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider = Column(String(50), default="anthropic")
    model = Column(String(100), default="claude-sonnet-4-6")
    api_key = Column(Text, nullable=True)            # stored as-is (env-level security)
    base_url = Column(String(500), nullable=True)    # for Ollama / custom endpoints
    allow_orders = Column(Boolean, default=False)    # allow Billy to place real orders
    allow_strategies = Column(Boolean, default=True) # allow Billy to create strategies
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


def init_billy_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Billy DB initialized")

    # Insert default settings row if missing
    try:
        if not db_session.query(BillySettings).first():
            db_session.add(BillySettings())
            db_session.commit()
    except Exception:
        db_session.rollback()
    finally:
        db_session.remove()


# ── Conversation CRUD ──────────────────────────────────────────────────────────

def save_message(role: str, content: str, tool_calls=None, tool_name: str = None):
    try:
        msg = BillyConversation(
            role=role,
            content=content,
            tool_calls=json.dumps(tool_calls) if tool_calls else None,
            tool_name=tool_name,
        )
        db_session.add(msg)
        db_session.commit()
        return msg.id
    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error saving Billy message: {e}")
    finally:
        db_session.remove()


def get_history(limit: int = 50) -> list[dict]:
    try:
        rows = (
            db_session.query(BillyConversation)
            .order_by(BillyConversation.created_at.desc())
            .limit(limit)
            .all()
        )
        rows.reverse()
        return [
            {
                "id": r.id,
                "role": r.role,
                "content": r.content,
                "tool_calls": json.loads(r.tool_calls) if r.tool_calls else None,
                "tool_name": r.tool_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    except Exception as e:
        logger.exception(f"Error fetching Billy history: {e}")
        return []
    finally:
        db_session.remove()


def clear_history():
    try:
        db_session.query(BillyConversation).delete()
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error clearing Billy history: {e}")
    finally:
        db_session.remove()


# ── Settings CRUD ──────────────────────────────────────────────────────────────

def get_settings() -> dict:
    try:
        s = db_session.query(BillySettings).first()
        if not s:
            return {
                "provider": "anthropic",
                "model": "claude-sonnet-4-6",
                "api_key": "",
                "base_url": "",
                "allow_orders": False,
                "allow_strategies": True,
            }
        return {
            "provider": s.provider,
            "model": s.model,
            "api_key": s.api_key or "",
            "base_url": s.base_url or "",
            "allow_orders": s.allow_orders,
            "allow_strategies": s.allow_strategies,
        }
    except Exception as e:
        logger.exception(f"Error fetching Billy settings: {e}")
        return {}
    finally:
        db_session.remove()


def save_settings(provider: str, model: str, api_key: str = "", base_url: str = "",
                  allow_orders: bool = False, allow_strategies: bool = True):
    try:
        s = db_session.query(BillySettings).first()
        if not s:
            s = BillySettings()
            db_session.add(s)
        s.provider = provider
        s.model = model
        s.api_key = api_key
        s.base_url = base_url
        s.allow_orders = allow_orders
        s.allow_strategies = allow_strategies
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        logger.exception(f"Error saving Billy settings: {e}")
    finally:
        db_session.remove()
