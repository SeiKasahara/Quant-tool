#!/usr/bin/env python
import asyncio
import hashlib
import feedparser
import httpx
import trafilatura
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from prefect import flow, task
from sqlalchemy.orm import Session
import structlog
import json
import sys

from app.db.session import SessionLocal
from app.db.models import (
    Document, Entity, DocumentEntity, Event, 
    Signal, SignalEvidence, Ticker, Company, AuditLog
)
from app.core.config import settings
from app.nlp.pipeline import nlp_pipeline
from app.nlp.events import event_extractor
from app.nlp.novelty import novelty_calculator
from app.services.fuse import signal_fuser
from app.services.notifier import slack_notifier
from app.services.snapshots import snapshot_service
from app.flows.mock_articles import MOCK_ARTICLES
from app.ingestion.pipeline import save_document_from_raw

logger = structlog.get_logger()


@task
def fetch_feeds(feed_urls: List[str], use_mock: bool = False) -> List[Dict]:
    """Fetch articles from RSS feeds or use mock data"""
    
    if use_mock:
        logger.info("Using mock articles for testing")
        return MOCK_ARTICLES
    
    articles = []
    
    for feed_url in feed_urls:
        try:
            logger.info(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:10]:  # Limit to recent articles
                article = {
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "published": datetime.fromtimestamp(
                        entry.get("published_parsed", datetime.now().timetuple())[:6]
                    ) if entry.get("published_parsed") else datetime.now(),
                    "source": _extract_source_from_url(feed_url),
                    "content": None  # Will be fetched separately
                }
                articles.append(article)
                
        except Exception as e:
            logger.error(f"Failed to fetch feed {feed_url}: {e}")
            # Fall back to mock if feed fails
            if not articles:
                logger.info("Falling back to mock articles due to feed failure")
                return MOCK_ARTICLES
    
    return articles if articles else MOCK_ARTICLES

def _extract_source_from_url(url: str) -> str:
    """Extract source name from URL"""
    if "dj.com" in url or "dowjones" in url:
        return "DJ"
    elif "nasdaq.com" in url:
        return "NASDAQ"
    elif "reuters.com" in url:
        return "Reuters"
    elif "bloomberg.com" in url:
        return "Bloomberg"
    elif "wsj.com" in url:
        return "WSJ"
    else:
        return "Unknown"

@task
async def extract_article_content(article: Dict) -> Dict:
    """Extract full text content from article URL"""
    
    # If content already provided (mock), return as-is
    if article.get("content"):
        return article
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(article["url"], timeout=10.0)
            html_content = response.text
            
            # Extract text using trafilatura
            text = trafilatura.extract(html_content)
            
            if text:
                article["content"] = text
                article["html"] = html_content
            else:
                # Fallback to title if extraction fails
                article["content"] = article["title"]
                article["html"] = f"<html><body><h1>{article['title']}</h1></body></html>"
                
    except Exception as e:
        logger.error(f"Failed to extract content from {article['url']}: {e}")
        article["content"] = article["title"]
        article["html"] = f"<html><body><h1>{article['title']}</h1></body></html>"
    
    return article

def compute_content_hash(content: str) -> str:
    """Compute hash of content for deduplication"""
    return hashlib.sha256(content.encode()).hexdigest()

def ensure_ticker_exists(db: Session, ticker_symbol: str) -> Optional[Ticker]:
    """Ensure ticker exists in database"""
    
    ticker = db.query(Ticker).filter(Ticker.symbol == ticker_symbol).first()
    
    if not ticker:
        # Create company first
        company = Company(
            name=f"{ticker_symbol} Company",
            sector="Technology",  # Default, would be looked up in production
            industry="Software"
        )
        db.add(company)
        db.flush()
        
        # Create ticker
        ticker = Ticker(
            symbol=ticker_symbol,
            company_id=company.id,
            exchange="NASDAQ",  # Default
            is_active=True
        )
        db.add(ticker)
        db.flush()
    
    return ticker

