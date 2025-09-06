import os
import asyncio
import json
from typing import AsyncIterator, Dict, Any, Optional

_subscribers = set()
_redis = None
_redis_lock = asyncio.Lock()
CHANNEL_NAME = os.getenv('INGEST_EVENTS_CHANNEL', 'ingest_events')

async def _get_redis():
    global _redis
    if _redis is not None:
        return _redis
    async with _redis_lock:
        if _redis is not None:
            return _redis
        try:
            import redis.asyncio as aioredis
            url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
            _redis = aioredis.from_url(url, decode_responses=True)
        except Exception:
            _redis = None
        return _redis

def _push_inmemory(event: Dict[str, Any]):
    # push event to all subscribers (non-blocking)
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass

def publish_event(event: Dict[str, Any]):
    # synchronous wrapper: schedule async publish to redis, and push to in-memory
    try:
        _push_inmemory(event)
    except Exception:
        pass

    async def _pub():
        r = await _get_redis()
        if not r:
            return
        try:
            await r.publish(CHANNEL_NAME, json.dumps(event))
        except Exception:
            # non-fatal
            return

    # schedule background publish
    try:
        asyncio.get_event_loop().create_task(_pub())
    except RuntimeError:
        # no running loop, ignore
        pass

async def subscribe() -> AsyncIterator[Dict[str, Any]]:
    """Async generator yielding events. Prefers Redis pub/sub; falls back to in-memory queue."""
    # Try Redis first
    r = await _get_redis()
    if r:
        pubsub = r.pubsub()
        await pubsub.subscribe(CHANNEL_NAME)
        try:
            while True:
                # get_message with timeout to allow cancellation
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and 'data' in msg and msg['data'] is not None:
                    data = msg['data']
                    if isinstance(data, (bytes, bytearray)):
                        data = data.decode('utf8')
                    try:
                        yield json.loads(data)
                    except Exception:
                        yield {"type": "raw", "data": data}
                else:
                    # yield control to allow cancellation and check in-memory queue as well
                    await asyncio.sleep(0)
        finally:
            try:
                await pubsub.unsubscribe(CHANNEL_NAME)
                await pubsub.close()
            except Exception:
                pass

    # Fallback: in-memory queue
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.add(q)
    try:
        while True:
            ev = await q.get()
            yield ev
    finally:
        _subscribers.discard(q)

