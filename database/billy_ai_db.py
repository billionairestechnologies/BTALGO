# database/billy_ai_db.py

import os

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
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
    """A chat conversation/thread"""

    __tablename__ = "billy_conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, default="New Chat")
    provider = Column(String(50), nullable=False, default="nexos")
    model = Column(String(100), nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class BillyMessage(Base):
    """A single message in a conversation"""

    __tablename__ = "billy_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    provider = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def init_db():
    """Initialize Billy AI tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Billy AI tables initialized")


# --- CRUD Operations ---

def create_conversation(title="New Chat", provider="nexos", model=""):
    """Create a new conversation"""
    conv = BillyConversation(title=title, provider=provider, model=model)
    db_session.add(conv)
    db_session.commit()
    return conv.id


def get_conversations(limit=50):
    """Get recent conversations"""
    convs = (
        BillyConversation.query
        .order_by(BillyConversation.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": c.id,
            "title": c.title,
            "provider": c.provider,
            "model": c.model,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        }
        for c in convs
    ]


def get_conversation_messages(conversation_id):
    """Get all messages for a conversation"""
    msgs = (
        BillyMessage.query
        .filter_by(conversation_id=conversation_id)
        .order_by(BillyMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "provider": m.provider,
            "model": m.model,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in msgs
    ]


def add_message(conversation_id, role, content, provider=None, model=None):
    """Add a message to a conversation"""
    msg = BillyMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        provider=provider,
        model=model,
    )
    db_session.add(msg)
    # Update conversation timestamp
    conv = BillyConversation.query.get(conversation_id)
    if conv:
        conv.updated_at = func.now()
    db_session.commit()
    return msg.id


def update_conversation_title(conversation_id, title):
    """Update conversation title"""
    conv = BillyConversation.query.get(conversation_id)
    if conv:
        conv.title = title
        db_session.commit()
        return True
    return False


def delete_conversation(conversation_id):
    """Delete a conversation and all its messages"""
    BillyMessage.query.filter_by(conversation_id=conversation_id).delete()
    BillyConversation.query.filter_by(id=conversation_id).delete()
    db_session.commit()
    return True
