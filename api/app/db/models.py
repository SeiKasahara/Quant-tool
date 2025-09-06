from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Text, JSON,
    ForeignKey, UniqueConstraint, Index, Boolean, DECIMAL
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from datetime import datetime

from app.db.base import Base

class Company(Base):
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(DECIMAL(20, 2))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    tickers = relationship("Ticker", back_populates="company")

class Ticker(Base):
    __tablename__ = "tickers"
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), unique=True, nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    exchange = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    company = relationship("Company", back_populates="tickers")
    signals = relationship("Signal", back_populates="ticker")
    prices = relationship("Price", back_populates="ticker")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True)
    source = Column(String(100), nullable=False, index=True)
    url = Column(Text, nullable=False)
    title = Column(Text)
    published_at = Column(DateTime, nullable=False, index=True)
    fetched_at = Column(DateTime, server_default=func.now())
    raw_text = Column(Text)
    html_snapshot_path = Column(Text)
    content_hash = Column(String(64), unique=True, nullable=False, index=True)
    lang = Column(String(10), default="en")
    embedding = Column(Vector(768))
    sentiment = Column(String(20))
    sentiment_score = Column(Float)
    meta = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    
    entities = relationship("DocumentEntity", back_populates="document")
    events = relationship("Event", back_populates="document")
    
    __table_args__ = (
        Index('idx_documents_published_desc', published_at.desc()),
    )

class Entity(Base):
    __tablename__ = "entities"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    entity_type = Column(String(50))
    ticker_id = Column(Integer, ForeignKey("tickers.id"))
    meta = Column(JSON, default={})
    
    ticker = relationship("Ticker")
    document_entities = relationship("DocumentEntity", back_populates="entity")

class DocumentEntity(Base):
    __tablename__ = "document_entities"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    entity_id = Column(Integer, ForeignKey("entities.id"), nullable=False)
    mentions = Column(Integer, default=1)
    relevance_score = Column(Float)
    
    document = relationship("Document", back_populates="entities")
    entity = relationship("Entity", back_populates="document_entities")
    
    __table_args__ = (
        UniqueConstraint('document_id', 'entity_id'),
    )

class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    event_time = Column(DateTime, nullable=False)
    event_type = Column(String(50), nullable=False)
    headline = Column(Text)
    confidence_extraction = Column(Float)
    affected_ticker = Column(String(20))
    payload = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    
    document = relationship("Document", back_populates="events")
    
    __table_args__ = (
        Index('idx_events_ticker_time', affected_ticker, event_time.desc()),
    )

class Signal(Base):
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    signal_time = Column(DateTime, nullable=False)
    base_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    direction = Column(String(10))  # 'up', 'down', 'neutral'
    label = Column(String(100))
    decay_seconds = Column(Integer, default=86400)
    meta = Column(JSON, default={})
    created_at = Column(DateTime, server_default=func.now())
    
    ticker = relationship("Ticker", back_populates="signals")
    evidence = relationship("SignalEvidence", back_populates="signal")
    
    __table_args__ = (
        Index('idx_signals_ticker_time', ticker_id, signal_time.desc()),
    )

class SignalEvidence(Base):
    __tablename__ = "signal_evidence"
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    kind = Column(String(50), nullable=False)  # 'document', 'event', 'metric'
    ref_id = Column(Integer, nullable=False)
    weight = Column(Float)
    details = Column(JSON, default={})
    
    signal = relationship("Signal", back_populates="evidence")

class Price(Base):
    __tablename__ = "prices"
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False)
    ts = Column(DateTime, nullable=False)
    open = Column(DECIMAL(10, 4))
    high = Column(DECIMAL(10, 4))
    low = Column(DECIMAL(10, 4))
    close = Column(DECIMAL(10, 4))
    volume = Column(Integer)
    
    ticker = relationship("Ticker", back_populates="prices")
    
    __table_args__ = (
        UniqueConstraint('ticker_id', 'ts'),
        Index('idx_prices_ticker_ts', ticker_id, ts.desc()),
    )

class Backtest(Base):
    __tablename__ = "backtests"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    params = Column(JSON, nullable=False)
    result = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_log"
    
    id = Column(Integer, primary_key=True)
    occurred_at = Column(DateTime, server_default=func.now(), nullable=False)
    actor = Column(String(100))
    action = Column(String(100), nullable=False)
    target_type = Column(String(50))
    target_id = Column(Integer)
    payload = Column(JSON, default={})
    
    __table_args__ = (
        Index('idx_audit_log_occurred', occurred_at.desc()),
        Index('idx_audit_log_target', target_type, target_id),
    )