@task
async def process_document(article: Dict, db: Session) -> Optional[Document]:
    """Process document through NLP pipeline and save to database"""
    
    content = article.get("content", "")
    if not content:
        return None
    
    # Check for duplicate
    content_hash = compute_content_hash(content)
    existing = db.query(Document).filter(Document.content_hash == content_hash).first()
    
    if existing:
        logger.info(f"Document already exists: {article['title']}")
        return existing
    
    # NLP processing
    nlp_result = nlp_pipeline.process_document(content)
    
    # Save HTML snapshot
    snapshot_path = snapshot_service.save_html_snapshot(
        url=article["url"],
        html_content=article.get("html", ""),
        source=article["source"],
        published_at=article["published"]
    )
    
    # Create document
    doc = Document(
        source=article["source"],
        url=article["url"],
        title=article["title"],
        published_at=article["published"],
        raw_text=content,
        html_snapshot_path=snapshot_path,
        content_hash=content_hash,
        lang="en",
        embedding=nlp_result["embedding"],
        sentiment=nlp_result["sentiment"],
        sentiment_score=nlp_result["sentiment_score"],
        meta={"tickers": nlp_result["tickers"]}
    )
    
    db.add(doc)
    db.flush()
    
    # Process entities
    for entity_data in nlp_result["entities"]:
        # Check if entity exists
        seen_entity_ids = set()
        entity = db.query(Entity).filter(Entity.name == entity_data["text"]).first()
        
        if not entity:
            # Try to link to ticker if it's an ORG
            ticker_id = None
            if entity_data["type"] == "ORG":
                for ticker_symbol in nlp_result["tickers"]:
                    ticker = ensure_ticker_exists(db, ticker_symbol)
                    if ticker:
                        ticker_id = ticker.id
                        break
            
            entity = Entity(
                name=entity_data["text"],
                entity_type=entity_data["type"],
                ticker_id=ticker_id
            )
            db.add(entity)
            db.flush()
        
        if entity.id in seen_entity_ids:
            # 如果这轮已经添加过，就直接把已有记录的 mentions +1
            existing_de = db.query(DocumentEntity).filter_by(
               document_id=doc.id, entity_id=entity.id
            ).first()
            if existing_de:
                existing_de.mentions = (existing_de.mentions or 0) + 1
            continue

        existing_de = db.query(DocumentEntity).filter_by(
            document_id=doc.id, entity_id=entity.id
        ).first()
        if existing_de:
            existing_de.mentions = (existing_de.mentions or 0) + 1
        else:
            db.add(DocumentEntity(
                document_id=doc.id,
                entity_id=entity.id,
                mentions=1,
                relevance_score=0.5
            ))
        seen_entity_ids.add(entity.id)

    # Extract events
    events = event_extractor.extract_events(
        content,
        doc.published_at,
        nlp_result["tickers"]
    )
    
    for event_data in events:
        event = Event(
            document_id=doc.id,
            event_time=event_data["event_time"],
            event_type=event_data["event_type"],
            headline=event_data["headline"],
            confidence_extraction=event_data["confidence_extraction"],
            affected_ticker=event_data["affected_ticker"],
            payload=event_data["payload"]
        )
        db.add(event)
    
    db.flush()
    
    # Log audit
    audit = AuditLog(
        actor="ingest_flow",
        action="ingest_doc",
        target_type="document",
        target_id=doc.id,
        payload={"url": article["url"], "source": article["source"]}
    )
    db.add(audit)
    
    return doc

