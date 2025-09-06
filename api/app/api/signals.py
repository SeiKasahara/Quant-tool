from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel

from app.core.deps import get_db_session
from app.db.models import Signal, SignalEvidence, Ticker, Document

router = APIRouter()

class SignalSource(BaseModel):
    kind: str
    id: int
    title: str

class SignalResponse(BaseModel):
    id: int
    ticker: str
    signal_time: datetime
    confidence: float
    base_score: float
    label: str
    direction: str
    sources: List[SignalSource]

class SignalsListResponse(BaseModel):
    items: List[SignalResponse]
    total: int

@router.get("", response_model=SignalsListResponse)
async def get_signals(
    q: Optional[str] = Query(None, description="Search query"),
    min_confidence: Optional[float] = Query(0.6, ge=0, le=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session)
):
    """Get signals with filtering"""
    
    # Build query
    query = db.query(Signal).join(Ticker).options(
        joinedload(Signal.ticker),
        joinedload(Signal.evidence)
    )
    
    # Apply filters
    filters = []
    
    if min_confidence is not None:
        filters.append(Signal.confidence >= min_confidence)
    
    if date_from:
        filters.append(Signal.signal_time >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        filters.append(Signal.signal_time <= datetime.combine(date_to, datetime.max.time()))
    
    if q:
        # Search in ticker symbol or signal label
        search_filter = or_(
            Ticker.symbol.ilike(f"%{q}%"),
            Signal.label.ilike(f"%{q}%")
        )
        filters.append(search_filter)
    
    if filters:
        query = query.filter(and_(*filters))
    
    # Order by signal time descending
    query = query.order_by(Signal.signal_time.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    signals = query.offset(offset).limit(limit).all()
    
    # Format response
    items = []
    for signal in signals:
        # Get sources from evidence
        sources = []
        for evidence in signal.evidence:
            if evidence.kind == "document":
                # Get document details
                doc = db.query(Document).filter(Document.id == evidence.ref_id).first()
                if doc:
                    sources.append(SignalSource(
                        kind="document",
                        id=doc.id,
                        title=doc.title or "Unknown"
                    ))
        
        items.append(SignalResponse(
            id=signal.id,
            ticker=signal.ticker.symbol,
            signal_time=signal.signal_time,
            confidence=signal.confidence,
            base_score=signal.base_score,
            label=signal.label,
            direction=signal.direction,
            sources=sources
        ))
    
    return SignalsListResponse(items=items, total=total)

@router.get("/{signal_id}")
async def get_signal(
    signal_id: int,
    db: Session = Depends(get_db_session)
):
    """Get single signal with full details"""
    
    signal = db.query(Signal).options(
        joinedload(Signal.ticker),
        joinedload(Signal.evidence)
    ).filter(Signal.id == signal_id).first()
    
    if not signal:
        return {"error": "Signal not found"}
    
    # Get all evidence details
    evidence_details = []
    for evidence in signal.evidence:
        details = {
            "kind": evidence.kind,
            "weight": evidence.weight,
            "details": evidence.details
        }
        
        if evidence.kind == "document":
            doc = db.query(Document).filter(Document.id == evidence.ref_id).first()
            if doc:
                details["document"] = {
                    "id": doc.id,
                    "title": doc.title,
                    "url": doc.url,
                    "source": doc.source,
                    "published_at": doc.published_at
                }
        
        evidence_details.append(details)
    
    return {
        "id": signal.id,
        "ticker": signal.ticker.symbol,
        "signal_time": signal.signal_time,
        "confidence": signal.confidence,
        "base_score": signal.base_score,
        "label": signal.label,
        "direction": signal.direction,
        "decay_seconds": signal.decay_seconds,
        "meta": signal.meta,
        "evidence": evidence_details,
        "created_at": signal.created_at
    }