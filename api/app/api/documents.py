from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.core.deps import get_db_session
from app.db.models import Document, DocumentEntity, Entity, Event

router = APIRouter()

@router.get("/{document_id}")
async def get_document(
    document_id: int,
    db: Session = Depends(get_db_session)
):
    """Get document details including entities and events"""
    
    # Get document with related data
    doc = db.query(Document).options(
        joinedload(Document.entities).joinedload(DocumentEntity.entity),
        joinedload(Document.events)
    ).filter(Document.id == document_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Format entities
    entities = []
    for doc_entity in doc.entities:
        entities.append({
            "id": doc_entity.entity.id,
            "name": doc_entity.entity.name,
            "type": doc_entity.entity.entity_type,
            "mentions": doc_entity.mentions,
            "relevance_score": doc_entity.relevance_score
        })
    
    # Format events
    events = []
    for event in doc.events:
        events.append({
            "id": event.id,
            "event_type": event.event_type,
            "event_time": event.event_time,
            "headline": event.headline,
            "confidence": event.confidence_extraction,
            "affected_ticker": event.affected_ticker,
            "payload": event.payload
        })
    
    # Generate excerpt (first 800 characters)
    excerpt = doc.raw_text[:800] if doc.raw_text else ""
    if len(doc.raw_text or "") > 800:
        excerpt += "..."
    
    return {
        "id": doc.id,
        "source": doc.source,
        "url": doc.url,
        "title": doc.title,
        "published_at": doc.published_at,
        "fetched_at": doc.fetched_at,
        "excerpt": excerpt,
        "full_text": doc.raw_text,
        "html_snapshot_path": doc.html_snapshot_path,
        "lang": doc.lang,
        "sentiment": doc.sentiment,
        "sentiment_score": doc.sentiment_score,
        "entities": entities,
        "events": events,
        "meta": doc.meta,
        "created_at": doc.created_at
    }

@router.get("/{document_id}/snapshot")
async def get_document_snapshot(
    document_id: int,
    db: Session = Depends(get_db_session)
):
    """Get HTML snapshot path for document"""
    
    doc = db.query(Document).filter(Document.id == document_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if not doc.html_snapshot_path:
        raise HTTPException(status_code=404, detail="No snapshot available")
    
    return {
        "document_id": doc.id,
        "snapshot_path": doc.html_snapshot_path,
        "url": f"/data/{doc.html_snapshot_path}"
    }