@task
async def generate_signals(doc: Document, db: Session) -> List[Signal]:
    """Generate signals from document and events"""
    
    signals = []
    
    # Get events for this document
    events = db.query(Event).filter(Event.document_id == doc.id).all()
    
    if not events and doc.sentiment_score > 0.8:
        # Create sentiment-based signal if no events but strong sentiment
        events = [{
            "event_type": "sentiment_signal",
            "affected_ticker": doc.meta.get("tickers", [""])[0] if doc.meta.get("tickers") else None,
            "confidence_extraction": doc.sentiment_score
        }]
    
    for event in events:
        if isinstance(event, Event):
            ticker_symbol = event.affected_ticker
            event_type = event.event_type
            evt_confidence = event.confidence_extraction
        else:
            ticker_symbol = event.get("affected_ticker")
            event_type = event.get("event_type")
            evt_confidence = event.get("confidence_extraction", 0.5)
        
        if not ticker_symbol:
            continue
        
        # Ensure ticker exists
        ticker = ensure_ticker_exists(db, ticker_symbol)
        if not ticker:
            continue
        
        # Calculate novelty
        novelty = novelty_calculator.calculate_novelty(
            text=doc.raw_text,
            ticker=ticker_symbol,
            published_at=doc.published_at,
            db=db,
            embedding=doc.embedding
        )
        
        # Calculate buzz score
        buzz_score = novelty_calculator.calculate_buzz_score(
            ticker=ticker_symbol,
            published_at=doc.published_at,
            db=db
        )
        
        # Calculate confidence
        confidence, base_score, components = signal_fuser.calculate_confidence(
            source=doc.source,
            novelty=novelty,
            event_type=event_type,
            buzz_score=buzz_score,
            signal_time=doc.published_at,
            current_time=datetime.now()
        )
        
        # Determine direction
        direction = signal_fuser.determine_signal_direction(
            event_type=event_type,
            sentiment=doc.sentiment,
            sentiment_score=doc.sentiment_score
        )
        
        # Generate label
        label = signal_fuser.generate_signal_label(
            event_type=event_type,
            sentiment=doc.sentiment,
            confidence=confidence
        )
        
        # Check if should alert
        should_alert, alert_reason = signal_fuser.should_alert(
            confidence=confidence,
            source_weight=components["source_weight"],
            novelty=novelty,
            has_second_source=False  # Would check for multiple sources in production
        )
        
        # Create signal
        signal = Signal(
            ticker_id=ticker.id,
            signal_time=doc.published_at,
            base_score=base_score,
            confidence=confidence,
            direction=direction,
            label=label,
            decay_seconds=86400,
            meta={
                "components": components,
                "alert_reason": alert_reason,
                "requires_second_source": not should_alert or alert_reason == "Needs second source confirmation"
            }
        )
        
        db.add(signal)
        db.flush()
        
        # Add evidence
        evidence = SignalEvidence(
            signal_id=signal.id,
            kind="document",
            ref_id=doc.id,
            weight=1.0,
            details={
                "title": doc.title,
                "url": doc.url,
                "sentiment": doc.sentiment,
                "novelty": novelty
            }
        )
        db.add(evidence)
        
        if isinstance(event, Event):
            event_evidence = SignalEvidence(
                signal_id=signal.id,
                kind="event",
                ref_id=event.id,
                weight=evt_confidence,
                details={
                    "event_type": event_type,
                    "headline": event.headline
                }
            )
            db.add(event_evidence)
        
        # Log audit
        audit = AuditLog(
            actor="ingest_flow",
            action="create_signal",
            target_type="signal",
            target_id=signal.id,
            payload={
                "ticker": ticker_symbol,
                "confidence": confidence,
                "label": label
            }
        )
        db.add(audit)
        
        signals.append(signal)
        
        # Send alert if needed
        if should_alert:
            sources = [{
                "title": doc.title,
                "url": doc.url,
                "source": doc.source
            }]
            
            evidence_data = {
                "novelty": novelty,
                "event_type": event_type,
                "sentiment": doc.sentiment
            }
            
            asyncio.create_task(
                slack_notifier.send_signal_alert(
                    ticker=ticker_symbol,
                    signal_label=label,
                    confidence=confidence,
                    direction=direction,
                    sources=sources,
                    signal_time=doc.published_at,
                    evidence=evidence_data
                )
            )
            
            # Log alert
            alert_audit = AuditLog(
                actor="ingest_flow",
                action="send_alert",
                target_type="signal",
                target_id=signal.id,
                payload={
                    "channel": "slack",
                    "reason": alert_reason
                }
            )
            db.add(alert_audit)
    
    return signals

@flow(name="ingest_flow")
async def ingest_flow(use_mock: bool = False):
    """Main ingestion flow"""
    
    logger.info("Starting ingestion flow", use_mock=use_mock)
    
    # Initialize NLP pipeline
    nlp_pipeline.initialize()
    
    # Get feed URLs
    feed_urls = settings.news_feeds_list if not use_mock else []
    
    # Fetch articles
    articles = fetch_feeds(feed_urls, use_mock=use_mock)
    logger.info(f"Fetched {len(articles)} articles")
    
    # Process each article
    db = None
    try:
        processed_docs = []
        all_signals = []
        
        for article in articles:
            try:
                # Extract content
                article = await extract_article_content(article)
                # If running in mock mode without DB, save documents to data/ via pipeline
                if use_mock:
                    saved = save_document_from_raw(article)
                    if saved:
                        processed_docs.append(saved)
                        logger.info('Processed mock document', title=saved.get('title'), url=saved.get('url'))
                    continue

                # Process document (DB path)
                db = SessionLocal()
                doc = await process_document(article, db)
                
                if doc:
                    processed_docs.append(doc)
                    
                    # Generate signals
                    signals = await generate_signals(doc, db)
                    all_signals.extend(signals)
                    
                    logger.info(
                        f"Processed document: {doc.title}",
                        doc_id=doc.id,
                        signals_generated=len(signals)
                    )

            except Exception as e:
                logger.error(f"Error processing article: {e}", article=article.get("title"))
                db.rollback()  # <<< 关键：回滚当前事务
                continue

        # Commit all changes
        db.commit()
        
        logger.info(
            "Ingestion flow completed",
            documents_processed=len(processed_docs),
            signals_generated=len(all_signals)
        )
        
        return {
            "documents": len(processed_docs),
            "signals": len(all_signals)
        }
        
    finally:
        db.close()

if __name__ == "__main__":
    # Support running directly for testing
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--mock", action="store_true", help="Use mock data")
    args = parser.parse_args()
    
    if args.once:
        asyncio.run(ingest_flow(use_mock=True))  # Always use mock for initial run
    else:
        # Would set up Prefect deployment here
        print("Use --once flag to run ingestion once")