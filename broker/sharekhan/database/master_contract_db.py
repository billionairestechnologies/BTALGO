import os

from sqlalchemy import Column, Float, Index, Integer, Sequence, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import NullPool

from utils.logging import get_logger

logger = get_logger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, poolclass=NullPool)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class SymToken(Base):
    __tablename__ = "symtoken"
    id = Column(Integer, Sequence("symtoken_id_seq"), primary_key=True)
    symbol = Column(String, nullable=False, index=True)
    brsymbol = Column(String, nullable=False, index=True)
    name = Column(String)
    exchange = Column(String, index=True)
    brexchange = Column(String, index=True)
    token = Column(String, index=True)
    expiry = Column(String)
    strike = Column(Float)
    lotsize = Column(Integer)
    instrumenttype = Column(String)
    tick_size = Column(Float)

    __table_args__ = (Index("idx_symbol_exchange", "symbol", "exchange"),)


def get_db_path():
    return DATABASE_URL


def master_contract_exists():
    try:
        return db_session.query(SymToken).first() is not None
    except Exception:
        return False


def init_db():
    logger.info("Sharekhan: Initializing Master Contract DB")
    Base.metadata.create_all(bind=engine)


def delete_symtoken_table():
    logger.info("Sharekhan: Clearing SymToken table")
    try:
        SymToken.query.delete()
        db_session.commit()
    except Exception as e:
        logger.exception(f"Sharekhan delete_symtoken_table error: {e}")
        db_session.rollback()


def bulk_insert_symtokens(records):
    """Insert a list of dicts into SymToken table, skipping duplicates."""
    if not records:
        return

    try:
        existing_tokens = {r.token for r in db_session.query(SymToken.token).all()}
        new_records = [r for r in records if r.get("token") not in existing_tokens]

        if new_records:
            db_session.bulk_insert_mappings(SymToken, new_records)
            db_session.commit()
            logger.info(f"Sharekhan: inserted {len(new_records)} symbols")
    except Exception as e:
        logger.exception(f"Sharekhan bulk_insert_symtokens error: {e}")
        db_session.rollback()


def get_symtoken(symbol, exchange):
    try:
        return db_session.query(SymToken).filter_by(symbol=symbol, exchange=exchange).first()
    except Exception:
        return None
