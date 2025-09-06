import os
import json
from datetime import datetime
from typing import Dict, Any
from app.ingestion.canonicalize import canonicalize_url, extract_text, parse_date
from app import metrics
from app.ingestion.dedup import content_hash, is_near_duplicate
from app.services.snapshots import snapshot_service
import structlog

logger = structlog.get_logger()

DATA_DIR = os.path.join(os.getcwd(), 'data')
SNAP_DIR = os.path.join(DATA_DIR, 'snapshots')
os.makedirs(SNAP_DIR, exist_ok=True)

def save_document_from_raw(raw: Dict[str, Any]) -> Dict[str, Any]:
    # canonicalize
    url = canonicalize_url(raw.get('url'))
    html = raw.get('html') or ''
    text = raw.get('content') or (extract_text(html) if html else '')
    published = parse_date(raw.get('published'))

    if not text or len(text.split()) < 20:
        logger.info('document_too_short', url=url)
        metrics.inc_counter('ingest_fetch_total', {'result': 'too_short'})
        return None

    chash = content_hash(text)

    if is_near_duplicate(text):
        logger.info('near_duplicate', url=url, hash=chash)
        metrics.inc_counter('ingest_fetch_total', {'result': 'duplicate'})
        return None

    # save snapshot
    snapshot_path = snapshot_service.save_html_snapshot(url=url, html_content=html or f"<html><body><h1>{raw.get('title')}</h1></body></html>", source=raw.get('source'), published_at=published)

    doc = {
        'source': raw.get('source'),
        'url': url,
        'title': raw.get('title'),
        'published_at': published,
        'fetched_at': datetime.utcnow().isoformat(),
        'raw_text': text,
        'html_snapshot_path': snapshot_path,
        'content_hash': chash,
        'lang': 'en',
        'meta': raw.get('meta') or {}
    }

    # write to data/docs as json for MVP (later: write to DB)
    docs_dir = os.path.join(DATA_DIR, 'documents')
    os.makedirs(docs_dir, exist_ok=True)
    out_path = os.path.join(docs_dir, f"doc_{chash}.json")
    with open(out_path, 'w', encoding='utf8') as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    logger.info('saved_document', url=url, path=out_path)
    metrics.inc_counter('ingest_fetch_total', {'result': 'saved'})
    metrics.inc_counter('ingest_saved_total', {'source': raw.get('source') or 'unknown'})
    return doc
