from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.services import ingest_events
import uuid
import asyncio

router = APIRouter()

class SourceCreate(BaseModel):
    name: str
    type: str
    params: Dict[str, Any] = {}
    schedule: Optional[str] = None
    rate_limit: Optional[Dict[str, Any]] = None
    enabled: bool = True

# In-memory store for demo
_SOURCES: Dict[str, Dict[str, Any]] = {}

@router.get("/sources")
def list_sources():
    return list(_SOURCES.values())

@router.post("/sources")
def create_source(payload: SourceCreate):
    sid = str(uuid.uuid4())
    obj = payload.dict()
    obj.update({"id": sid, "last_run": None, "next_run": None})
    _SOURCES[sid] = obj
    return obj

@router.get("/sources/{source_id}")
def get_source(source_id: str):
    s = _SOURCES.get(source_id)
    if not s: raise HTTPException(404)
    return s

@router.patch("/sources/{source_id}")
def update_source(source_id: str, payload: Dict[str, Any]):
    s = _SOURCES.get(source_id)
    if not s: raise HTTPException(404)
    s.update(payload)
    return s

@router.delete("/sources/{source_id}")
def delete_source(source_id: str):
    if source_id in _SOURCES:
        del _SOURCES[source_id]
        return {"ok": True}
    raise HTTPException(404)

@router.post("/sources/test")
def test_source_payload(payload: Dict[str, Any]):
    # Accept either an object payload or shorthand; return robots check + 3 previews
    previews = [
        {"title": "Test article 1", "published": "2025-09-07T10:00:00Z", "excerpt": "Preview text 1..."},
        {"title": "Test article 2", "published": "2025-09-07T11:00:00Z", "excerpt": "Preview text 2..."},
        {"title": "Test article 3", "published": "2025-09-07T12:00:00Z", "excerpt": "Preview text 3..."}
    ]
    return {"robots_allowed": True, "crawl_delay": 0, "previews": previews}

@router.post("/sources/{source_id}/test")
def test_source(source_id: str):
    if source_id not in _SOURCES: raise HTTPException(404)
    return test_source_payload(_SOURCES[source_id])

async def _demo_run_publisher(source_id: str):
    run_id = str(uuid.uuid4())
    ingest_events.publish_event({"type": "run_started", "run_id": run_id, "source_id": source_id, "source_name": _SOURCES.get(source_id, {}).get('name'), "started_at": "now"})
    # simulate fetches
    for i in range(3):
        await asyncio.sleep(1)
        ingest_events.publish_event({"type": "fetch_progress", "run_id": run_id, "url": f"http://example.com/{i}", "http_status": 200, "bytes": 1024+i, "latency_ms": 120+i*10})
        await asyncio.sleep(0.2)
        ingest_events.publish_event({"type": "normalized", "run_id": run_id, "hash": f"h{i}", "published_at": "now"})
    ingest_events.publish_event({"type": "run_finished", "run_id": run_id, "finished_at": "now", "stats": {"fetched": 3, "normalized": 3}})

@router.post("/sources/{source_id}/run")
def run_source(source_id: str, background: BackgroundTasks):
    if source_id not in _SOURCES: raise HTTPException(404)
    def _schedule():
        try:
            asyncio.get_event_loop().create_task(_demo_run_publisher(source_id))
        except RuntimeError:
            # no loop; spawn a new one briefly
            asyncio.run(_demo_run_publisher(source_id))
    background.add_task(_schedule)
    return {"ok": True, "message": "Run scheduled"}

@router.post("/sources/{source_id}/backfill")
def backfill_source(source_id: str, params: Dict[str, Any]):
    if source_id not in _SOURCES: raise HTTPException(404)
    # For demo, just return accepted
    return {"ok": True, "params": params}

@router.post("/import/url")
def import_url(payload: Dict[str, Any]):
    url = payload.get('url')
    dry = payload.get('dry_run', True)
    # return a simple preview
    preview = {"title": "Imported Title", "published": "2025-09-07T10:00:00Z", "excerpt": "Extracted excerpt from URL...", "url": url}
    return {"dry_run": dry, "preview": preview}
